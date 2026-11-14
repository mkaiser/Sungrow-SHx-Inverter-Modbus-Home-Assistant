# gerd's site lost its internet link overnight, 2026-11-13 to 2026-11-14

Observed during the read-only watch after the wallbox capability test
(`raw/gerd-wallbox-capability-test-2026-11-13.md`). The watch read the AC22E-01 (over TLS, port
516) every minute and the inverter (through the WiNet-S) every five minutes, over a WireGuard
tunnel from the development container.

| Time (local) | What was seen |
| --- | --- |
| 01:12, 01:15 | one wallbox read timed out each, the next read was normal |
| 02:44 | last good readings of both devices (wallbox idle, inverter in self-consumption) |
| 02:52 | wallbox read timed out |
| 02:56 | inverter read timed out on all three values |
| 02:52 to about 07:00 | every read timed out; a TCP connect to the wallbox's port 516 failed; the tunnel's network interface stayed up and the route to the site stayed in place, on this side |
| about 07:00 | the maintainer reported that the site's internet provider had disconnected the line during the night, and that the tunnel did not recover on its own |
| after restarting the tunnel (taken down, brought up) | a fresh handshake within seconds; port 516 accepted a connection; the next reads of both devices were normal |

Nothing was written to either device during the outage. The devices' state after it matched the
state before it (wallbox idle, no car; inverter EMS mode 0).

What was not established: the exact time the line came back (the check ran every two minutes
and was stopped to restart the tunnel), and whether the tunnel would have recovered by itself
given a keepalive on the site's side.
