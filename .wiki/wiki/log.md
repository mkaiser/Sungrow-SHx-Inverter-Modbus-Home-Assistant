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

## [2026-11-11] ingested | gerd's devices over mDNS, and their web pages

Asked over a VPN, unicast to each device's port 5353: gerd's WiNet-S and his wallbox at its own
address answer with a `_http._tcp` service whose TXT record names model, serial and units, and
the dongle's names the inverter and the SBR behind it too. The inverter's LAN port answers
nothing. The dongle's web page is HTTPS on 443; port 80, which its record names, refuses. The
wallbox serves no page. The device page's *Visit* link now opens `https://`. New query on
multicast and other firmware. Updated device-winet-s, device-wallbox, installation-gerd,
identify-by-what-answers, the index.

## [2026-11-11] changed | an iHomeManager entry shows its readings

The integration now polls an iHomeManager entry's device and shows 40 read-only sensors beside
its diagnosis, decoded as the unit measured on 2026-11-10 answered. 8554, the unknown codes
8047, 8048 and 8051-8052, channel 2 and 8029 get none. Updated device-ihomemanager.

## [2026-11-12] changed | a wallbox at its own address is its own entry, and the only one that writes

Decided by the maintainer: the direct path to a wallbox is preferred. The `wallbox_host` option
on an inverter entry is gone (entry minor version 3 drops it and its sub-device); an inverter
entry leaves out a wallbox at unit 3 whose own serial has an entry of its own, and only that
entry writes to a wallbox. No history is carried over: the YAML package never had a wallbox.
Nothing measured changed. Updated device-wallbox, device-winet-s and identify-by-what-answers.

## [2026-11-13] changed | discovery over mDNS, and the diagnosis records what a device announces

The integration's manifest now matches the two records measured at gerd, so Home Assistant offers
a WiNet-S naming an inverter, and a wallbox at its own address, without a search; the owner
confirms and the device is identified over Modbus as the search does. Nothing is read before
that, and an entry already set up is never moved by an announcement. Diagnoses from schema 27
carry `network_names` (mDNS records heard, reverse-DNS label, MAC vendor prefix), which answers
the multicast and other-firmware questions house by house. Nothing new measured. Updated the
query does-a-winet-s-advertise-over-mdns.

## [2026-11-13] ingested | #786: peter_sm, tristangrichard's SH8.0RT, an anonymous SH10RT through a proxy and an SG10RT

Four read-only diagnoses posted to #786 since 2026-11-11, committed unchanged: peter_sm's
nineteenth reading (Home Assistant, after dark; five blocks inconsistent in one round),
tristangrichard's SH8.0RT-V112 on P023 over the cable (the first SH8.0RT on P023; 12 link drops
outside the block read test), and from one anonymous site an SH10RT-V112 on P023 read through
modbus-proxy while the YAML package and evcc polled (37 of 37 blocks, no reconnect; added to
`contention`) and an SG10RT, the first three-phase string inverter (new page `device-sg-rt`).
New installation page tristangrichard.

## [2026-11-13] changed | the wallbox search tries units 2 and 4 behind a dongle

A WiNet-S may forward a wallbox at a unit other than the 3 measured at gerd: 2 and 4 are reported
elsewhere (ioBroker, evcc #7104, ha-modbus-manager #127, an AC011E-01 in #786), none measured
here. The search now tries 3, 2, 4 and 248, and counts a unit only if its model name starts with
`AC`. New query which-unit-does-a-winet-s-give-a-wallbox; updated device-wallbox, the index.

## [2026-11-14] changed | a remote site's link drop, and the tunnel that did not recover

The provider cut gerd's internet line at about 02:52; every read of the wallbox and inverter timed out until the tunnel was restarted at about 07:00. New concept remote-link-loss and its raw note; the index.

## [2026-11-14] answered | register 13023 is the charge within the min-max SoC window

At gerd the inverter's battery level read 1.5 % while the SBR096's own SoC read 11.4 % and the app
11.1 %, at a 10 % minimum: the maintainer's reading, that 13023 is relative to the usable window
between minimum and maximum SoC, fits, and so do 48 of 57 corpus pairs within 2 points (four
misses, all peter-sm). New entity register-13023, new source gerd-battery-level-2026-11-14;
updated device-sbr-battery, installation-gerd (max SoC now 100 %, 90 % until 2026-11-03), and the
SH6.0RT-20 source page that left the question open.

## [2026-11-14] ingested | gerd's wallbox is controlled through the inverter

On site with a car charging: the inverter manages the AC22E-01 and drives its output current
(21203), which the car follows at 0.1 A per count; writes to 21203 are overwritten. Charging
on/off (33540), mode (33541) and the user-defined current (33545, only in user-defined mode, 6 A
up) at the inverter were written over the cable and the WiNet-S and followed by the car; a mode
change can end the session. New source gerd-wallbox-inverter-control-2026-11-14; updated
device-wallbox (new section), installation-gerd, the index. The wallbox capability test now
writes only to a wallbox declared standalone and never disables or offers under 6 A.

## [2026-11-14] ingested | phase switching on a managed wallbox, from Sungrow's documents and owners

Read Sungrow's AC22E-01 datasheet and manual, the SH-RT and iSolarCloud manuals, the EV Power
Guide, ha-modbus-manager's two wallbox pages and Photovoltaikforum's 873-post AC22E-01 thread.
None offers a way to choose the phases of a wallbox an inverter manages: switching is automatic,
by owners' reports to one phase in PV surplus with energy purchase off. New raw note and source
wallbox-phase-switching-sources-2026-11-14, concept managed-wallbox-phases, query
can-a-managed-wallbox-be-set-to-one-phase; updated device-wallbox, where-are-sungrows-documents,
gerd-wallbox-inverter-control-2026-11-14 (no phase setting in the app; 33538/33539 refuse writes),
the index.

## [2026-11-14] measured | gerd's 33538/33539 refuse writes in PV surplus mode too

With charging off and the mode set to PV surplus, 33539 = 160 and 33538 = 0xAA were refused
(0x04) as they were in fast charge; 33539 read 161 in both modes; all put back. Updated the raw
note gerd-wallbox-inverter-control-2026-11-14, its source page, the query
can-a-managed-wallbox-be-set-to-one-phase, concept managed-wallbox-phases, the index.

## [2026-11-14] measured | 33550 is the app's energy purchase (Netzbezug)

At gerd, in PV surplus with charging off, the maintainer switched *Netzbezug* on and off in the
app; the inverter's 33550 read 170 and 85 within 5 s each time, nothing else moved and no charge
started. Updated the raw note gerd-wallbox-inverter-control-2026-11-14, its source page.

## [2026-11-14] ingested | gerd's app settings mapped to the wallbox's registers

The maintainer changed each of the charger's system parameters in iSolarCloud and back while the
wallbox and the inverter were read whole: enable 21211 (status 8 while disabled), Plug&Play 21298,
offline current 21299, power limit 21313, with input echoes; the offline current does not follow
the limit. New raw note and source gerd-wallbox-app-settings-2026-11-14; updated device-wallbox,
the index.

## [2026-11-14] measured | the charger's own app page writes the same words; mileage set back

At gerd, the charger's *Einstellungen* page: its Plug&Play moved holding 21298 and its Netzbezug
the inverter's 33550, as the other screens do; *Fahrstrecke pro kWh* is holding 21232, set back
from 5555.2 (left by the capability test of 2026-11-13) to 5.0. Updated the raw note and source
gerd-wallbox-app-settings-2026-11-14.

## [2026-11-14] measured | the integration's EV charger controls at gerd's, from Home Assistant

The four controls on gerd's inverter entry (P022, cable), each written once from the dev Home
Assistant and put back with no car charging: grid purchase both ways, the user current refused
outside user-defined mode and taken in it, the mode with charging kept off, charging on and off.
The block read as before afterwards. New raw note and source gerd-wallbox-ha-controls-2026-11-14;
the index.

## [2026-11-15] ingested | peter_sm's twentieth reading, the first network_names from a house (#786)

Posted by Korsberg: SH10RT-V112 on P023, the inverter's own LAN port, integration 0.1.0a40, with
a capability test (outcome 3). Its WiNet-S answered Home Assistant's multicast mDNS browse with
gerd's TXT layout and an `ethinfo` address; the inverter's MAC vendor prefix is `AC:19:9F`. EMS
mode 3 was taken; 33213 lost the connection a tenth time of ten, 33047 above its bound a third
time; 13074 times ten again; restart in 271 s. New source page; updated installation-peter-sm,
the P023 page, the 33213 and mDNS queries, the index.

## [2026-11-15] measured | discovery at the maintainer's house; a RAK WiFi module

Through the production Home Assistant on 0.1.0a40: zeroconf heard nothing from Sungrow; a RAK
WiFi module answers HTTP 401 on 80 and DHCP as rakmodule-*, RAKwireless's prefix; Sungrow's one
IEEE prefix is AC:19:9F; the network search missed the inverter twice while the manual step found
it. New raw note and source mkaiser-network-discovery-2026-11-15, entity device-rak-wifi-module,
query why-did-the-search-miss-mkaisers-inverter; updated installation-mkaiser, the mDNS query, the
index.

## [2026-11-15] decided | the owner's controls and a capability test never write at once

While a run writes, the integration's controls refuse; auto repeat waits after the owner wrote;
an owner's write replaces its register's entry in a leftover snapshot. Updated
capability-test-restore.

## [2026-11-15] ingested | mkaiser's sixth reading, the first plausibility block from hardware

A diagnostics download from the maintainer's production Home Assistant (0.1.0a40, SH10RT on P020,
its own LAN port), committed unchanged as -5: three auto-repeat capability-test runs (outcome 3,
0 failed), the forced-charging window now passing, five battery-power upper bounds stored above
their maximum, and the first plausibility block measured on hardware (power balance, tracker V×I
and both meter checks matched; battery idle). New source page; updated installation-mkaiser, the
P020 page, the index.

## [2026-11-15] corrected | auto repeat is on every entry

The integration stopped offering the diagnostics-only setup: there is one setup, it creates
entities, and the diagnosis and capability test are on every inverter's device page under
*Diagnostic*. Updated capability-test, which said auto repeat was a diagnostics-only entry's
alone.

## [2026-11-16] ingested | a Modbus proxy at the maintainer's house, and what 6100 says through one

