# Entities by firmware

**Generated — do not edit.** `scripts/generate/generate_firmware_support.py`
builds this from the surveys in
[device-survey/results/](../device-survey/results/), and CI checks that it
matches. [compatibility.md](compatibility.md) has the surveys themselves,
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
| ✓ W | Answered, and a write was confirmed on this firmware: read back over a cable by the [control test](../.wiki/wiki/concepts/control-test.md), or its effect watched (`CONFIRMED_ON_FIRMWARE`). A writable entity without the W has not had its write confirmed here. |
| ✗ | Answered "unavailable", refused, or did not answer. |
| 0? | Answered only zeros where the integration reads zero as absent (MPPT3 at night, a dongle's stand-in for "unavailable"): cannot tell. |
| – | Not fitted: needs a part (battery, meter, dual-channel meter, communication module, Sungrow pack, a pack module) none of these houses has. |
| *(empty)* | Untested: no survey reached these registers, or none can read them (the masked serial; the padded firmware strings at 2613 and 2629). |

A **dongle** column was read through a WiNet-S or Logger, which refuses
some blocks and answers 0 where the inverter answers "unavailable";
compare a dongle column with a dongle column.

## Inverters

Each survey's raw register dump is replayed through the integration's
own decoding and capability probe, so a cell is what the inverter
answered for the registers that entity reads.

### What the surveys say so far

**No cell is split.** Wherever two models on one firmware were both
surveyed, they answered every entity's registers alike, once what a
house has fitted is set aside. The assumption holds on this evidence;
it is tested only where a column pools more than one of the models.

What moves between firmware versions of one platform, over one kind of link:

- **SAPPHIRE-H, direct** (01011.95.03, B001.V000.P020, B001.V000.P022, B001.V000.P023): 6 differ.
  - Backup frequency: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Firmware version: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Cut PV generation *(switch)*: B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - PV generation cut *(binary_sensor)*: B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - PV generation cut code: B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Battery firmware version: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
- **SAPPHIRE-H, dongle** (01011.95.03, B001.V000.P020, B001.V000.P022, B001.V000.P023): 6 differ.
  - Feed-in limit ratio: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Communication module firmware version: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Firmware version: 01011.95.03 ✗, B001.V000.P020 ✓, B001.V000.P022 ✓, B001.V000.P023 ✓
  - Cut PV generation *(switch)*: 01011.95.03 ✗, B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - PV generation cut *(binary_sensor)*: 01011.95.03 ✗, B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
  - PV generation cut code: 01011.95.03 ✗, B001.V000.P020 ✗, B001.V000.P022 ✓, B001.V000.P023 ✓
- **SUNSTONE-H, dongle** (B000.V001.P068, B000.V002.P059, B000.V002.P065, B000.V002.P067): nothing differs.

### Columns

| Column | Platform | Firmware | Link | Models | Surveys |
| --- | --- | --- | --- | --- | --- |
| 1 | PEARL-H | B000.V000.P071 | dongle | SH15T, SH20T | 5 |
| 2 | SAPPHIRE-H | 01011.95.03 | direct | SH10RT-V112 | 2 |
| 3 | SAPPHIRE-H | 01011.95.03 | dongle | SH10RT-V112 | 2 |
| 4 | SAPPHIRE-H | B001.V000.P020 | direct | SH10RT, SH10RT-V112 | 5 |
| 5 | SAPPHIRE-H | B001.V000.P020 | dongle | SH10RT-20 | 2 |
| 6 | SAPPHIRE-H | B001.V000.P022 | direct | SH6.0RT-20, SH8.0RT-V112 | 4 |
| 7 | SAPPHIRE-H | B001.V000.P022 | dongle | SH8.0RT-V112 | 3 |
| 8 | SAPPHIRE-H | B001.V000.P023 | direct | SH10RT-20, SH10RT-V112, SH5.0RT-V112, SH6.0RT-V112 | 15 |
| 9 | SAPPHIRE-H | B001.V000.P023 | dongle | SH10RT-20, SH10RT-V112, SH5.0RT-V112, SH6.0RT-V112 | 6 |
| 10 | SUNSTONE-H | B000.V001.P068 | dongle | SH6.0RS | 1 |
| 11 | SUNSTONE-H | B000.V002.P059 | dongle | SH10RS | 1 |
| 12 | SUNSTONE-H | B000.V002.P065 | dongle | SH10RS | 1 |
| 13 | SUNSTONE-H | B000.V002.P067 | dongle | SH10RS | 1 |

Left out, with no register dump, no firmware or no way to tell the link:

- `sh10rs-b000v002p057-1p-bleughb-anon-92100523190-battery-sungrow-winet-wlan`
- `sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan`
- `sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan`
- `sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-wlan`
- `sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-7`
- `sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan`
- `sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan`

### Backup power

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Backup frequency | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup mode *(switch)* | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup mode code | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase A current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase A power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase A voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase B current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase B power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase B voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase C current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase C power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Backup phase C voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total backup power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Control

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Active power limitation *(binary_sensor)* | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Active power limitation code | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Active power limitation ratio | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EMS mode *(select)* | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EMS mode selection code | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit ratio | ✓ |  | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Forced charging days *(select)* | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging end 1 *(time)* | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging end 2 *(time)* | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging schedule *(switch)* | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging start 1 *(time)* | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging start 2 *(time)* | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging target SoC 1 *(number)* | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Forced charging target SoC 2 *(number)* | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekday discharge window 1 | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekday discharge window 2 | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekend discharge *(binary_sensor)* | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekend discharge window 1 | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Weekend discharge window 2 | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Everything else

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Power factor | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Power flow code | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Running state | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Running state code | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Shutdown inverter when limited to 0 % power *(binary_sensor)* | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Shutdown inverter when limited to 0 % power code | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Faults and alarms

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Any alarm *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BDC-side fault | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BDC-side permanent fault | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| DC-side fault | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Device alarm | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Fault reported *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Permanent fault | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| System fault 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| System fault 2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Identity and firmware

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ARM software version | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Communication module firmware version | ✓ | – | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| DSP software version | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Device type | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Device type code | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version part 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version part 2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version part 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Protocol version | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Serial number |  |  |  |  |  |  |  |  |  |  |  |  |  |

### Per phase

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Phase A current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Phase A power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Phase A voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Phase B current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase B power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase B voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase C current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase C power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Phase C voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |

### Power

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BDC rated power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Rated output power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Reactive power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total PV input power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total active power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Temperatures

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Device temperature | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The PV trackers

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cut PV generation *(switch)* | ✓ W |  | ✗ | ✗ | ✗ | ✓ W | ✓ W | ✓ W | ✓ W | ✓ | ✓ | ✓ W | ✓ |
| Daily PV generation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily exported energy from PV | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Export from PV this month | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Export from PV this year | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| MPPT1 current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT1 energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT1 power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT1 voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT2 current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT2 energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT2 power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT2 voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MPPT3 current | ✓ | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT3 energy | ✓ | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT3 power | ✓ | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT3 voltage | ✓ | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT4 current | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT4 energy | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT4 power | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| MPPT4 voltage | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | ✗ | 0? | 0? | 0? | ✓ | ✓ |
| PV generating (delayed) *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PV generating *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PV generation cut *(binary_sensor)* | ✓ |  | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PV generation cut code | ✓ |  | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PV generation this month | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| PV generation this year | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| PV power limitation *(binary_sensor)* | ✓ |  | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| PV power limitation code | ✓ |  | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Total PV generation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total exported energy from PV | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total site PV power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The battery

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BMS alarm | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS alarm 2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS fault 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS fault 2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS max charging current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS max discharging current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BMS protection | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery alarm | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery capacity high precision | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charge | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charge (health-rated) | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charge (nominal) | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging (delayed) *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging power | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging power signed | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery charging start power | ✗ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Battery charging start power *(number)* | ✗ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✗ | ✗ | ✗ | ✗ |
| Battery current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging (delayed) *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging power | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging power signed | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery discharging start power | ✗ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Battery discharging start power *(number)* | ✗ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✗ | ✗ | ✗ | ✗ |
| Battery fault | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery firmware version | ✓ | ✗ | – | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery forced charge/discharge *(select)* | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery forced charge/discharge command code | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery forced charge/discharge power | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery forced charge/discharge power *(number)* | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery level | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery level (nominal) | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max SoC | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max SoC *(number)* | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max charging power | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max charging power *(number)* | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max discharging power | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery max discharging power *(number)* | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery min SoC | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery min SoC *(number)* | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery power | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery reserved SoC for backup | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery reserved SoC for backup *(number)* | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery state of health | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery temperature | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Battery voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily PV generation & battery discharge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily battery charge energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily battery charge energy from PV | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily battery discharge energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Firmware version part 4 (Sungrow battery) |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Total PV generation & battery discharge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total battery charge energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total battery charge energy from PV | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total battery discharge energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The grid

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Daily exported energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily imported energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Export power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Export power signed | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Exporting power (delayed) *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Exporting power *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit *(number)* | ✓ |  | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ W | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit maximum | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit minimum | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit mode *(switch)* | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feed-in limit mode code | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Grid frequency | ✓ |  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Grid-side fault | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Import power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Importing power (delayed) *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Importing power *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total exported energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total imported energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The house

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Corrected load power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily consumed energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily consumed energy (smoothed) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Daily direct energy consumption | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Direct consumption this month | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Direct consumption this year | ✗ |  |  | ✓ |  | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Load control *(switch)* | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Load control mode *(select)* | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Load control mode enable code | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Load control mode selection code | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Load power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Negative load power (delayed) *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Negative load power *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Positive load power (delayed) *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Positive load power *(binary_sensor)* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Self-consumption of today | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total consumed energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total direct energy consumption | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### The meter

| Entity | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Meter active power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Meter channel 2 phase A active power | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Meter channel 2 phase B active power | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Meter channel 2 phase C active power | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Meter channel 2 total active power | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Meter phase A active power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Meter phase A current | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase A voltage | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase B active power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Meter phase B current | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase B voltage | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase C active power | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Meter phase C current | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |
| Meter phase C voltage | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | ✓ | 0? | 0? | 0? | 0? | 0? |

## Battery packs

A pack is a device on its own unit with firmware of its own, so a column
is its **BCU firmware**, the battery firmware string the inverter reports
at register 13280. Over the inverter's LAN port the pack answers on unit
200; through a WiNet-S, on unit 2. The model is the one the inverter's
capacity register (5639) matches. A cell is the survey's own decoded
reading of the pack: a component the pack refused with an exception is
absent, one lost to the link is untested.

### What the surveys say so far

**No cell is split.** Wherever two pack models on one firmware were both
surveyed, they answered every entity's registers alike, once what a
house has fitted is set aside. The assumption holds on this evidence;
it is tested only where a column pools more than one of the pack models.

What moves between firmware versions of one platform, over one kind of link:

- **SBHBCU-S, dongle** (22011.04.07, 22011.04.08 32, 22011.04.11): nothing differs.
- **SBRBCU-S, direct** (22011.01.21, 22011.01.27, 22011.01.30): nothing differs.
- **SBRBCU-S, dongle** (22011.01.21, 22011.01.27, 22011.01.27 24, 22011.01.30, 22011.01.30 44): nothing differs.

### Columns

| Column | Platform | Firmware | Link | Models | Surveys |
| --- | --- | --- | --- | --- | --- |
| B1 | SBHBCU-S | 22011.04.07 | unit 2 (dongle) | 25.34 kWh, no single model | 1 |
| B2 | SBHBCU-S | 22011.04.08 32 | unit 2 (dongle) | SBH300 | 1 |
| B3 | SBHBCU-S | 22011.04.11 | unit 2 (dongle) | SBH150, SBH200, SBH400 | 5 |
| B4 | SBRBCU-S | 22011.01.21 | unit 200 (cable) | SBR096 | 1 |
| B5 | SBRBCU-S | 22011.01.21 | unit 2 (dongle) | SBR096 | 1 |
| B6 | SBRBCU-S | 22011.01.27 | unit 200 (cable) | SBR096, SBR128, SBR256 | 4 |
| B7 | SBRBCU-S | 22011.01.27 | unit 2 (dongle) | SBR096 | 2 |
| B8 | SBRBCU-S | 22011.01.27 24 | unit 2 (dongle) | 32 kWh, no single model | 1 |
| B9 | SBRBCU-S | 22011.01.30 | unit 200 (cable) | SBR064, SBR096, SBR128, SBR160, SBR224 | 17 |
| B10 | SBRBCU-S | 22011.01.30 | unit 2 (dongle) | 44.8 kWh, no single model, SBR096, SBR128 | 8 |
| B11 | SBRBCU-S | 22011.01.30 44 | unit 2 (dongle) | SBR192 | 1 |

Left out, with a battery firmware but no pack reading, or no battery firmware:

- `sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan`
- `sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan`
- `sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan`
- `sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-winet`
- `sh15t-b000v000p071-3p-fullhd23-anon-08484305020-battery-unknown-winet-lan`

### Entities

| Entity | B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 | B9 | B10 | B11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pack voltage | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pack current | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pack temperature | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pack level | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pack state of health | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total pack charge energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Total pack discharge energy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Highest cell voltage | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Lowest cell voltage | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Cell voltage spread | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Warmest module temperature | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Coolest module temperature | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module with highest cell | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Highest cell number | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module with lowest cell | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Lowest cell number | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Warmest module | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Coolest module | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 1 highest cell voltage | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 1 lowest cell voltage | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 2 highest cell voltage | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 2 lowest cell voltage | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 3 highest cell voltage | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 3 lowest cell voltage | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 4 highest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 4 lowest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 5 highest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 5 lowest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 6 highest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 6 lowest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 7 highest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 7 lowest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Module 8 highest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | – | ✗ | ✗ |
| Module 8 lowest cell voltage | ✗ | ✗ | ✗ | – | ✗ | ✓ | ✗ | ✗ | – | ✗ | ✗ |
