# Entities by firmware

**Generated — do not edit.** `scripts/generate/generate_firmware_support.py`
builds this from the diagnoses in
[device-diagnosis/results/](../device-diagnosis/results/), and CI checks that it
matches. [compatibility.md](compatibility.md) has the diagnoses themselves,
one row each.

The question: **do devices on the same firmware support the same
registers?** A column is one platform and firmware, every model seen on
it pooled, so a cell marked **split** is a place where models on one
firmware disagree, and names them. A row is an entity the integration
can create: first on the inverter, then on an SBR or SBH battery pack.
The wallbox and SG string inverters are not in this page.

## Reading the tables

| Mark | Means |
| --- | --- |
| ✓ | Answered with a value. |
| ✓ W | Answered, and a write was confirmed on this firmware: read back over a cable by the [capability test](../.wiki/wiki/concepts/capability-test.md), or its effect watched (`CONFIRMED_ON_FIRMWARE`). A writable entity without the W has not had its write confirmed here. |
| ✗ | Answered "unavailable", refused, or did not answer. |
| 0? | Answered only zeros where the integration reads zero as absent (MPPT3 at night, a dongle's stand-in for "unavailable"): cannot tell. |
| – | Not fitted: needs a part (battery, meter, dual-channel meter, communication module, Sungrow pack, a pack module) none of these houses has. |
| *(empty)* | Untested: no diagnosis reached these registers, or none can read them (the masked serial; the padded firmware strings at 2613 and 2629). |

The **Diagnosis** column says how far a diagnosis can test the entity on any inverter, before a column says what one did:

| Diagnosis | Means |
| --- | --- |
| read | The raw register dump reaches its registers, so the columns can answer for it. |
| written | The capability test writes it and checks the raw word it reads back against the specification's scale. |
| watched | A behavioural check of the capability test writes it and watches what the inverter does. |
| *(empty)* | No part of the diagnosis reaches it: a column can only be empty there. |

A **dongle** column was read through a WiNet-S or Logger, which refuses
some blocks and answers 0 where the inverter answers "unavailable";
compare a dongle column with a dongle column.

## Inverters

Each diagnosis's raw register dump is replayed through the integration's
own decoding and capability probe, so a cell is what the inverter
answered for the registers that entity reads.

### What the diagnoses say so far

**4 cell(s) split**: models on one firmware disagree.

- MPPT3 current, in PEARL-H B000.V000.P067 dongle
- MPPT3 energy, in PEARL-H B000.V000.P067 dongle
- MPPT3 power, in PEARL-H B000.V000.P067 dongle
- MPPT3 voltage, in PEARL-H B000.V000.P067 dongle

What moves between firmware versions of one platform, over one kind of link:

- **PEARL-H, dongle** (B000.V000.P067, B000.V000.P071): 8 differ.
  - Communication module firmware version: B000.V000.P067 ✗, B000.V000.P071 ✓
  - MPPT3 current: B000.V000.P067 **split**: ✓ SH25T; 0? SH15T, B000.V000.P071 ✓
  - MPPT3 energy: B000.V000.P067 **split**: ✓ SH25T; 0? SH15T, B000.V000.P071 ✓
  - MPPT3 power: B000.V000.P067 **split**: ✓ SH25T; 0? SH15T, B000.V000.P071 ✓
  - MPPT3 voltage: B000.V000.P067 **split**: ✓ SH25T; 0? SH15T, B000.V000.P071 ✓
  - Export power: B000.V000.P067 ✗, B000.V000.P071 ✓
  - Export power signed: B000.V000.P067 ✗, B000.V000.P071 ✓
  - Import power: B000.V000.P067 ✗, B000.V000.P071 ✓
- **SAPPHIRE-H, direct** (01011.95.03, B001.V000.P020, B001.V000.P022, B001.V000.P023): 6 differ.
  - Backup frequency: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Firmware version: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Cut PV generation *(switch)*: B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - PV generation cut *(binary_sensor)*: B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - PV generation cut code: B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Battery firmware version: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
- **SAPPHIRE-H, dongle** (01011.95.03, B001.V000.P020, B001.V000.P022, B001.V000.P023): 7 differ.
  - Feed-in limit ratio: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Forced startup under low SoC *(switch)*: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Communication module firmware version: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Firmware version: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Cut PV generation *(switch)*: 01011.95.03 ✗, B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - PV generation cut *(binary_sensor)*: 01011.95.03 ✗, B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - PV generation cut code: 01011.95.03 ✗, B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
- **SUNSTONE-H, dongle** (B000.V001.P068, B000.V002.P059, B000.V002.P065, B000.V002.P067): nothing differs.

### Columns

| Column | Platform | Firmware | Link | Models | Diagnoses |
| --- | --- | --- | --- | --- | --- |
| 1 | PEARL-H | B000.V000.P067 | dongle | SH15T, SH25T | 2 |
| 2 | PEARL-H | B000.V000.P071 | dongle | SH15T, SH20T | 5 |
| 3 | SAPPHIRE-H | 01011.95.03 | direct | SH10RT-V112 | 2 |
| 4 | SAPPHIRE-H | 01011.95.03 | dongle | SH10RT-V112 | 2 |
| 5 | SAPPHIRE-H | B001.V000.P020 | direct | SH10RT, SH10RT-V112 | 5 |
| 6 | SAPPHIRE-H | B001.V000.P020 | dongle | SH10RT-20 | 2 |
| 7 | SAPPHIRE-H | B001.V000.P022 | direct | SH6.0RT-20, SH8.0RT-V112 | 4 |
| 8 | SAPPHIRE-H | B001.V000.P022 | dongle | SH8.0RT-V112 | 3 |
| 9 | SAPPHIRE-H | B001.V000.P023 | direct | SH10RT-20, SH10RT-V112, SH5.0RT-V112, SH6.0RT-V112 | 15 |
| 10 | SAPPHIRE-H | B001.V000.P023 | dongle | SH10RT-20, SH10RT-V112, SH5.0RT-V112, SH6.0RT-V112 | 6 |
| 11 | SUNSTONE-H | B000.V001.P068 | dongle | SH6.0RS | 1 |
| 12 | SUNSTONE-H | B000.V002.P059 | dongle | SH10RS | 1 |
| 13 | SUNSTONE-H | B000.V002.P065 | dongle | SH10RS | 1 |
| 14 | SUNSTONE-H | B000.V002.P067 | dongle | SH10RS | 1 |

Left out, with no register dump, no firmware or no way to tell the link:

- `sh10rs-b000v002p057-1p-bleughb-anon-92100523190-battery-sungrow-winet-wlan`
- `sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan`
- `sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan`
- `sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-wlan`
- `sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-7`
- `sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-8`
- `sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan`
- `sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan`
- `sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan`
- `sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-winet-lan`
- `sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan`

### What the capability test measured

Findings about the firmware rather than about one entity, from every
diagnosis whose run had the capability test, in the columns above. The
13074 write scale is asked by a write the device refuses or accepts,
so it holds through a dongle too; a readback counts over a cable only,
because a WiNet-S answers a written register stale. A behaviour cell
counts that check's runs: ✓ the inverter did as it was told, ×10 the inverter acted on a value off by a decade, ± right magnitude, wrong direction, ✗ nothing measurable happened, ? could not tell. An empty cell is a column no run measured.

| Measurement | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Export power limit write scale (13074) |  |  | 1:1 | 1:1 | ×10 |  | ×10 | ×10 | ×10 | ×10 |  |  | 1:1 |  |
| Settings read back as written, over a cable |  |  | 12/12 |  | 16/16 |  | 27/27 |  | 89/89 |  |  |  |  |  |
| Restart: running again after |  | 148 s | 170–197 s |  | 186–187 s |  | 181–185 s | 181 s | 168–197 s | 186 s |  |  |  |  |
| Behaviour: forced charge |  |  |  |  | ✓ 1 | ✓ 1 | ✓ 3 | ✓ 2 | ✓ 7, ✗ 1 | ✓ 2 |  |  |  |  |
| Behaviour: forced discharge |  | ✓ 2 | ✓ 1 |  | ✓ 1 | ✓ 1 | ✓ 3 | ✓ 1 | ✓ 4, ✗ 2, ? 3 | ✓ 1, ? 1 |  |  |  |  |
| Behaviour: charge ceiling |  |  |  |  |  | ✓ 1 |  |  | ✓ 1, ? 1 |  |  |  |  |  |
| Behaviour: export power limit |  |  | ✗ 1 |  | ✓ 1 | ✓ 1 | ✓ 1 | ? 1 | ✓ 4, ? 3 | ✓ 1 |  |  | ? 1 |  |
| Behaviour: PV generation cut |  | ✓ 1 |  |  |  |  | ✓ 3 | ✓ 2 | ✓ 3 | ✓ 1 |  |  | ✓ 1 |  |
| Behaviour: forced-charging window |  |  |  |  | ? 1 |  | ✓ 1, ? 1 | ✓ 1, ? 1 | ✓ 1, ? 3 | ? 1 |  |  |  |  |
| Behaviour: discharge windows away from now |  |  |  |  |  |  | ✓ 1 |  |  |  |  |  |  |  |
| Behaviour: site import limit |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

### Backup power

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Backup frequency | read | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup mode *(switch)* | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup mode code | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase A current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase A power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase A voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase B current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase B power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase B voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase C current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase C power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase C voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total backup power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Control

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Active power limitation *(binary_sensor)* | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Active power limitation code | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Active power limitation ratio | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EMS mode *(select)* | read + watched | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EMS mode selection code | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit ratio | read | ✓ | ✓ |  | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Forced charging days *(select)* | read + watched | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging end 1 *(time)* | read + watched | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging end 2 *(time)* | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging schedule *(switch)* | read + watched | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging start 1 *(time)* | read + watched | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging start 2 *(time)* | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging target SoC 1 *(number)* | read + watched | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging target SoC 2 *(number)* | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekday discharge window 1 | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekday discharge window 2 | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekend discharge *(binary_sensor)* | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekend discharge window 1 | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekend discharge window 2 | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Everything else

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Forced startup under low SoC *(switch)* | read | ✓ | ✓ |  | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ W | ✓ W | ✗ | ✗ | ✗ | ✗ |
| Power factor | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Power flow code | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Running state | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Running state code | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Shutdown inverter when limited to 0 % power *(binary_sensor)* | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Shutdown inverter when limited to 0 % power code | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Faults and alarms

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Any alarm *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BDC-side fault | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BDC-side permanent fault | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| DC-side fault | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Device alarm | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Fault reported *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Permanent fault | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| System fault 1 | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| System fault 2 | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Identity and firmware

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ARM software version | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Communication module firmware version | read | ✗ | ✓ | – | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| DSP software version | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Device type | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Device type code | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version | read | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version part 1 | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version part 2 | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version part 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Protocol version | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Serial number |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

### Per phase

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Phase A current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Phase A power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Phase A voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Phase B current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase B power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase B voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase C current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase C power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase C voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |

### Power

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BDC rated power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Rated output power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Reactive power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total PV input power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total active power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Temperatures

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Device temperature | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The PV trackers

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cut PV generation *(switch)* | read + watched | ✓ | ✓ W |  | ✗ | ✗ | ✗ | ✓ W | ✓ W | ✓ W | ✓ W | ✓ | ✓ | ✓ W | ✓ |
| Daily PV generation | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily exported energy from PV | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Export from PV this month | read | ✗ | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Export from PV this year | read | ✗ | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| MPPT1 current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT1 energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT1 power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT1 voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT2 current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT2 energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT2 power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT2 voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT3 current | read | **split**: ✓ SH25T; 0? SH15T | ✓ | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT3 energy | read | **split**: ✓ SH25T; 0? SH15T | ✓ | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT3 power | read | **split**: ✓ SH25T; 0? SH15T | ✓ | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT3 voltage | read | **split**: ✓ SH25T; 0? SH15T | ✓ | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT4 current | read | 0? | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT4 energy | read | 0? | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT4 power | read | 0? | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT4 voltage | read | 0? | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| PV generating (delayed) *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PV generating *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PV generation cut *(binary_sensor)* | read | ✓ | ✓ |  | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PV generation cut code | read | ✓ | ✓ |  | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PV generation this month | read | ✗ | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| PV generation this year | read | ✗ | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| PV power limitation *(binary_sensor)* | read | ✓ | ✓ |  | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| PV power limitation code | read | ✓ | ✓ |  | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Total PV generation | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total exported energy from PV | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total site PV power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The battery

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BMS alarm | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS alarm 2 | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS fault 1 | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS fault 2 | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS max charging current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS max discharging current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS protection | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery alarm | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery capacity high precision | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charge | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charge (health-rated) | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charge (nominal) | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging (delayed) *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging power | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging power signed | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging start power | read | ✗ | ✗ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Battery charging start power *(number)* | read + written | ✗ | ✗ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✗ | ✗ | ✗ | ✗ |
| Battery current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging (delayed) *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging power | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging power signed | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging start power | read | ✗ | ✗ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Battery discharging start power *(number)* | read + written | ✗ | ✗ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✗ | ✗ | ✗ | ✗ |
| Battery fault | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery firmware version | read | ✓ | ✓ | ✗ | – | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery forced charge/discharge *(select)* | read + watched | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery forced charge/discharge command code | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery forced charge/discharge power | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery forced charge/discharge power *(number)* | read + written + watched | ✓ | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery level | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery level (nominal) | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max SoC | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max SoC *(number)* | read + written + watched | ✓ | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max charging power | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max charging power *(number)* | read + written | ✓ | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max discharging power | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max discharging power *(number)* | read + written | ✓ | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery min SoC | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery min SoC *(number)* | read + written | ✓ | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery power | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery reserved SoC for backup | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery reserved SoC for backup *(number)* | read + written | ✓ | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery state of health | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery temperature | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily PV generation & battery discharge | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily battery charge energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily battery charge energy from PV | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily battery discharge energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version part 4 (Sungrow battery) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Total PV generation & battery discharge | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total battery charge energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total battery charge energy from PV | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total battery discharge energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The grid

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Daily exported energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily imported energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Export power | read | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Export power signed | read | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Exporting power (delayed) *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Exporting power *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit *(number)* | read + written + watched | ✓ | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit maximum | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit minimum | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit mode *(switch)* | read + watched | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit mode code | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Grid frequency | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Grid import limit | read | ✓ | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Grid-side fault | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Import power | read | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Importing power (delayed) *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Importing power *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total exported energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total imported energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The house

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Corrected load power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily consumed energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily consumed energy (smoothed) | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily direct energy consumption | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Direct consumption this month | read | ✗ | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Direct consumption this year | read | ✗ | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Load control *(switch)* | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Load control mode *(select)* | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Load control mode enable code | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Load control mode selection code | read | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Load power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Negative load power (delayed) *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Negative load power *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Positive load power (delayed) *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Positive load power *(binary_sensor)* | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Self-consumption of today | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total consumed energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total direct energy consumption | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The meter

| Entity | Diagnosis | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Meter active power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Meter channel 2 phase A active power | read | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Meter channel 2 phase B active power | read | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Meter channel 2 phase C active power | read | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Meter channel 2 total active power | read | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Meter phase A active power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Meter phase A current | read | 0? | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase A voltage | read | 0? | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase B active power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Meter phase B current | read | 0? | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase B voltage | read | 0? | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase C active power | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Meter phase C current | read | 0? | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase C voltage | read | 0? | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |

## Battery packs

A pack is a device on its own unit with firmware of its own, so a column
is its **BCU firmware**, the battery firmware string the inverter reports
at register 13280. Over the inverter's LAN port the pack answers on unit
200; through a WiNet-S, on unit 2. The model is the one the inverter's
capacity register (5639) matches. A cell is the diagnosis's own decoded
reading of the pack: a component the pack refused with an exception is
absent, one lost to the link is untested.

### What the diagnoses say so far

**No cell is split.** Wherever two pack models on one firmware were both
diagnosed, they answered every entity's registers alike, once what a
house has fitted is set aside. The assumption holds on this evidence;
it is tested only where a column pools more than one of the pack models.

What moves between firmware versions of one platform, over one kind of link:

- **SBHBCU-S, dongle** (22011.04.07, 22011.04.08 32, 22011.04.11): nothing differs.
- **SBRBCU-S, direct** (22011.01.21, 22011.01.27, 22011.01.30): nothing differs.
- **SBRBCU-S, dongle** (22011.01.21, 22011.01.27, 22011.01.27 24, 22011.01.30, 22011.01.30 44): nothing differs.

### Columns

| Column | Platform | Firmware | Link | Models | Diagnoses |
| --- | --- | --- | --- | --- | --- |
| B1 | SBHBCU-S | 22011.04.07 | unit 2 (dongle) | 25.34 kWh, no single model | 1 |
| B2 | SBHBCU-S | 22011.04.08 32 | unit 2 (dongle) | SBH300 | 1 |
| B3 | SBHBCU-S | 22011.04.11 | unit 2 (dongle) | SBH150, SBH200, SBH400 | 5 |
| B4 | SBRBCU-S | 22011.01.21 | unit 200 (cable) | SBR096 | 1 |
| B5 | SBRBCU-S | 22011.01.21 | unit 2 (dongle) | SBR096 | 1 |
| B6 | SBRBCU-S | 22011.01.27 | unit 200 (cable) | SBR096, SBR128, SBR256 | 4 |
| B7 | SBRBCU-S | 22011.01.27 | unit 2 (dongle) | SBR096 | 2 |
| B8 | SBRBCU-S | 22011.01.27 24 | unit 2 (dongle) | 32 kWh, no single model | 1 |
| B9 | SBRBCU-S | 22011.01.30 | unit 200 (cable) | SBR064, SBR096, SBR128, SBR160, SBR192, SBR224 | 19 |
| B10 | SBRBCU-S | 22011.01.30 | unit 2 (dongle) | 44.8 kWh, no single model, SBR096, SBR128, SBR192 | 9 |
| B11 | SBRBCU-S | 22011.01.30 44 | unit 2 (dongle) | SBR192 | 1 |

Left out, with a battery firmware but no pack reading, or no battery firmware:

- `sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan`
- `sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan`
- `sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan`
- `sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-winet`
- `sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan`
- `sh15t-b000v000p067-3p-code-imstillalive-anon-07241574740-battery-unknown-meter-logger`
- `sh15t-b000v000p071-3p-fullhd23-anon-08484305020-battery-unknown-winet-lan`
- `sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger`

### Entities

| Entity | Diagnosis | B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 | B9 | B10 | B11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pack voltage | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pack current | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pack temperature | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pack level | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pack state of health | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total pack charge energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total pack discharge energy | read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Highest cell voltage | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Lowest cell voltage | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Cell voltage spread | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Warmest module temperature | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Coolest module temperature | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module with highest cell | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Highest cell number | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module with lowest cell | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Lowest cell number | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Warmest module | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Coolest module | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 1 highest cell voltage | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 1 lowest cell voltage | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 2 highest cell voltage | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 2 lowest cell voltage | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 3 highest cell voltage | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 3 lowest cell voltage | read | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 4 highest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 4 lowest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 5 highest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 5 lowest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 6 highest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 6 lowest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 7 highest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 7 lowest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 8 highest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | – | ✗ | ✗ |
| Module 8 lowest cell voltage | read | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | – | ✗ | ✗ |
