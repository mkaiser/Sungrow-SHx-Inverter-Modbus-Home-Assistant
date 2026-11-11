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

## [2026-11-05] ingested | Sungrow's register names and issue #554's 0 % shutdown flag

Sungrow's hybrid protocol V1.1.2, V1.1.5, V1.1.9 and V1.1.11 and the SG's V1.1.58, read for the
names of the registers the integration reads; the documents stay outside the repository and the
notes record names only. V1.1.11 names 123 of 138 hybrid registers and V1.1.58 all 57 SG ones;
the 15 unlisted are an open query. The limit family turned from *Export* to *Feed-in* by V1.1.9,
while measured flows stay *export*; 13075 is *Off-grid option*. New pages for holding 13017, a
command that reads 0 on SH-RT, 0x55 on SH-T and is unavailable on SH-RS, and holding 31213, the
undocumented flag issue #554 found: 0xAA on four SH-RS and two SH15T, 0x55 on every SH-RT, which
contradicts the earlier claim in the code that every survey read one value.

## [2026-11-05] ingested | evcc's Sungrow templates and wallbox driver

evcc at `bcea759cd9`, compared register by register, with the issues in which its users read real
devices. The hybrid, SG and wallbox maps agree everywhere evcc reads. Two iHomeManager readings
overturn the map, which followed Sungrow's V1.0.2: holding 8028 answers 0x55/0xAA, not 0/1, and
input 4358/4360/4362 carry the phase voltages no document lists; both are now read, held `field`.
evcc's wallbox driver is not MIT and derives from Louisbertelsmann's map, which corrects
`doc/architecture.md`; the SG resets 5008 to 110 % while its limitation is off; a wallbox drops an
idle session after 60 s. Logger leads (Voyanti's GPL transcription of the 1.0.2.7 protocol) went on
its open query.

## [2026-11-05] answered | do models on one firmware answer alike?

`doc/firmware_support.md`, generated from every survey with a register dump, pools them by platform
and firmware and replays each through the integration's decoding and probe. No model disagrees with
another on its firmware in the five columns that pool two; the SUNSTONE-H firmware each have one
model so far, and stay open.

## [2026-11-05] answered | do battery packs on one firmware answer alike?

`doc/firmware_support.md` gained the SBR and SBH packs, columned by BCU firmware and link, from each
survey's decoded `battery_pack` block. No pack model disagrees with another on its firmware in the
four columns that pool two; unit 2 refuses the cell and module blocks on every pack.

## [2026-11-05] updated | registers 13017 and 31213 in the integration

31213 is decoded to an on/off sensor, its number kept only for legacy ids. 13017 is a *Force startup*
button gated on a watched write, which no firmware has, so it is created nowhere yet; its raw sensor
is gone.

## [2026-11-06] ingested | Sungrow's Logger protocol 1.0.2.9 and the Logger manuals

The protocol, marked public, found on an installer's file server, with 1.0.2.5's text beside it. It
agrees with the identity block mapped before and lists the rest: inputs 8021-8036, the array
8058-8109 with 64-bit totals sent high word first, and holding 8002-8020. All of it is now in
`src/sungrow_modbus/logger/registers.py`, held `spec`; the survey reads the documented blocks first.
The Logger1000 manual Ver129 adds that only port 516, with TLS, is open by default from P044.
Where every document and map was found, and what was not, is a saved answer, so the searches are
not repeated.

## [2026-11-06] ingested | shcshc76/sungrow, the origin of Eisbaeeer/sungrow

Its AC011E-01 tables, read again with their protocol addresses: they agree with the wallbox map
everywhere they overlap, read 21263 as a working mode as two other maps do, and name 21268 an
enable flag. Its README's claim that a WiNet-S faults when the wallbox is polled faster than every
10 s went on the wallbox and WiNet-S pages, unmeasured.

## [2026-11-06] ingested | Sungrow's hybrid protocol V1.1.17

The newest version, found through a third party's guide and served by Sungrow. V1.1.16 was not found
anywhere, but V1.1.17 differs from it in device types only, and no register has changed since
V1.1.11. It answers the open V1.1.16 question for one of the fifteen registers (the serial, 4990);
the other fourteen are unlisted. Its five MG10-25TL types are in `DEVICE_TYPES` as a `Family.TL`
of their own, because the document groups them apart from MG5-12RL. 13017 works only
grid-connected.

## [2026-11-06] answered | what do the registers only V1.1.17 lists read?

The three registers the hybrid map does not read, read off the surveys already committed: 31222 is
13074 divided by ten on all 46 surveys that read both, 13043 is 255 or 0 on every survey (never a
DRM state), and 13080 is 0 on 42, 330 on two houses and 875, then 961, on an SH20T in EMS mode 3, so
it is not the heartbeat setting its name says.


## [2026-11-06] ingested | peter_sm's eighth reading, from a diagnostics download (#786)

Posted by Korsberg, 0.1.0a26 on Home Assistant 2026.11.0: the `survey` section of the integration's
diagnostics, committed as `-7`. Nothing new: the same firmware, probes and answering components as
the seventh reading, live values only, and no control test, register dump or block read test, which a
diagnostics download does not take. The installation's first reading from a diagnostics download and
the first on Home Assistant 2026.11.0.

## [2026-11-06] ingested | gerd's wallbox, the control test's dry run

The wallbox control test's first hardware run, read only over TLS with no car. The output current
setting read 0 idle (160 and 151 while charging), so its scale needs a car charging; input 21322
read 161 beside it, so it is not the setting's echo, as the one earlier reading suggested.

## [2026-11-06] ingested | gerd's TLS certificate, by hash

Port 516 of gerd's WiNet-S and of his wallbox serve the byte-identical certificate, serial number
1, RSA-2048, valid 2024 to 2054; its SHA-256 is now recorded. Two products on one certificate
points to one built into the firmware; the same hash from another house would settle it.

## [2026-11-06] ingested | bar12's TLS certificate: the same as gerd's

bar12's WiNet-S, confirmed by its stand-in through the same address, serves the certificate gerd's
WiNet-S and wallbox serve, byte for byte. Two houses and two products on one certificate: it is
built into the firmware, and port 516's TLS authenticates nothing.

## [2026-11-06] ingested | icefest's SH6.0RS on P066, through a WiNet-S and over RS485 (#786)

Two diagnostics downloads ten minutes apart, both with the control test and a restart. P066 stores
13074's word as handed, answers 31211 with 0x55, and refuses the forced-charging window's days word
(33209) with 0x04 on both paths. The dongle run's code 5 was that refused word, which a dongle cannot
read back and whose refusal proves nothing there; the RS485 run found it holding its original
value. RS485 through a Waveshare converter
answers 6100, so it reads as direct. The first SBR192 read on a direct link.

## [2026-11-07] ingested | the site import power limit, register 32998 (discussion #546)

Three owners on the undocumented register iSolarCloud calls "Site import power limit". Jam3s97
wrote 1300 on an SH10RS and the meter held 13.00 kW, through a WiNet-S and over RS485, and the
device refused 5001 with an exception: the unit is 0.01 kW, which Korsberg's 9.5 kW and ulfben's
11.00 kW readbacks fit. On ulfben's SH10RT-V112 the battery force-charges at full power whatever
the limit says, before and after an update to 95.14; that is open. New: the register's page and
the query; the pages that called its unit unknown now give it.

## [2026-11-07] ingested | mkaiser: the site import limit under a forced charge, on P020

A watched write at night, over the cable, with leave: under a 4500 W forced charge through 13050
and 13051, register 32998 at 200 held import at 1978 W median against 5088 W before, by cutting
the charge to ~1500 W, within one ~5 s sample each way. Every word was restored and read back.
The query is narrowed, not answered: ulfben's SH10RT-V112 is reported to ignore it.

## [2026-11-07] ingested | mkaiser-import-limit-pv-2026-11-07

A watched write of register 32998 on mkaiser's SH10RT (P020) with ~1.1 kW PV:
under a forced charge the cap is on grid import alone, 1 (0.01 kW) charges from PV
only, and 0 and 5001 are refused with exception 0x04. Updated register-32998, the
forced-charge query, P020 and installation-mkaiser.

## [2026-11-07] updated | register-32998, control-test

The integration reads register 32998 as the diagnostic sensor Grid import limit, and the
control test gained `--import-limit` (survey leave, integration option). Not yet run in the
engine on hardware.

## [2026-11-07] ingested | code-imstillalive: an SH25T and an SH15T through a Logger1000A (#791)

Two read-only surveys from the integration's button, four minutes apart, both on
`PEARL-H_B000.V000.P067`: the first SH25T, the first P067 on the T, and the first inverters read
through a Logger. Each answered on a Logger port of its own and refused what a WiNet-S refuses
(6100, 2613, 2629, the history). 31211 answers 0x55 on P067, which joins `ANSWERING`; 33149 and
33150 answer 0xFFFF. Another Home Assistant polled throughout. New: the installation and P067
pages; the SH-T, Logger, 31211 and transport detection pages and the Logger query updated.

## [2026-11-07] ingested | peter_sm's ninth and tenth readings, diagnostics downloads (#786)

Posted by Korsberg on 0.1.0a27. The ninth adds nothing new. The tenth carries a control test:
nine readbacks matched, 13074 times ten by refusal, a Modbus restart in 269 s, and the charge
window's write of 33213 lost the connection a third time. Its file is named `battery-thirdparty`
because its document lost the `battery_pack` section; the pack is the SBR160.

## [2026-11-07] ingested | mkaiser-import-limit-engine-2026-11-07

The first engine run of `--import-limit`, at mkaiser's SH10RT (P020): the cap was met and 0 and
5001 were refused. With the PV isolator open the inverter first went to Standby, and a run
refused. Updated register-32998, control-test, the forced-charge query, P020, installation-mkaiser.

## [2026-11-07] ingested | mkaiser-import-limit-load-2026-11-07

A watched write of 32998 at mkaiser's SH10RT (P020) after dark, the battery held idle by a forced
stop: at a 2.00 kW cap the house imported its whole ~2.2 kW load. The cap limits a charge, not
the house. Updated register-32998, P020, installation-mkaiser.

## [2026-11-07] ingested | bar12-import-limit-2026-11-07 and bar12-forced-startup-2026-11-07

bar12's SH10RT-20 (P023) after dark, the battery empty and the inverter in Standby. 32998 capped a
forced charge over the cable and written through the WiNet-S; with the battery empty it did not cap
the load. A forced charge, EMS or scheduled, woke the inverter in ~2 min. The first watched writes of
13017: a switch, 0xAA on and 0x55 off, every other word refused, so the factory 0 cannot be put
back. Updated register-13017 (overturned: it reads back what is written), register-32998,
register-13000, device-winet-s, P023, installation-bar12, the forced-charge query.

## [2026-11-07] updated | register-13017: a switch in the integration

The *Force startup* button became the switch *Forced startup under low SoC* (0xAA on, 0x55 off,
the factory 0 read as off), confirmed on P023 from the bar12 run.

## [2026-11-07] renamed | the survey is the diagnosis, the control test the capability test

`device-survey/` is now `device-diagnosis/`, its launchers `diagnosis.sh`, `.cmd` and `.ps1`
(`tests` in place of `control`), and the scripts `sungrow_diagnosis.py`,
`sungrow_capability_test.py` and `sungrow_wallbox_capability_test.py`. The library modules are
`sungrow_modbus.diagnosis`, `diagnosis_document` and `capability_test`; the concept pages are
`capability-test` and `capability-test-restore`. Schema 25 puts part B's block under
`capability_test`; the committed documents keep `control_test` at their own numbers and are
unchanged. Entries above this one use the names of their day.

## [2026-11-08] added | the forced startup check (register 13017)

The capability test gains `--forced-startup`: from low-SoC standby it writes 0xAA, watches the
inverter start, writes 0x55, watches it sleep, and restores the register. The restore's one
equivalence, 13017's factory 0 put back as 0x55, is on capability-test-restore. Updated
register-13017. No hardware run yet.

## [2026-11-08] ingested | bar12-import-limit-schedule-2026-11-07 and gerd-import-limit-2026-11-08

bar12 (P023): 32998 capped a charge commanded by the forced-charging schedule, within one sample,
following the load. gerd (P022): it capped an EMS forced charge over the cable and through the
WiNet-S. Under gerd's polling Home Assistant the dongle stopped answering mid-restore and the cable
closed every session for most of an hour; the restore was read back over the other path. Updated
register-32998, P022, P023, installation-gerd, device-winet-s, the forced-charge query.

## [2026-11-08] ingested | gerd-import-limit-schedule-2026-11-08

gerd (P022), through the WiNet-S while the house's Home Assistant held the cable: 32998 capped a
charge commanded by the forced-charging schedule (4399 → 862 W, import 994 W against 1.00 kW).
The dongle read 33208 back current and 33210-33214 as 0 throughout. Updated register-32998, P022,
device-winet-s, the forced-charge query.

## [2026-11-08] ingested | mkaiser-import-limit-export-2026-11-08

mkaiser's SH10RT (P020) with ~1 kW of PV above the load: a 0.01 kW cap left a charge from PV
alone, and with the charge limited to 100 W (which stopped it), export and PV went on unchanged.
Updated register-32998, P020, installation-mkaiser.

## [2026-11-08] added | several capability test runs fold into one block

Home Assistant keeps every capability test run per firmware and folds them into a schema-3 block
with dated runs, `summary`, `still_missing` and `contradictions`, so checks that need different
moments (the import limit after dark, the PV cut in sun) reach one document. Updated
capability-test and the ingest workflow.

## [2026-11-08] added | continuous capability testing

A switch whose on is the leave for runs that start on their own, until switched off or a restart:
it starts a run when the polled readings match what a missing check needs. AGENTS.md's leave rule
names it. Updated capability-test.

## [2026-11-08] changed | the terminal's --merge-into folds runs

`sungrow_capability_test.py --merge-into` keeps the runs a document carries and adds its own;
`--replace` puts it in their place. Continuous mode stays on diagnostics-only entries, by decision.
Updated capability-test.

## [2026-11-08] changed | the diagnosis entities renamed, and the checks counted

Every diagnosis entity is named *Diagnosis: ...* so the device page's *Diagnostic* card keeps
them together; *Capability test status* is *Diagnosis: test summary* and shows how long an
extended run has taken; five counters split the folded checks by outcome (`ledger.counts`).
Updated capability-test.

## [2026-11-08] ingested | mkaiser-import-limit-discharge-2026-11-08 and mkaiser-forced-startup-2026-11-08

mkaiser's SH10RT (P020), cable, after dark. With the battery's discharge limit at 500 W under a
~1.1 kW load, a 0.05 kW cap on 32998 left the battery at 499 W and import at ~700 W. 13017's 0xAA
woke the inverter from low-SoC Standby (Running after 3 min 35 s), 0x55 sent it back within ~21 s,
0x01 is refused; 13017 is left at 0x55. A minimum SoC raised above the SoC made it charge from the
grid at its charge limit, reporting 0x8000. So P020 is confirmed for the forced startup switch, and
32998 is the number *Grid import limit* on P020, P022 and P023. Updated register-32998,
register-13017, P020, installation-mkaiser, the index.

## [2026-11-08] ingested | sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter

mkaiser's SH10RT (P020) from the Marketplace testbed (preview 0.1.0a30, this tree's library), two
extended runs, everything restored. The forced-charging window did as it was told, now established
on P020. Writes lost the connection at four protocol addresses with Home Assistant polling, and
the engine reported such a loss as "refused with an exception", which folds as established; it now
reports a drop. Updated installation-mkaiser, P020, the 33213 query, the index.

