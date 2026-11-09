# Session 1 — Setup + core checks

Goal: `diagnose.py` runs on your laptop and prints a verdict.

Do it one step at a time. Stop after each step and check it worked
before moving on.

## Step 1 — Copy the files

Copy the whole `network-troubleshooting-toolkit` folder to your
laptop, e.g. next to your other projects:

`C:\Users\lucas\OneDrive\Desktop\network-troubleshooting-toolkit`

Open a terminal in that folder (in File Explorer: click the address
bar, type `cmd`, press Enter — or open VS Code there).

Check the files are there:

```
dir
```

You should see `diagnose.py`, `SESSION_PLAN.md`, `README.md`.

## Step 2 — Check Python

```
python --version
```

You already have Python from the Home Network Monitor, so this
should print Python 3.11 or newer. If it doesn't, use the same
Python you used for that project.

No pip installs needed for Session 1 — the tool uses the standard
library only.

## Step 3 — Start git

```
git init
git add .
git commit -m "Session 1: core checks — gateway, internet, DNS"
```

## Step 4 — Run it

```
python diagnose.py
```

You should see something like:

```
Network Troubleshooting Toolkit — Session 1
Gateway detected: 192.168.0.1

Check                        Target           Result   Latency
-----------------------------------------------------------------
Gateway (router)             192.168.0.1      UP       3.2 ms
Internet                     8.8.8.8          UP       77.0 ms
Internet                     1.1.1.1          UP       15.0 ms
DNS lookup                   google.com       OK       142.250.x.x

Verdict: All checks passed — your connection looks healthy.
```

Your latencies will be different — that's normal. The gateway
should be 192.168.0.1 (your router). If it shows a different
address, that's what `ipconfig` reported — tell me what it says.

## Step 5 — Understand the verdict

The checks run in layer order, and the verdict names the first
layer that failed:

- Gateway DOWN → local problem. Wi-Fi / cable / router.
  The internet and DNS checks can't tell you anything yet.
- Gateway UP, internet DOWN → your home network is fine,
  the fault is past the router — ISP / modem.
- Gateway + internet UP, DNS FAIL → internet works, names
  don't resolve. That's a DNS problem, not a dead connection.
- All UP → healthy.

Done when: the run prints the table plus a one-line verdict.
Send me a screenshot of the output (or paste the verdict line)
and we'll move to Session 2 — traceroute, ports, and Wi-Fi signal.
