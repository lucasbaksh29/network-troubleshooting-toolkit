# Network Troubleshooting Toolkit — Session Plan

Five morning sessions (9 a.m.–1 p.m. each). One goal per session.
If a session runs short, stop at its done-when check — don't bleed
into the next one.

Laptop only, Windows first, Python standard library only — no pip
installs needed for the core tool. It reuses what you already know
from the Home Network Monitor (ping, SQLite, plain-English status)
and adds the checks a helpdesk / field tech actually runs on a call:
gateway, internet, DNS, traceroute, ports, Wi-Fi.

Your router is 192.168.0.1. The tool auto-detects the gateway from
`ipconfig` and falls back to that address.

## Session 1 — Setup + core checks

Goal: `diagnose.py` runs and gives a plain-English verdict.

- Copy the project files to a folder on the laptop, open a terminal there
- `git init` and make a first commit (so the work is tracked from day one)
- Run `python diagnose.py` — it checks, in order:
  1. Gateway (your router) — ping
  2. Internet — ping 8.8.8.8 and 1.1.1.1
  3. DNS — resolve google.com
- Read the verdict at the bottom: it names the fault layer, e.g.
  "Local network problem — can't reach your router", "Internet is
  down past your router", "DNS problem — internet works, names don't
  resolve", or "All checks passed"
- Learn the layer order: if the gateway is down, the later checks
  can't tell you anything — that's why they run in that order

Done when: `diagnose.py` prints a table of the three checks plus a
one-line verdict, on your real home network.

## Session 2 — Traceroute + ports + Wi-Fi

Goal: find *where* a connection breaks, not just *that* it breaks.

- Traceroute to 8.8.8.8: show each hop, flag the hop where replies stop
- TCP port checks: 80 / 443 on google.com, 53 on 8.8.8.8 — a port
  closed is a different fault from a host down
- Wi-Fi signal: `netsh wlan show interfaces` — signal %, SSID, channel
- Add these to the verdict: e.g. "Wi-Fi signal weak (38%) — move
  closer / check interference" vs "Traceroute stops at hop 2 — ISP"

Done when: a run shows hops, port results, and Wi-Fi signal, and the
verdict uses at least one of them.

## Session 3 — Reports + history

Goal: a run leaves a report a tech could hand to a user or an ISP.

- Save each run to `reports/` as a timestamped text report and JSON
- Store runs in SQLite (`runs.db`) so you can compare: is this
  slower than yesterday? Did DNS fail before?
- Add `--save` (default on) and a `--last` command to show the
  previous run side-by-side with this one
- Report format: date/time, each check with result + latency, verdict,
  and one "try this next" suggestion

Done when: two runs exist in `runs.db`, and `--last` shows the
previous run's verdict next to the current one.

## Session 4 — Interactive menu + custom targets

Goal: the tool works on someone else's problem, not just your network.

- Interactive menu: 1) Full diagnosis  2) Ping a host  3) Check a
  port  4) DNS lookup  5) Last run  6) Quit
- Custom targets: ping any host/IP the user types, check any port,
  look up any domain — with the same plain-English output
- Handle bad input gracefully: unknown host, port out of range,
  empty input — print a clear message, don't crash

Done when: you can run the menu, ping a host you type in, and check
a port you type in, without editing any code.

## Session 5 — Portfolio-ready

Goal: someone hiring can look at this and understand it in two minutes.

- Rewrite the README: what it is, what it checks, how to run it,
  a screenshot / sample report
- Take 2–3 screenshots (terminal run, a failing verdict, a report file)
- Clean up the code: remove dead code, make sure everything runs from
  a fresh copy with only the README steps
- Push it to GitHub as a public repo, e.g. `network-troubleshooting-toolkit`
- Write a short "what I learned" section in the README: OSI layers
  in practice (local / ISP / DNS), ICMP vs TCP, traceroute hops,
  Wi-Fi signal, writing reports a non-technical user can follow

Done when: the repo is public, the README explains it with a sample
report, and a stranger could clone it and run Session 1.
