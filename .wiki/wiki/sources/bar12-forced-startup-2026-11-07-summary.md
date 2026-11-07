---
type: source
title: bar12-forced-startup-2026-11-07.md
source_path: raw/bar12-forced-startup-2026-11-07.md
ingested: '2026-11-07'
created: '2026-11-07'
tags: [register-13017, forced-startup, standby, sh10rt-20, sapphire-h-b001-v000-p023, bar12, winet-s, write]
---

# Forced startup under low SoC, bar12, 2026-11-07

`.wiki/raw/bar12-forced-startup-2026-11-07.md` records the first watched writes of
[register 13017](../entities/register-13017.md), at [bar12](../entities/installation-bar12.md)'s
[SH10RT-20](../entities/device-sh-rt.md) on [P023](../entities/firmware-sapphire-h-b001-v000-p023.md),
after dark with the battery below its minimum SoC, over the cable and through the
[WiNet-S](../entities/device-winet-s.md).

| Claim | Evidence | Status |
| --- | --- | --- |
| 0xAA wakes an inverter in low-SoC Standby, with no other command | Starting after 2 min 36 s and 3 min 55 s, Running after 5 min 20 s, battery idle | watched by this repository, two runs |
| It is a switch, not a pulse: 0xAA stays, and keeps the inverter running | read 0xAA for 23 min, Running, no reset | one run |
| 0x55 is off: a running inverter at low SoC returns to Standby | within ~20 s, three times | three runs |
| Both read back as written | 0xAA and 0x55, at once, cable and dongle | every write |
| Only 0xAA and 0x55 are taken | 0, 0x01 and 0xFF refused with exception 0x04 | one write each |
| So the factory 0 cannot be put back | the restore of 0 refused 19 times | one run |
| Through a WiNet-S the same, and the dongle's read is current | the cable read 0xAA 9 s after the dongle's write; wake and stop as over the cable | one run |

Not measured: any other firmware; whether the inverter resets 13017 itself after longer than 23
minutes, or on PV, as #444 reports (0xAA to 0x55 after ~20 min, firmware unknown).