## [2026-11-09] changed | the diagnosis mode select, Start and Stop

The device page now chooses what runs in *Diagnosis: mode* (read-only, extended test single run,
extended test auto repeat) and starts it with *Diagnosis: start*; *Diagnosis: stop* ends a run at
its next check, keeps what it measured, restores in full and starts no restart. Auto repeat leaves
out what the kept runs established, the inverter restart included. Updated capability-test.

## [2026-11-09] ingested | issue #786 and #792: peter_sm's eleventh to fifteenth readings, the second SH6.0RT-20 reading, BiergitKraft's SH10T

Korsberg posted five more diagnostics downloads of peter_sm's SH10RT-V112 (P023, cable). The
charge window's write of 33213 lost the connection in all three new runs that tried it, six of six
now; forced discharge and the export limit acted again, nine of nine readbacks matched, 13074
times ten; four restarts, 271-361 s. The anonymous SH6.0RT-20's second
reading (0.1.0a32) repeats the first. BiergitKraft's SH10T (issue #792), the first SH10T and the first
`PEARL-H_B001` firmware, through a WiNet-S2 with an SBH100 at unit 2: 33149-33150 answered through
the dongle; the capability test refused in Standby. New: installation-biergitkraft,
firmware-pearl-h-b001-v001-p038. Updated installation-peter-sm, the 33213 query, P023, device-sh-t,
device-sh-rt, device-sbh-battery, the index.

