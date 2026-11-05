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

## [2026-11-03] ingested | gerd's wallbox through a charging session

One TLS session, 30 s reads, 11:55-15:07 UTC; the car stopped at 14:50:42. 21313 fell to 0 94 s
after the power did, as the status went 3, 5, 6; the control pilot went 5.94 V to 8.97 V. 21310 kept
the session's energy. 21308/21310 signedness stays open (never above 10.76 kW). 21267 counts one in
about 5.4 s, not one in 10.

## [2026-11-03] ingested | gerd's third readings, cable, WiNet-S and wallbox, while a car charged

Around noon, the owner's Home Assistant stopped, a car charging at about 10.7 kW. Cable: exit 0,
9/9, 13074 times ten, every behaviour check did as told including both windows, Running after
181 s with the start sent three times. WiNet-S: the PV cut did as told, the stop and the window
write were refused with an exception, the battery too low for the rest. Wallbox over TLS and at
unit 3: 21313 read 527 during the session, 21320 held the time of the reading. The cable
snapshot showed a forced-charging window the 2026-11-01 dongle run had left; the dongle run of
today left 33210/33211 at 13:26 although 33211's write was refused with 0x04 (read afterwards
over the cable by the maintainer, then put back to the owner's 00:00-00:00, target 0). The
restore now always writes through a dongle.

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

## [2026-11-02] ingested | an anonymous SH10RT-V112 on P020, through a Modbus proxy and direct (#786)

Two read-only runs ten minutes apart with a BYD HVS 10.2: the first through a modbus-proxy
add-on while the YAML package polled through it, the second straight to the inverter. Both
answered 36 of 36 blocks with no reconnect and decoded the same 233 fields, and 6100 answered
through the proxy, so it is transparent to transport detection. 31211 reads 0xFFFF, the fourth
house on P020 to; the history block answers whole over the cable.

## [2026-11-02] ingested | robbensonmio's SH10RT on P020 with an SBR256, and their SBR cell registers (#786, #788)

Read only over the cable, every block answered. The first eight-module SBR, on the oldest BCU
firmware in the corpus; `cell_type_module_n` reads 1 in every slot where other packs read 66 to
76, so it is not one flag. Issue #788's finding that 10765-10780 are each module's highest and
lowest cell, not sixteen cells, matches the library's reading, and every cable SBR reading in
the corpus agrees with it.

## [2026-11-02] ingested | peter_sm's fifth to seventh readings (#786)

The fifth (evening, 0.1.0a24): the control test declined, Standby. The sixth and seventh, 13
minutes apart over the cable: 9/9 readbacks, 13074 times ten by refusal, the forced charge,
forced discharge and export limit as commanded in both. Both lost the connection on the charge
window's write of 33213, at the same word each time; opened as a query, since fwitten's P023
cable run wrote the same window cleanly.

## [2026-11-02] ingested | ra1k_0's SH20T: the PV cut confirmed on P071 (#772)

Through a WiNet-S at 20 kW PV and a full battery: the PV cut did as told (20421 W, 28 W,
20395 W), the first on an SH-T, and P071 joins `CONFIRMED_ON_FIRMWARE`; the query on P022 and
P071 is answered. A restart: 2 s to stop, 147.5 s to run. The outcome 4 is 13074 written at the
fallback of ten and read back as forwarded through the dongle, the same lead as the first run,
not evidence. The owner says the SH20T has no LAN port of its own.

## [2026-11-02] ingested | bleughb's AC-coupled SH10RS on SUNSTONE-H P057, from a diagnostics download (#789)

The owner attached the integration's diagnostics twice; the second carries a control test, and
its `survey` section is committed under the library's own name for it. No register dump and no
block read test, which a diagnostics download does not take. 13074 stores a written word as
handed, by the probe's acceptance, as on P065; 31211 reads 0x55. The forced checks moved the
battery but the house, with two SG5.0RS beside it, moved more. A restart: 4 s, 291 s.

## [2026-11-04] updated | SBR per-module entities (#788)

[SBR battery](entities/device-sbr-battery.md): each fitted module's highest and lowest cell
are now diagnostic entities, disabled by default, gated on a non-zero cell type. No new
reading; the gate is held to the cable documents already ingested.

## [2026-11-04] ingested | bleughb's two SG5.0RS and the SG power limitation note (#786)

