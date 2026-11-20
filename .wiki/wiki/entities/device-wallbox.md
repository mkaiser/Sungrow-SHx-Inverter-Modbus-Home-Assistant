---
type: entity
title: Sungrow AC wallbox
tags: [wallbox, ac22e-01, ac011e-01, sub-device, tls]
created: '2026-10-29'
---

# Sungrow AC wallbox

AC011E-01 and AC22E-01. In the integration it is a **device of its own**,
with 35 fields in five components (`src/sungrow_modbus/wallbox/`). Its
entities are **read only**. The capability test writes to it only with the
owner's leave **and only when it is declared standalone**: a wallbox a hybrid
inverter manages is controlled through the inverter, not through its own
registers ([below](#under-an-inverters-energy-management)).

## Under an inverter's energy management

A wallbox on a hybrid inverter's bus (its EV charger settings in iSolarCloud) is driven by the
inverter. Measured at [gerd](installation-gerd.md) on 2026-11-14
([the session](../sources/gerd-wallbox-inverter-control-2026-11-14-summary.md)):

- **The inverter writes the wallbox's output current (holding 21203)** every few seconds; a write
  to it from outside is overwritten within seconds and the car does not follow it. After a start
  it ramps from 6 A by about 1.4 A every 5 s, and **the car follows it**, which settles 21203 at
  0.1 A per count.
- **The control is the inverter's holding block at unit 1**: 33540 charging on (0xAA) / off
  (0x55), 33541 the mode (160 fast, 161 PV surplus, 162 scheduled, 163 user defined), 33545 the user-defined
  current at 0.1 A per count, writable only in user-defined mode, 6 A to (at least) the rating.
  Switching the mode can end a session; charging on starts it again. Over the cable and through
  the WiNet-S alike. The library's map is `src/sungrow_modbus/hybrid_inverter/ev_charger.py`; the
  inverter's entry offers these four words as controls only on firmware where the writes were
  watched (`CONFIRMED_ON_FIRMWARE` in `src/sungrow_modbus/hybrid_inverter/capabilities.py`); run
  from Home Assistant at gerd's, each took its write
  ([the controls](../sources/gerd-wallbox-ha-controls-2026-11-14-summary.md)). Since the inverter
  takes a current above the rating, that entry offers the user current only up to the wallbox's
  own rated current (input 21263), wherever one is read -- behind the dongle here, or in the
  wallbox's own entry -- and 32 A, the largest Sungrow wallbox's rating, where nothing reports
  one.
- **What the night of 2026-11-16/17 added** ([the night](../sources/gerd-wallbox-night-2026-11-16-summary.md)):
  in user-defined mode 21203 settles at the user current, in 0.1 A, and the car draws about 0.7 A
  less, **but it follows a change 4-5 minutes late** while the car follows within seconds
  ([the afternoon](../sources/gerd-wallbox-2026-11-17-afternoon-summary.md)); in fast mode it is the inverter's *offer* (24-28 A) above the 16 A a phase the car takes, so it is
  not the car's current there. **A change of mode to or from user defined while charging ended the session
  within 6 s** that night, and charging on restarts it; the afternoon after, with the battery off its minimum
  and a little PV, the same changes in both directions did not end it
  ([the afternoon](../sources/gerd-wallbox-2026-11-17-afternoon-summary.md)), so a writer must expect either (about 6 s, full power in about 40 s); a user-defined mode
  entered with charging off turns charging on by itself and starts at 6 A. Writing charging on while on,
  or the mode it already has, changes nothing. The inverter does not end a fast charge at the home battery's
  minimum (a charge ran for hours at 0.2-0.5 %), and a car can suspend a charge for hours with the inverter's
  word on (`suspended by the vehicle`), and finish the charge later by itself
  ([the morning](../sources/gerd-car-morning-2026-11-17-summary.md)); what ends a session without a write is open
  ([why a managed wallbox stops charging](../queries/why-does-a-managed-wallbox-stop-charging.md)).
- **The afternoon of 2026-11-17** ([the afternoon](../sources/gerd-wallbox-2026-11-17-afternoon-summary.md)):
  the four controls from Home Assistant with a car charging each did what they say; the managed test passed
  again from the terminal and its restore (settle, then watch the car) held. With nothing written, the car
  was cut to 6-8 A and ramped back four times right after house load spikes, within one session. The managed
  test cannot run from Home Assistant where the inverter entry is on the LAN cable: the link between the
  wallbox entry and its inverter entry is made only through the dongle probe.
- **The afternoon of 2026-11-20** ([the afternoon](../sources/gerd-wallbox-2026-11-20-summary.md)):
  **162 is *scheduled charging*** (*Terminiertes Laden*): 33542 is its target in 0.1 kWh and 33543/33544
  its departure, a u32 low word first holding the local time as if it were UTC; it charges at the minimum
  or at full power, not at a computed rate, keeps its choice through a mid-session change, and ends the
  session at its target. A car stopped for 15 minutes starts again on charging on over Modbus, no replug.
  **A charging off reads back on for about 10 s** before it reads off, and a stop reaches the car 10-18 s
  before the inverter's word reads off. With one client per path a mode change ended no session.
  **33546-33549 are the user-defined mode's daily window** (start and end, local time as if UTC; midnight to
  midnight is a whole day): its end ends the session and moves the window to the next day, its start did not
  hold back a charge the save switched on ([the evening](../sources/gerd-wallbox-2026-11-20-user-window-summary.md)).
  Through the WiNet-S the block read 360 times in an hour at 10 s with none lost.
  **The window's start switches charging on by itself** as its end switches it off, a daily schedule; and each
  mode's words take a write only in that mode -- the window only in 163 and only as one four-word write
  ([18:20](../sources/gerd-wallbox-2026-11-20-test4-summary.md)).
- Nothing on the wallbox alone tells a managed wallbox from a standalone one (input 21314 read 1
  idle and 3 charging, as on every earlier reading), so the capability test needs the owner to
  say so (`Options.standalone`), and refuses a setting that moves with nothing written. In Home
  Assistant that is a wallbox entry's own option, *Does no inverter manage this wallbox?*, off
  until it is switched on. **Behaviour is what can be inferred**, and it is shown rather than
  acted on: 21203 moving during a charge with nothing written says managed, holding still through
  a charge suggests standalone, and an idle wallbox says nothing
  (`src/sungrow_modbus/wallbox/management.py`, the `management` attribute of *Diagnosis: test
  summary*).
- **And nothing on the inverter alone tells it either.** Holding 33541 reads **161**, a named
  mode (*PV surplus*), with the user current at 16.0 A and energy purchase on, at
  [mkaiser](installation-mkaiser.md)'s, [swo14](installation-swo14.md)'s and
  [peter-sm](installation-peter-sm.md)'s -- three houses with no wallbox at all. So that is the
  block's factory state, not a report of a wallbox, and `Capability.EV_CHARGER`
  (`src/sungrow_modbus/hybrid_inverter/capabilities.py`), which grants itself on a named code,
  is granted where there is nothing to charge. The one reading that differs is the house with
  the [AC011E-01](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-14076202309-battery-unknown-winet-summary.md):
  163 (*user defined*) at 10.0 A. **What does tell**: a wallbox answering on the inverter's bus,
  the app showing EV charger settings under the inverter, and 21203 moving with nothing writing
  it. So the four controls ask for a wallbox on the bus as well as the capability
  (`SungrowRuntimeData.has_wallbox`, `custom_components/sungrow_modbus/coordinator.py`): without
  one they are not created, whatever 33541 reads.

- **The phases are the inverter's too**: it switches a managed wallbox to one phase by itself,
  by owners' reports in PV surplus with grid purchase off, and nothing documented chooses them;
  the wallbox's own 21204 did not ([a managed wallbox's phases](../concepts/managed-wallbox-phases.md)).

