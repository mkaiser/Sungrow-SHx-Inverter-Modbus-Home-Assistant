# Compatibility

**Generated — do not edit.** `scripts/generate/generate_compatibility.py` builds
this from the surveys in
[device-survey/](device-survey/), and CI checks that it
matches.

Which parts of the register map a device answers varies by model, phase
count, wiring, transport and firmware. The specification says what
*exists*, not what a particular machine does with it — so every row
below comes from a survey taken off real hardware, and a model with
no survey is listed as **untested** rather than assumed to work.

## Reported setups

| Setup | By | Model | Connection | Battery (as reported) | ARM firmware | Phases | MPPT3 | MPPT4 | Battery | Sungrow battery | Meter direct | Firmware block | PV power limit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan` | bar12 | SH10RT-20 (`0x0E13`) | WiNet-S, wired (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan` | bar12 | SH10RT-20 (`0x0E13`) | WiNet-S, WiFi (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan` | bar12 | SH10RT-20 (`0x0E13`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | yes | yes | yes | no |
| `sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan` | bar12 | SH10RT-20 (`0x0E13`) | WiNet-S, WiFi (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan` | sisu70 | SH10RT-20 (`0x0E13`) | direct LAN port (reported) | Sungrow SBR128 | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | — | yes | yes | no |
| `sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan` | sisu70 | SH10RT-20 (`0x0E13`) | WiNet-S, wired (reported) | Sungrow SBR128 | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-wlan` | sisu70 | SH10RT-20 (`0x0E13`) | WiNet-S, WiFi (reported) | Sungrow SBR128 | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan` | mkaiser | SH10RT (`0x0E03`) | direct LAN port (reported) | Pylontech Force H1, 14.4kWh | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | — | yes | yes | no |
| `sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan` | fwitten | SH10RT-V112 (`0x0E0F`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | no | — | no | — | no |
| `sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-winet` | fwitten | SH10RT-V112 (`0x0E0F`) | WiNet-S (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | no | — | — | yes | no |
| `sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan` | fwitten | SH10RT-V112 (`0x0E0F`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | yes | yes | — | no |
| `sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-winet` | fwitten | SH10RT-V112 (`0x0E0F`) | WiNet-S (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh10rt-v112-b001v000p023-3p-anonymous-anon-91477823483-battery-sbr160-meter-direct-lan` | anonymous | SH10RT-V112 (`0x0E0F`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | — | yes | yes | no |
| `sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-direct-lan` | fwitten | SH10RT-V112 (`0x0E0F`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | no | — | no | yes | no |
| `sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-winet` | fwitten | SH10RT-V112 (`0x0E0F`) | WiNet-S (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | no | — | — | yes | no |
| `sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan` | fwitten | SH10RT-V112 (`0x0E0F`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | yes | yes | yes | no |
| `sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-winet` | fwitten | SH10RT-V112 (`0x0E0F`) | WiNet-S (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan` | peter_sm | SH10RT-V112 (`0x0E0F`) | direct LAN port (reported) | SBR160 | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | — | yes | yes | no |
| `sh15t-b000v000p071-3p-fullhd23-anon-08484305020-battery-unknown-winet-lan` | FullHD23 | SH15T (`0x0E25`) | WiNet-S, wired (reported), **via a Modbus proxy** | Sungrow SBR128 | `ARM_PEARL-H_V11_V01_A` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | yes |
| `sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan` | jm493 | SH15T (`0x0E25`) | WiNet-S, wired (reported) | — | `ARM_PEARL-H_V11_V01_A` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | yes |
| `sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005` | ra1k_0 | SH20T (`0x0E26`) | WiNet-S, WiFi (reported) | SBH400-V11 | `ARM_PEARL-H_V11_V01_A` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | yes |
| `sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan` | ra1k_0 | SH20T (`0x0E26`) | WiNet-S, WiFi (reported) | SBH400-V11 | `ARM_PEARL-H_V11_V01_A` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | yes |
| `sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan` | Firetribe | SH6.0RT-V112 (`0x0E0D`) | direct LAN port (reported) | SB096 | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | — | yes | yes | no |
| `sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan` | Firetribe | SH6.0RT-V112 (`0x0E0D`) | WiNet-S, wired (reported) | SBR096 | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | — |
| `sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan` | gerd | SH8.0RT-V112 (`0x0E0E`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | yes | yes | yes | no |
| `sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan` | gerd | SH8.0RT-V112 (`0x0E0E`) | WiNet-S, WiFi (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |

[^dongle]: Read through a WiNet-S or Logger, which answers **0**
    where the inverter answers the specification's "unavailable"
    — so a yes here may be a capability the machine does not
    have. Measured on one SH8.0RT-V112 read both ways four
    minutes apart: its own LAN port called MPPT3, MPPT4 and the
    second meter channel unavailable, and its dongle reported
    them as zero. The integration guards this in
    [`capabilities.py`](../src/sungrow_modbus/inverter/capabilities.py);
    the table cannot, so it says so.

**Battery (as reported)** is free text, because no register
reports a battery's brand. What Modbus can establish is whether
the pack is a Sungrow one — the SBR/SBH per-module block at unit
200 answers or it does not — and, when it is, *which* model: the
capacity it reports matches one entry in the datasheet table, and
the filename carries that model. For a third-party pack the make
is whatever the person who sent the survey wrote down.

**By** is whoever provided it, and defaults to anonymous: a
survey is worth having either way, and nobody should have to
attach their name to contribute one.

Firmware is in the table because it decides more than the model
does: which registers a device answers moves between versions, so
two surveys are only comparable if both say which firmware
they were taken on.

**Connection** is marked _(reported)_ where the contributor told
us. Registers 6100-6195 are documented as not forwarded by a
WiNet-S/S2 or Logger, so their answering proves a direct path;
register 13265 names the communication module when there is one,
and only corroborates, because two measured dongles returned it
empty. What no register reaches is the **medium**: a WiNet-S
answers identically wired and over WiFi. One dongle read on both
of its addresses returned identical documents — every probe, every
field, even the TLS certificate — so only the person who plugged
the cable in can say which was which, and that is what _(reported)_
carries.
**WiFi versus Ethernet on a WiNet-S is not determinable over
Modbus** — nothing in the protocol reports it — so the survey
records what the contributor said and draws no conclusion.

## What can be attributed to firmware

The question these surveys exist to answer: **which**
capabilities move between firmware versions, as opposed to between
models or between transports? Sungrow publishes no release notes, so
the only way to know is to compare two readings that agree on model
and transport and differ only in firmware.

### SH10RT-20, winet_lan

Same model, same transport, different firmware — so a difference
here is the firmware's.

| Capability | SAPPHIRE-H_B001.V000.P020 | SAPPHIRE-H_B001.V000.P023 |
| --- | --- | --- |
| unit 2 SBR battery module block | present | — |
| unit 2 inverter device type code | no answer | — |
| unit 200 SBR battery module block | no answer | — |
| unit 248 wallbox serial (direct) | no answer | — |
| unit 3 wallbox serial | no answer | — |

### SH10RT-20, winet_wlan

Same model, same transport, different firmware — so a difference
here is the firmware's.

**No capability differs.** Every curated probe answered the
same way on B001.V000.P020 and B001.V000.P023, which is a result worth having: it says this firmware
change moved nothing this project reads.

### Everything else

Every reading by model and transport. A second firmware in any row
that has only one would make the next pair.

| Model | Transport | Inverter firmware |
| --- | --- | --- |
| SH10RT | direct_lan | B001.V000.P020 (1 reading) |
| SH10RT-20 | direct_lan | B001.V000.P023 (2 readings) |
| SH10RT-20 | winet_lan | B001.V000.P020 (1 reading) |
| SH10RT-20 | winet_lan | B001.V000.P023 (1 reading) |
| SH10RT-20 | winet_wlan | B001.V000.P020 (1 reading) |
| SH10RT-20 | winet_wlan | B001.V000.P023 (2 readings) |
| SH10RT-V112 | direct_lan | B001.V000.P023 (4 readings) |
| SH10RT-V112 | direct_lan | unknown (2 readings) |
| SH10RT-V112 | winet | B001.V000.P023 (2 readings) |
| SH10RT-V112 | winet | unknown (2 readings) |
| SH15T | winet_lan | B000.V000.P071 (2 readings) |
| SH20T | winet_wlan | B000.V000.P071 (2 readings) |
| SH6.0RT-V112 | direct_lan | B001.V000.P023 (1 reading) |
| SH6.0RT-V112 | winet_lan | B001.V000.P023 (1 reading) |
| SH8.0RT-V112 | direct_lan | B001.V000.P022 (1 reading) |
| SH8.0RT-V112 | winet_wlan | B001.V000.P022 (1 reading) |

## Models this library knows, and whether anybody has tested one

Every model in Appendix 1 of the protocol document. **Untested** means
nobody has sent a survey — not that it does not work. What the
library will do on an untested model is decided by its family, and the
last column says what that rules out before anything is even read.

| Code | Model | Family | Tested | Known absent |
| --- | --- | --- | --- | --- |
| `0x0D03` | SH5K-V13 | K | untested | mppt3, mppt4, pv_power_limitation, three_phase |
| `0x0D06` | SH3K6 | K | untested | mppt3, mppt4, pv_power_limitation, three_phase |
| `0x0D07` | SH4K6 | K | untested | mppt3, mppt4, pv_power_limitation, three_phase |
| `0x0D09` | SH5K-20 | K | untested | mppt3, mppt4, pv_power_limitation, three_phase |
| `0x0D0A` | SH3K6-30 | K | untested | mppt3, mppt4, pv_power_limitation, three_phase |
| `0x0D0B` | SH4K6-30 | K | untested | mppt3, mppt4, pv_power_limitation, three_phase |
| `0x0D0C` | SH5K-30 | K | untested | mppt3, mppt4, pv_power_limitation, three_phase |
| `0x0D0D` | SH3.6RS | RS | untested | battery_start_power, firmware_versions, meter_channel_2, mppt3, pv_power_limitation, three_phase |
| `0x0D0F` | SH5.0RS | RS | untested | battery_start_power, firmware_versions, meter_channel_2, mppt3, pv_power_limitation, three_phase |
| `0x0D10` | SH6.0RS | RS | untested | battery_start_power, firmware_versions, meter_channel_2, mppt3, pv_power_limitation, three_phase |
| `0x0D17` | SH3.0RS | RS | untested | battery_start_power, firmware_versions, meter_channel_2, mppt3, pv_power_limitation, three_phase |
| `0x0D18` | SH4.0RS | RS | untested | battery_start_power, firmware_versions, meter_channel_2, mppt3, pv_power_limitation, three_phase |
| `0x0D1A` | SH8.0RS | RS | untested | battery_start_power, firmware_versions, meter_channel_2, mppt3, pv_power_limitation, three_phase |
| `0x0D1B` | SH10RS | RS | untested | battery_start_power, firmware_versions, meter_channel_2, mppt3, pv_power_limitation, three_phase |
| `0x0D27` | MG5RL | MG | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, mppt3, mppt4, pv_power_limitation |
| `0x0D28` | MG6RL | MG | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, mppt3, mppt4, pv_power_limitation |
| `0x0D29` | MG8RL | MG | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, mppt3, mppt4, pv_power_limitation |
| `0x0D2A` | MG10RL | MG | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, mppt3, mppt4, pv_power_limitation |
| `0x0D2B` | SH5RL | RL | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, pv_power_limitation, three_phase |
| `0x0D2C` | SH6RL | RL | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, pv_power_limitation, three_phase |
| `0x0D2D` | SH8RL | RL | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, pv_power_limitation, three_phase |
| `0x0D2E` | SH10RL | RL | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, pv_power_limitation, three_phase |
| `0x0D2F` | MG12RL | MG | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, mppt3, mppt4, pv_power_limitation |
| `0x0D31` | MG7.5RL | MG | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, mppt3, mppt4, pv_power_limitation |
| `0x0D41` | SH3RL | RL | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, pv_power_limitation, three_phase |
| `0x0D42` | SH3.6RL | RL | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, pv_power_limitation, three_phase |
| `0x0D43` | SH4RL | RL | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, meter_channel_2, pv_power_limitation, three_phase |
| `0x0E00` | SH5.0RT | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E01` | SH6.0RT | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E02` | SH8.0RT | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E03` | SH10RT | RT | **yes** | mppt3, mppt4, pv_power_limitation |
| `0x0E08` | SH5.0RT-V122 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E09` | SH6.0RT-V122 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E0A` | SH8.0RT-V122 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E0B` | SH10RT-V122 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E0C` | SH5.0RT-V112 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E0D` | SH6.0RT-V112 | RT | **yes** | mppt3, mppt4, pv_power_limitation |
| `0x0E0E` | SH8.0RT-V112 | RT | **yes** | mppt3, mppt4, pv_power_limitation |
| `0x0E0F` | SH10RT-V112 | RT | **yes** | mppt3, mppt4, pv_power_limitation |
| `0x0E10` | SH5.0RT-20 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E11` | SH6.0RT-20 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E12` | SH8.0RT-20 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E13` | SH10RT-20 | RT | **yes** | mppt3, mppt4, pv_power_limitation |
| `0x0E20` | SH5T | T | untested | battery_start_power, mppt4 |
| `0x0E21` | SH6T | T | untested | battery_start_power, mppt4 |
| `0x0E22` | SH8T | T | untested | battery_start_power, mppt4 |
| `0x0E23` | SH10T | T | untested | battery_start_power, mppt4 |
| `0x0E24` | SH12T | T | untested | battery_start_power, mppt4 |
| `0x0E25` | SH15T | T | **yes** | battery_start_power, mppt4 |
| `0x0E26` | SH20T | T | **yes** | battery_start_power, mppt4 |
| `0x0E28` | SH25T | T | untested | battery_start_power, mppt4 |
| `0x0E39` | SH100CX | CX | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, forced_startup, meter_channel_2, pv_power_limitation |
| `0x0E3A` | SH110CX | CX | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, forced_startup, meter_channel_2, pv_power_limitation |
| `0x0E3D` | SH125CX | CX | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, forced_startup, meter_channel_2, pv_power_limitation |
| `0x0E51` | SH50CX | CX | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, forced_startup, meter_channel_2, pv_power_limitation |
| `0x0E52` | SH80CX | CX | untested | active_power_limit, feed_in_limitation_ratio, firmware_versions, forced_startup, meter_channel_2, pv_power_limitation |

## Sending one

### First, get the file

Either way produces a file with **no serial number, no host address and
no timestamp**. That is deliberate: it is what lets you post it in
public without any private channel needing to exist.

1. **From the integration** — Settings → Devices & Services → Sungrow
   Modbus → the three-dot menu → *Download diagnostics*.
2. **Before installing anything** —
   [`device-survey/scripts/python/sungrow_survey.py`](../device-survey/scripts/python/sungrow_survey.py),
   run from that folder, which needs nothing but Python.

### Then send it, by whichever route you already have

**No GitHub account needed for the first one.**

- **[Discord](https://discord.gg/ZvYBejFkm2)** — drop the file in and say
  what your setup is. Nothing else required, and several people there
  like to help.
- **A [compatibility report](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/new?template=compatibility_report.yml)**
  if you do have a GitHub account. The form asks the questions that turn
  out to matter — model, how many inverters, how it is connected,
  battery, meter, wallbox — so nothing has to be asked afterwards.
- **A pull request** adding your file to
  [device-survey/](device-survey/), if you are comfortable
  with git. This is the format the capability model already reads, so
  it is the shortest path from your hardware to working code.

The capability model in
[`capabilities.py`](../src/sungrow_modbus/inverter/capabilities.py)
is built from these, so a survey from an untested model is the
single most useful thing anybody can contribute — including one that
says everything works.