The first string-inverter surveys: two diagnostics downloads of 0.1.0a25 through a WiNet-S on
WiFi, each `survey` section committed unchanged under `device-survey/results/string_inverter/`.
The read block (input 4950-5229 and 7013-7032, holding 5000-5049) answers in one round; the
meter block and the per-string block read 0. Both machines read the power limitation on at 100 %.
With them the owner's note on holding 5007 and 5008, which curtail the output; new entity page
[SG-RS](entities/device-sg-rs.md). No write watched, so no code follows.

## [2026-11-04] ingested | an anonymous SH6.0RT-20 on P023 with an SBR064 (#786)

The first SH6.0RT-20 (`0x0E11`), read only from Home Assistant, through a Modbus proxy with EVCC
polling too. Every block answered in all three rounds. A two-module SBR064, the smallest pack yet;
read nearly empty, the inverter's battery level (1.2 %) sits below the pack's own SoC (6.3 %).

## [2026-11-04] answered | registers 33042 and 33274

Over the corpus, holding 33042 reads 0xFFFF in all 42 dumps that hold it and 33274 reads 0 in all
19 that answered it, so neither becomes an entity:
[registers 33042 and 33274](entities/register-33042-and-33274.md). The SG's phases B and C read 0
on a single-phase machine, so the integration now leaves them out by output type; the
compatibility page has an SG section.

## [2026-11-04] updated | SG entities by tracker and phase count

Because bleughb's SG5.0RS reads MPPT3 to MPPT12 and phases B and C as 0, the integration now
decides an SG's tracker and phase entities by the source's tracker count per model and the
output type ([SG-RS](entities/device-sg-rs.md)). The SG also gets `Fault reported` from its work
state, and `scripts/dev/simulator_sg.json` serves bleughb's survey for the dev loop.

## [2026-11-04] ingested | the discharge window at mkaiser, on P020

Two evening runs with `--discharge-window`, no PV, the owner's Home Assistant restarted. The first
skipped it, the battery discharging 495 W against the 500 W floor; with the house load raised the
second moved every window away from now and the discharge went 722.5, 0, 719 W: it works on P020.
gerd's cable run (3799, 0, 3800 W on P022, 2026-11-03) was the first; the control-test page and
the 2026-11-01 entries said it had run nowhere. Forced charge and discharge obeyed, the restore
left nothing changed, 8 of 9 readbacks matched (13074 kept its word, feed-in limitation being off).

## [2026-11-04] ingested | mahagon's SH5.0RT-V112 on P023 with an SBR096, cable and WiNet-S2 (#786)

The first SH5.0RT-V112 (`0x0E0C`) and the first 5 kW machine on version 1 `.95.14`, two read-only
runs eight minutes apart with the owner's YAML package polling. On the cable 236 of 245 fields
answered, with blocks read inconsistently in one round under the polling; through the WiNet-S2
161 answered, the history, firmware and meter blocks refused as at every dongle. 31211 reads 0x55.
The export-scale probe was refused three times, so 13074 multiplies; a refusal cannot tell ten from
0.1 % of the 5000 W rating, so item 7 of the wanted list stays open for a control test on this
size. The three-module pack's `cell_type_module_n` reads 1, as on the SBR256.


## [2026-11-05] ingested | brendan's SH10RS on P067 with two SBR224, WiNet-S (#786)

The first survey on `SUNSTONE-H_B000.V002.P067` (version 1 `.02.67`), through a WiNet-S on Ethernet
with the owner's pollers running. 31211 reads 0x55, 13087 is 0xAA with 13074 at raw 50. Register
5639 reads 44.8 kWh, twice an SBR224, beside 488.8 V of one stack: the capacity register sums the
packs, the likelier cause of the anonymous P059 survey's 32.0 kWh too. The control test did not run:
the inverter reported "Key stop", nothing was written, the PV cut on P067 stays unconfirmed.

## [2026-11-05] ingested | an anonymous SH6.0RT-20 on P022 with an SBR128 (#786)

The second SH6.0RT-20 and the first on P022 (version 1 `.95.13`), from the preview integration's
diagnostics, through a Modbus proxy on the inverter's own LAN port with the YAML package stopped.
Every block answered in three rounds, no reconnects. 31211 reads 0x55; export limit off with 13074
at raw 7600 (no write, scale unmeasured); a four-module SBR128 reads 12.8 kWh. Read only, so no
code change: P022 is already confirmed.
