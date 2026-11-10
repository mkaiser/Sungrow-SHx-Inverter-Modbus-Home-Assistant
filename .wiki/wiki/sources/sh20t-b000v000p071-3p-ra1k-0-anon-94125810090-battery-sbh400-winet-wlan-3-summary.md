---
type: source
title: sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-3.json
source_path: ../device-diagnosis/results/inverter/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-3.json
ingested: '2026-11-10'
created: '2026-11-10'
tags:
  - diagnosis
  - sh20t
  - pearl-h-b000-v000-p071
  - ra1k-0
  - winet_wlan
  - capability-test
---

# SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi, outcome 5

Read 2026-11-10 at 11:57 UTC from Home Assistant with integration 0.1.0a35, posted by Raik0 to
issue #786, with one capability test run at 12:10 UTC. Committed as the contributor posted it.
Source: `device-diagnosis/results/inverter/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-3.json`.

| | |
| --- | --- |
| Installation | [ra1k-0](../entities/installation-ra1k-0.md) |
| Model | [SH20T](../entities/device-sh-t.md), type code `0x0E26` |
| Stand-in serial | `anon-94125810090` |
| Inverter firmware | [`PEARL-H_B000.V000.P071`](../entities/firmware-pearl-h-b000-v000-p071.md) |
| ARM / DSP firmware | `ARM_PEARL-H_V11_V01_A` / `MDSP_PEARL-H_V11_V01_A` |
| Battery firmware | `SBHBCU-S_22011.04.11` |
| Communication module firmware | `WINET-SV300.001.03.P032` |
| Transport (owner) | a [WiNet-S](../entities/device-winet-s.md) on WiFi; the iHomeManager named as another poller |
| Transport (measured) | through a communication module; register 6100 refused |
| Battery | [SBH400](../entities/device-sbh-battery.md) (unit 2; the SBR cell and module blocks refused with 0x02) |

## What did not answer

Refused with 0x02 in every round: the sub-controller (2613) and battery (2629) firmware blocks,
the monthly PV generation (6227) and the monthly export from PV (6596). The monthly direct
consumption (6417) answered, **every month 0**, beside a daily direct consumption of 118.1 kWh:
a dongle's zero, not a reading ([zero means absent](../concepts/zero-means-absent.md)). The
diagnosis does not grant the history here, so no sensor carries those zeros. **33149 answered in
every round** of the block read test, while the capability test's own probe found the start
thresholds absent; see [P071](../entities/firmware-pearl-h-b000-v000-p071.md). No reconnects,
nothing intermittent.

## Capability test

Outcome **5**: **one register was not restored**, so the house may be left changed. Through a
WiNet-S only the behavioural leg is evidence; the run says so of its own readbacks.

- **Not restored: `forced_charging_days_raw` (register 33209)**, held at 1. The charge-window
  check's write of 33209 was refused with 0x04, and the restore's five writes of 1 were refused
  too. Through a WiNet-S a refused write has landed before, so whether 33209 changed is not known;
  every write to it was of the value it held. The run asks for it to be read over the inverter's
  own port, which this SH20T does not have
  ([the installation](../entities/installation-ra1k-0.md)). See
  [the restore](../concepts/capability-test-restore.md).
- The discharge-window write (33155, protocol address 33154) was also refused with 0x04: the
  owner names the iHomeManager as another poller of this inverter ([a busy WiNet-S](../queries/does-a-busy-winet-s-refuse-with-0x04.md)).
- Readback: five of seven matched. [13074](../entities/register-13074.md): **not determined**
  again (20000 W held, bounds 0-20000 W, so no safe probe word); written divided by ten, word 60
  for 600 W, and the dongle reported 60, two points with the wrong slope, as in the
  [second reading](sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005-summary.md).
  `battery_forced_charge_discharge_power` (13052) read 1840 for 2400 written: the dongle's stale
  cache, which also held 2600 when the forced charge was to be written.
- Forced charge: could not tell (the house moved 818 W). Forced discharge: **nothing measurable
  happened**, 794 W before, 825 W during, 940 W after, against 1250 W commanded. 13052 read
  2600 through the dongle beside it, so the command's own value is not known.
- Write paths, each taken: backup mode (13075, its own word 0xAA), load control (13011 0x55,
  13002 3), the weekend discharge enable (33179, 0xAA). EMS modes 0, 2 and 4 were taken; 3 was
  the mode held.
- Upper bounds: `battery_min_soc` refused 51 %, `battery_max_soc` 101 %, and
  **`battery_max_discharge_power` refused 26339 W above its 26239 W maximum** (0x04). The same
  value was taken for `battery_max_charge_power` and `battery_forced_charge_discharge_power`;
  through a dongle whether it was stored cannot be read.
- Restart: stopped in 2.1 s (13000 read `0x1300`), Running after 148.0 s. "Settings survived"
  reads **no**, from the dongle's cache, which the run itself says reports writes stale.
- Not checked: the start thresholds (33149 did not answer the run's probe), the charge ceiling
  (not charging), the export limit (2710 W of discharge produced no export), the PV cut (PV 0 W),
  the import limit (the forced charge's value off), and window 2's encoding (the owner's schedule
  is on).
