# gerd's wallbox, the control test's dry run, 2026-11-06

Run by the maintainer's session over a VPN, `device-survey/scripts/python/sungrow_wallbox_control_test.py`
without `--leave`, at the wallbox's own address (TLS 516, unit 248), around 20:51 UTC. Read only:
nothing was written. No car was connected. No serial, no address.

| Reading | Register | Raw word | Decoded |
| --- | --- | ---: | --- |
| Model name | input 21216 | | AC22E-01 |
| Rated current | input 21263 | 320 | 32.0 A at 0.1 A |
| Output current setting | holding 21203 | 0 | 0 at either scale |
| Start/stop | holding 21212 | 1 | |
| Charger enabled | holding 21211 | 1 | |
| Phase setting | holding 21204 | 0 | three phase |
| Charging status | input 21317 | 1 | idle |
| Phase currents | input 21303/21305/21307 | 0 | 0.0 A |
| Available current | input 21322 | 161 | 16.1 A at 0.1 A |

Exit 0, "dry run: the plan resolved, and nothing was written"; not established: "no car is
charging".
