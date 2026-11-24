# T090 - Which firmware and models support the site import limit (32998), and is only a cluster without it

Asked for by the maintainer on 2026-11-24. T078's decision (withhold the control when
[33500](../.wiki/wiki/entities/register-33500.md) reads 0xAA) stands until this answers.

## Questions

1. On which firmware, per model family, does 32998 cap a forced charge?
2. Is being in a cluster what stops it, or something else those two houses share?

## What is known

Watched under a forced charge; details in [register 32998](../.wiki/wiki/entities/register-32998.md).

| Family | Firmware | Lone inverter | Cluster |
| --- | --- | --- | --- |
| SH-RT | P020 | holds: mkaiser (SH10RT) | none measured |
| SH-RT | P022 | holds: gerd (SH8.0RT-V112) | none measured |
| SH-RT | P023 | holds: bar12 (SH10RT-20), peter-sm (SH10RT-V112) | does not: fwitten (SH10RT-V112), five caps |
| SH-RT | 01011.95.03 | **none measured** | does not: swo14 (SH10RT-20), one cap, battery at 3.3 % against a 10 % floor |
| SH-RS | P066 | holds: icefest (SH6.0RS) | none measured |
| SH-RS | P065 | holds by the owner's meter: Jam3s97 (SH10RS), no forced charge known | none measured |
| SH-RS | P057, P059, P067, P068 | not measured | none measured |
| SH-T | P038, P067, P071 | not measured; a dump reads 43.47 kW (ra1k-0) | none measured |
| any | ulfben's SH10RT-V112, firmware unknown | does not, by report; whether it is a cluster is not known | |

So no firmware has both a lone inverter and a cluster measured except P023, where they differ, and
01011.95.03 has no lone inverter at all: there, firmware and cluster cannot be told apart.

## Candidates other than the cluster

Backup mode (13075, 0xAA at both failing houses) is ruled out at a lone SH10RT on P020: the cap held with it on
([the run](../.wiki/wiki/sources/mkaiser-import-limit-backup-mode-2026-11-24-summary.md)). Not tried: P023, or a cluster with it off.

Others: the slave in Standby at 0 W throughout (no cluster with both running is measured); a setting fwitten and swo14 share;
the meter's place in a cluster; a site-level controller taking over the limit.

## Steps

1. Read 33500-33502 wherever a house is reachable: bar12 and gerd (lone, P023 and P022, cable and WiNet-S),
   fwitten's two WiNet-S. Read only. Add them to the diagnosis's register dump, so every later diagnosis says
   whether it is a cluster.
2. Compare the holding blocks of fwitten's master and peter-sm's, same model and firmware, for what else differs.
   Read only; the register dumps first.
3. At fwitten, with the maintainer's go: one cap with the slave running, in daylight; 13075 off as well if that fails.
4. Ask for the `--import-limit` check in `device-diagnosis/devices-wanted.md`: an SH-T (any), an SH-RS not on P066,
   a lone SH-RT on 01011.95.03 (decides swo14), a second cluster (decides question 2).
5. Ask on #546 whether ulfben's house is a cluster and which 13250 firmware it runs.
6. Write the answers in `register-32998.md` and its query; revise T078's rule and `CONFIRMED_ON_FIRMWARE` by them.

## Status log

- **2026-11-24, 21:00**: backup mode tried at mkaiser, restored: not the cause there. Next: a second cluster (row 13 of
  `devices-wanted.md`), step 3 in daylight, step 5's question (text with the maintainer), bar12's 33500.
- **2026-11-24, 20:30**: steps 1, 2 and 4 done: 33500 read at fwitten, gerd and mkaiser, cable and WiNet-S (bar12 not
  reachable); 33499-33501 added to `src/sungrow_modbus/dump.py`; the dumps compared, which found backup mode;
  row 13 in `devices-wanted.md`. Next: step 3, waiting for the go; step 5's text is with the maintainer.
- **2026-11-24**: written; nothing started. Next: step 1.
