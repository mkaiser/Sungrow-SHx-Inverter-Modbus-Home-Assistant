# T078 - The site import limit (32998) at a cluster master

Whether 32998 caps grid import at fwitten's cluster (two SH10RT-V112 on P023), where the
capability test's check left import unmoved
([the run](../.wiki/wiki/sources/fwitten-import-limit-engine-2026-11-22-summary.md)), and if so
through which unit. It decides whether a cluster master is offered *Grid import limit*.

## The run

By script, `tmp/fwitten-t078/cluster_import_limit.py` (local only), over both inverters' cable
ports. Check only by default; `--run` asks for a typed confirmation. It proves both stand-ins,
flushes a snapshot before the first write and puts back every raw word, checked by raw read,
retrying until it holds. The samples log the meter, the battery, both inverters' AC power, state
and 32998 read back, every few seconds.

| Phase | Forced charge (master) | Cap | What it settles |
| --- | --- | --- | --- |
| A | 1250 W | master, 625 W under the import | the failed case again, with the word read back |
| B | 4000 W | master, 2000 W under the import | whether A was too small |
| C | 4000 W | slave alone, same cap | whether the slave's register is the one that counts |
| D | 4000 W | both, same cap | whether the cluster needs both |

Each cap is held 90 s and lifted for 60 s, so each has a bracket on both sides. About 15 min.

Gates: battery 15-85 %, PV under 50 W on both, no forced command or EMS mode set, master running.
It ends early, and restores, at 89 % battery, over 12 kW of import, or when the meter stops answering.

Not in it: the cap written through the WiNet-S. Do it only if B or D holds over the cable.

## Status log

- **2026-11-24, run**: done 18:13-18:27 CET, exit 0, all restored and read back by a second client. A, B, C and D
  all **did not hold**, every cap read back ([the source](../.wiki/wiki/sources/fwitten-import-limit-cluster-2026-11-24-summary.md)). Not run through the WiNet-S,
  which B or D holding was the condition for. The slave's 13050 was **not** read, so the mirroring stays open (T089). Next: the maintainer's decision on the control.
- **2026-11-24**: script written and run against a fake cluster (cap held, not held, held by the slave only,
  a flaky link, an outage during the run, Ctrl-C); restored every time. Not run on hardware.
  fwitten is reached with `vpn.sh up witten`. Waits for the battery to fall under 85 % and the
  maintainer's go for the writes.