The house polls its inverter through a modbus-proxy on the production Home Assistant's machine, so
the search finds one inverter at two addresses, with one serial and one route note at both. The
config flow's probe of 6100 answers through the proxy; a config entry's probe of the same address
does not, three times, while the same entry reads `direct` at the inverter's own LAN port. Neither
card could be named a proxy: a proxy is named only where the searching Home Assistant is its host,
and no ARP entry crosses a container bridge. The offer order then fell through to the host string,
which is fixed to compare addresses. New raw note and source mkaiser-modbus-proxy-2026-11-16, query
does-a-modbus-proxy-carry-6100; updated contention, transport-detection, register-6100,
installation-mkaiser, the search query (narrowed), the index.

## [2026-11-16] decided | an entry keeps its own route measurement

Where [register 6100](entities/register-6100.md) says nothing, the entry shows unknown rather
than carrying the config flow's measurement of the same address or retrying the read. The flow's
answer is another session's, and three attempts at a proxy in one evening had already got nothing
where the inverter's own LAN port answered at once. Recorded on the proxy query.

## [2026-11-16] ingested | mkaiser-mac-prefixes-2026-11-16

Two neighbour-cache lookups from the Windows host that carries the dev
container, on the house's own segment: the inverter's own LAN port answers
Sungrow's `AC:19:9F` -- the second reading of one, after peter_sm's
eighteenth diagnosis -- and the proxy beside it answers a locally
administered prefix, because that Home Assistant runs on a virtual machine.
New: [telling a proxy from the inverter](concepts/telling-a-proxy-from-the-inverter.md),
gathering the three tests and the 2x2 with
[register 6100](entities/register-6100.md). Updated:
[installation-mkaiser](entities/installation-mkaiser.md),
[transport detection](concepts/transport-detection.md).

## [2026-11-16] decided | a locally administered MAC ranks a card, a foreign one only notes it

IEEE's U/L bit is clear in every registered prefix, so a prefix with it set
says no manufacturer issued the port -- which neither an inverter nor a
communication module can be, and which no future Sungrow registration can
overturn. A merely foreign registered prefix stays a note: a
[RAK module](entities/device-rak-wifi-module.md) carries RAKwireless's
`AC:1F:09`, so hardware says "not Sungrow" too, and being wrong that way
tells somebody their inverter is a proxy.
`wifi_module.is_locally_administered` and the picker in
`config_flow_schemas.py`.

## [2026-11-16] decided | a short list of hypervisor prefixes ranks a card too

The U/L bit misses a hypervisor that holds an IEEE block, and the common ones
do -- Proxmox's `BC:24:11` has been registered since June 2023, which is the
maintainer's own stack, where only the machine's age put its address on the
invented side of the test. `wifi_module.VIRTUAL_MAC_PREFIXES` names Proxmox,
Hyper-V, VMware, VirtualBox, Xen and Parallels, and ranks a card like an
invented address: the claim is positive, so being wrong would need Sungrow to
ship an inverter with a VMware port. It stays short -- stale costs a label,
never a wrong one -- and
[telling a proxy from the inverter](concepts/telling-a-proxy-from-the-inverter.md)
says why a longer one would be the weaker note's job instead.

## [2026-11-16] decided | the diagnosis measures its reader rather than asking about it

Asked whether the user-data section should record how Home Assistant is
installed -- virtual machine, container, native -- to explain an empty mDNS
browse or an absent MAC prefix. It should not. The answer would be testimony
about Home Assistant while the diagnosis runs wherever it runs, often not on
Home Assistant at all, and Home Assistant OS is a container with host
networking, so the answer would predict a blindness that is not there.

Schema 28 measures it instead: `mdns.services_heard`, every `_http._tcp`
instance that answered rather than only the Sungrow ones, and
`on_device_segment`, whether the reading machine holds an address on the
device's own network. That follows
[identify by what answers](concepts/identify-by-what-answers.md) applied to
the reader, and costs a contributor nothing where a question costs every one
of them a prompt. It is what makes
[does a WiNet-S advertise over mDNS](queries/does-a-winet-s-advertise-over-mdns.md)
answerable: until now `nothing_answered` has been the same word for the
device's silence and the reader's.

Install type, where it is wanted for support, belongs in Home Assistant's own
`diagnostics.py` download, which nothing publishes.

## [2026-11-16] ingested | sh10rt-v112-b001v000p023-3p-anonymous-anon-14076202309-battery-unknown-winet

A Home Assistant diagnostics download posted to issue #786: an SH10RT-V112 on
P023 through a WiNet-S, with a wallbox behind the dongle. The diagnosis
section alone, so no register dump and no block read test. The inverter reads
as a dongle throughout -- 6100, 5741 and 5744 refused, 2612 and 2628
unanswered.

The wallbox is the news. It is the third read anywhere and the first that is
not an AC22E-01: an **AC011E-01 at unit 4**, 16 A over three phases,
`AC011K-AE-25_V1.7.18` where 21216 says `AC011E-01`. It answers
[which unit a WiNet-S gives a wallbox](queries/which-unit-does-a-winet-s-give-a-wallbox.md)
-- not always 3, and the unit is a property of the installation -- and
confirms 21203 at 0.1 A per count on the very model whose other map reads it
as 0.01 A: 6.0 A idle, where 0.01 A would make it 0.6 A. Its 21272 and 21273
read 4140 W and 11040 W, 6 A and 16 A over three 230 V phases, so the 2023 EV
Power Guide's 4.14 kW minimum is now read from a wallbox.

Updated: [the wallbox](entities/device-wallbox.md),
[P023](entities/firmware-sapphire-h-b001-v000-p023.md), the index, and
`wallbox/discovery.py`'s note, where unit 4 was reported and is now measured.
`devices-wanted.md`'s row 5 asks for a third model or a second of either
instead.

## [2026-11-16] ingested | mkaiser-mdns-2026-11-16

A multicast browse from the maintainer's **Windows host on the house LAN**,
not the dev container -- the point of the run. `probe.py mdns --seconds 15`,
read only.

**44 service instances, 35 service types, four of them `_http._tcp`, and not
one Sungrow record.** No `WiNet-WebServer`, no `SUNGROW*`, and no match for
`sungrow`, `winet` or `solar` in any instance name, server name or TXT value.
The host held an address on the inverter's own /24 and the inverter in its ARP
cache under `AC:19:9F`, so `on_device_segment` was true.

That is the half of the pair schema 28's `mdns.services_heard` was added for:
a `nothing_answered` **with records heard beside it**. Until now every reading
of an inverter's own LAN port was the ambiguous kind, where "the device says
nothing" and "this machine hears nothing" wear the same word. So **an SH10RT's
own LAN port advertises nothing over mDNS** is now measured, and so is the
[RAK WiFi module](entities/device-rak-wifi-module.md)'s silence beside it.

The Windows firewall sub-question, which nobody had written down, is answered
from the rules the firewall holds: a Python process binding UDP 5353 raises the
Defender Firewall dialog **once per interpreter** -- Windows' own `mDNS (UDP-In)`
rule is scoped to `svchost.exe`/`dnscache` and does not cover it -- and
answering it writes a `TCP Query User{...}` and a `UDP Query User{...}` rule
granting inbound TCP and UDP on **any** local port, Private and Public, to that
binary. Both were already present here, so this run raised nothing and added
nothing. Whether *declining* silences the browse is now an explicit open
sub-question: it would be a third silence, indistinguishable from the
container's.

Also recorded: `pip install -e ".[discovery]"` is not enough to start
`probe.py` on a bare interpreter -- `modbus_connection.tmodbus` needs `serialx`,
which comes only with `modbus-connection[tmodbus]`.

Updated: [the query](queries/does-a-winet-s-advertise-over-mdns.md) (two
results to three, two new open sub-questions),
[mkaiser](entities/installation-mkaiser.md), the
[RAK WiFi module](entities/device-rak-wifi-module.md),
[telling a proxy from the inverter](concepts/telling-a-proxy-from-the-inverter.md),
and the index.

## [2026-11-16] ingested | mkaiser-mdns-firewall-2026-11-16

Four 15-second browses from the maintainer's Windows host, changing only the
Windows Defender Firewall state. **A declined prompt does not silence the
browse. It degrades it**: 37 instances and 3 `_http._tcp` where the baseline
had 44 and 4, with the baseline reproduced exactly after restoring, so the
drop is the firewall and not a quiet network.

That is the bad answer to the sub-question the morning's browse left open.
`services_heard` would have read 3 -- non-zero, healthy looking, eight records
short. The field tells a deaf machine from a silent device and **nothing
more**, which `device-diagnosis/reference.md` now says and the new concept
page [a browse is a floor](concepts/mdns-browse-is-a-floor.md) holds.

**Two corrections, both to claims committed earlier today.**

The [RAK WiFi module](entities/device-rak-wifi-module.md) **does** advertise
over mDNS, under `_rak47x._tcp` on port 5000, with its firmware version and
its whole MAC address in the TXT record. It is intermittent: heard in one
browse, missed in two others the same afternoon, all three counting 44
instances. The morning's page said it announced nothing; so did the
2026-11-15 reading. Both were browses that missed it.

And the headline is restated. "An SH10RT's own LAN port advertises nothing"
rested on one browse that heard everything; it now rests on five browses with
no Sungrow record, which is strong and is not proof -- those same browses
missed a device that was advertising.

Also fixed, and found by the run crashing: `probe.py mdns` died with
`UnicodeEncodeError` on a legacy Windows console, because a TXT value that is
not text becomes U+FFFD and cp1252 cannot encode it. Records print sorted by
instance name, so everything after the offender was lost -- `SUNGROW*` and
`WiNet-WebServer` sort after the Thread border router that triggered it. A
contributor would have seen a short list with no Sungrow in it and no reason
to doubt it. `main` now forces UTF-8 on stdout and stderr
(`device-diagnosis/scripts/python/probe.py`), verified under
`PYTHONIOENCODING=cp1252`.