## [2026-11-09] ingested | mkaiser's night of auto repeat and the development instance's run

Two diagnostics downloads of mkaiser's SH10RT (P020, cable), integration 0.1.0a32. The first holds
19 auto-repeat runs from 20:46 to 11:03 UTC: ten refused in low-SoC Standby without writing; the
others established the forced charge (eight times), the forced-charging window and the site
import limit (seven times each), and in the morning the forced discharge and the charge ceiling, new on
P020. Restarts took 367 s after dark and 186 s in daylight. The discharge windows' raw write lost the
connection three times. The second, from `make dev`, repeated the ceiling; its charge window read
"nothing measurable happened" with the battery already near its charge ceiling, and folded as
established. Updated installation-mkaiser, P020, the index.

## [2026-11-09] changed | auto repeat runs in 30-minute slots from Start, waits for Running

Auto repeat starts at most one run in each 30-minute slot counted from the press of *Diagnosis:
start*, no longer at most twelve a day, and none while the inverter is not running, after a night
at mkaiser's spent ten runs refused in low-SoC Standby. Updated capability-test.

## [2026-11-09] changed | write paths, start thresholds and readings checked over days

The capability test gains write-path checks (no-op writes, window 2 encoding, EMS options, each
number's upper bound), the two start thresholds as behavioural checks, a headroom look before a
charge window is written, and 13088 recorded during the export check. Auto repeat feeds the
polled readings to plausibility checks every minute and counts them with the runs; a check
established by day is measured once more at night. Not run on hardware yet. Updated
capability-test.

## [2026-11-09] changed | the network search finds a wallbox at its own address

The config flow's sweep also looks on port 516 and probes it over TLS at unit 248; a wallbox that
names itself and gives a serial is offered in the picker and set up as an entry of its own (read
only, identified by its own serial, no inverter). Dongle-carried wallboxes (unit 3) are not
searched for. Not run on hardware yet. Updated device-wallbox.

## [2026-11-09] changed | diagnoses for a wallbox, an iHomeManager and a Logger from Home Assistant

A wallbox entry gets a read-only diagnosis that writes the same document as `wallbox_direct.py`;
read at gerd's outside Home Assistant on the same code path, it answered 299 registers and kept
its stand-in. The network search also asks unit 247 (ports 502-505, and TLS 516 where no wallbox
answers) and offers an iHomeManager or a Logger as a diagnosis-only entry, the same document as
`ihomemanager_direct.py`. Neither device has been read here. Updated device-wallbox,
device-ihomemanager, device-logger.

## [2026-11-09] checked | the wallbox entry's diagnosis, run from Home Assistant at gerd's

*Diagnosis: start* on the standalone AC22E-01 entry in the dev Home Assistant read 32 values and
published the stand-in the committed wallbox documents carry, address withheld. The wallbox was
idle, so the document adds nothing to them and is not ingested. Updated nothing else.

## [2026-11-10] changed | the standalone wallbox entry gets its own capability test

The maintainer decided that a wallbox entry at its own address has its own
capability test (leave and cap in its options, its own snapshot, ledger,
plausibility and auto repeat), that no `wallbox_host` is moved onto such an
entry since wallbox support is new, and that the search should show which
inverters sit behind a Logger (how a Logger is handled beyond that is open).
Not run on hardware yet. Updated device-wallbox.

## [2026-11-10] changed | a dongle's "kept its old value" settles nothing

Auto repeat at gerd's through his WiNet-S counted battery_max_charge_power,
battery_max_discharge_power and battery_max_soc as not supported on one
readback each that showed the old value, while the same runs watched the
inverter obey battery_max_soc. The capability test now records such a
readback as inconclusive and auto repeat does not wait for it, as
device-winet-s says of legs A and B; kept runs are read the same way. The
runs are not ingested. Updated nothing else.

## [2026-11-10] ingested | #786: peter_sm x3, ra1k_0's SH20T, an iHomeManager and an AC22E-01

Korsberg's three diagnostics of peter_sm's SH10RT-V112 (P023, cable), integrations 0.1.0a33,
a34 and a36: three new runs, the first ingested with the write-path checks and upper bounds.
33213 lost the connection in all three, nine of nine now, but so did 13059 once and 13050 and
33047 twice, so the query now weighs a link that drops on writes. 13058 and 13059 refuse a step
past their maximum; 33047, 33048, 13052, 33149 and 33150 store it. Restarts 363 s, 271 s, 303 s.
Raik0's SH20T (P071, WiNet-S) ended with outcome 5: 33209's restore refused five times through
the dongle, every write of the value it held; 33048 refused a value above its bound. Two
anonymous documents, kept unconnected to any installation: the first
iHomeManager measured (SV930.001.00.P020, port 503, all 56 mapped fields; 8001 is "AW0" low
word first, which the map misreads) and a second AC22E-01 whose 21320 holds a finished
session's end. Updated installation-peter-sm, installation-ra1k-0, P023, P071, device-ihomemanager,
device-wallbox, device-winet-s, capability-test, the 33213, iHomeManager and busy WiNet-S
queries, the index.

## [2026-11-10] changed | the iHomeManager's protocol number is read low word first

The iHomeManager measured today sends "AW0" at 8001-8002 as `0x3000 0x4157`, low word first like
its U32s, and the map read it high word first and published "0". The map now reads it low word
first; the Logger's, which no unit has answered yet, is unchanged. Updated device-ihomemanager,
the iHomeManager source page.

## [2026-11-11] corrected | after 33213 the next write drops too; 13088 recorded

The 33213 query said the discharge-window write after 33213 dropped because the link was not
back. It was back for reads: that check read the house for 20 s, readings that vary, before its
own write dropped, in all three runs. After the other drops (13059, 13050, 33047) the next write
went through at once, so only 33213's loss is followed by a second. Also recorded what the
ingest left out: the export check's 13088 reads 12.5 % for 1250 W on peter_sm's 10 kW
SH10RT-V112, the limit as a share of the rating. Updated the 33213 query, P023.

## [2026-11-11] changed | 13022 as battery power where 5214 is refused

The inverter's self consumption now takes its battery term from 13022 (U16, W) signed by 13001's
charging and discharging bits where 5214 is refused, as evcc does. Checked against gerd's cable
document of 2026-11-03, which read 3800 W at both (`register_dump`, protocol addresses 13021 and
5213). No committed diagnosis refuses 5214: 60 answered it, two intermittently. Updated nothing
else.

## [2026-11-11] queried | is battery power firmware dependent?

35 readings across ten firmwares with 5214, 13022 and 13001 in one dump: 5214's sign follows
13001's charging and discharging bits in all 35, 13022 holds the same magnitude unsigned, and a
battery-less inverter reads 13022 as 65535. No committed diagnosis refuses 5214; #655 (an SH8.0RS
through a WiNet-S) and #770 (a third-party battery) report it missing, and SAPPHIRE 51.0x is
unread. New query is-battery-power-firmware-dependent, the index.

## [2026-11-11] changed | an iHomeManager entry shows its readings

The integration now polls an iHomeManager entry's device and shows 40 read-only sensors beside
its diagnosis, decoded as the unit measured on 2026-11-10 answered. 8554, the unknown codes
8047, 8048 and 8051-8052, channel 2 and 8029 get none. Updated device-ihomemanager.
