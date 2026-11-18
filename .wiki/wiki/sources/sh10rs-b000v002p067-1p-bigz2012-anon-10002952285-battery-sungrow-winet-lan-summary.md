---
type: source
title: sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan.json
source_path: ../device-diagnosis/results/inverter/sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan.json
ingested: '2026-11-18'
created: '2026-11-18'
tags:
  - diagnosis
  - sh10rs
  - sunstone-h-b000-v002-p067
  - bigz2012
  - winet
  - capability-test
  - pv-cut
  - mdns
---

# SH10RS, B000.V002.P067, bigz2012, a WiNet-S2 on Ethernet: the PV cut works on P067

Part A read 2026-11-16 at 15:30 UTC from the terminal diagnosis after dark
(`--capability-test no`), with a daylight capability test run 2026-11-17 at 23:24 UTC and merged
into the same document (`--cut-pv`, `--no-restart`: the owner has servers on the backup circuit,
so the inverter restart must never run). Posted to issue #786 as a gist. Source:
`device-diagnosis/results/inverter/sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan.json`.

| | |
| --- | --- |
| Installation | [bigz2012](../entities/installation-bigz2012.md) |
| Model | [SH10RS](../entities/device-sh-rs.md), type code `0x0D1B`, single phase |
| Stand-in serial | `anon-10002952285` |
| Inverter firmware | [`SUNSTONE-H_B000.V002.P067`](../entities/firmware-sunstone-h-b000-v002-p067.md) |
| ARM / DSP firmware | `ARM_SUNSTONE-H_V11_V01_A` / `MDSP_SUNSTONE-H_V11_V01_A` |
| Version 1 / 2 | `SUNSTONE-H_01011.02.69` / `SUNSTONE-H_03021.01.16` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV300.001.03.P032` (a WiNet-S2, wired) |
| Transport (owner) | a WiNet-S on Ethernet |
| Transport (measured) | through a communication module; register 6100 refused |
| Battery | **two [SBR224](../entities/device-sbr-battery.md)**, 44.8 kWh reported, at unit 2 |
| PV | four MPPTs; at the capability test 4153 W |
| At part A | after dark: no PV, battery 20.7 %, discharging 1084 W |

## The PV cut works on P067

**The behavioural leg, in daylight, with `established: true`**: total DC power **3467 W before,
0 W during, 3641 W after**. Through a dongle that is the whole evidence and it is enough -- a
WiNet-S cannot invent a house that stops generating
([a dongle's readback](../entities/device-winet-s.md) is what it cannot be trusted on).

So [register 31211](../entities/register-31211.md) is confirmed on a second
[SH-RS](../entities/device-sh-rs.md) firmware, and `CONFIRMED_ON_FIRMWARE` gains
`SUNSTONE-H_B000.V002.P067` (`src/sungrow_modbus/hybrid_inverter/capabilities.py`,
`tests/test_pv_generation_cut.py`). The switch now ships on P065 and P067.

The two forced checks acted as well, both well clear of the drift:

| Check | Commanded | Before | During | After |
| --- | --- | --- | --- | --- |
| Forced charge | 1250 W | 2847 W | **1234 W** | 3009 W |
| Forced discharge | 1250 W | -2728 W | **1256 W** | -2496 W |

## Outcome 4 is not a device scale finding

The run exits **4** -- "at least one value came back off by a decade" -- on one readback:
`export_power_limit` (13074), written 600 W, read back 60. The owner asks for it to be
discarded, and the document agrees with them:

- **Feed-in limitation is off** (13087 holds 0x55), and while it is off the register ignores
  every write without an exception. The run says so itself: "the export limit's write scale was
  not determined, so it was written divided by ten".
- **The readback came through a WiNet-S**, whose answer is a stale cache. The 60 is the word the
  dongle forwarded, not what the register holds. The run's own `not_established` says every
  readback verdict here describes what the dongle reported.

So the decade is the tool's division by ten being echoed back, and
[13074](../entities/register-13074.md)'s write scale on P067 is **unmeasured**, not wrong. The
owner reports independently that the register reads and writes watts 1:1 here and holds 10000 for
a 10 kW cap, which is a report rather than a measurement; a probe needs feed-in limitation on.

**This narrows a standing lead.** At [ra1k-0](../entities/installation-ra1k-0.md)'s SH20T on
[P071](../entities/firmware-pearl-h-b000-v000-p071.md) the same thing happened -- word 60 written
with the mode off, 60 reported back through a WiNet-S -- and it was kept open as possible evidence
that P071 stores the word as handed. Two dongles on two firmware families now produce the pattern,
which is what a forwarded word echoed from a cache would do and not what "the register took it"
predicts. It stays open, but the dongle is now the better explanation.

## What the dongle refuses

The block read test narrowed four blocks, each refused with **exception 0x02** in 2 of 2 attempts,
register by register: the sub-controller firmware (2613, 15 registers), the battery firmware
(2629, 15), the PV generation history (6227, 53) and the export-from-PV history (6596, 42). 34
blocks answered in every round, none intermittently, with no reconnects. The meter phase registers
5741 and 5744 are refused as well, and 6100 with them.

That is the WiNet-S's usual shape. The owner suspects the dongle's forwarding limit rather than
absent hardware, and offers a run on the inverter's own LAN port for the both-paths comparison --
which is what `device-diagnosis/devices-wanted.md` asks for under "also worth sending", and would
settle the export limit's write scale here as well.

## The dongle's mDNS record names both packs

A 5-second multicast browse heard one `_http._tcp` service, the dongle's own, on a machine that
shares the inverter's subnet. Its TXT record, in the layout measured at
[gerd](gerd-mdns-2026-11-11-summary.md), has **two battery fields**:

- `battery1=2;200;8423;<stand-in>;1;516;SBR224;`
- `battery2=3;201;8423;<stand-in>;1;516;SBR224;`
- `inverter=1;3355;<stand-in>;1;516;SH10RS;1;3;`
- `board=SUNGROW;1;WiNet-S2;<stand-in>;1;`

Three things follow:

- **A second pack has units of its own**: 3 through the dongle and 201 over the cable, where the
  first has 2 and 200. The integration reads one pack, at 2 or 200
  ([SBR](../entities/device-sbr-battery.md)), so a second pack's registers are unread.
- **Unit 3 behind a dongle is not only a wallbox.** It is where
  [a wallbox](../entities/device-wallbox.md) answers at every house measured, and here it is the
  second battery. Nothing is misidentified, because identity comes from what answers rather than
  from a unit id ([identify by what answers](../concepts/identify-by-what-answers.md)) -- the
  wallbox serial probe at unit 3 got no answer here -- but a sweep that trusted the number would
  have been wrong.
- **Each pack carries its own serial** in the record, which is three serials for one house: the
  inverter's, the dongle's and one per pack. The packs report no serial over Modbus.
- The trailing field of `inverter` is **`1;3`** where [peter-sm](../entities/installation-peter-sm.md)'s
  SH10RT reads `1;4` and gerd's SH8.0RT the same; it is still unexplained, and it is not the
  tracker count (this machine has four MPPTs and reads 3).

**The reverse-DNS label is `espressif`**, the first real one in the corpus -- peter-sm's was
masked. A WiNet-S2's address resolves to a name from the chip vendor, not from Sungrow, so a
discovery matcher keyed on "sungrow" in a hostname would miss it.

## The capability test (outcome 4)

Six of seven readbacks matched; the seventh is the export limit above. `restored`: thirteen
settings written back through the dongle -- which takes a write but answers a readback stale, so
each was written and not read back -- and one already at its original word. Nothing is left
changed.

- **Battery ceiling 13974 W.** 14074 W was refused at 33047, 33048 and 13052 with exception
  **0x04**.
- **100 % is the ceiling for `battery_max_soc`**: 101 % refused with 0x04.
- **EMS mode options 2, 3 and 4 were all taken**; 0 was held before the run.
- **Write paths**: backup mode (13075) and load control (13011, 13002) each took their own words.
- **`battery_charging_start_power` and `battery_discharging_start_power` are genuinely absent**
  on this model -- the run says "the device does not have it (battery_start_power did not
  answer)", which is what the `nan_value` work in #743 concluded for the SH-RS.
- Not measured: the charge ceiling (the battery was at 39.4 %, under the 55 % the check needs to
  keep clear of `battery_max_soc`'s own 50 % floor), the export limit's effect (feed-in
  limitation off, and no leave to lift it), both schedule windows (no leave) and the restart (not
  asked for).
