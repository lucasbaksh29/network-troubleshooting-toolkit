# Network Troubleshooting Toolkit

A small Python tool that diagnoses a home / small-office network
problem and says, in plain English, where the fault is — your
router, your ISP, or DNS.

Built for hands-on IT support / network technician work. Laptop
only, Windows first, Python standard library only — no pip installs
needed.

## What it checks

It runs the checks in layer order, so the first failure names the
fault. If the gateway is down, the later checks can't tell you
anything — that's why they run in that order.

1. **Gateway (router)** — ping your router (auto-detected from
   `ipconfig`, fallback `192.168.0.1`)
2. **Internet** — ping `8.8.8.8` and `1.1.1.1`
3. **DNS** — resolve `google.com`
4. **Traceroute to 8.8.8.8** — each hop, so you see *where* a
   connection breaks, not just *that* it breaks
5. **TCP port checks** — `google.com:80`, `google.com:443`,
   `8.8.8.8:53` — ping can be up while a port is closed
6. **Wi-Fi signal** — SSID, signal %, channel (`netsh`, Windows)

Then it prints a one-line verdict, e.g.:

- "Local network problem — can't reach your router."
- "Internet is down past your router — your home network is fine, the fault is with your ISP."
- "DNS problem — the internet works, but names don't resolve."
- "All checks passed — your connection looks healthy."

## How to run it

```bash
python diagnose.py            # full diagnosis, saves a report
python diagnose.py --menu     # interactive menu (see below)
python diagnose.py --last     # show the last two saved runs
python diagnose.py --no-save  # run without saving
```

No pip installs needed. Python 3 only, standard library only.

## Interactive menu

`python diagnose.py --menu` opens the menu, so the tool works on
someone else's problem, not just your own network:

```
1) Full diagnosis
2) Ping a host
3) Check a port
4) DNS lookup
5) Last run
6) Quit
```

Type any host, port, or domain — bad input (empty host, a port
that isn't a number, a port out of range, an unknown host) prints
a clear message instead of crashing.

## Reports and history

Every run is saved, so a tech can hand the result to a user or
an ISP:

- A timestamped report in `reports/` (`.txt` + `.json`)
- Runs stored in SQLite (`runs.db`), so you can compare:
  is this slower than yesterday? Did DNS fail before?
- `python diagnose.py --last` shows your last two runs
  side by side, newest first

## Sample run

Real run on a home network, Nov 9, 2026:

```
Gateway (router)             192.168.0.1    UP       4.0 ms
Internet                     8.8.8.8        UP       100.0 ms
Internet                     1.1.1.1        UP       57.0 ms
DNS lookup                   google.com     OK       74.125.26.101

Traceroute to 8.8.8.8 (each hop):
  Hop 1   192.168.0.1      4.0 ms
  ...
  Hop 13  8.8.8.8          100.0 ms

Port checks (TCP connect):
  Web (HTTP)     google.com:80    OPEN
  Web (HTTPS)    google.com:443   OPEN
  DNS            8.8.8.8:53       OPEN

Wi-Fi: signal 85%  channel 36

Verdict: All checks passed — your connection looks healthy.
Note: Hop 2 didn't answer traceroute, but traffic still got
through — some ISP routers ignore traceroute, so that's not
a fault.
```

## What I learned

- **OSI layers in practice** — local vs ISP vs DNS, by testing
  in that order instead of guessing.
- **ICMP vs TCP** — a host can answer a ping while a port is
  closed, so a port check catches faults ping misses.
- **Traceroute hops** — a hop timing out in the *middle* of a
  route is normal (some ISP routers ignore traceroute); only
  the *last* hops timing out means the route stopped. An early
  version of this tool got that wrong and flagged a successful
  13-hop route as stopped — fixed in Session 3.
- **Wi-Fi signal** — under 50% is weak, 85% is excellent;
  a slow connection isn't always an ISP problem.
- **Reports a non-technical user can follow** — one verdict
  line, one "try this next" suggestion, saved to a file.

## Sessions

Built in five sessions, one step at a time:

- Session 1 — Setup + core checks (gateway, internet, DNS)
- Session 2 — Traceroute + ports + Wi-Fi signal
- Session 3 — Reports + history (saved reports, SQLite, compare runs)
- Session 4 — Interactive menu + custom targets
- Session 5 — Portfolio-ready (this README, screenshots, GitHub)