Updated: [the query](queries/does-a-winet-s-advertise-over-mdns.md) (three
results to four), [the morning's browse](sources/mkaiser-mdns-2026-11-16-summary.md),
[the RAK module](entities/device-rak-wifi-module.md),
[mkaiser](entities/installation-mkaiser.md), `device-diagnosis/reference.md`,
and the index.

## [2026-11-16] ingested | the firewall browse, run a second time

[The second run](sources/mkaiser-mdns-firewall-run2-2026-11-16-summary.md) of
the four-browse firewall test at [mkaiser](entities/installation-mkaiser.md),
three and a half hours after the first, with the script unchanged. Restore
verified by read-back, exit 0.

**Answered: it is the same eight records every time.** The counts do not
compare between runs -- more devices were on air in the afternoon, 46 allowed
against 44 -- so the runs were compared per record. Of the 42 instances heard
in an allowed browse in both, 33 survived all four degraded browses and the
**same 8 were lost in all four**: a NAS's three, a door station's three, a
streaming stick's one and the
[RAK module](entities/device-rak-wifi-module.md)'s. One `_matter._tcp` was lost
once per run, in the other state each time. The first run's "why those, and is
it luck" is half settled: it is not luck.

**And it is the record, not the host.** A TV switched off during run 1 was on
for run 2 and published four records from one address: `_airplay._tcp` survived
both degraded browses while `_googlecast`, `_display` and `_ghp` were lost. So
the mechanism is not reachability, a route or a VLAN. Those three records are
also the only apparent disagreement between the runs, and only because the TV
was off the first time. The address family is ruled out too: nearly every
record on both sides publishes IPv4 and IPv6.

**Still open, and now worth asking**: what separates those eight from the 33.
The hypothesis to test is unicast against multicast answers, which Windows'
"allow unicast response to multicast" would split exactly this way. That is a
packet capture, and nothing the integration ships waits on it.

A sixth, seventh, eighth and ninth browse with no Sungrow record of any kind,
so "an SH10RT's own LAN port advertises nothing" now rests on nine. Four
allowed browses across the day heard 44, 44, 46 and 47 and no two were the same
set.

Updated: [an mDNS browse is a floor](concepts/mdns-browse-is-a-floor.md),
[the query](queries/does-a-winet-s-advertise-over-mdns.md) (four results to
five), and the index.

## [2026-11-16] ingested | the forced startup mode's first run on hardware, mkaiser

The capability test engine's own `forced_startup` mode had never run on an
inverter; it ran at [mkaiser](entities/installation-mkaiser.md)'s SH10RT on
P020, over the cable, from Home Assistant's `run_capability_test` action, with
the battery at 0.0 % against its 10 % minimum and no PV
([the run](sources/mkaiser-forced-startup-2026-11-16-summary.md)).

It did what the simulator said it would: 0xAA, left standby after 123 s,
Running after 208 s, 0x55, back in standby 16 s later, verdict "the inverter
did as it was told", outcome 0 and no finding. The guard admitted low-SoC
standby without argument, part B wrote that one probe and nothing else, and
the restore had nothing to put back -- 13017 already held the 0x55 the
2026-11-08 run left there.

Two things worth keeping beyond the verdict. **The timing repeats**: 123 s and
208 s against 121 s and 215 s eight days earlier, same inverter, firmware and
cable. And **a state change is not evidence of a register change**: the same
evening, with 13017 off and nothing written, the inverter took a
fifteen-second running window by itself at 22:48, so the report of 0xAA being
flipped back (issue #444) has to be settled by reading the register, not by
watching the running state.

The same run's part A brought the house's plausibility checks to five matched
of 24 established six.

Updated: [register 13017](entities/register-13017.md) (the mode has run; a
0x55 on B001 firmware says a write has happened there, not that the firmware
differs), [installation mkaiser](entities/installation-mkaiser.md), and the
index.

## [2026-11-17] ingested | an inverter takes a second session from the polling address, mkaiser

The one explanation
[why did the search miss the maintainer's inverter](queries/why-did-the-search-miss-mkaisers-inverter.md)
carried -- that an inverter's own LAN port refuses or stalls a second TCP
connection from an address that already holds one -- is measured and **wrong**
([the run](sources/mkaiser-second-session-2026-11-17-summary.md)).

The dev container swept its own /24 twice while its own Home Assistant had
been polling the inverter without a break since the previous evening: 12 of 12
connects accepted in 7.6 to 21.8 ms, the inverter found by both sweeps, and
the poller lost no connection over either. So [contention](concepts/contention.md)
does not explain the miss.

What is left is narrower and worth saying plainly: the production Home
Assistant reaches this inverter **through a modbus-proxy on its own machine**,
so the session held from that address is the proxy's, not Home Assistant's.
The sweep that would settle it is the same one from the production machine
with the proxy running.

Updated: [the query](queries/why-did-the-search-miss-mkaisers-inverter.md)
(its question is now the open one, two results to three),
[installation mkaiser](entities/installation-mkaiser.md), and the index.

## [2026-11-17] ingested | 13017 left on for 90 minutes, mkaiser

The open half of [register 13017](entities/register-13017.md) -- whether an
inverter flips `0xAA` back by itself or when PV arrives (issue #444 reports
~20 minutes) -- answered at mkaiser's SH10RT on P020, read back from the
register rather than judged by the running state
([the watch](sources/mkaiser-forced-startup-left-on-2026-11-17-summary.md)).

**It does not flip back.** 13017 held `0xAA` for 90 minutes 48 seconds, the
longest watch on record against bar12's 23 minutes, and dawn did not undo it
either: PV rose above 0 W at 59 minutes and the register still read `0xAA`
31 minutes later. The inverter ran 56 minutes in the dark on `0xAA` alone with
the battery at 0 %. So #444 is not reproduced on P020; other firmware, or
iSolarCloud rewriting the register, are what is left to explain it.

The wake timing is now three runs over nine days by three methods at one
house: `Starting` at 121, 123 and 122 s, `Running` at 215, 208 and 207 s.

The restore was late and the page says so: the watcher's Home Assistant token
expired 29 minutes in, so its `finally` block could not write, and the
register was put back by hand 50 minutes after the intended end. The lesson is
on the source page -- a restore that depends on a credential which can expire
mid-run is not a restore.

Updated: [register 13017](entities/register-13017.md),
[installation mkaiser](entities/installation-mkaiser.md), and the index.

## [2026-11-17] ingested | Diagnosis: stop mid part B, on hardware, mkaiser

Only the simulator had seen *Diagnosis: stop* pressed while a capability test
was writing. It was pressed on hardware at mkaiser's SH10RT on P020, 60
seconds into part B, after six settings had been written and during the forced
charge probe ([the run](sources/mkaiser-stop-mid-run-2026-11-17-summary.md)).

[The restore](concepts/capability-test-restore.md) ran to completion in about
50 seconds: all seventeen touched settings read back at their pre-run values
with **zero mismatches**, the snapshot store was dropped, the owner's controls
were released, and the running state read `Running` before and after -- **no
restart started**. The run reported "ran, but checks were skipped or
inconclusive", 0 findings, no error, which is what a deliberately interrupted
run should say.

Updated: [the restore](concepts/capability-test-restore.md),
[installation mkaiser](entities/installation-mkaiser.md), and the index.

## [2026-11-17] ingested | a forced charge from the grid, mkaiser

A 48-minute forced charge at mkaiser's SH10RT on P020, 0.0 % to 25.5 % at a
steady 4501 W, run from the scenes in `doc/scenes.md`
([the charge](sources/mkaiser-forced-charge-2026-11-17-summary.md)).

What it settles about the scenes: a scene **does** set both selects, which is
what the rewrite was for; it moves **no energy** by itself, because the charge
power is a separate number sitting at its factory 0; and the companion
automation's `state_attr(number..., 'max')` renders a real figure on hardware,
7420 W. That last one matters more than it looks: the same `max` read 7148 W
with the pack empty and 7318 W a minute later, because the pack's limit falls
back to what the BMS will take at that moment
(`src/sungrow_modbus/battery/power.py`). A scene storing a fixed watt figure
would be wrong at almost every moment; reading the entity's `max` at
activation is right.

About the battery: the state of charge advances in steps of about **1.1
percentage points**, not the 0.1 its register's scale suggests -- roughly
160 Wh per step on this pack -- so anything comparing an SoC delta with an
energy figure has to allow for it. SoC and energy otherwise agree: 2.25 kWh
delivered against 2.07 kWh implied.

And a caution for whoever reads a counter during a test: register 13040 sits
on the 600 s tier, so it read 0.00 kWh nine minutes into a 4.5 kW charge and
then moved in 0.5-0.8 kWh steps.

Updated: [installation mkaiser](entities/installation-mkaiser.md) and the
index.

## [2026-11-17] ingested | which write bounds the inverter enforces, mkaiser

Run 3 of auto repeat at mkaiser's SH10RT on P020 ran the upper-bound checks
with the battery at ~22 %, and they answer the range-check question directly
([the run](sources/mkaiser-range-checks-2026-11-17-summary.md)).

**Only the state-of-charge bound is the device's.** 13057 refused 101 % with
exception 0x04. Every battery *power* bound was taken and stored above its
maximum: 7374 W against 7274 for max charge and max discharge power, 1010 W
against 1000 for both start-power thresholds. So the entity's maximum is the
only guard there is, which is the measured form of the claim the range-check
work rests on.

The forced charge/discharge power looked like an exception -- 7374 W written,
7370 W stored -- and is not: 7370 W is still above the 7274 W maximum, and the
difference is the register rounding to 10 W. The capability test recorded it
as "the device clamped it" all the same, because
`capability_test/writepath.py` treats any readback word below the written word
as a clamp without asking whether the stored value is inside the bound, and
`CLAMPED` maps to established in `capability_test/ledger.py`. A register that
rounds to its own step is therefore recorded as enforcing a maximum it does
not enforce, and the check is never asked again. Logged here because the fix
is a code change, tracked in `Todo.md`.

Also kept, because they say what a day's testing needs: the charge ceiling
wants the battery charging above 55 %; both start-power thresholds want
battery power between 200 and 800 W; and the pack's own limit moves mid-check
-- a manufactured discharge asked 4823 W and the pack took 4820 W.

Updated: the index.

## [2026-11-17] ingested | what a lived-in house costs the capability test, mkaiser

Runs 3 and 4 of auto repeat each lost a behavioural check to the drift gate,
and the reason is about houses rather than about this inverter
([the runs](sources/mkaiser-drift-gate-2026-11-17-summary.md)).

A behavioural check refuses to attribute a change when the house drifted more
than `max(150 W, 15 %)` across the measurement. That is the right answer -- an
unattributable change is not evidence -- but run 4 shows when it bites: the
quantity under test was a battery flow of about 206 W, so the tolerance was
the 150 W floor, roughly three quarters of the signal, and one appliance
switching on lost the check. Run 3 lost the export power limit the same way,
at the other end of the scale, to 2126 W of drift.

**The conditions fight each other.** Both start-threshold checks need the
battery moving 200 to 800 W with all of it through the battery, and a battery
moves that gently when PV is weak -- which is when household load dominates
the meter and staying inside 150 W is hardest. So they wait not on one
condition but on two that tend to exclude each other: a quiet house with a
gently moving battery.

Also kept, because they say what a day's testing needs: the forced discharge
wants a battery above its minimum, the charge ceiling wants it high enough for
`battery_max_soc` (floor 50 %) to be put under it, and the export limit wants
something to spend on making an export. The forced charge passed.

Updated: the index.

## [2026-11-17] ingested | the charging start threshold settles, mkaiser

The charging start threshold check had never run anywhere: it wants a battery
charging 200 to 800 W, which a forced charge cannot give because it charges at
kilowatts. It settled at mkaiser's SH10RT on P020, in a run auto repeat
started by itself, with the battery at its floor taking a trickle from a
brightening sky
([the run](sources/mkaiser-charging-threshold-2026-11-17-summary.md)).

Commanded 1000 W against 230 W of charging: charging stopped, and came back at
309 W when the threshold went back. "The inverter did as it was told" -- the
behaviour the YAML package's author predicted in a comment and labelled a
guess.

**It corrects this morning's reading.**
[What a lived-in house costs the capability test](sources/mkaiser-drift-gate-2026-11-17-summary.md)
reasoned that the start thresholds might never settle at a house with people
in it, since a gently moving battery and a quiet house tend not to co-occur.
One of the two has now settled, with before and after of 230 W and 309 W
staying inside the gate, where the discharging one failed on 216 W of drift
from a measurement of the same shape and size. So the gate at low power is a
matter of catching the window, not a wall. That page now says so; the
discharging threshold is still open.

Three plausibility checks settled the same hour -- battery, phase and tracker
voltage times current -- the tracker's having waited at 4 of 20 for PV above
300 W, which reached 772 W. The ledger stands at 36 of 54.

Updated: [the drift gate](sources/mkaiser-drift-gate-2026-11-17-summary.md)
and the index.

## [2026-11-17] ingested | the discharging start threshold settles too, mkaiser

An hour after the charging one, the discharging start threshold settled at
mkaiser's SH10RT on P020, in a run auto repeat started by itself: 1000 W
commanded against 205 W of discharge, the discharge stopped, and it came back
at 221 W ([the run](sources/mkaiser-discharging-threshold-2026-11-17-summary.md)).
Both start thresholds are now established on this firmware.

**This finishes a correction made twice in one day.** The morning's note
reasoned that these two checks might never settle at a house with people in
it, because a gently moving battery and a quiet house tend not to co-occur.
Both settled within three hours of each other, on the day the note was
written. The decisive evidence is the same check failing and then passing --
same register, same commanded value, same inverter, starting from 216.5 W and
205.0 W, differing only in whether the house stayed put. So the drift gate at
low power costs **attempts, not outcomes**, and what settles these checks is
leaving auto repeat running so it keeps trying.

The same run recorded `battery_ceiling_w = 5000` for the third consecutive
run, the owner's configured figure, against 7096-7274 before that option
reached the capability test.

Updated: [the drift gate](sources/mkaiser-drift-gate-2026-11-17-summary.md),
whose conclusion is now marked wrong while its reasoning about why these
checks are slow stands, and the index.

## [2026-11-17] corrected | today's pages read the battery level as the pack's

Three pages written today took [register 13023](entities/register-13023.md)
for the pack's absolute state of charge. It is not, and this wiki already
said so: the level is the charge **within the minimum-maximum SoC window**,
0 % being the minimum, established on 2026-11-14 from gerd's reading. Today's
pages were written against an established page by accident, not from new
evidence.

Confirmed again at the maintainer's while correcting: level 3.7 % with the
window at 10-90 % gives a nominal 13.0 %, exactly what
`Derived.battery_level_nominal` computes from the two limits.

What changed:

- **The forced charge page claimed the level and the energy agreed.** They do
  not. With the window at 10-100 %, 14.4 points of level is 13.0 points of
  pack -- about 1.87 kWh against 2.25 kWh delivered, a 17 % shortfall.
  Charging losses and a nameplate capacity that is the owner's configured
  figure both land in that, so nothing is concluded from it yet; it wants a
  longer charge to measure properly. The step size goes with it: ~1.1 points
  of window is ~1.0 point of pack, roughly 143 Wh here rather than 160.
- **The charging threshold page** said the battery was "at its 10 % floor".
  It read 10 % of the window, about 19 % of the pack, and was not at the
  floor.
- **The discharging threshold page** now says which scale its 11 % is.

The raw notes keep what they said, being sources; the pages state what is
true now.

## [2026-11-17] ingested | gerd-wallbox-night-2026-11-16

A VPN night at [gerd](entities/installation-gerd.md)'s, with a car charging
([the source](sources/gerd-wallbox-night-2026-11-16-summary.md), raw
`raw/gerd-wallbox-night-2026-11-16.md`). The managed capability test passed on its first run on hardware
(6, 8, 10 A followed, 5 A refused, stop and start timed). Writing charging on while on, or the mode it
already has, changes nothing; a change of mode to or from user defined while charging ends the session
within 6 s and charging on restarts it; **21203 is the user current exactly in user-defined mode and the
inverter's offer (24-28 A) in fast mode**, above the 16 A a phase the car takes. The managed test's restore changed the mode
back to fast and declared the house back before the inverter ended the session (28 s later): the restore has to
wait for the inverter to settle. A fast charge ran for hours at 0.2-0.5 % without ending, so the battery's
minimum alone does not end one. From 02:19 the car suspended its own charge
for hours with the inverter and the wallbox willing, and the inverter's word went off at 03:50. One ISP
reconnect, about 3.5 min, ridden out by the tunnel watchdog.

Updated: [the wallbox](entities/device-wallbox.md) (what the night added),
[gerd](entities/installation-gerd.md), a new query
[why a managed wallbox stops charging](queries/why-does-a-managed-wallbox-stop-charging.md), and the index.

## [2026-11-17] query | two protocol PDFs from discussion #795

Discussion #795 posted Sungrow's hybrid protocol V1.1.4 and the iHomeManager protocol V1.0.2. Neither
adds anything: the iHomeManager file is byte for byte the `test.1` copy already read (same SHA-256), and
hybrid V1.1.4 (2024-08-20) predates V1.1.11, this project's base. Both are recorded in
[where Sungrow's documents are](queries/where-are-sungrows-documents.md), whose `tmp/manuals/` is now a
bind mount of a folder outside the repository.

## [2026-11-17] ingested | gerd-car-morning-2026-11-17

The owner's report the morning after the wallbox night ([the source](sources/gerd-car-morning-2026-11-17-summary.md),
raw `raw/gerd-car-morning-2026-11-17.md`): the car reached 100 % after sitting `suspended by the vehicle`
from 02:19, so the suspension was a pause; and the car says its Internet connection is not established,
which makes the car app's statuses that night suspect, its "done at 47 %" included.

Updated: [why a managed wallbox stops charging](queries/why-does-a-managed-wallbox-stop-charging.md),
[gerd](entities/installation-gerd.md), [the wallbox](entities/device-wallbox.md), and the index.

## [2026-11-17] ingested | gerd-wallbox-2026-11-17-afternoon

A VPN afternoon at [gerd](entities/installation-gerd.md)'s with the car charging from 80 % to 92 %
([the source](sources/gerd-wallbox-2026-11-17-afternoon-summary.md), raw
`raw/gerd-wallbox-2026-11-17-afternoon.md`). The four EV charger controls were written from Home Assistant,
and each did what it says. Two mode changes while charging (fast to user defined and back) **did not** end the
session, where the night before both did. 21203 follows a user-current change 4-5 minutes late. The car was cut
back four times with nothing written, after house load spikes. The managed test passed again from the terminal,
and the restore that settles and then watches the car held on its first hardware run. From Home Assistant the
managed test took the standalone path and wrote nothing: an inverter entry on the cable never links to the
wallbox entry. Two integration faults were found and fixed in the same change (the extended-test guard on a
wallbox entry, and a standalone snapshot that would have gone back through a managed wallbox).

Updated: [the wallbox](entities/device-wallbox.md) (21203 lags; a mode change does not always end a session),
[gerd](entities/installation-gerd.md), [why a managed wallbox stops charging](queries/why-does-a-managed-wallbox-stop-charging.md)
(three results to four), and the index.

## [2026-11-17] ingested | the midnight-reset check fails on a clock at the maintainer's

The readings checks have been observing between runs at
[mkaiser](entities/installation-mkaiser.md)'s SH10RT since the evening of 2026-11-16. After 932
observations one of them has **failed** -- their first failure on hardware -- and the inverter
did nothing wrong
([the midnight reset](sources/mkaiser-midnight-reset-2026-11-17-summary.md)).

`daily counters reset at midnight` recorded `daily_pv_generation fell from 4.4 to 0 at 23:04`.
The development instance keeps UTC; the inverter keeps German local time, measured an hour ahead
of it in run 2's `inverter_clock`. So the fall happened at **00:04 on the inverter's clock**, to a
clean zero: a textbook pass, judged against the wrong midnight. The observation is stamped with
`dt_util.as_local(now)` and `_near_midnight` spans 23:30 to 00:30 of *that* clock.

The clock that would settle it is already collected, in every run's `conditions`. A failed
readings check counts as answered, so auto repeat will not wait for a second midnight: the row
stands as the house's one failure until the ledger is cleared or the check's revision is raised.

What changed:

- **`concepts/capability-test.md`** said the readings checks were not measured on hardware yet.
  They have been, at mkaiser's, and the page now carries both the passes and this failure.
- **`entities/installation-mkaiser.md`** gains the failure and the 926 passes of
  `lifetime counters never fall`, still short of its day of polls.

## [2026-11-18] ingested | the midnight reset repeats, to the minute

A second night of observing at [mkaiser](entities/installation-mkaiser.md)'s SH10RT, read at 1440
observations ([the second night](sources/mkaiser-midnight-reset-night-2-2026-11-18-summary.md)).

The inverter reset `daily_pv_generation` from 1.6 to a clean 0 at 00:03 on its own clock, against
4.4 to 0 at 00:04 the night before: different days, different totals, the same minute. **Its
counters are sound, measured twice.** What repeats with them is the false failure, because the
development instance still keeps UTC while the inverter keeps German local time.

That changes the defect's status rather than its diagnosis. It is not an occasional artefact but
one failure a night, for as long as the two clocks disagree. Each night's sentence carries that
day's kWh figure, so it is distinct and is appended: the row grows until five are kept.

What changed:

- **`concepts/capability-test.md`** said a failed readings check "counts as answered". True of the
  verdict, but it understated the behaviour: the check keeps judging and accumulating distinct
  failures, and `verdict()` cannot recover while any is held. The page now says so.
- **`entities/installation-mkaiser.md`** carries the second night and the counts at 1440
  observations: `lifetime counters never fall` at 1434 passes with no failure, `running states`
  with its day of polls seen.

## [2026-11-18] ingested | the first day of polls anywhere

The two readings checks that wait for **a day of polls** reached their minimum at
[mkaiser](entities/installation-mkaiser.md)'s SH10RT, the first time either has anywhere
([the day of polls](sources/mkaiser-day-of-polls-2026-11-18-summary.md)). Over 1470 observations
spanning 30 hours -- a day, a night, a forced charge from the grid, five hours of low-SoC standby
and a six-minute burst of lost connections -- `lifetime counters never fall` passed on 1464 judged
steps with none going backwards, and `running states` passed on four codes, all in the decode
table. The house stands at **39 of 54**.

The running-state counts carry a sampling lesson worth keeping: `Starting` was caught **once** in
1470 polls, so a code's absence from such a listing is not evidence the inverter never entered it.

What changed:

- **`entities/register-13000.md`** gains what a day of polling actually produces, and the warning
  that a one-minute cadence samples a transient state by luck.
- **`entities/installation-mkaiser.md`** carries the settle and the new count.

## [2026-11-18] ingested | peter_sm's twenty-first and twenty-second readings (#786)

Two more readings of [peter-sm](entities/installation-peter-sm.md)'s SH10RT-V112 on P023, 79
minutes apart on 2026-11-16, posted by Korsberg
([the twenty-first](sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-19-summary.md),
[the twenty-second](sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-20-summary.md)).
The second is the first committed document written by **schema 28**, and names integration
0.1.0a43.

**The site import limit holds on an SH10RT-V112.** The capability test's `--import-limit` check ran
at this house for the first time and ran twice: under a forced charge over the cable, caps of
800 W and 1730 W took import from 1438 W to 768 W and from 2359 W to 1702 W, each returning when
the cap came off. That is ulfben's model, on ulfben's firmware family, obeying -- so neither the
model nor the firmware explains the one report against
[register 32998](entities/register-32998.md), and only how that charge was commanded is left.

What changed:

- **`entities/register-32998.md`** gains the SH10RT-V112 confirmation, and the one difference in
  the range words: 5001 **lost the connection** here instead of being refused with 0x04.
- **`queries/does-the-import-limit-hold-during-a-forced-charge.md`** narrows to the command path.
- **`entities/installation-peter-sm.md`** carries both readings: the forced charge measured again
  for the first time since the third reading (the house had held `battery_max_charge_power` at
  10 W), an eleventh and twelfth link drop on 33213, a third on EMS mode 3, and restarts ten and
  eleven, both back at 271 s.

## [2026-11-18] ingested | Maximo101's SH10RS on P067, with an iHomeManager and an AC22E-01 (#786)

A read-only diagnostics download from an Australian house with an
[SH10RS](entities/device-sh-rs.md) on [P067](entities/firmware-sunstone-h-b000-v002-p067.md), two
[SBR192](entities/device-sbr-battery.md), an [iHomeManager](entities/device-ihomemanager.md) and an
AC22E-01 [wallbox](entities/device-wallbox.md) on its own entry
([the reading](sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)).
Six downloads were posted, three pairs of the same entry seconds apart; all six agree on what they
establish, so the one taken after the owner answered the diagnosis's questions is committed.

**Version 1 and version 2 moved under an unchanged P067**: `.02.69` and `.03021.01.16` here
against `.02.67` and `.01.15` at the first P067 reading twelve days before. The inverter firmware
string alone does not say what an SH-RS is running.

What changed:

- **`entities/firmware-sunstone-h-b000-v002-p067.md`** leads with the moving versions.
- **`entities/device-sh-rs.md`** gains two standing overrides of the family table: 13250 answers on
  every SH-RS read, against V1.1.16's remark, and the SH8/10RS's four MPPTs answer although `MPPT3`
  lists the RS family absent. The probe keeps both, so nothing is lost.
- **`entities/device-sbr-battery.md`** gains "two packs read as one capacity", now measured at two
  houses: 44.8 kWh for two SBR224 and 38.6 kWh for two SBR192.
- **`entities/installation-maximo101.md`** is new.

Left open: the house's AC22E-01 could not be ingested. A **wallbox-only entry's diagnostics report
carries no `diagnosis` section** although the entry runs one -- `diagnostics.py` returns its entry
and device rows and stops -- so three downloads of it hold nothing to read. Noted in `Todo.md`.

## [2026-11-18] ingested | swo14's cluster: two SH10RT-20 on 01011.95.03, a BYD pack, a proxy (#786)

Three readings from a **second master/slave cluster**, each with a capability test
([the host](sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-summary.md),
[the host again](sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-2-summary.md),
[the slave](sources/sh10rt-20-3p-sw14-anon-25617150722-battery-none-direct-lan-summary.md)). Both
inverters are on the older [`SAPPHIRE-H_01011.95.03`](entities/firmware-sapphire-h-01011-95-03.md),
reached through a Modbus proxy on a port each, with a **third-party BYD HVM 11 kWh** pack on the
host and none on the slave.

Five things it settles or moves:

- **[13074](entities/register-13074.md) is 1:1 on `.95.03` at a second installation**, and on a
  model that is not fwitten's SH10RT-V112. The firmware decides, not the model.
- **A cluster slave's unit id is 2 and it answers 0 for what it lacks**, twice now, so
  `device-diagnosis/devices-wanted.md` no longer asks for a cluster.
- **Register 5214 answers `0x7FFFFFFF` with no battery**, undeclared until now, so the slave's
  battery power read 2,147,483,647 W. Declared in
  `src/sungrow_modbus/hybrid_inverter/registers.py` with a test of its own.
- **[Register 6100](entities/register-6100.md) answers through a Modbus proxy** on both entries,
  on the entry's own polling connection -- the case mkaiser's proxy would not answer
  ([the query](queries/does-a-modbus-proxy-carry-6100.md) narrows to the address, not proxies).
- **[Register 32998](entities/register-32998.md) did not hold** on `.95.03`: a 520 W cap against
  1030 W of import moved nothing. The first SH-RT where it failed, and the integration already
  gates the control to P020, P022 and P023.

What changed:

- **`entities/installation-swo14.md`** is new.
- **`entities/firmware-sapphire-h-01011-95-03.md`** gains the second installation, the two ways
  13250 fails (a closed connection at fwitten, an exception here), and 13017's silence.
- **`entities/register-13023.md`** gains what a battery-less slave answers: 0xFFFF on P023, 0 here.
- **`queries/is-battery-power-firmware-dependent.md`** gains the S32 sentinel and a real BYD pack
  answering 5214, which bears on #770.

## [2026-11-18] ingested | bigz2012's SH10RS: the PV cut works on P067 (#786)

A read-only run after dark on 2026-11-16 with a **daylight capability test merged into the same
document** on 2026-11-17, through a wired WiNet-S2, the inverter restart deliberately left out --
the owner has servers on the backup circuit
([the reading](sources/sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan-summary.md)).

**[Register 31211](entities/register-31211.md) cuts PV on
[P067](entities/firmware-sunstone-h-b000-v002-p067.md)**: 3467 W before, 0 W during, 3641 W
after, `established: true`. The behavioural leg is the whole evidence through a dongle, and it is
the kind a dongle cannot spoil. `CONFIRMED_ON_FIRMWARE` gains the firmware, so the switch now
ships on P065 and P067 (`src/sungrow_modbus/hybrid_inverter/capabilities.py`).

**The run's outcome 4 is not a device finding**, and the owner's reading of it is right: 13074 was
written divided by ten because the scale could not be asked with feed-in limitation off, and the
60 that came back is the dongle's cache echoing the word it forwarded. The write scale on P067 is
unmeasured, not wrong. That **narrows the P071 lead** at
[ra1k-0](entities/installation-ra1k-0.md), where the same pattern was kept open as possible
evidence of a 1:1 firmware: two dongles on two firmware families now produce it, which a cache
explains and "the register took it" does not.

**The dongle's mDNS record names both SBR224**, `battery1` at units 2 and 200 and `battery2` at
**3 and 201**, each with its own serial. Unit 3 behind a dongle is a
[wallbox](entities/device-wallbox.md) at every other house measured -- here it is a battery, which
is why devices are identified by
[what answers](concepts/identify-by-what-answers.md). The first real reverse-DNS label in the
corpus comes with it: **`espressif`**, not a Sungrow name.

What changed:

- **`entities/installation-bigz2012.md`** is new.
- **`entities/firmware-sunstone-h-b000-v002-p067.md`** leads with the confirmed cut, and carries
  the 13974 W battery ceiling and the absent start-power registers.
- **`entities/register-31211.md`**, **`entities/device-sh-rs.md`**: P067 in the table and in the
  confirmed list.
- **`entities/register-13074.md`**: the second echoed word, and what it does to the P071 lead.
- **`entities/device-sbr-battery.md`** gains "a second pack has units of its own".
- **`queries/does-a-winet-s-advertise-over-mdns.md`** gains the WiNet-S2's record and the label.
- **`device-diagnosis/devices-wanted.md`**: item 8 drops P067.

## [2026-11-18] changed | the midnight check names every counter that fell; consumed energy holds at zero

[#797](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/797) reports
what [#708](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/708)
reported before it: `daily_consumed_energy` spikes deeply negative at midnight. The YAML
package's share of the cause -- a template recomputing on each of its five inputs separately --
is already gone, since the integration computes a derived value from one coherent poll. What was
left open is the device's share: an inverter that zeroes its eight daily counters across several
polls would still give one poll some of today and some of yesterday.

**That is now measured rather than assumed.** `daily counters reset at midnight` names every
counter that fell in the one poll, with before and after, and every counter still standing, and
it says so whether it passes or fails -- a passing judgement may now leave a *note*, which is
reported behind the verdict either way (`EventCheck.notes`,
`src/sungrow_modbus/capability_test/plausibility.py`). At
[mkaiser](entities/installation-mkaiser.md)'s the row is red on a clock, not on the inverter, and
the nightly failure sentence carries the measurement all the same. The two nights observed there
named only `daily_pv_generation`, so **nothing is established yet**: one more night says it.

**`daily_consumed_energy` and `total_consumed_energy` are held at zero as a floor** regardless
(`_consumed`, `src/sungrow_modbus/hybrid_inverter/derived.py`). A house cannot consume a negative
amount, and at the only moment the sum goes negative the true value is a few minutes of
consumption, so zero is the better answer and not merely the floor. It is the one place the
integration's arithmetic departs from the YAML package's on purpose; the entity ids, units and
state classes are untouched, so history is unaffected. `inverter_self_consumption` stays signed,
for the reason its docstring gives: it is an instantaneous balance whose mean clamping would
bias.

What changed:

- **`concepts/capability-test.md`** gains "a check can measure while it judges", and what is
  still unmeasured.
- **`doc/capability_tests.md`**: what the midnight check records beyond its verdict.
- **`doc/integration_migration.md`**: consumed energy never reads below zero.
- Tests: a staggered midnight in `tests/test_plausibility.py`, and `tests/test_derived.py`
  reading a half-done reset as 0 rather than -18 kWh.

## [2026-11-19] ingested | Maximo101's SH10RS, read again: a tracker granted a string it has not got

[Maximo101](wiki/entities/installation-maximo101.md) posted four downloads of their
[SH10RS](wiki/entities/device-sh-rs.md) entry to #786, two on 0.1.0a43 and two on 0.1.0a44, plus
two of the AC22E-01 entry. The 0.1.0a44 inverter download is committed as
`device-diagnosis/results/inverter/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2.json`
([the reading](wiki/sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2-summary.md));
the other three say nothing about the hardware that it does not.

**The first `plausibility` block from a contributor's machine**, and it runs two minutes, so only
the two tracker checks answered -- and `mppt4 carries a string` answered **wrong**. That input
reads 39.5 V to 53.6 V with 0.0 A in all five downloads of this machine, at 3.8 kW of PV and at
10.5 kW alike, while the other three trackers account for `total_dc_power` to within 1 %.
`TrackerCheck` grants a tracker on a voltage above 50 V alone, and an unloaded input drifts past
that. Open: whether the check should require the tracker's current.

**The implausible lifetime total is a broken high word, on every P067 machine read.**
`total_battery_charge` is 13041 and 13042; at Maximo101's the low word counts properly -- it rose
by the 38.0 kWh the battery took in two days -- while 13042 reads `0xFFFF`, the specification's
*unavailable*, composed into the total as data. [bigz2012](wiki/entities/installation-bigz2012.md)
and [brendan](wiki/entities/installation-brendan.md), the other two
[P067](wiki/entities/firmware-sunstone-h-b000-v002-p067.md) machines, read 14,844.2 and 6,374.1
kWh against discharge totals of 20,874.6 and 12,708.0, which no battery can do. Restoring the
wraps their high words have lost puts the three at 21,397.8, 12,927.7 and 17,226.5 kWh, each just
above its own discharge, and exactly one whole number of wraps does that for each. Every other
lifetime total on the three is exact. Nothing downstream rejects the figure as it stands: it is a
`total_increasing` sensor at 429 million kWh that then rises plausibly.

**The AC22E-01 is still unread, and now the reason is known.** Its 0.1.0a44 download carries
`"diagnosis": null` where the 0.1.0a43 one had no such key: the report asks for the document now,
and a wallbox entry's download serves the *last run's*, which is held in memory and does not
survive the restart an upgrade brings. What it needs is *Diagnosis: start* on the wallbox's own
device page, then the download in the same session.

**And the inverter's EV charger block is a default, not a report of a wallbox.** Holding 33541
reads 161 (*PV surplus*) at 16.0 A here, and the same at
[mkaiser](wiki/entities/installation-mkaiser.md)'s,
[swo14](wiki/entities/installation-swo14.md)'s and
[peter-sm](wiki/entities/installation-peter-sm.md)'s, none of which has a wallbox.
`Capability.EV_CHARGER` grants itself on a named code alone, so it is granted where there is
nothing to charge; what that costs, and when, is Todo item 18.

What changed:

- **`wiki/entities/installation-maximo101.md`**, **`device-sh-rs.md`** and
  **`firmware-sunstone-h-b000-v002-p067.md`**: the second reading, the three strings on four
  trackers, the moving lifetime total.
- **`wiki/concepts/capability-test.md`** and **`doc/capability_tests.md`**: what a *matched*
  tracker verdict does and does not say.
- **`wiki/entities/device-wallbox.md`**: nothing on the inverter tells a managed wallbox from a
  standalone one either.

## [2026-11-19] changed | a wallbox entry's download reads the wallbox, and the EV controls ask for one

**The download no longer depends on a run having happened.** A wallbox entry's diagnostics report
served the document the last run left, which is held in memory, so a restart emptied it and an
upgrade is a restart. It now reads the wallbox and builds the document, as an inverter entry's
download does, with the kept capability test and readings' checks behind it -- both outlive a
restart, because the ledger and the plausibility store are loaded at setup
(`WallboxDiagnosisRunner.async_read_document`, `custom_components/sungrow_modbus/diagnostics.py`).
A run in flight is left alone: it is writing and watching a car, and the document it has already
left says the same things.

**And the inverter's wallbox controls ask for a wallbox.** `Capability.EV_CHARGER` is granted by
holding 33541 reading a named mode, which is the block's factory state on houses with no wallbox
([the wallbox](wiki/entities/device-wallbox.md)), so the four controls now require one answering
on the inverter's bus as well (`SungrowRuntimeData.has_wallbox`). Nothing changes for a house with
a wallbox; what it prevents is the next firmware joining `CONFIRMED_ON_FIRMWARE` and handing
somebody four controls for a wallbox they have not got.

What changed:

- `custom_components/sungrow_modbus/diagnostics.py`, `wallbox_diagnosis.py`, `coordinator.py`,
  and `Capability.EV_CHARGER`'s own words in
  `src/sungrow_modbus/hybrid_inverter/capabilities.py`.
- Tests: a download with no run before it, a download during a run, and an inverter with the
  capability but no wallbox.

## [2026-11-19] changed | a broken high word is refused by its size, and found by what it contains

**T019.** `total_battery_charge` published 429,494,295.3 kWh at
[Maximo101](wiki/entities/installation-maximo101.md)'s and reached the recorder, because a
high word of `0xFFFF` over a sound low word is a number and not a sentinel. Two defences
now, and the corpus says neither does the other's half
([a million kWh is not a reading](wiki/concepts/a-million-kwh-is-not-a-reading.md)):

- **A ceiling of a million kWh on every energy counter wider than one word** -- all 74 of
  them, across the six device maps -- as a property of the field, so that the sensors, the
  diagnosis's readings and the plausibility checks refuse the same reading
  (`src/sungrow_modbus/model.py`). The largest honest counter in the corpus is 79,459.6 kWh.
- **`lifetime battery counters contain each other`**, judged on one poll, which is what
  catches the two machines whose high word is only a wrap short and whose readings are
  otherwise perfectly plausible. Margin 10 % over a floor of 100 kWh, measured against the
  four machines that cross the line honestly by up to 4.17 %.

Maximo101's reading **passes** the containment -- 429 million is larger than everything it
is compared with -- so the division is exact: the ceiling takes the absurd reading, the
containment takes the plausible one.

What changed:

- `src/sungrow_modbus/model.py` (`CeilingField`, `energy_counter`), the six
  `*/registers.py` maps, and `src/sungrow_modbus/capability_test/plausibility.py`.
- `doc/integration_migration.md` says that a statistic already recorded is the owner's to
  delete, and how (**Developer tools -> Statistics**); the integration deletes nobody's data.
- Tests: `tests/test_energy_ceiling.py` (every multi-word energy counter, and every
  committed document against the ceiling) and the corpus section of
  `tests/test_plausibility.py`.
- [SUNSTONE-H_B000.V002.P067](wiki/entities/firmware-sunstone-h-b000-v002-p067.md) says how
  the integration answers it.

## [2026-11-19] changed | the midnight check judges on the inverter's clock, and a corrected check forgets

**T016.** The readings checks' first failure on hardware was a clock, not an inverter
([mkaiser](wiki/entities/installation-mkaiser.md)'s, two nights running): a daily counter
resets on the **inverter's** midnight, and the check judged the fall by Home Assistant's
local time, so an hour of timezone difference recorded a clean reset at the inverter's 00:04
as `daily_pv_generation fell from 4.4 to 0 at 23:04`.

- **Judged on the inverter's clock**, read from the six `system_clock_*` fields the `clock`
  component already polls (holding 5000-5005). Where the inverter's clock did not read,
  Home Assistant's is used and the sentence says so.
- **Both readings, not an offset.** Where the two clocks differ by two minutes or more the
  sentence prints each one -- `reset at 00:04 by the inverter's clock, where Home Assistant
  read 23:04` -- because the inverter's clock is polled every 600 s and an offset computed
  from a stale reading would understate it. A difference is not a fault: nothing requires a
  Home Assistant to keep its inverter's timezone.
- **Readings checks now carry revisions**, which answers a question the plan left open.
  `CHECK_REVISIONS` in `plausibility.py` -- not `coverage.py`'s, which is the write paths'
  and which a readings row never passes through. A stored state whose revision has moved is
  dropped for **that check alone**, so a corrected check forgets what it judged by the rule
  it no longer runs while its neighbours keep days of evidence. Checked against the real
  store read that night: the failure goes, `lifetime counters never fall` keeps its 926
  passes. Nothing has to be pressed afterwards; ordinary polling fills the row again.

A `SCHEMA` bump would have thrown away every check's evidence at every house to correct one,
and is still there for when the shape itself changes.

What changed:

- `src/sungrow_modbus/capability_test/plausibility.py`, and `doc/capability_tests.md`, whose
  table also gains the containment check added with T019.
- Tests: the hardware failure replayed as a pass, a fall at noon still a finding, clocks that
  agree not both printed, an unread and an impossible clock, and the revision drop against
  the state read off hardware.
- [The capability test](wiki/concepts/capability-test.md) and
  [mkaiser](wiki/entities/installation-mkaiser.md) say what is true now; the two source pages
  keep what was measured then.

## [2026-11-19] ingested | all seven scenes on hardware, and a scene is not atomic

**T009 and T013.** The scenes of `doc/scenes.md` beyond the one press, at
[mkaiser](wiki/entities/installation-mkaiser.md)'s SH10RT on P020, 12:35-13:11 CET
([the run](wiki/sources/mkaiser-scenes-2026-11-19-summary.md)). The pack was **empty**, so a
forced charge made the battery scenes testable: 0.0 % to 8.7 % in 14 minutes at -4502 W.

- **Both forced scenes move what they are told**, to within two watts, and both need the
  `number..._power` line the 2026-11-17 fix added. The discharge scene **overwrote** the power
  the charge left, so the line writes rather than filling a blank.
- **Bypass holds the battery at 0 W** and sends the PV it was absorbing to the grid: -814 W out
  of the battery's column and 1057 W into the grid's in the same poll, against an unmoved load.
- **Both export scenes work**, and *Max Export Power* is half a thing without its automation --
  which was not installed here. The document now names the automation at the scene that needs it.
- **A scene is not atomic.** Three of seven presses did nothing first time and worked on a
  retry; one named the cause: `Could not write ...: Connection lost before response was
  received`. Both registers of that scene were written singly between the failures and both took.
  This inverter carries the production Home Assistant and the development instance at once and
  logged 34 lost connections in the hour ([contention](wiki/concepts/contention.md)). A scene
  abandons the rest of its writes when one raises, so it fails more readily than a single write.

Every setting was restored to the snapshot and verified by read-back, and a detached restore was
armed before the first write -- it logs in afresh each time, because an access token lasts thirty
minutes, which is how a watch once left 13017 on for fifty minutes past its window.

What changed:

- `doc/scenes.md`: the retry lesson where a reader meets it, the automation named at each scene
  that needs one, and why the automations read the maximum rather than storing it -- the ceiling
  moves with the pack (7148 W empty, 7420 W at 25 %, 7318 W a minute later), which was T009's
  one remaining need.
- [mkaiser](wiki/entities/installation-mkaiser.md) says what the house showed.

## [2026-11-19] answered | a tracker needs current, and who drives a wallbox

Two open questions settled in the code rather than by a new reading, and the pages they were
open on now state the rule.

- **A tracker carries a string only if current comes with the voltage.**
  [Maximo101](wiki/entities/installation-maximo101.md)'s floating `mppt4` drifts to 53.6 V at
  0.0 A and was called *matched*; the check now wants at least one count of current beside the
  voltage, keeps the voltage rule where a model reports no tracker current, and both tracker
  checks carry revision 2 so every house drops what the old rule gathered
  ([the capability test](wiki/concepts/capability-test.md),
  [SH-RS](wiki/entities/device-sh-rs.md)).
- **Who drives a wallbox is inferred from 21203, shown, and never acted on.** Moving twice
  during a charge says managed, 30 charging polls without a move suggest standalone, an idle
  wallbox says nothing; writing its own registers waits for the owner's answer in the entry's
  options ([the wallbox](wiki/entities/device-wallbox.md)).

Beside them, from the same session: the managed wallbox's user current is now bounded by the
rating the wallbox reports at input 21263 rather than a flat 32 A, and
[the restore](wiki/concepts/capability-test-restore.md) carries the rule a watch broke on
2026-11-17 -- a restore that depends on a credential which can expire is not a restore.

## [2026-11-20] ingested | the daily counters reset in one step

`.wiki/raw/mkaiser-midnight-reset-answered-2026-11-20.md`, the third night of auto
repeat at mkaiser's SH10RT on P020 and the first on the corrected midnight check.
**Eight daily counters fell to zero in the same one-minute poll**, none left
standing, at 00:09 by the inverter's clock against 23:09 by Home Assistant's: this
inverter resets them in one step, which is what T017 asked. The check passes where
three nights had failed on a clock, and the row cleared itself when its revision
rose rather than needing the ledger wiped. `lifetime battery counters contain each
other` settled in the same stretch, 175 passes, the first time anywhere. A second
night of auto repeat in low-SoC Standby started zero runs, as designed
([eight in one poll](wiki/sources/mkaiser-midnight-reset-answered-2026-11-20-summary.md),
[the capability test](wiki/concepts/capability-test.md),
[SH-RT](wiki/entities/device-sh-rt.md), [mkaiser](wiki/entities/installation-mkaiser.md)).

## [2026-11-20] ingested | gerd-wallbox-2026-11-20

An afternoon at gerd's over a tunnel from the devcontainer, a car charging
([the source](sources/gerd-wallbox-2026-11-20-summary.md), raw `raw/gerd-wallbox-2026-11-20.md`). Mode 162
mapped (scheduled charging: target and departure words, minimum or full power, ends at its target); a stopped
car restarted by charging on; a charging off reads back on for about 10 s; the mode select's writes ended no
session with one client per path. `entities/device-wallbox.md` and the query
`queries/why-does-a-managed-wallbox-stop-charging.md` updated.

## [2026-11-20] ingested | gerd-wallbox-2026-11-20-user-window

The evening at gerd's ([the source](sources/gerd-wallbox-2026-11-20-user-window-summary.md), raw
`raw/gerd-wallbox-2026-11-20-user-window.md`): 33546-33549 mapped as the user-defined mode's daily window, its end
ending a session; an hour of the block through the WiNet-S with none lost. `entities/device-wallbox.md` and the
query `queries/why-does-a-managed-wallbox-stop-charging.md` updated.

## [2026-11-20] ingested | gerd-wallbox-2026-11-20-test4

The last hour at gerd's ([the source](sources/gerd-wallbox-2026-11-20-test4-summary.md), raw
`raw/gerd-wallbox-2026-11-20-test4.md`): the window's start switches charging on; the window takes a write only in
mode 163 as one four-word write; the block put back as found. Test 4 did not run (the car unplugged).
`entities/device-wallbox.md` updated.

## [2026-11-20] updated | legacy-id-adoption

#798: a re-added entry's entity ids come back from the registry's deleted entities ahead of the claim's
`suggested_object_id`; the claim now renames onto a free legacy id. Area-prefixed device-scoped ids still
switch to legacy ids. [Adopting the legacy entity ids](concepts/legacy-id-adoption.md).

## [2026-11-20] ingested | sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-2

icefest's third reading, over RS485 through a Waveshare converter, a diagnostics download posted on #786
([the source](sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-2-summary.md)).
The PV cut (811 W, 0 W, 576 W) and the site import limit (1040 W, 528 W at 520 W, 1029 W) watched on
`SUNSTONE-H_B000.V001.P066`; the forced-charging window refused again. `installation-icefest.md`,
`firmware-sunstone-h-b000-v001-p066.md`, `register-31211.md`, `register-32998.md` and `device-sh-rs.md`
updated; P066 added to both controls' `CONFIRMED_ON_FIRMWARE`.

## [2026-11-20] ingested | gerd-wallbox-capability-test-2026-11-13

The wallbox capability test's first writing run at gerd's
([the source](sources/gerd-wallbox-capability-test-2026-11-13-summary.md)), frozen in `raw/` since that
day and now given its page: a disable ended the session and writing the enable back did not undo it; no
write of 21203 changed the car's draw, the inverter managing the wallbox. Linked from
`installation-gerd.md` and `device-wallbox.md`; nothing on them changes, the later sessions already carry
what it settled.

## [2026-11-20] ingested | gerd-wallbox-2026-11-20-pairing

The evening at gerd's with no car ([the source](sources/gerd-wallbox-2026-11-20-pairing-summary.md)), read
only: the pairing of a TLS wallbox entry with the inverter entry on the cable works on hardware, and an
inverter entry through the WiNet-S gives the wallbox up to its own entry and takes it back when that is
deleted (T059's step 2). `installation-gerd.md` and `device-wallbox.md` updated.

## [2026-11-21] ingested | gerd-ha-migration-2026-11-21

The integration's first setup on a production Home Assistant that had run the YAML package, behind a
modbus proxy on both paths ([the source](sources/gerd-ha-migration-2026-11-21-summary.md)): 150 legacy ids
adopted from placeholders; a gap of more than ten days in the old statistics restarted every lifetime sum at
0, so the Energy dashboard showed a huge negative hour, repaired with `recorder/adjust_sum_statistics`. The
proxy add-on ignores its top-level upstream once `devices:` is set; a pending discovery card aborts a manual
add as `already_in_progress`. `legacy-id-adoption.md` updated.

## [2026-11-21] ingested | mkaiser-production-install-2026-11-21

The integration (0.1.0a46) on the maintainer's production Home Assistant beside the still-running YAML
package, both through one modbus-proxy add-on, neither losing reads
([the source](sources/mkaiser-production-install-2026-11-21-summary.md)). Extended test: 21/54 passed,
every readback matched. The site import limit held with PV below the load (engine) and, by hand under
passing clouds, with PV above it; the engine's fixed 1250 W charge cannot take the PV-above-load case.
Through the proxy the entry read 6100 while its *Connection* stayed unknown. `register-32998.md`,
`installation-mkaiser.md` and `does-a-modbus-proxy-carry-6100.md` updated.

## [2026-11-21] ingested | mkaiser-production-sweep-2026-11-20

The setup search from the maintainer's production Home Assistant, with the modbus-proxy running and the
YAML package polling through it, found the inverter's own LAN port and the proxy as one inverter
([the source](sources/mkaiser-production-sweep-2026-11-20-summary.md)), with the sweep code unchanged
since the a40 that missed it. `why-did-the-search-miss-mkaisers-inverter.md` answered (does not
reproduce), `installation-mkaiser.md` updated. The dialog's summary came in the system language beside
an English step.

## [2026-11-21] ingested | gerd-auto-repeat-2026-11-21

A day of the diagnosis in extended auto repeat on gerd's own Home Assistant, ten runs on P022
([the source](sources/gerd-auto-repeat-2026-11-21-summary.md)): 37/55 passed, none failed. 13052's hard
limit is the inverter's rated power (8000 W), so the house's 10000 W could not be restored (exit 5); set to
8000 W by hand. P022 enforces the SoC limits' upper bounds and not the five power limits', as P023. Forced
discharge, the export limit, the charging start threshold and the charge ceiling confirmed; run 4's
discharge-window verdict was a procedure error (charging read as a discharge). New page
`register-13052.md`; `installation-gerd.md`, `firmware-sapphire-h-b001-v000-p022.md` and
`capability-test.md` updated.

## [2026-11-21] ingested | gerd-t076-2026-11-21

The day's three capability-test fixes installed on gerd's Home Assistant over a new SSH add-on, as a
local build of 0.1.0a46 with them ([the source](sources/gerd-t076-2026-11-21-summary.md)). With the
restart permission off and the test history cleared, one run: exit 0, the discharge window confirmed
(533.5 W, 0 W, 468 W) and the discharging start threshold confirmed, overturning the morning's
"not supported". `installation-gerd.md` and `firmware-sapphire-h-b001-v000-p022.md` updated.

## [2026-11-21] ingested | pvsonnenfreund-sbr096-cell-registers-788

An owner's raw-socket reads of the SBR cell block on an SBR096 of three modules, BCU `.01.30`, behind an
SH10RT-V112 on P023 ([the source](sources/pvsonnenfreund-sbr096-cell-registers-788-summary.md)): the
per-module cell extremes hold in 12 of 12 reads, the module serials carry data on this BCU, and two
mismatched frames past the cell block (protocol addresses 10750 for 41 words, and 10791 alone). New page
`installation-pvsonnenfreund.md`; `device-sbr-battery.md` and `padded-frames.md` updated.

## [2026-11-21] retired | legacy_entity_map.json

The YAML package's entity record moved from `doc/legacy_entity_map.json` into
`scripts/generate/tables/legacy_entities.py`, row for row, and the tests that
held the Python to the YAML were removed. The source page and its index entry
went with the file; `legacy-id-adoption.md`, `legacy-slot.md`,
`device-sbr-battery.md` and `register-13074.md` now cite the table, the
readings or the register map instead of the removed tests.

## [2026-11-21] updated | capability-test check revisions

`capability-test.md` says what voids a kept run: firmware, transport, a
simulated run, age, or a raised `CHECK_REVISIONS` entry, never an update by
itself; and that 0.1.0a48 raised three checks after the signed stop fix.

## [2026-11-21] ingested | mkaiser-self-consumption-standby

The inverter self-consumption estimate over 2.5 h of Standby at the maintainer's SH10RT
([the source](sources/mkaiser-self-consumption-standby-2026-11-21-summary.md)): median 0.6 W, range
-181 to 174 W, since in Standby it is import minus load and the inverter counts its own draw as load.

## [2026-11-21] ingested | mkaiser-mppt-energy-day

One day of *MPPTn energy* against *Daily PV generation* at the maintainer's SH10RT over the cable
([the source](sources/mkaiser-mppt-energy-day-2026-11-21-summary.md)): 22.93 against 23.3 kWh, a ratio
of 0.984; hourly ratios 0.88-1.04 because 13002 steps on a slow tier. Whether 13002 is DC or AC is open.

## [2026-11-22] ingested | fwitten-import-limit-engine

The capability test's `--import-limit` check at fwitten's master SH10RT-V112 on P023, over the cable
after dark ([the source](sources/fwitten-import-limit-engine-2026-11-22-summary.md)): a 1090 W cap
under a 1250 W forced charge left import at 1718 W, the first failure of register 32998 on P023 and
a contradiction of peter-sm on the same model and firmware. `register-32998.md`, the forced-charge
query, `installation-fwitten.md` and the P023 page say so; both failures on record are cluster masters.

## [2026-11-22] ingested | gerd-forced-startup-and-restart

A watched night window at gerd's SH8.0RT-V112 on P022, over the cable
([the source](sources/gerd-forced-startup-and-restart-2026-11-22-summary.md)): register 13017 is a
switch on P022 as on P020 and P023 (left standby 163 s, Running 208 s, back 17 s after 0x55), and a
restart needs one start command: the night boot waits ~4.5 min in Standby before Starting, Running at
369 s, the same as with the engine's four re-sends. `register-13017.md`, `register-13000.md`,
`installation-gerd.md` and the P022 page say so; the code grants the switch on P022 and stops
re-sending into Standby.

## [2026-11-22] ingested | sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-4

gerd's fourth cable reading, downloaded from his own Home Assistant
([the source](sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-4-summary.md)): the kept capability run of 2026-11-21 evening and the
plausibility checks over 1706 polls; every established check matches, export-side checks still wait.

## [2026-11-22] updated | auto repeat runs the forced startup; a stuck daily counter is named

`capability-test.md` and `register-13017.md`: auto repeat runs the forced startup mode by itself
in low-SoC standby until a kept run has established it, with no option of its own. A new readings
check, *daily counters keep up with the totals*, names a daily counter that stands still while its
lifetime counter rises 1 kWh -- what #797 reports, and what the pair checks cannot see, since their
trails start only when the daily counter steps (`doc/capability_tests.md`).

## [2026-11-22] ingested | sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-21

peter_sm's twenty-third reading, posted by Korsberg to #786
([the source](sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-21-summary.md)).
Its run of 2026-11-18 after dark ended in **outcome 5**, the one code that means a house may be
left changed, and on reading it is a false alarm: every setting read back, no poll was refused,
and the restart's "the link dropped" is an inverter that stayed in Standby with its pack at 1.0 %,
under the 5 % minimum, as it would have without the test. The plausibility section's running
states (154 Running to 57 Standby over the following three days) show it ran again.
`installation-peter-sm.md`, `register-13000.md`, `capability-test.md` and the 33213 query (now
thirteen of thirteen, with the eleventh and twelfth it was missing) say so.

## [2026-11-23] updated | device-wallbox

How a plugged-in car is told: the control pilot's three bands, from the readings at gerd, behind the
new binary sensor *Car connected*. The pilot while the wallbox is disabled is unmeasured and asked for
in `devices-wanted.md`.

## [2026-11-23] changed | register-13017

Its switch is *Low-SoC standby* now, on where the inverter may sleep (`0x55`, the factory 0) and off where
it stays awake (`0xAA`): the measurements show a state, not a wake. A new entity; the old one is removed.
Unmeasured: `0xAA` written while the inverter still runs, before the battery is low.

## [2026-11-23] changed | capability-test

Auto repeat's fixed 30-minute slots became a wait by what the last run settled, and the minimum SoC and
backup reserve readbacks wait for a battery above 15 %. At mkaiser's on 2026-11-22 seventeen runs were due
for those two alone, at 0 to 3.7 %, where they have no safe probe value, and none settled a check.

## [2026-11-23] ingested | sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan-2

GalKar's second reading (#786), a capability test while exporting in daylight
([the source](sources/sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan-2-summary.md)). Word 125 to 13074 held export at 106.5 W, so **P071 stores the word as
handed**, by one watched limit; `register-13074.md`, which called P071 undetermined, the P071 and SH-T pages and
`installation-galkar.md` say so, with what is not exact (no readback, 13088 at 0.5 %). Outcome 5 on 33208, a
busy dongle's refusal of the value held.

## [2026-11-23] ingested | sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-6

The maintainer's completed auto-repeat collection, 56 of 56 over 26 runs ([the source](sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-6-summary.md)).
New on P020: 13059 refuses 51 %, the export limit holds, the forced discharge acts. `installation-mkaiser.md`
and the P020 page say so.

## [2026-11-24] ingested | gerd-wallbox-2026-11-24

A morning at gerd's from his own Home Assistant ([the source](sources/gerd-wallbox-2026-11-24-summary.md)): the managed test passed there, grid
purchase chooses the phases in PV surplus and no block word does, Plug&Play decides a plug-in. The wallbox and phases
pages and both queries say so.

## [2026-11-24] updated | mkaiser-import-limit-pv-2026-11-07

The run's second half already had PV above the load with a bracket after the cap (PV ~1.05-1.1 kW, load ~0.6 kW).
`register-32998.md` and the summary say so; T001 is closed on it.

## [2026-11-24] ingested | four readings of swo14's cluster

Host and slave, without and with the car charging (#786): [host](sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3-summary.md), [host, car](sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4-summary.md),
[slave](sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-summary.md), [slave, car](sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-2-summary.md). The slave's second run ended in
**outcome 5** and nothing is left changed; a query opened on a slave mirroring the master's EMS mode. 13022 is signed on
01011.95.03, which overturns "never signed". Two cluster masters now miss the export limit under a manufactured
discharge. The earlier host page's "communication module: none fitted" is corrected: both inverters have a WiNet-S.

## [2026-11-24] ingested | fwitten-import-limit-cluster-2026-11-24

32998 at fwitten's cluster, over the cable, on the master, the slave and both, under 1250 W and 3601 W
forced charges ([the source](sources/fwitten-import-limit-cluster-2026-11-24-summary.md)): four caps, each read back, none held. The register, installation, P023 and SH-RT
pages and the forced-charge query say so; a slave's 32998 is no longer unmeasured.

## [2026-11-24] ingested | fwitten-cluster-mirror-2026-11-24

A cluster slave's 13050 follows the master's on P023, and 33500 tells a cluster member from a lone inverter
([the source](sources/fwitten-cluster-mirror-2026-11-24-summary.md)). The query is answered, `register-33500.md` is new.

## [2026-11-24] updated | register-13074: a skipped readback still asks the write scale

With the readback of 13074 skipped and feed-in limitation off, the capability test left the scale unasked and
divided by ten (T088, measured at swo14). It now lifts the mode for the probe, on the same leave as the readback;
the export check's revision is 2, so a kept verdict is asked again.

## [2026-11-24] ingested | cluster-mode-33500-reads-2026-11-24

33500-33502 at three houses, cable and WiNet-S ([the source](sources/cluster-mode-33500-reads-2026-11-24-summary.md)). The register dumps compared for T090: backup mode
(13075, and 33000 with it) fits the import limit's failures as well as a cluster does; `register-32998.md` and the query say so.

## [2026-11-24] ingested | mkaiser-import-limit-backup-mode-2026-11-24

Backup mode, the other thing both failing clusters share, does not stop the import limit at mkaiser's lone SH10RT
([the source](sources/mkaiser-import-limit-backup-mode-2026-11-24-summary.md)): it held with 13075 on as off. `register-32998.md` and the query say so.

## [2026-11-24] changed | register-32998

A cluster member (33500 = 0xAA) is no longer offered the number; the page says so.

## [2026-11-24] ingested | cluster-mode-33500-two-words-2026-11-24

33500-33502 in one request, cable and WiNet-S ([the source](sources/cluster-mode-33500-two-words-2026-11-24-summary.md)); `register-33500.md` says so.

## [2026-11-24] changed | is-battery-power-firmware-dependent

The fallback reads 13022 as two's complement on 01011.95.03; the page says so.

## [2026-11-24] ingested | cluster-mode-33500-bar12-2026-11-24

bar12's 33500 ([the source](sources/cluster-mode-33500-bar12-2026-11-24-summary.md)); `register-33500.md` has a third lone inverter.

## [2026-11-24] changed | capability-test-restore

A second capability test in a cluster is refused; the page says so.

## [2026-11-24] ingested | github-ulfben-cluster-2026-11-24

ulfben's plant, the third import-limit failure, is a cluster by the owner's posts ([the source](sources/github-ulfben-cluster-2026-11-24-summary.md)); the register page and the query say so.
