# Devices wanted

**Which measurements are still missing, and what each one would settle.**
What has been measured is [compatibility.md](../doc/compatibility.md).

**How to send one:** [Contributing your device diagnosis](README.md#contributing-your-device-diagnosis).

## Most wanted

In the order it would help. Each line names what one diagnosis settles;
details are under [Why each one](#why-each-one).

| # | Device or situation | What one diagnosis settles |
| --- | --- | --- |
| 1 | **An inverter of the K or MG family** (SH*K, MG*RL) | Nothing from either family has been read, so every capability the two are given today is an inference |
| 2 | **A second iHomeManager** (unit 247, port 502, 503 or 504), on firmware other than `SV930.001.00.P020` above all | One unit has been read; a second tells the device's behaviour from that unit's. Its Modbus TCP must be opened in the app first, see [item 2](#2-a-second-ihomemanager) |
| 3 | **A second SH-T (SH10T, SH20T, SH25T…) through its WiNet-S**, with the capability test and feed-in limitation allowed, in daylight with export, and nothing else polling it | One SH15T on P071 held its export limit as if register 13074 stores the word as handed; a second house confirms it, or says it holds on another firmware |
| 4 | **A Sungrow Logger1000, 3000 or 4000** | The first reading of the Logger itself: inverters have been read through one, the Logger not. Answer *a Logger* to the transport question so the diagnosis also reads the Logger itself |
| 5 | **A third wallbox model** (AC007-00), or a second AC011E-01 | One AC011E-01 and two AC22E-01s have been read. A second of either model tells a unit's values from a model's constants; an AC007-00 is unread entirely |
| 6 | **A Sungrow wallbox that no inverter manages** (not set up as an inverter's EV charger in iSolarCloud), with a car charging, set up as an entry of its own with its extended test allowed | Whether its current, start/stop and phases can be set at the wallbox itself. Every wallbox tested so far was an inverter's, which overwrites those settings |
| 7 | **Version 1 between `.95.03` and `.95.12`**, with the capability test and feed-in limitation on | Where the export limit's write scale changes ([#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)) |
| 8 | **An SH-RS on `SUNSTONE-H` P057, P059 or P068**, with the capability test, in daylight | Whether the PV cut (register 31211) works there: it answers on all three, and has been watched cutting on P065, P066 and P067 only |
| 9 | **Any SG string inverter other than an SG5.0RS or SG10RT** | Its tracker and phase count, which decide its entities: the source's table is unverified for most models, and an SG answers 0 for hardware it lacks |
| 10 | **Any inverter on a three-wire grid (3P3L, no neutral)**: the diagnosis shows the output type it reads from register 5002 | On 3P3L, registers 5019-5021 carry line voltages, and the integration creates no phase voltages or phase powers there. One reading shows what to create instead |
| 11 | **Any hybrid in low-SoC standby**: the battery at its minimum, no PV, usually at night. Run `scripts/diagnosis.sh tests <host> --forced-startup`, or in Home Assistant the `run_capability_test` action with *Forced startup only* | Whether register 13017 (the *Low-SoC standby* switch) wakes this firmware and sends it back to sleep. Watched on P020, P022 and P023 only, so the switch is created there only: an SH-T above all, and an SH-RT that has never run it, whose factory 0 the restore puts back as `0x55` |
| 12 | **A Sungrow wallbox switched off (disabled) in the app**, once with a car plugged in and once without | What the control pilot (register 21312) reads then, which is what *Car connected* is made from: it has been read unplugged, connected and charging, but never while the wallbox is disabled |
| 13 | **A hybrid whose grid import limit nobody has watched**: an SH-T, an SH-RS on other firmware than P066, a single SH-RT on version 1 `.95.03`, or, above all, **any master/slave cluster**; with `--import-limit` (in Home Assistant, the `run_capability_test` action), after dark | Which firmware and models obey the site import limit (register 32998), and whether a cluster is what stops it: it held at every single inverter tried and failed at both clusters |
| 14 | **An SH-T (SH10T, SH15T, SH20T, SH25T) read over its own LAN port**, with the capability test allowed, in daylight | Every SH-T so far was read through a WiNet-S or a Logger, so what the capability test's checks do over a cable on the T series is unmeasured |

## Not needed any more

Already read several times over. Please send one of these **only** if it
differs from what is in [`results/inverter/`](results/inverter/) in one of the ways below:

- an **SH10RT-20 or SH10RT-V112 on P023**, on either path (eight
  inverters);
- an **SH8.0RT-V112 on P022** or an **SH6.0RT-V112 on P023**;
- an **SBR096** behind any of those;
- a **WiNet-S certificate hash**: two houses, a WiNet-S and a wallbox all
  serve one certificate, so another hash adds nothing.

It is still worth sending when it brings **a firmware update** since your
last diagnosis (that is how a silent change is noticed), **the first capability
test** for its model and firmware, **both paths** of one machine minutes
apart, or a **battery size** nobody has read.

A **second master/slave cluster** was read on 2026-11-17 and kept both rules the
config flow rests on -- a slave's own unit id is 2, and it answers 0 where a lone
inverter answers 0xFFFF -- so a third is no longer wanted on its own account.

## Where the coverage is today

<!-- coverage: generated by scripts/generate/generate_devices_wanted.py -->

Generated from [`results/`](results/) by `scripts/generate/generate_devices_wanted.py`; edit that, not this.

37 inverters, each counted once by its stand-in serial however many times it was read: 34 hybrids and 3 SG string inverters. Beside them 3 wallboxes read, 2 at their own address and 1 on an inverter's bus, and an iHomeManager.

| Axis | Covered | Missing |
| --- | --- | --- |
| Hybrid inverter model | **13 of 61**: SH10RS, SH10RT, SH10RT-20, SH10RT-V112, SH10T, SH15T, SH20T, SH25T, SH5.0RT-V112, SH6.0RS, SH6.0RT-20, SH6.0RT-V112, SH8.0RT-V112 | the other models |
| Product family | RS, RT, T | CX, K, MG, RL, TL |
| SG string inverter model | **2 of 40**: SG10RT, SG5.0RS | the other models |
| Phase / output type | single phase, three phase 3P4L | three phase 3P3L |
| Inverter firmware | PEARL-H `B000.V000.P067`, `B000.V000.P071`, `B001.V001.P038`; SAPPHIRE-H `B001.V000.P020`, `B001.V000.P022`, `B001.V000.P023`; SUNSTONE-H `B000.V001.P066`, `B000.V001.P068`, `B000.V002.P057`, `B000.V002.P059`, `B000.V002.P065`, `B000.V002.P067` | any other |
| Version 1 | PEARL-H `01011.01.42`, `01011.01.45`, `01011.94.41`, `01011.95.41`; SAPPHIRE-H `01011.95.03`, `01011.95.11`, `01011.95.12`, `01011.95.13`, `01011.95.14`; SUNSTONE-H `01011.02.61`, `01011.02.65`, `01011.02.67`, `01011.02.69`, `01011.03.68` | see item 7 |
| Communication module | `WINET-SV200.001.00` P036, P038, P040, P043, P044, P045; `WINET-SV300.001.03` P021, P024, P030, P031, P032, P033 | any other |
| Sungrow battery | SBH100, SBH150, SBH200, SBH300, SBH400, SBR064, SBR096, SBR128, SBR160, SBR192, SBR224, SBR256 | SBH250, SBH350 |
| Third-party battery | 4 inverters | other packs |
| Transport | Logger, WiNet-S, WiNet-S or Logger, WiNet-S over WiFi, WiNet-S wired, direct LAN; 10 inverters through a Modbus proxy | any route not listed |
| Capability test | 17 of 34 hybrid inverters | every other model and firmware |
| Wallbox | AC011E-01, AC22E-01 | AC007-00 |
| iHomeManager | read | a second unit |
| Sungrow Logger | the Logger itself unread; 2 inverters read through one | the Logger's own registers |

<!-- coverage: end -->

## Why each one

What has been measured, and what each answer would change, is in the
[wiki](../.wiki/wiki/index.md); these say only why a diagnosis is wanted.

### 1. An inverter of the K or MG family

Nothing from either family has been read. Every capability they are given in
[compatibility.md](../doc/compatibility.md) is inferred from the family; one
diagnosis confirms the lot or finds the first exception. Fewer entities than the
YAML package gave on the same machine is itself a finding.

### 2. A second iHomeManager

One unit has been read, on `iHomeManager-SV930.001.00.P020`: a second, on other
firmware above all, shows which of its readings are the device's and which that
unit's. **Open its Modbus TCP first**, in the iSolarCloud app:
*iHomeManager settings → Forwarding channel settings*, port 502, 503 or 504,
SSL off. Each port takes one connection, so stop other clients. The diagnosis
finds it at unit 247 and writes a document of its own. In Home Assistant,
*Add integration* → *Search my network* offers it too; add it and press
*Diagnosis: start*. It may also silence
inverter registers 5741-5746 (#647, #651). See
[iHomeManager](../.wiki/wiki/entities/device-ihomemanager.md).

### 3. A second SH-T through its WiNet-S, in daylight, with export

Every T so far was read through a WiNet-S or a Logger, and the T seems to have no LAN
port of its own (an SH20T owner says so; Sungrow's SH5T-SH25T manual lists a
WiNet-S2 and a COM2 terminal). Run it with the capability test, feed-in
limitation allowed, while the house exports, with every other poller stopped: through a dongle only
what the inverter does counts. One SH15T held 106.5 W for a word of 125, which says P071 stores
the word as handed; its readback was refused by a busy dongle. An SBH pack's cell layout, which a dongle refuses, stays unread. See
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

### 5. A third wallbox model

Sungrow publishes no register document, so every name in the map comes from
reading. An AC011E-01 read on 2026-11-16 settled the output current setting's
scale -- 0.1 A per count, against 0.01 A in another source's AC011E-based map
([wallbox_registers.md](../doc/wallbox_registers.md)) -- and found a wallbox
at unit 4 behind a WiNet-S, where the only one measured before answered at 3.
What is left is telling one unit's values from a model's constants, which
needs a second of either model, and the AC007-00, which is unread. The
diagnosis finds one behind a WiNet-S, or at its own address on port 516.

### 6. A Sungrow wallbox that no inverter manages

A managed wallbox is controlled at its inverter, which is tested with a car charging
([wallbox](../.wiki/wiki/entities/device-wallbox.md)). On one nobody else drives, the wallbox's own
registers are the control, and none of them has been watched with a car: the current and its scale,
start and stop, the phase switch, and what it falls back to when nobody reads it. The test runs from the
wallbox's own entry in Home Assistant, interrupts the charge for a few minutes and puts everything
back. If evcc drives yours, stop evcc first.

### 7. Version 1 between `.95.03` and `.95.12`

13074 stores a written word 1:1 only on `.95.03` and multiplies it by ten on
every later firmware measured ([register 13074](../.wiki/wiki/entities/register-13074.md),
[#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)).
A machine in between places the change (one on `.95.11` has been read, but
without the scale): `diagnosis.sh tests <host>
--export-scale` asks with one write that changes nothing. That the factor is ten
watts, and not a share of the rated power, was settled on a 6 kW inverter.

### 8. An SH-RS on P057, P059 or P068

Register 31211, the PV cut, answers on all three, and has been watched cutting
on P065, P066 and P067, so the integration offers the switch on those
([register 31211](../.wiki/wiki/entities/register-31211.md)). A capability test
in daylight, with the PV cut allowed, watches it on one more. P066 was settled
on 2026-11-20 over RS485: 811 W before, 0 W during, 576 W after.

### 9. An SG string inverter other than an SG5.0RS or SG10RT

The SG map is from another project's source and unmeasured for most models,
and an SG answers 0 for hardware it lacks, so its tracker and phase count
decide its entities ([SG-RS](../.wiki/wiki/entities/device-sg-rs.md), [SG-RT](../.wiki/wiki/entities/device-sg-rt.md)).

### 10. An inverter on a three-wire grid (3P3L)

Register 5002 says 3P3L when there is no neutral; then 5019-5021 carry line
voltages, and the integration creates no phase voltages or phase powers.
Nothing on 3P3L has been read.

### 11. A hybrid in low-SoC standby

Register 13017 wakes a standby inverter and sends it back to sleep on P020, P022
and P023, watched ([register 13017](../.wiki/wiki/entities/register-13017.md)); the
switch is created only there. A run in standby, battery at its minimum and no
PV, watches it on one more firmware.

### 12. A wallbox switched off in the app

*Car connected* is made from the control pilot (register 21312), read unplugged, connected and charging
but never while the wallbox is disabled (*Ladegerät aktivieren* off, status 8). Two read-only runs, with a car
plugged in and without, say whether it can be trusted then.

## Also worth sending

- **Both transports of one machine**, minutes apart: every such pair so far
  produced a rule.
- **The same machine after a firmware update**: updates arrive silently.

## Not wanted

- Readings from an installation whose owner has not agreed. A stand-in serial
  is not consent.
- A reading taken while something else polled the inverter.

### 13. A hybrid whose grid import limit nobody has watched

Register 32998 held on P020, P022, P023 and the SH-RS's P066
([register 32998](../.wiki/wiki/entities/register-32998.md)). It did not at two
clusters. The `--import-limit` check
measures it and puts everything back; it writes only with your leave.
