# The wallbox registers, and how each one was established

Sungrow publishes no register document for its AC wallboxes. What follows was
read off one — an **AC22E-01**, through the WiNet-S of an SH8.0RT-V112 at
unit 3 (on 2026-09-08 while a car charged, on 2026-10-13 with none
connected) and at its own LAN address over TLS at unit 248 (2026-10-14) —
and then compared against every other source that could be found: two community projects that measured their own, a discussion
on this repo covering the same model, and a GPL-licensed project read for
what exists rather than copied. Every row says how strongly it is held and by
whom, and [where they disagree](#where-the-sources-disagree-and-what-settles-it)
says which won and why.

The measurement is worth more than a table usually would be, because it caught
a **charging session ending**: two full dumps 157 s apart, then 21 samples over
ten minutes during which the car finished. A register that resets, one that
keeps climbing and one that freezes are three different things, and only a
session boundary tells them apart.

## The sources

| Source | Device | Licence | Notes |
| --- | --- | --- | --- |
| **Here** | AC22E-01, one firmware: two readings via a WiNet-S, a session ending (single phase) and idle with no car (three phase); one at its own address over TLS, idle | MIT, this repo | Published as a dongle section in an inverter document and as a wallbox document in `device-survey/results/wallbox/`, serial masked. `probe.py dump --save` writes unmasked raw readings beside the script, which stay local |
| [Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant](https://github.com/Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant) | Not stated | **No licence file** — used with the author's permission, and only for *which register means what* | Its charging-status enum is the single most useful thing any of the three has |
| [KevinD987/sungrow-ac011e](https://github.com/KevinD987/sungrow-ac011e) | AC011E-01, by measurement | **MIT** | Carries its own confidence marks — VERIFIED, LIKELY, UNVERIFIED — and says plainly that the allocation is not manufacturer-confirmed and may move between firmwares |
| [Discussion #571](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/571) on this repo | AC22E-01 | this repo's own tracker | The **same model measured here**, which none of the other sources is. Gives names in the manufacturer's own idiom — `SetOutI`, `PhaseSwitch`, `Availability`, `RemoteControl`, `State` — and one scale that this project's reading contradicts, below |
| [Eisbaeeer/sungrow](https://github.com/Eisbaeeer/sungrow) | AC011E-01 | **No licence file**, and no permission asked -- so a lead to measure, never a definition | The only source that names input 21267 (protocol 21266), below |
| [Jam3s97/sungrow_ihomemanager](https://github.com/Jam3s97/sungrow_ihomemanager) | iHomeManager, tested with AC22E-01 | **GPL-3.0** | Read for *what exists*, never copied. GPL-3.0 is incompatible with this repo's MIT, so no definition here comes from it — what it contributed is the name of an **official Sungrow document**, `iHM.Communication.Protocol`, which is the licence-clean route to the same registers |

Descriptions here are written from this project's own readings. Where a source
named something this project had not identified, that is marked, and the
wording is still ours.

## How to read the confidence column

| Mark | Means |
| --- | --- |
| **three sources** | Measured here and named the same way by both projects. As solid as this gets without a manufacturer document |
| **two sources** | Measured here and named by one of them |
| **measured here** | Established from how it behaved across the session; neither project names it |
| **named elsewhere** | One or both projects name it, and the value read here is consistent but does not by itself prove it |
| **open** | Nobody, including this measurement, can name it |

Addresses are protocol addresses, one below the register number, as everywhere
in this project. **The tables below give register numbers**, and so does the
prose unless it says "protocol". Everything is at the unit the wallbox
answered on — 3 through a WiNet-S, 248 at its own address — never at unit 1.

## Two ways in

| Path | Protocol | Unit | In the integration |
| --- | --- | --- | --- |
| through the WiNet-S, at the dongle's address | plain Modbus TCP, port 502 | 3 | found behind the inverter's entry by itself |
| at the wallbox's own LAN address | Modbus TCP inside TLS, port 516 | 248 | when the entry's `wallbox_host` option names it |

Same wallbox both ways: firmware string, lifetime energy and the live block
agree word for word. Over TLS only unit 248 answers (0-255 swept); the
wallbox has no port 502 and no web interface. Its certificate is
Sungrow-signed (issuer `OT.SUNGROW`, CN `sun`) and byte-identical to the
WiNet-S's at the same house, so it authenticates nothing and is not
verified (`ModbusTlsParams(verify=False, check_hostname=False)`).

**Not through the inverter's own LAN port.** No unit from 0 to 255 answers
the model name there, while unit 1 answers its device type on the same link:
the inverter goes silent on the wallbox's addresses rather than refusing
them. RS485 at unit 248 (9600 8N1, per [evcc discussion
#20739](https://github.com/evcc-io/evcc/discussions/20739)) is reported, not
measured; `wallbox.UNITS` tries 248 behind a plain endpoint for it.

**Over TLS a read must start on a data point's first register**; any other
start times out, reproducibly on fresh connections (protocol 21295 x24
answers, 21296 and 21300 time out). Through a WiNet-S any start answers.
The valid starts, from one-register reads at every address (serial
skipped), in **protocol** addresses:

- input: 21210, 21212, 21214, 21215, 21223, 21224, 21225, 21240, 21243,
  21258, 21261-21272, 21274-21279, then every second address 21281-21299,
  21301-21307, 21309, 21311-21317, 21319, 21321, 21322, 21326, 21330,
  21331, 21336, 21337, 21339-21345, 21347, 21349-21355, 21357,
  21359-21365, 21369, 21373, 21374;
- holding: 21200, 21202-21204, 21206, 21208, 21210-21212, 21214-21216,
  21220, 21222-21233, 21249, 21281, 21297-21301, 21311-21317.

Every mapped field starts on one, so the list is also **the wallbox's own
field layout**, undecoded registers included. The integration polls in
reads that each begin on a field, so the same components serve both paths
(protocol addresses): identity input 21215 x20, ratings input 21261 x12,
live input 21299 x23, settings holding 21202 x10 and 21231 x1. The live read
runs on every fast poll; the other three every 30th, five minutes on the
default ten-second interval. Nothing writes to the wallbox.

**The direct path reads what the dongle zeroes.** Where both answer, the
dongle returns 0 for input registers 21211-21214 (a short code, masked like
the serial until a second wallbox shows whether it identifies the unit),
21241-21250 (a second version string, `V1.0...`), 21267, and 21332-21336
(0xFFFF directly). Input 21360 and 21363-21365 hold values directly and lie
beyond what the dongle bands read. The firmware string at 21226 reads whole
directly. Holding: the same 50 addresses either way below 21249, and
21250-21313 only directly.

Read again directly on 2026-10-29, a fortnight after the wallbox document
and with no car connected, which says what is fixed and what moves:

- **Fixed:** input 21241-21250 (`V1.01.1.000.0.0.000` and padding),
  21332-21336 (0xFFFF), 21360 (2), 21363 (60), 21364 (1); holding 21260-21281
  and 21286-21311 except as below; holding 21282-21285, ASCII `20240115`, a
  date; holding 21298 (1) and 21299 (60), the same pair as input 21364 and
  21363, so most likely a setting and its echo; holding 21313 (220).
- **Holding 21250-21259: twenty ASCII digits, constant.** Shaped like an
  identifier -- a charge point or card number -- so `WALLBOX_MASKED` masks it
  as it does the serial, and the committed wallbox document carries it masked.
- **Moves:** input 21267 counts up, about one every 8 to 10 s across three
  reads four minutes apart, yet read 1754 on 2026-10-15 and 21154 now, so it
  wraps or restarts. Eisbaeeer/sungrow names it "holding register changed";
  KevinD987 lists its meaning as open. **It counts neither writes nor
  reads** (2026-10-29, one TLS session, no other client on the wallbox): +12
  across two quiet minutes with one read every 20 s, +1 across twenty reads
  in under two seconds, and no step at a write of holding 21203 to the value
  it held. It ticks on its own at about one per 10 s -- 21690 tens of
  seconds is 60 hours, which would make it an uptime counter wrapping after
  7.6 days, and fits the low value of 2026-10-15. Not yet confirmed by a
  restart.
- **A holding read straight after a write, in the same TLS session,
  answered with input 21267's value** instead of holding 21203's; on fresh
  connections 21203 read 0, as in the wallbox document. One observation, so
  a reader should open a new connection after a write before trusting a
  readback. Input 21365 is signed and wanders, -66 then -59 to -61:
  the shape of a signal strength in dBm, not confirmed. Holding 21312 went
  from 0 to 2.
- **Input 21314, the start mode, read 3**, outside the 0-2 the table names.

Checked against every other project this document cites, evcc's driver and
Eisbaeeer/sungrow on 2026-10-29: none names input 21211-21214, 21360-21365,
holding 21250-21259, 21282-21285, 21298/21299 or 21312, nor a start mode 3.

Still undecoded: whether 21267 is uptime, 21365, the setting at holding 21298/21299
and its echo, holding 21312, and what start mode 3 means.

## Input registers

| Register | Type | Scale | Meaning | Read here | Confidence |
| --- | --- | --- | --- | --- | --- |
| 21201-21206 | ASCII | — | Serial number. **Never published**; masked out of every survey | 11 characters | three sources |
| 21216-21220 | ASCII | — | Model string, spelled out | `AC22E-01` | two sources |
| 21224 | u16 | — | Device type code: `0x3F80` AC22E-01, `0x20DA` AC011E-01, `0x20ED` AC007-00 | `0x3F80` | two sources |
| 21225 | u16 | — | Phase count in use. **Follows the phase mode**, not the wiring: 1 in single-phase mode, 3 in three-phase mode, on the same three-phase installation | 1 / 3 | two sources |
| 21226-21235 | ASCII | — | Firmware version string. Whole only when read in one request starting at 21226; a read that starts inside it gets zeros for the rest | `LE-01.1E1.001.901.25` | measured here |
| 21262 | u16 | 1 V | Nominal voltage | 230 | three sources |
| 21263 | u16 | 0.1 A | Rated current — 32.0 A, which is what a 22 kW three-phase unit draws. The AC011E project reads this address as a work mode and marks it UNVERIFIED; an enum would not be 320, so either the models differ or that mark is optimistic. It held 320 across a change of both phase mode and start mode, which a work mode would not | 320 | measured here |
| 21268 | u16 | — | Remote control status | 1 | named elsewhere |
| 21270 | u16 | — | Actual phase mode: 0 three phase, 1 single phase. The holding setpoint agrees | 1 | three sources |
| 21272 | u16 | 1 W | Minimum charging power: 6 A at 230 V on each phase in use, so it follows the phase mode | 1380 / 4140 | named elsewhere |
| 21273 | u16 | 1 W | Nominal (maximum) charging power. 22080 names the model as surely as the type code does | 22080 | two sources |
| 21300/21301 | u32, **low word first** | 1 Wh | Lifetime energy. **32-bit, not 16** — see below | 280.157 → 280.305 kWh | measured here |
| 21302, 21304, 21306 | u16 | 0.1 V | Charging voltage, phases A/B/C. **0 when not charging** | 2279, 0, 0 | three sources |
| 21303, 21305, 21307 | u16 | 0.1 A | Charging current, phases A/B/C | 88-146, 0, 0 | three sources |
| 21308/21309 | u32, low word first | 1 W | Charging power | 1995-3324 W | three sources |
| 21310/21311 | u32, low word first | 1 Wh | **This session's** energy. Reset to 15 when a new session began, which is what separates it from 21300 | 15 → 124 Wh | three sources |
| 21312 | u16 | 0.01 V | **Control-pilot voltage.** 5.97 V charging, 9.03 V connected and not, 11.91 V with no vehicle — the levels IEC 61851 defines for states C, B and A, drifting as an analogue reading should | 597 / 903-893 / 1191 | two sources |
| 21313 | u16 | — | **Open.** 131-256 while charging, 0 when not, and 0 with no vehicle; roughly a thirteenth of the power but not consistently. Neither project documents it | 192-256 | open |
| 21314 | u16 | — | Start mode: 0 stopped, 1 start with EMS, 2 start by swiping | 1 | two sources |
| 21315 | u16 | — | Power request | 1 | named elsewhere |
| 21316 | u16 | — | Power control allowed | 1 | named elsewhere |
| 21317 | u16 | — | **Charging status.** Codes below | 1 / 3 / 4 / 6 | three sources |
| 21318/21319 | u32, low word first | epoch | Charging **start** time. See the note on the clock. 0 with no vehicle connected, as is 21320 | 17:25:24 | named elsewhere |
| 21320/21321 | u32, low word first | epoch | Charging **end** time; it advances while charging and freezes when the session ends | 17:28:28 | named elsewhere |
| 21322 | u16 | 0.1 A | Tracks the output current setting in holding 21203 — 160 against 160 — but read 161 once while the setting stayed at 160, so "available current" fits better than "the setting, echoed" | 160-161 | measured here |

## Holding registers

Every one is a **setting**. This project reads them; the survey writes nothing,
and no file in `device-survey/` implements a Modbus write function.

| Register | Type | Scale | Meaning | Read here | Confidence |
| --- | --- | --- | --- | --- | --- |
| 21203 | u16 | 0.1 A | Output current setting. The AC011E project gives its range as 60-160, i.e. 6-16 A — that is an 11 kW unit's range, and a 22 kW unit should go to 320 | 160 → 16.0 A | two sources |
| 21204 | u16 | — | Phase mode setpoint: 0 three phase, 1 single phase | 1 | three sources |
| 21211 | u16 | — | Availability / charger enable: 0 disabled, 1 enabled | 1 | two sources |
| 21212 | u16 | — | Start/stop: 0 start, 1 stop | 0 / 1 | two sources |
| 21225-21230 | u16 × 6 | — | **The wallbox's clock**, local time: year (two digits), month, day, hour, minute, second. Read 26, 10, 13, 21, 12, 23 at 21:12 local on 2026-10-13, and 26, 9, 8, 17, 57, 44 during the run of 2026-09-08 | 26-10-13 21:12:23 | measured here |
| 21231 | u16 | — | Configured unit id, read-only | 248 | named elsewhere |
| 21232 | u16 | 0.1 km/kWh | Mileage per kWh, for the app's range estimate | 50 → 5.0 | named elsewhere |
| 21233 | u16 | — | Configured minimum current | 6 | named elsewhere |
| 21263 | u16 | — | Working mode: 0 network, 2 plug and play, 6 EMS, says one project. **No answer through the dongle**; 0 inside a block read at its own address, where no read may start on it | no answer / 0 | named elsewhere |

## The charging status codes

Nine codes, from the wallbox project; the four measured here are marked.

| Code | Meaning | Seen |
| --- | --- | --- |
| 1 | Idle | **yes**, with no vehicle connected |
| 2 | Standby | |
| 3 | Charging | **yes** |
| 4 | Suspended by the charge point | **yes**, briefly, between two sessions |
| 5 | Suspended by the vehicle | |
| 6 | Completed | **yes**, and it stayed there |
| 7 | Reserved | |
| 8 | Disabled | |
| 9 | Fault | |

This is where a cross-check earns its keep. Watching one session, `6` looks
like "idle" — it is what the register reads when nothing is happening. It is
*Completed*, and an integration showing it as idle would be wrong every time a
car finished charging and stayed plugged in.

## Three things this measurement settled

**The lifetime counter is 32-bit.** The two projects disagree: one reads
address 21299 as a word-swapped `uint32`, the other as a 16-bit value with the
next register "not part of the meter". Here register 21301 held `4` while
21300 read 18013, and `4 × 65536 + 18013` is 280,157 Wh — 280.157 kWh, which
is a plausible lifetime for this unit and moved by 148 Wh over ten minutes in
step with the power reading. For that to be coincidence, an unrelated register
would have to hold exactly the right high word. On an AC011E with under 65 kWh
lifetime the two readings are indistinguishable, which is presumably how the
disagreement arose.

**The control-pilot voltage was a guess here and is VERIFIED there.** Register
21312 read 597 while charging and 903 when connected and idle. Those are 5.97
and 9.03 volts, the levels IEC 61851 defines for states C and B, which made it
a hypothesis worth writing down — and the AC011E project, measured
independently on different hardware, names that address exactly. Two
measurements, one on each model, agreeing on a register neither manufacturer
documents.

**The end time is a timestamp, not energy.** Register 21320 climbed by 251
over ten minutes while the session counter climbed by 148, and "a second
energy counter" is a reasonable-looking wrong answer. Decoding it as a
word-swapped epoch gives the day's date and a plausible minute, and it
freezes the moment charging stops.

## The clock is local, not UTC

Both timestamps decode as a word-swapped 32-bit Unix epoch whose value is the
**wall clock where the wallbox is**, not UTC: the end time decoded to 17:28:28
at a moment when local time was 17:29 and UTC was 15:29. So decode as an
epoch, then read the result as local time — the same quirk the inverter's own
clock registers have.

The wallbox's own clock agrees: holding 21225-21230 spell out the date and
time field by field, and both readings showed local summer time (UTC+2), not
UTC. Nothing decodes them yet; they are in the dump.

## What answers at all

Measured across the whole span through the WiNet-S, so a reader knows where
to look and where not to:

- **input 21201-21280 and 21297-21340 answer; 21281-21296 refuse.**
- **holding 21201-21248 answers**, then only scattered addresses up to 21328.

`WALLBOX_BANDS` in `src/sungrow_modbus/dump.py` is those ranges, 206
addresses, with the firmware string in a band of its own so it is read
whole. `WALLBOX_TLS_BANDS` is the direct path's: twelve reads, each starting
on a valid start, 299 addresses. The survey dumps a wallbox whenever one
answers — independently of the inverter's own dump question, because the
dump is a fraction of the inverter's cost and a wallbox is the rarest thing
this project sees. `WALLBOX_MASKED` masks the serial (input 21201-21206) and
the short code at 21211-21214, and the document carries a hashed stand-in
for the serial, as it does for the inverter's.

## What a survey carries

Through a dongle, the `wallbox` section of the inverter's document. At its
own address, a **wallbox document** of its own (`"document": "wallbox"`, no
`device` section, `connection` naming TLS on 516), written by
`wallbox_direct.py` and published in `device-survey/results/wallbox/`. The
section is the same either way:

```json
"wallbox": {
  "unit": 3,
  "path": "dongle",
  "serial_anonymized_hashed": "anon-5155200572",
  "readings": {
    "charging_status": {"register": 21317, "value": 3, "means": "charging",
                        "held": "three sources"},
    "control_pilot_voltage": {"register": 21312, "value": 5.97, "unit": "V",
                              "held": "two sources"},
    "lifetime_energy": {"register": 21300, "value": 279949, "unit": "Wh",
                        "held": "measured here"},
    "unnamed_register_21313": {"register": 21313, "value": 261, "held": "open"}
  },
  "register_dump": {"input": {"21299": 17805, "…": 0}, "holding": {"…": 0}}
}
```

Thirty-two named readings, each carrying **the register it came from** and
**how many independent sources hold it** — so a reader of one survey does
not have to come and find this document to know how much to trust a line. The
words stay beside them, for anybody who disagrees with an interpretation here.

Two properties worth stating, because both are the sort of thing that is
easier to get right once than to notice later:

- The decode runs on the **masked** dump, not the raw one, so a reading can
  never come from a register the document is refusing to publish. The field
  table not listing the serial is then a second line of defence rather than
  the only one.
- A field with a word missing is **absent**, not zero. Publishing a failed
  read as `0` would make a claim about somebody's configuration out of
  nothing.
- `path` says which way the wallbox was reached, `dongle` or `tls`, because
  the two do not read alike. The terminal survey's dongle section omits it.

The model string is `AC22E-01`, not truncated: the survey decodes it from
the field table, never by eye. The type code `0x3F80`, the 22080 W maximum
and the 32.0 A rating all agree it is an AC22E-01, not an AC011E-01.

## Where the sources disagree, and what settles it

Discussion #571 names the **same model** measured here, and it disagrees in
two places. Searching for other people's work is worth repeating
periodically.

### Holding 21203, the output current setting: 0.1 A, not 0.01

Discussion #571 gives `SetOutI (21202)` a scale of **0.01 A**. This project
reads 0.1 A, and the reading settles it from inside one document:

| Register | Raw | At 0.1 | At 0.01 |
| --- | --- | --- | --- |
| holding 21203, output current setting | 151 | **15.1 A** | 1.51 A |
| input 21322, available current | 161 | **16.1 A** | 1.61 A |
| input 21263, rated current | 320 | **32.0 A** | 3.2 A |

The same wallbox reports a **minimum charging power of 1380 W**, and
1380 / 230 is exactly **6.0 A** — the lowest current a Type 2 charge point is
permitted to offer. A setting of 1.51 A is below the device's own floor, so
0.01 cannot be right. And 0.1 is corroborated twice over: the rated current
comes out at 32.0 A, which is the 32 A in `AC22E-01`'s 22 kW, and the maximum
charging power of 22080 W is 32 A across three phases at 230 V.

So the scale here stays 0.1, and the disagreement is recorded rather than
averaged. It may still be right for the AC011E-01, which is a different
model.

### Input 21308 and 21310: signed or unsigned?

Discussion #571 declares `ActivePower (21307)` and `ChargedEnergy (21309)` as
**signed** 32-bit. This project declares both unsigned, and **the reading
cannot tell**: they held 0 W and 105 Wh, which decode identically either way.

Left unsigned for now, with the reasoning stated rather than hidden. An
AC22E-01 does not discharge a vehicle, so a negative charging power has no
physical meaning on this model — but that is an argument from the datasheet
and not from a register, and a wallbox that does support V2G would break it.
What would settle it is a reading above 2^31, which needs 2.1 GW or 2.1 GWh
and will therefore never arrive, or a manufacturer document.

### What it confirms, which matters as much

Three things this project had held loosely are now held by a fourth source
that measured the same model:

- **The 1–9 charging status table**, end to end, idle through faulted. It was
  already the strongest thing in this file and is now the strongest thing by
  a wider margin.
- **The 0.1 scales on inputs 21302–21307**, the six phase voltages and
  currents.
- **Unit 248 for a direct connection**, measured here at the wallbox's own
  LAN address over TLS ([Two ways in](#two-ways-in)). [evcc discussion
  #20739](https://github.com/evcc-io/evcc/discussions/20739) describes the
  same unit as **Modbus RTU at 9600 8N1** over RS485, which is not measured
  here, and says the wallbox must be in **EMS mode**.

## What is still open

- Register **21313**: measured behaviour, and no name in any of the three
  sources. Only a charging session can say more, and the signedness of
  21308/21310 with it -- now readable both ways.
- Register 21263 *input* reads 320, where the AC011E project reads that
  address as a work mode. It held 320 while the phase mode and start mode both
  changed, so the work-mode reading looks wrong for this model; a manufacturer
  document would settle it.
- Input 21215 changed from 123 to 251 between the readings, and nothing names
  it.
- Holding 21316-21329, in the scattered region above 21248, reads the same
  words in both readings but **shifted by one address**. A record that moves
  is not a set of registers, and nothing here should be decoded from it.
- Holding **21250-21313 answers at the wallbox's own address**, where no
  read through the dongle reached it; nothing decodes it yet. The holding
  21316-21329 shift above may be the dongle's own block reads landing off a
  data point's start -- the direct path's map of starts is the place to
  check it.
- Input **21211-21214** holds a short code only the direct path answers.
  Whether it differs between units is unknown, so the dump masks it like the
  serial until a second wallbox is read.
- What only the direct path shows -- the second version string, 21267,
  21332-21336, 21360, 21363-21365 and the upper holding registers -- is
  undecoded.
- Everything here is one unit, one firmware, read through a dongle and at
  its own address. A second AC22E would settle most of the remaining marks.
