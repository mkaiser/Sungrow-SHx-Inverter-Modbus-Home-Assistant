# T090 - Which firmware and models support the site import limit (32998), and is only a cluster without it

Asked for by the maintainer on 2026-11-24. Until it answers, the control is withheld when
[33500](../.wiki/wiki/entities/register-33500.md) reads 0xAA (`doc/architecture.md`, *Decisions*).

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

1. At fwitten, with the maintainer's go (deferred 2026-11-24): one cap in daylight with the slave running, a new gate set beside
   `tmp/fwitten-t078/cluster_import_limit.py`; 13075 off as well if that fails, after asking the owner, whose backup it switches off.
2. Answers to row 13 of `device-diagnosis/devices-wanted.md`; every diagnosis since 2026-11-24 carries 33500 and 33501.
3. The #546 question to ulfben (Todo's I3; the maintainer posts it or says so).
4. Write the answers in `register-32998.md` and its query; revise `WITHHELD_FROM` and `CONFIRMED_ON_FIRMWARE` by them.

## Status log

- **2026-11-24, close**: everything above the open steps is done and pushed up to 4366e38; nothing uncommitted but this close.
  33500 is 0xAA at one cluster and 0x55 at mkaiser, gerd and bar12. Next: step 2, as diagnoses come in.
- **2026-11-24, 22:24**: bar12 read (0x55, cable and WiNet-S); its tunnel profile was replaced. Step 1 is done.
- **2026-11-24, 22:20**: step 3 (the daylight cap at fwitten) deferred by the maintainer.
- **2026-11-24, 21:50**: 33501 read beside 33500 (one request, measured) and published in every reading; bar12 tried again,
  no answer. Next: the daylight cap at fwitten, bar12, and the answers to row 13. Uncommitted.
- **2026-11-24, 21:00**: backup mode tried at mkaiser, restored: not the cause there. Next: a second cluster (row 13 of
  `devices-wanted.md`), step 3 in daylight, step 5's question (text with the maintainer), bar12's 33500.
- **2026-11-24, 20:30**: steps 1, 2 and 4 done: 33500 read at fwitten, gerd and mkaiser, cable and WiNet-S (bar12 not
  reachable); 33499-33501 added to `src/sungrow_modbus/dump.py`; the dumps compared, which found backup mode;
  row 13 in `devices-wanted.md`. Next: step 3, waiting for the go; step 5's text is with the maintainer.
- **2026-11-24**: written; nothing started. Next: step 1.
