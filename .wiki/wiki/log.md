## [2026-10-29] initialized | wiki

Wiki knowledge base initialized, in the format of `@llmwiki/core` 0.1.2
(microsoft/llmwiki at `e09126f`).

## [2026-10-29] ingested | 23 fingerprints

Every committed document in `device-fingerprints/inverter/` and
`device-fingerprints/wallbox/`, one source page each, with entity pages for
models, firmware and installations.

## [2026-10-29] ingested | register and reference documents

`doc/legacy_entity_map.json`, `doc/wallbox_registers.md`,
`doc/cross_reference_modbus_manager.md`, and
`github-issues-user-findings.md`, which moved into `raw/`.

## [2026-10-29] ported | AGENTS.md

The device knowledge in the root `AGENTS.md` (the control test, register
13074, reading registers, the WiNet-S, finding devices, migration, serials)
moved into concept and entity pages. `AGENTS.md` keeps the rules and links
here.


## [2026-10-29] renamed | fingerprint -> survey

What earlier entries call a fingerprint is a survey document: it records a
device's capabilities and configuration, and identifies nothing.
`device-fingerprints/` is now `device-survey/`, and the library and
integration modules are `survey_document`. Source pages, tags and links
follow.

## [2026-10-29] ingested | firetribe's SH6.0RT-V112 on P023, cable and WiNet-S (#784)

Two readings from Home Assistant, each with a control test: on the cable it
refused because the inverter was starting; through a WiNet-S two other clients
poll, the leg-B writes were refused with 0x04 while the forced charge was
obeyed. Opened the query on 0x04 through a busy dongle.

## [2026-10-29] ingested | gerd's wallbox read directly again

Second direct reading of the registers only the TLS path shows, a fortnight
after the wallbox document. Holding 21250-21259, twenty constant ASCII digits,
is now masked like the serial, in the library and in the committed document.

## [2026-10-29] answered | a busy WiNet-S refuses with 0x04

Reproduced firetribe's 0x04 on gerd's WiNet-S with three concurrent readers,
twice; one reader alone got every answer. 0x04 joins 0x06 in
`model.SETTLES_NOTHING`.

## [2026-10-29] measured | gerd's wallbox input 21267 is not a write counter

With no other client on the wallbox: it ticks about once per 10 s through
quiet, rapid reads and a same-value holding write alike. Likely uptime in tens
of seconds. The integration now shows the wallbox's own serial on its device
page and still publishes only its stand-in.

## [2026-10-30] ingested | ra1k_0's SH20T with a control test (#772), and Korsberg's second reading (#785)

ra1k_0: the first control test on an SH-T, through a WiNet-S. The forced
discharge acted; 13074's write scale was not determined, and with feed-in
limitation off the dongle reported a written word as handed, which contradicts
B001's "ignores writes" if the register took it. Korsberg: the second reading,
now signed peter_sm, so the installation page moved to that handle; 13074 times
ten again, and the forced checks ran against the house's own 10 W battery caps.

## [2026-10-30] ingested | gerd's wallbox beside Sungrow's portal

The owner's iSolarCloud page and a direct read five minutes later: input
21201-21206 is the serial the portal shows, and 21300 and 21310 count in Wh.
The serial's first four characters were in three test fixtures as the
supposed model prefix; they are the placeholder serial's now. The car had
finished charging, so 21313 and the sign of 21308/21310 stay open.

## [2026-10-30] built | the survey reads an iHomeManager

`sungrow_modbus.ihomemanager` maps Sungrow's V1.0.2 document, and the survey
reads a found iHomeManager into a document of its own instead of stopping.
The document lists no serial; text in an undocumented gap is masked and
published as a stand-in. Each port takes one connection, on 502, 503 or 504.

## [2026-10-30] changed | an iHomeManager is identified by 0x072A only

