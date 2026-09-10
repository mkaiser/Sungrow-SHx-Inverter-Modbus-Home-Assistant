# Compatibility

**Generated — do not edit.** `scripts/generate_compatibility.py` builds
this from the fingerprints in
[device-fingerprints/](device-fingerprints/), and CI checks that it
matches.

Which parts of the register map a device answers varies by model, phase
count, wiring, transport and firmware. The specification says what
*exists*, not what a particular machine does with it — so every row
below comes from a fingerprint taken off real hardware, and a model with
no fingerprint is listed as **untested** rather than assumed to work.

## Reported setups

| Setup | By | Model | Connection | Battery (as reported) | ARM firmware | Phases | MPPT3 | MPPT4 | Battery | Sungrow battery | Meter direct | Firmware block | PV power limit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-178-023` | bar12 | SH10RT-20 (`0x0E13`) | WiNet-S / Logger | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-178-041` | bar12 | SH10RT-20 (`0x0E13`) | WiNet-S / Logger | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter` | mkaiser | SH10RT (`0x0E03`) | direct LAN port (reported) | Pylontech Force H1, 14.4 kWh | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | — | yes | yes | no |
| `sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-winet` | fwitten | SH10RT-V112 (`0x0E0F`) | WiNet-S (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | no | — | — | yes | no |
| `sh10rt-v112-3p-fwitten-anon-33442450531-battery-none` | fwitten | SH10RT-V112 (`0x0E0F`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | no | — | no | — | no |
| `sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter` | fwitten | SH10RT-V112 (`0x0E0F`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | yes | yes | — | no |
| `sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-winet` | fwitten | SH10RT-V112 (`0x0E0F`) | WiNet-S (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |
| `sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter` | gerd | SH8.0RT-V112 (`0x0E0E`) | direct LAN port (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | no | no | yes | yes | yes | yes | no |
| `sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan` | gerd | SH8.0RT-V112 (`0x0E0E`) | WiNet-S, WiFi (reported) | — | `ARM_SAPPHIRE-H_V11_V01_B` | three phase 3P4L | yes?[^dongle] | yes?[^dongle] | yes | — | — | yes | no |

[^dongle]: Read through a WiNet-S or Logger, which answers **0**
    where the inverter answers the specification's "unavailable"
    — so a yes here may be a capability the machine does not
    have. Measured on one SH8.0RT-V112 read both ways four
    minutes apart: its own LAN port called MPPT3, MPPT4 and the
    second meter channel unavailable, and its dongle reported
    them as zero. The integration guards this in
    [`capabilities.py`](../src/sungrow_modbus/capabilities.py);
    the table cannot, so it says so.

**Battery (as reported)** is free text, because no register
reports a battery's brand. What Modbus can establish is whether
the pack is a Sungrow one — the SBR/SBH per-module block at unit
200 answers or it does not — and, when it is, *which* model: the
capacity it reports matches one entry in the datasheet table, and
the filename carries that model. For a third-party pack the make
is whatever the person who sent the fingerprint wrote down.

**By** is whoever provided it, and defaults to anonymous: a
fingerprint is worth having either way, and nobody should have to
attach their name to contribute one.

Firmware is in the table because it decides more than the model
does: which registers a device answers moves between versions, so
two fingerprints are only comparable if both say which firmware
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
Modbus** — nothing in the protocol reports it — so the fingerprint
records the round-trip latency as evidence and draws no conclusion.

## What can be attributed to firmware

The question these fingerprints exist to answer: **which**
capabilities move between firmware versions, as opposed to between
models or between transports? Sungrow publishes no release notes, so
the only way to know is to compare two readings that agree on model
and transport and differ only in firmware.

**Nothing, yet — and that is a measurement rather than a gap in
this page.** No two committed readings share a model and a
transport while differing in firmware, so every capability
difference between them is also a model difference and cannot be
separated from it.

What exists, and why none of it pairs up:

| Model | Transport | Inverter firmware |
| --- | --- | --- |
| SH10RT | direct_lan | B001.V000.P020 (1 reading) |
| SH10RT-20 | unsure | B001.V000.P020 (2 readings) |
| SH10RT-V112 | direct_lan | unknown (2 readings) |
| SH10RT-V112 | winet | unknown (2 readings) |
| SH8.0RT-V112 | direct_lan | B001.V000.P022 (1 reading) |
| SH8.0RT-V112 | winet_wlan | B001.V000.P022 (1 reading) |

So the reading that would unlock this is **not** a new model. It
is a second reading of a model already here, on a different
firmware -- which is worth saying plainly, because a wanted list
otherwise reads as 'any hardware welcome' and the most valuable
contribution is the least obvious one.

- **SH10RT** is recorded on B001.V000.P020. Any other firmware on one would make its capabilities attributable.
- **SH10RT-20** is recorded on B001.V000.P020. Any other firmware on one would make its capabilities attributable.
- **SH8.0RT-V112** is recorded on B001.V000.P022. Any other firmware on one would make its capabilities attributable.

## Models this library knows, and whether anybody has tested one

Every model in Appendix 1 of the protocol document. **Untested** means
nobody has sent a fingerprint — not that it does not work. What the
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
| `0x0E0D` | SH6.0RT-V112 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E0E` | SH8.0RT-V112 | RT | **yes** | mppt3, mppt4, pv_power_limitation |
| `0x0E0F` | SH10RT-V112 | RT | **yes** | mppt3, mppt4, pv_power_limitation |
| `0x0E10` | SH5.0RT-20 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E11` | SH6.0RT-20 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E12` | SH8.0RT-20 | RT | untested | mppt3, mppt4, pv_power_limitation |
| `0x0E13` | SH10RT-20 | RT | **yes** | mppt3, mppt4, pv_power_limitation |
| `0x0E20` | SH5T | T | untested | mppt4 |
| `0x0E21` | SH6T | T | untested | mppt4 |
| `0x0E22` | SH8T | T | untested | mppt4 |
| `0x0E23` | SH10T | T | untested | mppt4 |
| `0x0E24` | SH12T | T | untested | mppt4 |
| `0x0E25` | SH15T | T | untested | mppt4 |
| `0x0E26` | SH20T | T | untested | mppt4 |
| `0x0E28` | SH25T | T | untested | mppt4 |
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
   [`scripts/sungrow_scan/portable.py`](../scripts/sungrow_scan/portable.py),
   which needs nothing but Python and the inverter's address.

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
  [device-fingerprints/](device-fingerprints/), if you are comfortable
  with git. This is the format the capability model already reads, so
  it is the shortest path from your hardware to working code.

The capability model in
[`capabilities.py`](../src/sungrow_modbus/capabilities.py) is built from
these, so a fingerprint from an untested model is the single most useful
thing anybody can contribute — including one that says everything works.

