"""Network Troubleshooting Toolkit — Sessions 1 + 2 + 3.

Session 1: three core checks, in layer order, plus a plain-English
verdict:
  1. Gateway (your router) — ping
  2. Internet — ping 8.8.8.8 and 1.1.1.1
  3. DNS — resolve google.com to an IP address

Session 2: find *where* a connection breaks, not just *that* it breaks:
  4. Traceroute to 8.8.8.8 — each hop, flag where replies stop
  5. TCP port checks — 80 / 443 on google.com, 53 on 8.8.8.8
  6. Wi-Fi signal — `netsh wlan show interfaces` (Windows only)

  Fix from Session 2: a hop timing out in the *middle* of a
  traceroute is normal — some ISP routers ignore traceroute, but
  traffic still passes through. Only the *last* hops timing out
  means the route stopped. The old code counted any timeout as a
  stop, so it wrongly flagged a successful 13-hop route.

Session 3: a run leaves a report a tech could hand to a user or ISP:
  - Each run is saved to reports/ as a timestamped .txt and .json
  - Runs are stored in SQLite (runs.db) so you can compare runs
  - `python diagnose.py --last` shows the previous run next to
    the current one

Session 4: interactive menu, so the tool works on someone else's
problem, not just your network:
  - `python diagnose.py --menu` opens the menu
  - 1) Full diagnosis  2) Ping a host  3) Check a port
    4) DNS lookup  5) Last run  6) Quit
  - Custom targets are typed in — any host, any port, any domain.
    Bad input (empty host, port out of range, unknown host) prints
    a clear message instead of crashing.

Run it:
    python diagnose.py            # full diagnosis, saves a report
    python diagnose.py --last     # show the last two saved runs
    python diagnose.py --no-save  # run without saving
    python diagnose.py --menu     # interactive menu
"""

import json
import platform
import re
import socket
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = HERE / "runs.db"
REPORTS_DIR = HERE / "reports"

FALLBACK_GATEWAY = "192.168.0.1"
INTERNET_HOSTS = ["8.8.8.8", "1.1.1.1"]
DNS_TEST_DOMAIN = "google.com"
TRACE_TARGET = "8.8.8.8"
# (label, host, port)
PORT_CHECKS = [
    ("Web (HTTP)", "google.com", 80),
    ("Web (HTTPS)", "google.com", 443),
    ("DNS", "8.8.8.8", 53),
]


