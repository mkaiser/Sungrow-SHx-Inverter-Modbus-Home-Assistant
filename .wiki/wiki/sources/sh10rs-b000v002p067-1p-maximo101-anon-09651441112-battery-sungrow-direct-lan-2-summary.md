---
type: source
title: sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2.json
ingested: '2026-11-19'
created: '2026-11-19'
tags:
  - diagnosis
  - sh10rs
  - sunstone-h-b000-v002-p067
  - maximo101
  - winet
  - plausibility
---

# SH10RS, B000.V002.P067, Maximo101, through a WiNet-S2, second reading

Read 2026-11-19 at 02:20 UTC -- 13:20 in the house's own time -- from a Home Assistant
diagnostics download on integration 0.1.0a44 (`command_line`: "home assistant diagnostics",
schema 28), with no capability test, in full sun with the battery already full. Posted to issue
#786. Source:
`device-diagnosis/results/inverter/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2.json`.

**Four downloads of this entry, one committed.** Two pairs were posted, one before the upgrade to
0.1.0a44 and one after, each pair the same config entry taken from the inverter's device page and
the battery's seconds apart. Everything the four say about the hardware is identical to
[the first reading](sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)
-- same firmware strings, same capability probes, same features, same refusals -- so only the
0.1.0a44 one is committed, because it is the only one carrying a **`plausibility` block**.

| | |
| --- | --- |
| Installation | [Maximo101](../entities/installation-maximo101.md) |
| Model | [SH10RS](../entities/device-sh-rs.md), type code `0x0D1B`, single phase |
| Stand-in serial | `anon-09651441112` |
| Inverter firmware | [`SUNSTONE-H_B000.V002.P067`](../entities/firmware-sunstone-h-b000-v002-p067.md), version 1 `SUNSTONE-H_01011.02.69` |
| Battery | two [SBR192](../entities/device-sbr-battery.md) at unit 2, SoC 100 %, the pack idle |
| Transport (measured) | through a communication module; 6100 refused, as before |
| At the time | 10,458 W of PV, 9,996 W out, nothing through the meter, running state `0x4000` (External EMS mode) |

## Plausibility, three observations

The first `plausibility` block from a contributor's machine; the only other in the corpus is
[mkaiser's](sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-5-summary.md).
It spans **two minutes**, 13:18:43 to 13:20:43 local, so almost nothing in it is established:
every ratio check wants 20 observations and the energy checks want kilowatt-hours of flow. Two
checks answered:

| Check | Verdict | Detail |
| --- | --- | --- |
| mppt3 carries a string | matched | 3 daylight polls with a voltage |
| mppt4 carries a string | matched | 3 daylight polls with a voltage |
| lifetime counters never fall | not established | 2 of 1440 events |
| daily counters reset at midnight | not established | 0 of 1 events |
| every other check | not established | 0 to 3 observations of the 20 or 30 it wants |

**The `mppt4` verdict is wrong, and the reading says why.** See below.

## MPPT4 answers a voltage and carries nothing

Over five downloads of this machine spanning two days, `mppt4` reads **39.5 V to 53.6 V and
0.0 A every time**, at 3,825 W of PV and at 10,458 W alike, while the voltage wanders 14 V inside
86 seconds -- a floating input, not a string under load. The three live trackers' V x I account
for `total_dc_power` to within 1 % in all five, and in one of them exactly (174.1 x 11.9 +
325.5 x 11.5 + 380.4 x 10.5 = 9,809 W, the reported figure).

`TrackerCheck` grants the tracker on voltage alone (`TRACKER_LIVE_V` is 50 V in
`src/sungrow_modbus/capability_test/plausibility.py`), so a floating input that drifts above 50 V
in daylight reads as a string. That is what happened here. The current is the discriminator and
it answers on this model: `mppt4_current` is in the same block, and it is 0.0 A, not absent
([zero means absent](../concepts/zero-means-absent.md) cuts the other way only where nothing
answered).

So this machine has **three strings on four trackers**, and
[the first reading's](sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)
"four MPPTs answer" stands as written -- four answer, three carry power.

## `total_battery_charge`: the low word counts, the high word is wrong

The register is 13041 and 13042, low word first (`src/sungrow_modbus/hybrid_inverter/registers.py`).
Here they read **0xFFFF 0x9F6D** and, two days later, **0xFFFF 0xA0E9** -- the low word rose 380
tenths, 38.0 kWh, while `total_battery_charge_from_pv` rose 32.5 and `total_battery_discharge`
29.8. So the low word is a working counter and the high word is `0xFFFF`, which is this
specification's *unavailable*, composed into the total as though it were data.

**It is not this machine alone: all three P067 machines in the corpus have it**, and no machine on
any other firmware does.

| Machine | 13042 | 13041 | as read | own discharge total |
| --- | --- | --- | --- | --- |
| [bigz2012](../entities/installation-bigz2012.md) | `0x0002` | `0x43DA` | 14,844.2 kWh | 20,874.6 kWh |
| [brendan](../entities/installation-brendan.md) | `0x0000` | `0xF8FD` | 6,374.1 kWh | 12,708.0 kWh |
| Maximo101 | `0xFFFF` | `0xA0E9` | 429,494,295.3 kWh | 16,668.7 kWh |

A battery cannot give out more than it took in, and `total_battery_charge_from_pv` is a part of
the charge, not a thing beside it -- yet it reads higher than the charge on all three. Add the
missing wraps of the low word (65,536 tenths, 6,553.6 kWh) and each lands just above its own
discharge total: **21,397.8**, **12,927.7** and **17,226.5 kWh**, at ratios of 1.025, 1.017 and
1.034. Exactly one whole number of wraps does that for each machine; one more puts it 50 % above
the discharge, one fewer below it. So the inverter's own figure here is about **17,226.5 kWh**,
and the high word is missing two wraps rather than carrying a sign.

Every other lifetime total on these machines is exact: `total_direct_energy_consumption` +
`total_battery_charge_from_pv` + `total_exported_energy_from_pv` equals `total_pv_generation` to
the 0.1 kWh on all three, as it does on every machine in the corpus. Only this one register's
high word is wrong.

**What it costs**: a `total_increasing` sensor takes 429,494,295.3 kWh and then rises plausibly,
so nothing downstream rejects it. The `nan=0xFFFFFFFF` sentinel the fault words use does not
catch it, because the low word is alive.

## The wallbox download has the key now, and nothing in it

Two more downloads of the **AC22E-01** entry were posted, one on each version. The 0.1.0a44 one
carries `"diagnosis": null` where the 0.1.0a43 one has no such key at all, so the report now asks
for the document (`custom_components/sungrow_modbus/diagnostics.py`) and there is none to hand
over: a wallbox entry's download serves **the last run's** document, which is held in memory and
not written to disk (`DiagnosisState.document` in `custom_components/sungrow_modbus/diagnosis.py`),
and an upgrade restarts Home Assistant. An inverter entry's download builds its document on the
spot, which is why it never shows this.

So the AC22E-01 is still unread, and what it needs is *Diagnosis: start* on the wallbox's own
device page **before** the download, in the same Home Assistant session.