A Logger answers a type code at 8000 on unit 247 too (discussion #262), so
any other code is reported as a unit-247 device and not read as an
iHomeManager.

## [2026-10-30] ingested | the PV cut confirmed on P022 at gerd

A control test over gerd's cable cut DC power 2938 W -> 0 W -> 1913 W; P022
joins `CONFIRMED_ON_FIRMWARE`. Two earlier runs that day cut to 0 W as well
and were called inconclusive by the drift gate, so a stop is now judged by its
bracket (`STOP_BRACKET_W`). The same run: 9/9 readbacks, 13074 x10, restart
181 s in daylight.

## [2026-10-30] decided | an SBR on its own unit is a Sungrow battery

`Capability.SUNGROW_BATTERY` is granted when a pack answers on its own unit
and 5639 names an SBR, so its write bounds come from the datasheet. An SBH
waits on one direct-LAN survey. The holding 21250-21259 digits in old commits
of gerd's wallbox document stay in git history.

## [2026-10-30] built | the survey reads a Sungrow Logger raw

Named by its type code at unit 247, its identity decoded and the rest of its
8000 block published raw with text masked. Behind an inverter, unit 247 is
asked only when the owner answers `logger` for the transport.

## [2026-10-30] changed | forced checks respect the house's battery limits

A forced charge or discharge, and the discharge that manufactures an export,
are commanded under `battery_max_charge_power` / `battery_max_discharge_power`
where those are lower, and skipped with the limit named where too low to
measure: peter-sm's 10 W caps made both forced checks report nothing.

## [2026-10-30] moved | survey documents into device-survey/results/

`device-survey/inverter/` and `device-survey/wallbox/` are now
`device-survey/results/inverter/` and `device-survey/results/wallbox/`;
iHomeManager and Logger documents go in `results/ihomemanager/` and
`results/logger/`. The documents themselves are unchanged.

## [2026-10-31] ingested | peter_sm's third reading (#785), every check confirmed

On 0.1.0a19, with the house's battery limits back at 10000 W: outcome 0, 9/9
readbacks, 13074 x10 by refusal a third time, and forced charge, forced
discharge and the export limit all as commanded over the cable. Committed as
`-2`, the survey's number for a taken name. A run 14 minutes earlier on an
older release was not committed; this one covers it.

## [2026-10-31] moved | findings out of devices-wanted.md

`device-survey/devices-wanted.md` now says only what is wanted. Its findings
moved here: the SBH readings (scales, state of charge, over-rating), the SBR
position encoding, and how an iHomeManager's Modbus TCP is opened. The wiki
keeps frozen copies of the register documents in `raw/`; the `doc/` copies
are ordinary docs, and `doc/cross_reference_modbus_manager.md` is retired.

## [2026-10-31] found | the history registers are cable-only

Inputs 6196-6198 (daily PV yields) answer on every cable survey and are
refused through every WiNet-S. The YAML package's dropped monthly and yearly
sensors (6227 on) are in the same V1.1.16 block, unread so far.

## [2026-10-31] ingested | peter_sm's fourth reading (#785), an SBR224 and GalKar's SH15T (#786)

peter_sm on 0.1.0a23, committed as `-3`: the first cable dump of the whole
history block (6101-6826, every address answered, monthly values up to
October), the forced-charging schedule off, register 32998 at 950; control
test outcome 3 with the battery at 8.7 % in the evening, 13074 x10 by refusal
a fourth time, forced charge as commanded. An anonymous SH10RT-V112 on P023
with a seven-module SBR224, read only: the position words hold up to module 7,
and the discharge schedules have the same layout at a second house. GalKar's
SH15T on P071 through a WiNet-S, from a diagnostics download whose `survey`
section is committed: the first SH-T forced charge (as commanded) and restart
(stopped 2 s, running 145 s), writes and the 13074 read refused by a busy
dongle, and 33149-33150 answering in one round against the capability table.

## [2026-10-31] ingested | the first SH-RS: an SH6.0RS on SUNSTONE-H P068 (#786)

Through a WiNet-S, read only, published as anonymous. 31211 answers 0x55 on
P068; the forced-charging block and the discharge schedules answer with the
SH-RT layout; the history block is refused, as through every dongle; twelve
blocks lost connections in some rounds with the owner's pollers stopped. The
battery firmware string carries bytes after its NUL, which the library now
drops (strings end at the first NUL).

## [2026-11-01] found | the yearly history slots start at 2015

In peter-sm's cable dump (#785) each quantity's 2026 yearly slot (6272, 6451,
6630) holds the sum of its monthly values, which places the first slot at
2015, U32 low word first, 0.1 kWh; the slots after 2029 read 0xFFFF. The
monthly registers hold the current calendar year only. Read by the
integration as this month and this year per quantity.

## [2026-11-01] ingested | Jam3s97's SH10RS on SUNSTONE-H P065, with a control test (#786)

Through a WiNet-S on Ethernet, the owner's pollers running. The PV cut did as it was told
(3465 W, 0 W, 3092 W): the first cut on an SH-RS and the first through a dongle, so P065 joins
`CONFIRMED_ON_FIRMWARE` and a dongle is shown to forward the write. 13074's probe was accepted
with feed-in limitation on: P065 stores a written word as handed, the second firmware to do so.
The stop was refused with an exception, the battery was full, and the SBH300 reads 30.41 kWh.
bicnz's second SH6.0RS attachment is byte-identical to the committed one.

## [2026-11-01] ingested | second readings at mkaiser and fwitten's master, with the timed windows

Both over the inverter's own LAN port on this tree's library, around noon, full control test.
fwitten with the owner's Home Assistant polling, every block still answered. The forced-charging
window did as it was told on P023 (3258.5, 3599, 3339.5 W); on P020 it raised charging from 772 W
to 4499 W and was judged "could not tell" when the house fell afterwards. The discharge window
ran nowhere, both batteries charging. 13074 times ten at both; the PV cut confirmed on P023 a
second time; restarts 186 s and 194 s. Both dumps carry the whole history block, and each 2026
yearly slot equals the sum of its months: the layout holds at three cable houses.

## [2026-11-01] ingested | gerd's second readings, cable and WiNet-S, with the timed windows

Both around noon with the owner's Home Assistant stopped, full control test. Cable: 9/9, 13074
times ten, the PV cut and export limit did as told, the charge window raised charging to 4399.5 W
and was judged "could not tell" on drift. WiNet-S: the charge window and the PV cut did as told
through the dongle. With fwitten and mkaiser the charge window raised charging on P020, P022 and
P023 at every run. gerd's history breaks "a year is the sum of its months": PV and export each
sit 1610.3 kWh above. The wallbox read after a 7854 Wh session this morning.

## [2026-11-01] ingested | bar12's second readings, cable and WiNet-S, with the timed windows

Early afternoon, nothing else polling, full control test. Cable: 9/9, 13074 times ten, the PV cut
did as told, the history's yearly slots equal their months (four houses of five), but the battery
swung by about 1000 W on its own, so neither the forced discharge nor the charge window was
measured. WiNet-S: every behavioural check did as told through the dongle; the charge window rose
from 1216 W to 4100 W and swung to -1912 W after it closed.

## [2026-11-01] found | a charge window starts in 4 s and stops in 2 s; a start is judged by its bracket

A 2 s trace of the charge window check at mkaiser (P020): a flat 4499 W charge 4 s after the
enable, 0 W 2 s after it went back, no rebound; the house drifted afterwards as PV fell. Every
charge window of the day had risen clearly, and two were called "could not tell" on drift. A
start standing `WINDOW_START_W` above both neighbours is now confirmed ahead of drift, and the
wait after the window is 20 s. Confirmed live at mkaiser with the fix.

## [2026-11-01] ingested | an anonymous SH10RS on SUNSTONE-H P059 (#786)

Through a WiNet-S on Ethernet, read only, the owner's pollers running: six holding blocks came and
went with exceptions, as through a busy dongle. 31211 answers 0x55 on P059, the third SH-RS
firmware to; the schedules have the SH-RT layout. The pack reports 32.0 kWh at 5639 against a
voltage of about six or seven SBR modules, unexplained. The owner first hit #787's import error.
