# Devices wanted

**Which measurements are still missing, and what each one would settle.**
What has been measured is [compatibility.md](../doc/compatibility.md).

**How to send one:** [Contributing your device diagnosis](README.md#contributing-your-device-diagnosis).

## Most wanted

In the order it would help. Each line names what one diagnosis settles;
details are under [Why each one](#why-each-one).

| # | Device or situation | What one diagnosis settles |
| --- | --- | --- |
| 1 | **A single-phase inverter of the K or MG family** (SH*K, MG*) | Single phase is read on the SH-RS and on an SG5.0RS; nothing from the K or MG family has been, so every capability those two families are given today is an inference |
| 2 | **An iHomeManager** (unit 247, port 502, 503 or 504) | The first reading of the device at all. Its Modbus TCP must be opened in the app first, see [item 2](#2-an-ihomemanager) |
| 3 | **An SH-T (SH15T, SH20T…) through its WiNet-S**, with the capability test and feed-in limitation allowed, in daylight with export | Every T so far was read through a WiNet-S or a Logger, and the T seems to have no LAN port of its own. Settles the export limit's write scale (register 13074) on P071 by what the inverter does, and the PV cut on P071 |
| 4 | **A Sungrow Logger1000, 3000 or 4000** | The first reading of the Logger itself: inverters have been read through one, the Logger not. Answer *a Logger* to the transport question so the diagnosis also reads the Logger itself |
| 5 | **A wallbox other than the one already read**, an AC011E-01 above all | Which of its registers identify a unit and which are a model constant, and a scale another source reads differently |
| 6 | **A charging car**, at any house with a Sungrow wallbox | What input 21313 does over a session, and whether 21308/21310 are signed. Two runs a few minutes apart while charging |
| 7 | **Version 1 between `.95.03` and `.95.12`, or a `.95.14` that is not 10 kW** | Where the export limit's write scale changes ([#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)) |
| 8 | **A second master/slave cluster** | Whether a slave's address 2 is a rule or one house's convention |
| 9 | **An SH-RS on `SUNSTONE-H` P057, P059, P066, P067 or P068**, with the capability test, in daylight | Whether the PV cut (register 31211) works there: it answers on all five, and has been watched cutting on P065 only |
| 10 | **Any SG string inverter other than an SG5.0RS** | Its tracker and phase count, which decide its entities: the source's table is unverified for most models, and an SG answers 0 for hardware it lacks |
| 11 | **Any inverter on a three-wire grid (3P3L, no neutral)**: the diagnosis shows the output type it reads from register 5002 | On 3P3L, registers 5019-5021 carry line voltages, and the integration creates no phase voltages or phase powers there. One reading shows what to create instead |
| 12 | **Any hybrid in low-SoC standby**: the battery at its minimum, no PV, usually at night. Run `scripts/diagnosis.sh tests <host> --forced-startup`, or in Home Assistant the `run_capability_test` action with *Forced startup only* | Whether *Forced startup under low SoC* (register 13017) wakes this firmware and sends it back to sleep. Watched by hand on P023 only, so the switch is created there only; the check has not run on hardware yet |

## Not needed any more

Already read several times over. Please send one of these **only** if it
differs from what is in [`results/inverter/`](results/inverter/) in one of the ways below:

- an **SH10RT, SH10RT-20 or SH10RT-V112 on P023**, on either path (five
  houses);
- an **SH8.0RT-V112 on P022** or an **SH6.0RT-V112 on P023**;
- an **SBR096** behind any of those;
- a **WiNet-S certificate hash**: two houses, a WiNet-S and a wallbox all
  serve one certificate, so another hash adds nothing.

It is still worth sending when it brings **a firmware update** since your
last diagnosis (that is how a silent change is noticed), **the first capability
test** for its model and firmware, **both paths** of one machine minutes
apart, or a **battery size** nobody has read.

## Where the coverage is today

28 documents from 10 houses: 11 inverters, 13 inverter documents with a
capability test, and one wallbox read at its own address.

| Axis | Covered | Missing |
| --- | --- | --- |
| Inverter model | **8 of 42**: SH10RT, SH10RT-20, SH5.0RT-V112, SH6.0RT-V112, SH8.0RT-V112, SH10RT-V112, SH15T, SH20T | every model outside RT and T |
| Product family | RT and T | RS, MG, RL, K, CX, TL (MG10-25TL) |
| Phase / output type | three phase 3P4L only | **single phase**, and three phase 3P3L |
| Inverter firmware | `B001.V000.P020`, `P022`, `P023`, `B000.V000.P071` | a fifth |
| Version 1 | `SAPPHIRE-H_01011.95.03`, `.95.12`, `.95.13`, `.95.14`, `PEARL-H_01011.01.45` | see item 7 |
| Communication module | WiNet-S `P040`, `P043`, `P044`, `P045`; WiNet-S2 `P032`, `P033` | a Logger |
| Battery | SBR096, SBR128, SBR160, SBH200, SBH400, one Pylontech | the other SBR and SBH sizes, other third-party packs |
| Transport | direct LAN, WiNet-S and WiNet-S2, wired and WiFi | a Logger, a Modbus proxy, **a T on a cable, if one exists** |
| Wallbox | AC22E-01 | AC011E-01, AC007-00 |
| iHomeManager | none | any |
| Sungrow Logger | two inverters read through a Logger1000A; the Logger itself unread | the Logger's own registers |

## Why each one

What has been measured, and what each answer would change, is in the
[wiki](../.wiki/wiki/index.md); these say only why a diagnosis is wanted.

### 1. Any single-phase inverter

Nothing single-phase has been read. Every RS capability in
[compatibility.md](../doc/compatibility.md) is inferred from the family; one
diagnosis confirms the lot or finds the first exception. Fewer entities than the
YAML package gave on the same machine is itself a finding.

### 2. An iHomeManager

Never measured. **Open its Modbus TCP first**, in the iSolarCloud app:
*iHomeManager settings → Forwarding channel settings*, port 502, 503 or 504,
SSL off. Each port takes one connection, so stop other clients. The diagnosis
finds it at unit 247 and writes a document of its own. In Home Assistant,
*Add integration* → *Search my network* offers it too; add it and press
*Diagnosis: start*. It may also silence
inverter registers 5741-5746 (#647, #651). See
[iHomeManager](../.wiki/wiki/entities/device-ihomemanager.md).

### 3. An SH-T through its WiNet-S, in daylight, with export

Every T so far was read through a WiNet-S or a Logger, and the T seems to have no LAN
port of its own (an SH20T owner says so; Sungrow's SH5T-SH25T manual lists a
WiNet-S2 and a COM2 terminal). Run it with the capability test, feed-in
limitation and PV cut allowed, while the house exports: through a dongle only
what the inverter does counts, and that settles 13074's write scale and the PV
cut on P071. An SBH pack's cell layout, which a dongle refuses, stays unread. See
[SH-T](../.wiki/wiki/entities/device-sh-t.md).

### 4. A Sungrow Logger1000, 3000 or 4000

The Logger itself never measured: two inverters have been read through a Logger1000A, each on a
port of its own, but the Logger refused the integration's identity read. It fronts a whole installation, the shape the
one-entry-per-endpoint design was built for. **Answer "a Logger" to the
transport question** so the diagnosis also reads it at unit 247, and say which
unit ids it lists. A current Logger1000 opens only port 516 with TLS; the
diagnosis tries that too, so no setting needs changing. In Home Assistant,
*Search my network* offers it too; add it and press *Diagnosis: start*. See
[Logger](../.wiki/wiki/entities/device-logger.md).

### 5. A wallbox other than the AC22E-01

Sungrow publishes no register document. An AC011E-01 would settle the output
current setting's scale, 0.1 A here against 0.01 A in another source's
AC011E-based map ([wallbox_registers.md](../doc/wallbox_registers.md)). The
diagnosis finds one behind a WiNet-S, or at its own address on port 516.

### 6. A charging car

Two runs a few minutes apart while a car charges: what input 21313 does over
a session, and whether 21308/21310 are signed.

### 7. Version 1 between `.95.03` and `.95.12`, or a `.95.14` that is not 10 kW

13074 stores a written word 1:1 only on `.95.03` and multiplies it by ten on
every later firmware measured ([register 13074](../.wiki/wiki/entities/register-13074.md),
[#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)).
A machine in between places the change: `diagnosis.sh tests <host>
--export-scale` asks with one write that changes nothing. A `.95.14` that is
not 10 kW tells "0.1 % of rated power" from "10 W" apart, which coincide at
10 kW. A 5 kW SH5.0RT-V112 on `.95.14` has answered the probe with a refusal, which both
readings give: a capability test on one, with limitation on, settles it.

### 8. An SBR192 on a direct link

The one size not yet read over a cable ([SBR battery](../.wiki/wiki/entities/device-sbr-battery.md)).

### 9. A second master/slave cluster

One cluster gave two rules the config flow relies on: a slave's device
address is 2, and a slave answers 0 where a standalone inverter answers
0xFFFF. A second shows whether they are rules or one house's convention.

## Also worth sending

- **Both transports of one machine**, minutes apart: every such pair so far
  produced a rule.
- **The same machine after a firmware update**: updates arrive silently.

## Not wanted

- Readings from an installation whose owner has not agreed. A stand-in serial
  is not consent.
- A reading taken while something else polled the inverter.