def find_gateway():
    """Auto-detect the default gateway, or fall back to 192.168.0.1.

    Windows: parse `ipconfig` for "Default Gateway".
    Other systems: try `ip route`, then fall back.
    """
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(
                ["ipconfig"], capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                if "Default Gateway" in line and ":" in line:
                    gateway = line.split(":", 1)[1].strip()
                    if gateway:
                        return gateway
        else:
            result = subprocess.run(
                ["ip", "route"], capture_output=True, text=True, timeout=10
            )
            match = re.search(r"default via (\S+)", result.stdout)
            if match:
                return match.group(1)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return FALLBACK_GATEWAY


def ping(host):
    """Ping a host once. Returns (up: bool, latency_ms: float | None)."""
    if platform.system() == "Windows":
        cmd = ["ping", "-n", "1", "-w", "1000", host]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, None
    if result.returncode != 0:
        return False, None
    text = result.stdout + result.stderr
    match = re.search(r"time[=<]([\d.]+)\s*ms", text)
    return True, float(match.group(1)) if match else None


def check_dns(domain):
    """Try to resolve a domain name. Returns (ok: bool, ip: str | None)."""
    try:
        return True, socket.gethostbyname(domain)
    except OSError:
        return False, None


def check_port(host, port, timeout=3):
    """Try a TCP connect to host:port. Returns True if it connects."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def traceroute(host, max_hops=15):
    """Trace the route to a host.

    Returns a list of (hop, ip_or_None, latency_ms_or_None).
    A hop with no IP means it timed out — replies stopped there.
    Returns [] if the traceroute command itself failed.
    """
    if platform.system() == "Windows":
        cmd = ["tracert", "-d", "-h", str(max_hops), "-w", "1000", host]
    else:
        cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", "1", host]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    hops = []
    for line in (result.stdout + result.stderr).splitlines():
        match = re.match(r"\s*(\d+)\s+(.*)", line)
        if not match:
            continue
        hop = int(match.group(1))
        rest = match.group(2)
        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", rest)
        times = re.findall(r"(\d+(?:\.\d+)?)\s*ms", rest)
        latency = float(times[0]) if times else None
        hops.append((hop, ip_match.group(1) if ip_match else None, latency))
    return hops


def wifi_info():
    """Wi-Fi details on Windows, or None if not on Wi-Fi / not Windows.

    Returns {"ssid": str, "signal": int, "channel": str} — signal is
    a percentage. Parses `netsh wlan show interfaces`.
    """
    if platform.system() != "Windows":
        return None
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    info = {}
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "ssid":
            info["ssid"] = value
        elif key == "signal":
            match = re.search(r"(\d+)", value)
            if match:
                info["signal"] = int(match.group(1))
        elif key == "channel":
            info["channel"] = value
    if "ssid" not in info:
        return None
    return info


def verdict(gateway_up, internet_up, dns_ok):
    """One-line plain-English verdict, from the layer that failed first."""
    if not gateway_up:
        return (
            "Local network problem — can't reach your router. "
            "Check Wi-Fi / cable, then restart the router."
        )
    if not internet_up:
        return (
            "Internet is down past your router — your home network is "
            "fine, the fault is with your ISP. Restart the modem/router, "
            "then call your ISP if it stays down."
        )
    if not dns_ok:
        return (
            "DNS problem — the internet works, but names don't resolve. "
            "Try changing DNS to 8.8.8.8 / 1.1.1.1."
        )
    return "All checks passed — your connection looks healthy."


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            gateway TEXT NOT NULL,
            gateway_up INTEGER NOT NULL,
            gateway_ms REAL,
            internet_ms_8888 REAL,
            internet_ms_1111 REAL,
            dns_ok INTEGER NOT NULL,
            dns_ip TEXT,
            verdict TEXT NOT NULL,
            wifi_ssid TEXT,
            wifi_signal INTEGER,
            hops_reached INTEGER,
            target_reached INTEGER NOT NULL,
            raw_json TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


def save_run(conn, results):
    """Save a run to runs.db and to reports/<timestamp>.txt + .json."""
    conn.execute(
        "INSERT INTO runs (ts, gateway, gateway_up, gateway_ms,"
        " internet_ms_8888, internet_ms_1111, dns_ok, dns_ip, verdict,"
        " wifi_ssid, wifi_signal, hops_reached, target_reached, raw_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            results["ts"],
            results["gateway"],
            int(results["gateway_up"]),
            results["gateway_ms"],
            results["internet_ms"].get("8.8.8.8"),
            results["internet_ms"].get("1.1.1.1"),
            int(results["dns_ok"]),
            results["dns_ip"],
            results["verdict"],
            (results["wifi"] or {}).get("ssid"),
            (results["wifi"] or {}).get("signal"),
            len([h for h in results["hops"] if h[1] is not None]),
            int(bool(results["hops"] and results["hops"][-1][1] == TRACE_TARGET)),
            json.dumps(results, default=str),
        ),
    )
    conn.commit()

    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = results["ts"].replace(":", "").replace(" ", "_")
    text_path = REPORTS_DIR / f"{stamp}.txt"
    json_path = REPORTS_DIR / f"{stamp}.json"
    text_path.write_text(results["report_text"], encoding="utf-8")
    json_path.write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )
    return text_path, json_path


def show_last(conn):
    """Print the last two saved runs, side by side, newest first."""
    rows = conn.execute(
        "SELECT ts, gateway_ms, internet_ms_8888, internet_ms_1111,"
        " dns_ok, wifi_signal, verdict FROM runs ORDER BY id DESC LIMIT 2"
    ).fetchall()
    if not rows:
        print("No saved runs yet. Run `python diagnose.py` first.")
        return
    print("Last saved runs (newest first):")
    print()
    for ts, gw_ms, ms8888, ms1111, dns_ok, wifi_signal, verdict_text in rows:
        print(f"  {ts}")
        print(f"    Gateway: {gw_ms if gw_ms is not None else '-'} ms")
        print(f"    Internet 8.8.8.8: {ms8888 if ms8888 is not None else '-'} ms")
        print(f"    Internet 1.1.1.1: {ms1111 if ms1111 is not None else '-'} ms")
        print(f"    DNS: {'OK' if dns_ok else 'FAIL'}")
        print(f"    Wi-Fi signal: {wifi_signal if wifi_signal is not None else '-'}%")
        print(f"    Verdict: {verdict_text}")
        print()
    if len(rows) == 2:
        # Simple comparison: did the verdict change?
        if rows[0][6] != rows[1][6]:
            print("Verdict changed since the previous run.")
        else:
            print("Verdict is the same as the previous run.")


def run_diagnosis(save=True):
    """Run the full diagnosis (Sessions 1-3) and print the report."""
    gateway = find_gateway()
    now = datetime.now().isoformat(timespec="seconds")

    gateway_up, gateway_ms = ping(gateway)
    internet_results = [ping(host) for host in INTERNET_HOSTS]
    internet_up = any(up for up, _ in internet_results)
    internet_ms = {
        host: latency for host, (up, latency) in zip(INTERNET_HOSTS, internet_results)
    }
    dns_ok, dns_ip = check_dns(DNS_TEST_DOMAIN)
    hops = traceroute(TRACE_TARGET)
    port_results = {
        (label, port): check_port(host, port)
        for label, host, port in PORT_CHECKS
    }
    wifi = wifi_info()
    verdict_text = verdict(gateway_up, internet_up, dns_ok)

    # Session 2 fix: only trailing timeouts mean the route stopped.
    # A timeout in the middle, with later hops answering, is normal.
    trailing_timeouts = 0
    for _hop, ip, _lat in reversed(hops):
        if ip is None:
            trailing_timeouts += 1
        else:
            break
    answered = [h for h in hops if h[1] is not None]
    stopped_at = answered[-1][0] if (trailing_timeouts and answered) else None
    middle_timeouts = [
        hop for hop, ip, _lat in hops[:-trailing_timeouts or None]
        if ip is None
    ] if hops else []

    notes = []
    if wifi is not None and wifi.get("signal") is not None:
        if wifi["signal"] < 50:
            notes.append(
                f"Wi-Fi signal is weak ({wifi['signal']}%) — move closer "
                "to the router or check for interference."
            )
        elif wifi["signal"] < 70:
            notes.append(
                f"Wi-Fi signal is only {wifi['signal']}% — usable, but "
                "worth checking if the connection feels slow."
            )
    if middle_timeouts:
        notes.append(
            f"Hop {middle_timeouts[0]} didn't answer traceroute, but "
            "traffic still got through — some ISP routers ignore "
            "traceroute, so that's not a fault."
        )
    if stopped_at is not None:
        notes.append(
            f"Traceroute stopped answering after hop {stopped_at} — "
            "the fault is past that hop (usually ISP side)."
        )
    if internet_up and not port_results.get(("Web (HTTPS)", 443), True):
        notes.append(
            "Ping works but HTTPS port 443 is closed — web browsing "
            "will fail even though the internet is up."
        )

    # Build the printable report (also saved to reports/ in Session 3).
    lines = []
    lines.append("Network Troubleshooting Toolkit — Sessions 1 + 2 + 3 + 4")
    lines.append(f"Gateway detected: {gateway}")
    lines.append(f"Run at: {now}")
    lines.append("")
    lines.append(f"{'Check':<28} {'Target':<16} {'Result':<8} Latency")
    lines.append("-" * 65)
    lines.append(
        f"{'Gateway (router)':<28} {gateway:<16} "
        f"{'UP' if gateway_up else 'DOWN':<8} "
        f"{f'{gateway_ms:.1f} ms' if gateway_ms is not None else '-'}"
    )
    for host, (up, latency) in zip(INTERNET_HOSTS, internet_results):
        lines.append(
            f"{'Internet':<28} {host:<16} "
            f"{'UP' if up else 'DOWN':<8} "
            f"{f'{latency:.1f} ms' if latency is not None else '-'}"
        )
    lines.append(
        f"{'DNS lookup':<28} {DNS_TEST_DOMAIN:<16} "
        f"{'OK' if dns_ok else 'FAIL':<8} {dns_ip or '-'}"
    )
    lines.append("")
    lines.append(f"Traceroute to {TRACE_TARGET} (each hop):")
    if not hops:
        lines.append("  Traceroute unavailable — command failed.")
    else:
        for hop, ip, latency in hops:
            if ip is None:
                lines.append(f"  Hop {hop:<3} * * *  (timed out)")
            else:
                latency_text = f"{latency:.1f} ms" if latency is not None else "-"
                lines.append(f"  Hop {hop:<3} {ip:<16} {latency_text}")
    lines.append("")
    lines.append("Port checks (TCP connect):")
    for label, host, port in PORT_CHECKS:
        up = port_results[(label, port)]
        lines.append(f"  {label:<14} {host}:{port:<6} {'OPEN' if up else 'CLOSED'}")
    lines.append("")
    if wifi is None:
        lines.append("Wi-Fi: not connected via Wi-Fi (or not Windows).")
    else:
        lines.append(
            f"Wi-Fi: {wifi.get('ssid', '?')}  "
            f"signal {wifi.get('signal', '?')}%  "
            f"channel {wifi.get('channel', '?')}"
        )
    lines.append("")
    lines.append(f"Verdict: {verdict_text}")
    for note in notes:
        lines.append(f"Note: {note}")
    report_text = "\n".join(lines)
    print(report_text)

    results = {
        "ts": now,
        "gateway": gateway,
        "gateway_up": gateway_up,
        "gateway_ms": gateway_ms,
        "internet_up": internet_up,
        "internet_ms": internet_ms,
        "dns_ok": dns_ok,
        "dns_ip": dns_ip,
        "hops": hops,
        "ports": {f"{label}:{port}": up for (label, port), up in port_results.items()},
        "wifi": wifi,
        "verdict": verdict_text,
        "notes": notes,
        "report_text": report_text,
    }

    if save:
        conn = init_db()
        try:
            text_path, json_path = save_run(conn, results)
            print()
            print(f"Saved report: {text_path.name}")
            print(f"Saved data:   {json_path.name}")
            print("Saved to history (runs.db) — use --last to compare runs.")
        finally:
            conn.close()


def ask_host(prompt):
    """Ask for a host/domain. Returns None if the input was empty."""
    host = input(prompt).strip()
    if not host:
        print("No host entered — nothing to check.")
        return None
    return host


def menu_ping():
    host = ask_host("Host to ping (e.g. google.com or 8.8.8.8): ")
    if host is None:
        return
    up, latency = ping(host)
    if up:
        latency_text = f"{latency:.1f} ms" if latency is not None else "-"
        print(f"{host} is UP — {latency_text}")
    else:
        print(f"{host} is DOWN or didn't answer — check the name/IP and try again.")


def menu_port():
    host = ask_host("Host to check (e.g. google.com): ")
    if host is None:
        return
    port_text = input("Port to check (1-65535, e.g. 443): ").strip()
    try:
        port = int(port_text)
    except ValueError:
        print(f"'{port_text}' isn't a number — enter a port like 80 or 443.")
        return
    if not 1 <= port <= 65535:
        print(f"Port {port} is out of range — ports go from 1 to 65535.")
        return
    if check_port(host, port):
        print(f"{host}:{port} is OPEN.")
    else:
        print(f"{host}:{port} is CLOSED or didn't answer.")


def menu_dns():
    domain = ask_host("Domain to look up (e.g. google.com): ")
    if domain is None:
        return
    ok, ip = check_dns(domain)
    if ok:
        print(f"{domain} resolves to {ip}.")
    else:
        print(f"Couldn't resolve {domain} — check the spelling, or DNS may be down.")


def run_menu():
    """Interactive menu (Session 4). Loops until the user quits."""
    while True:
        print()
        print("Network Troubleshooting Toolkit — Menu")
        print("  1) Full diagnosis")
        print("  2) Ping a host")
        print("  3) Check a port")
        print("  4) DNS lookup")
        print("  5) Last run")
        print("  6) Quit")
        try:
            choice = input("Choose 1-6: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return
        print()
        if choice == "1":
            run_diagnosis(save=True)
        elif choice == "2":
            menu_ping()
        elif choice == "3":
            menu_port()
        elif choice == "4":
            menu_dns()
        elif choice == "5":
            conn = init_db()
            try:
                show_last(conn)
            finally:
                conn.close()
        elif choice == "6":
            print("Goodbye.")
            return
        else:
            print(f"'{choice}' isn't an option — choose 1 to 6.")


def main():
    if "--menu" in sys.argv:
        run_menu()
        return
    if "--last" in sys.argv:
        conn = init_db()
        try:
            show_last(conn)
        finally:
            conn.close()
        return
    run_diagnosis(save="--no-save" not in sys.argv)


if __name__ == "__main__":
    main()