The app's enable (*Ladegerät aktivieren*) is holding 21211 and its Start/Stop holding 21212 (0
starts). The app's system parameters are the wallbox's own holding registers, not the inverter's:
Plug&Play 21298, the offline current 21299 (0.1 A) and the power limit 21313 (0.1 kW, which the
maximum current at input 21263 and the nominal power at 21273 follow); a disabled charger reads
status **8** ([the app's settings](../sources/gerd-wallbox-app-settings-2026-11-14-summary.md)). A disable written
over Modbus on 2026-11-13 ended a charge that the enable written back did not resume, and offers
of 5 A and 0 left the wallbox suspended ([the run](../sources/gerd-wallbox-capability-test-2026-11-13-summary.md)); the capability test no longer writes either.

## Two ways in

| Path | Protocol | Unit | In the integration |
| --- | --- | --- | --- |
| at its own LAN address | Modbus TCP inside TLS, port **516** | **248** | **an entry of its own**, offered by the network search; the preferred path |
| through the [WiNet-S](device-winet-s.md) | Modbus TCP, port 502 | **3** (2 or 4 reported elsewhere: [which unit](../queries/which-unit-does-a-winet-s-give-a-wallbox.md)) | found behind the inverter's entry by itself, read only, and only while no entry of its own has the same serial |

At its own address it answers mDNS as `_http._tcp` on port 516, which is its Modbus TLS port,
not a web page (it serves none), with a TXT record naming its model, serial and units 3 and
248 ([gerd](../sources/gerd-mdns-2026-11-11-summary.md)).

The network search looks on port 516 and offers a wallbox that answers there
over TLS as **an entry of its own**, identified by its own serial. An inverter
entry that finds the same wallbox at unit 3 leaves it to that entry and
removes its own sub-device, so one wallbox is one device; only the entry of
its own writes to it (`custom_components/sungrow_modbus/__init__.py`,
`wallbox_capability_test.py`). That entry has a *Diagnosis: start*
whose read-only mode writes the same wallbox document as `wallbox_direct.py`
(`custom_components/sungrow_modbus/device_diagnosis.py`), and a capability
test of its own in the extended modes, with its own leave and cap in the
entry's options (`custom_components/sungrow_modbus/wallbox_diagnosis.py`).
An inverter entry on the LAN cable never sees the wallbox, so the wallbox
entry's options ask which inverter manages it; the named entry then gets the
EV charger controls and runs the managed test's writes (`CONF_WALLBOX_MANAGED_BY`,
`tests/test_wallbox_pairing.py`; on hardware:
[the pairing](../sources/gerd-wallbox-2026-11-20-pairing-summary.md)).
Never reachable through the inverter's own LAN port
(every unit 0-255 swept). It needs no [iHomeManager](device-ihomemanager.md),
and sweeping for one cannot find it. Where an iHomeManager is installed it
drives the wallbox over 516 itself, so a wallbox entry may find the port taken
(reported to evcc, not measured here:
[evcc cross-reference](../sources/cross-reference-evcc-summary.md)).

**Sixty seconds without Modbus traffic and the wallbox drops the
connection** and applies its fallback current, by evcc's account; evcc reads
the status every 30 s for it
([evcc cross-reference](../sources/cross-reference-evcc-summary.md)). The
integration reads the wallbox on the inverter's fast tier
(`custom_components/sungrow_modbus/coordinator.py`), inside that by default;
a fast tier set above 60 s would let the wallbox drop the session.

**Through a WiNet-S, not faster than every 10 s**: polled faster, the dongle
goes into a fault state, by an ioBroker user's account
([shcshc76 cross-reference](../sources/cross-reference-shcshc76-summary.md));
not measured here. The fast tier's default is exactly 10 s
(`DEFAULT_INTERVALS` in `src/sungrow_modbus/hybrid_inverter/registers.py`),
so the defaults sit on that edge and a shorter fast tier would cross it.

## Reading rules

- **Over TLS a read must start on a data point's first register.** 21295 ×24
  answers, 21296 ×10 times out. A pooled block must begin at one.
- **A dongle forwards any start**, and answers 0 for several registers the
  direct path reads.
- **The serial (input 21201-21206) sits just below the model name.**
  `wallbox.probe_units` reads the name. The integration reads the serial
  once, for the device page's `serial_number`, and identifies the device by
  the inverter's serial plus `-wallbox`. The serial words are masked when
  the document is published, and replaced by `wallbox.serial_anonymized_hashed`;
  see [serial anonymization](../concepts/serial-anonymization.md).

`sungrow_diagnosis.py` sweeps port 516. A wallbox found there is read by
`device-diagnosis/scripts/python/wallbox_direct.py` into a **wallbox
document** of its own, published in `device-diagnosis/results/wallbox/` beside
`results/inverter/`.

The register map, with how strongly each row is held:
[wallbox registers](../sources/wallbox-registers-summary.md).

## Measured

One AC22E-01 at [gerd](installation-gerd.md): through the dongle in the
[WiNet-S diagnosis](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-summary.md),
and at its own address in the
[wallbox document](../sources/ac22e01-gerd-anon-41346964423-wallbox-tls-summary.md).
Read directly again on 2026-10-29: holding 21250-21259 is a constant
20-digit ASCII number, shaped like an identifier, and is masked like the serial;
input 21267 ticks about once per 5 s whatever a client reads or writes,
the shape of an uptime counter; the start mode read 3, outside the
documented 0-2. Checked against Sungrow's own portal on 2026-10-30: input
21201-21206 is the serial it shows, and 21300 and 21310 count lifetime and
session energy in Wh; see
[the portal cross-check](../sources/gerd-wallbox-isolarcloud-2026-10-30-summary.md).
After a 7854 Wh session that ended at 11:33 on 2026-11-01, input 21310 still held the session's
energy, input 21313 read 0 and the start mode 3
([the dongle reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2-summary.md)).
During a session on 2026-11-03, read over TLS and through the dongle, input 21313 read **527**
in both, the start mode 3, and **input 21320 held the time of the reading** rather than an end
([TLS](../sources/ac22e01-gerd-anon-41346964423-wallbox-tls-2-summary.md),
[dongle](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3-summary.md)). Over the whole session
([the log](../sources/gerd-wallbox-charging-session-2026-11-03-summary.md))
21313 fell to 0 when the charging ended, 94 s after the power did, as the
status went 3, 5 (suspended by the vehicle), 6 (completed). Whether 21308/21310
are signed is still open: the session never left 10.7 kW.
What is fixed and what moves is in
[wallbox registers](../sources/wallbox-registers-summary.md).
RS485 at unit 248 is reported by others and never measured here; see
[the open query](../queries/does-a-wallbox-answer-unit-248-on-rs485.md).

A second AC22E-01, on the same firmware `LE-01.1E1.001.901.25`, read by a contributor from a
standalone wallbox entry in Home Assistant on 2026-11-10, answered the same 279 addresses over
TLS. With a session completed that morning, **21320 held the session's end**, 07:30:00 on the
wallbox's clock, 3574 s after its start, hours before the reading; 21313 read 0, the start mode 3,
and the phase voltages 0 with no charge
([the diagnosis](../sources/ac22e01-anonymous-anon-12522147000-wallbox-tls-summary.md)).

The [capability test's dry run](../sources/gerd-wallbox-dry-run-2026-11-06-summary.md) on
2026-11-06, with no car: the output current setting (holding 21203) read **0**, against 160
and 151 while charging, and input 21322 read 161 beside it, so 21322 is not the setting
echoed. Nothing is written to a wallbox outside a capability test with leave.
With a car charging on 2026-11-14 it read 316 against a draw of 16.0 A, which rules out 0.01 A
per count before any write ([the session](../sources/gerd-wallbox-inverter-control-2026-11-14-summary.md)).
The map that reads 21203 as 0.01 A is AC011E-based, so the disagreement stood until an
**AC011E-01** was read: one at unit 4 behind a WiNet-S, idle, reads 6.0 A at 0.1 A per count --
the minimum a wallbox offers, where 0.01 A would make it 0.6 A
([the diagnosis](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-14076202309-battery-unknown-winet-summary.md)).

## The first AC011E-01

Read 2026-11-16 at unit **4** behind a WiNet-S, 16 A over three phases, `AC011K-AE-25_V1.7.18`
where 21216 says `AC011E-01` -- the part number an owner buys against the name the register
holds, so identity keeps to the type code (`0x20DA`) and the `AC` prefix. Its 21272 reads
4140 W and its 21273 11040 W, which are 6 A and 16 A over three 230 V phases: the 4.14 kW
minimum the 2023 EV Power Guide names, now read from a wallbox
([the sources](../sources/wallbox-phase-switching-sources-2026-11-14-summary.md)). It also
settles [which unit a WiNet-S gives a wallbox](../queries/which-unit-does-a-winet-s-give-a-wallbox.md):
not always 3.
