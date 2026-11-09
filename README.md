# Network Troubleshooting Toolkit

A small Python tool that diagnoses a home / small-office network
problem and says, in plain English, where the fault is — your
router, your ISP, or DNS.

Built for hands-on IT support / network technician work. Laptop
only, Windows first, Python standard library only.

## What it checks (Session 1)

1. **Gateway (router)** — ping your router
2. **Internet** — ping 8.8.8.8 and 1.1.1.1
3. **DNS** — resolve google.com

Then it prints a one-line verdict, e.g.:

- "Local network problem — can't reach your router."
- "Internet is down past your router — your home network is fine, the fault is with your ISP."
- "DNS problem — the internet works, but names don't resolve."
- "All checks passed — your connection looks healthy."

## How to run it

```
python diagnose.py
```

No pip installs needed.

## Sessions

- Session 1 — Setup + core checks (gateway, internet, DNS)
- Session 2 — Traceroute + ports + Wi-Fi signal
- Session 3 — Reports + history (saved reports, SQLite, compare runs)
- Session 4 — Interactive menu + custom targets
- Session 5 — Portfolio-ready (README, screenshots, GitHub)

See `SESSION_PLAN.md` for the full plan.

## What I learned

_(To be filled in as the sessions are completed.)_
