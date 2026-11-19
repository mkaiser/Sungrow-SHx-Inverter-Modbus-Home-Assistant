# T026 - An SH-T through its WiNet-S, in daylight, with export

**An SH-T through its WiNet-S, in daylight, with export** (any SH15T
owner; ra1k_0 says the SH20T has no LAN port of its own, #772, and
Sungrow's SH5T-SH25T manual lists a WiNet-S2 Ethernet connection and a
COM2 terminal, no LAN terminal: the manual's contents page, read through a
search; its text was not fetched). So the T has **no cable path** to ask
for, and what a dongle run can settle is its behavioural leg only. One run
with the capability test (`--enable-export-limit`) settles:
- **13074 on P071.** The dongle reported a word written with feed-in
 limitation off as handed, where B001 ignores it. Readbacks through a
 dongle are stale, so only the export check (the house must export) can
 say whether P071 stores 1:1; if it does, the integration's
 unanswered-probe fallback of ten sets a tenth of the asked export limit
 on an SH-T.
- **An SBH on a direct link** cannot be had without a cable.
 `Capability.SUNGROW_BATTERY` is granted for an SBR found on its own unit
 (`with_sungrow_battery`); an SBH is not until its own-unit reading is
 seen without a dongle. Parked until a T is found with a direct path.
- **Whether an iHomeManager silences 5741-5746** (#647, #651), which
 every WiNet-S refuses anyway; ra1k_0 has one.
Still open on the T besides: whether 13018 acts as 31211 does, and
33149-33150 (battery start power): the capability table marks them absent,
but BiergitKraft's SH10T on `PEARL-H_B001.V001.P038` answered them through
a WiNet-S2 in every round (#792), as GalKar's did once. That SH10T is a
second candidate for the run above. Its first capability test was refused
in Standby after dark, so it needs daylight with the inverter Running.
