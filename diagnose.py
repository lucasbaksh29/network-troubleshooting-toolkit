"""Network Troubleshooting Toolkit — Session 1.

Runs the three core checks, in layer order, and prints a
plain-English verdict:

  1. Gateway (your router) — ping
  2. Internet — ping 8.8.8.8 and 1.1.1.1
  3. DNS — resolve google.com to an IP address

Order matters: if the gateway is down, the later checks can't
tell you anything, so the verdict stops there.

Run it:
    python diagnose.py
"""

import platform
import re
import socket
import subprocess

FALLBACK_GATEWAY = "192.168.0.1"
INTERNET_HOSTS = ["8.8.8.8", "1.1.1.1"]
DNS_TEST_DOMAIN = "google.com"


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


def main():
    gateway = find_gateway()

    print("Network Troubleshooting Toolkit — Session 1")
    print(f"Gateway detected: {gateway}")
    print()
    print(f"{'Check':<28} {'Target':<16} {'Result':<8} Latency")
    print("-" * 65)

    gateway_up, gateway_ms = ping(gateway)
    print(
        f"{'Gateway (router)':<28} {gateway:<16} "
        f"{'UP' if gateway_up else 'DOWN':<8} "
        f"{f'{gateway_ms:.1f} ms' if gateway_ms is not None else '-'}"
    )

    internet_results = [ping(host) for host in INTERNET_HOSTS]
    internet_up = any(up for up, _ in internet_results)
    for host, (up, latency) in zip(INTERNET_HOSTS, internet_results):
        print(
            f"{'Internet':<28} {host:<16} "
            f"{'UP' if up else 'DOWN':<8} "
            f"{f'{latency:.1f} ms' if latency is not None else '-'}"
        )

    dns_ok, dns_ip = check_dns(DNS_TEST_DOMAIN)
    print(
        f"{'DNS lookup':<28} {DNS_TEST_DOMAIN:<16} "
        f"{'OK' if dns_ok else 'FAIL':<8} {dns_ip or '-'}"
    )

    print()
    print("Verdict:", verdict(gateway_up, internet_up, dns_ok))


if __name__ == "__main__":
    main()
