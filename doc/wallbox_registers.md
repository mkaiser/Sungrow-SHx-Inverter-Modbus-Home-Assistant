# The wallbox registers, and how each one was established

Sungrow publishes no register document for its AC wallboxes. What follows was
read off one — an **AC22E-01** on 2026-09-08, through the WiNet-S of an
SH8.0RT-V112 at unit 3 — and then compared against every other source that
could be found: two community projects that measured their own, a discussion
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
| **Here** | AC22E-01, one firmware, one session, via a WiNet-S | MIT, this repo | `.testdata/dumps/wallbox-charging-*` holds the raw readings; they carry the real serial and stay local |
| [Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant](https://github.com/Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant) | Not stated | **No licence file** — used with the author's permission, and only for *which register means what* | Its charging-status enum is the single most useful thing any of the three has |
| [KevinD987/sungrow-ac011e](https://github.com/KevinD987/sungrow-ac011e) | AC011E-01, by measurement | **MIT** | Carries its own confidence marks — VERIFIED, LIKELY, UNVERIFIED — and says plainly that the allocation is not manufacturer-confirmed and may move between firmwares |
| [Discussion #571](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/571) on this repo | AC22E-01 | this repo's own tracker | Found 2026-09-09. The **same model measured here**, which none of the other sources is. Gives names in the manufacturer's own idiom — `SetOutI`, `PhaseSwitch`, `Availability`, `RemoteControl`, `State` — and one scale that this project's reading contradicts, below |
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
in this project. **The tables below give register numbers.** Everything is at
the unit the wallbox answered on — 3 through a WiNet-S, 248 direct — never at
unit 1.

## Input registers

| Register | Type | Scale | Meaning | Read here | Confidence |
| --- | --- | --- | --- | --- | --- |
| 21201-21206 | ASCII | — | Serial number. **Never published**; masked out of every fingerprint | 11 characters | three sources |
| 21216-21220 | ASCII | — | Model string, spelled out | `AC22E-01` | two sources |
| 21224 | u16 | — | Device type code: `0x3F80` AC22E-01, `0x20DA` AC011E-01, `0x20ED` AC007-00 | `0x3F80` | two sources |
| 21225 | u16 | — | Phase count as wired | 1 | two sources |
| 21226-21235 | ASCII | — | A version string, and a fragment: the field is longer than the ten registers read | `LE-01.1E1.001.` | measured here |
| 21262 | u16 | 1 V | Nominal voltage | 230 | three sources |
| 21263 | u16 | 0.1 A | Rated current — 32.0 A, which is what a 22 kW three-phase unit draws. The AC011E project reads this address as a work mode and marks it UNVERIFIED; an enum would not be 320, so either the models differ or that mark is optimistic | 320 | measured here |
| 21268 | u16 | — | Remote control status | 1 | named elsewhere |
| 21270 | u16 | — | Actual phase mode: 0 three phase, 1 single phase. The holding setpoint agrees | 1 | three sources |
| 21272 | u16 | 1 W | Minimum charging power | 1380 | named elsewhere |
| 21273 | u16 | 1 W | Nominal (maximum) charging power. 22080 names the model as surely as the type code does | 22080 | two sources |
| 21300/21301 | u32, **low word first** | 1 Wh | Lifetime energy. **32-bit, not 16** — see below | 280.157 → 280.305 kWh | measured here |
| 21302, 21304, 21306 | u16 | 0.1 V | Charging voltage, phases A/B/C. **0 when not charging** | 2279, 0, 0 | three sources |
| 21303, 21305, 21307 | u16 | 0.1 A | Charging current, phases A/B/C | 88-146, 0, 0 | three sources |
| 21308/21309 | u32, low word first | 1 W | Charging power | 1995-3324 W | three sources |
| 21310/21311 | u32, low word first | 1 Wh | **This session's** energy. Reset to 15 when a new session began, which is what separates it from 21300 | 15 → 124 Wh | three sources |
| 21312 | u16 | 0.01 V | **Control-pilot voltage.** 5.97 V charging, 9.03 V connected and not — the two levels IEC 61851 defines for states C and B, drifting as an analogue reading should | 597 / 903-893 | two sources |
| 21313 | u16 | — | **Open.** 131-256 while charging, 0 when not; roughly a thirteenth of the power but not consistently. Neither project documents it | 192-256 | open |
| 21314 | u16 | — | Start mode: 0 stopped, 1 start with EMS, 2 start by swiping | 1 | two sources |
| 21315 | u16 | — | Power request | 1 | named elsewhere |
| 21316 | u16 | — | Power control allowed | 1 | named elsewhere |
| 21317 | u16 | — | **Charging status.** Codes below | 3 / 4 / 6 | three sources |
| 21318/21319 | u32, low word first | epoch | Charging **start** time. See the note on the clock | 17:25:24 | named elsewhere |
| 21320/21321 | u32, low word first | epoch | Charging **end** time; it advances while charging and freezes when the session ends | 17:28:28 | named elsewhere |
| 21322 | u16 | 0.1 A | Tracks the output current setting in holding 21203 — 160 against 160 — but read 161 once while the setting stayed at 160, so "available current" fits better than "the setting, echoed" | 160-161 | measured here |

## Holding registers

Every one is a **setting**. This project reads them; the survey writes nothing,
and no file in `scripts/sungrow_scan/` implements a Modbus write function.

| Register | Type | Scale | Meaning | Read here | Confidence |
| --- | --- | --- | --- | --- | --- |
| 21203 | u16 | 0.1 A | Output current setting. The AC011E project gives its range as 60-160, i.e. 6-16 A — that is an 11 kW unit's range, and a 22 kW unit should go to 320 | 160 → 16.0 A | two sources |
| 21204 | u16 | — | Phase mode setpoint: 0 three phase, 1 single phase | 1 | three sources |
| 21211 | u16 | — | Availability / charger enable: 0 disabled, 1 enabled | 1 | two sources |
| 21212 | u16 | — | Start/stop: 0 start, 1 stop | 0 | two sources |
| 21231 | u16 | — | Configured unit id, read-only | — | named elsewhere |
| 21232 | u16 | 0.1 km/kWh | Mileage per kWh, for the app's range estimate | 50 → 5.0 | named elsewhere |
| 21233 | u16 | — | Configured minimum current | — | named elsewhere |
| 21263 | u16 | — | Working mode: 0 network, 2 plug and play, 6 EMS. **Did not answer here**, though one project names it | no answer | named elsewhere |

## The charging status codes

Nine codes, from the wallbox project; the three this session visited are
marked.

| Code | Meaning | Seen |
| --- | --- | --- |
| 1 | Idle | |
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
energy counter" was a reasonable-looking wrong answer — it was in this
repository for an afternoon. Decoding it as a word-swapped epoch gives today's
date and a plausible minute, and it freezes the moment charging stops.

## The clock is local, not UTC

Both timestamps decode as a word-swapped 32-bit Unix epoch whose value is the
**wall clock where the wallbox is**, not UTC: the end time decoded to 17:28:28
at a moment when local time was 17:29 and UTC was 15:29. So decode as an
epoch, then read the result as local time — the same quirk the inverter's own
clock registers have.

## What answers at all

Measured across the whole span, so a reader knows where to look and where not
to:

- **input 21201-21280 and 21297-21340 answer; 21281-21296 refuse.**
- **holding 21201-21248 answers**, then only scattered addresses up to 21328.

`WALLBOX_DUMP_BANDS` in `scripts/sungrow_scan/probe.py` is those ranges, and
`scripts/sungrow_scan/collect.py` dumps them whenever a wallbox answers —
independently of the inverter's own dump question, because 206 addresses is a
tenth of that dump's cost and a wallbox is the rarest thing this project sees.
The serial is masked by `WALLBOX_DUMP_MASKED`, which exists because it was
once published.

## What a fingerprint now carries

Schema 14. The `wallbox` section of a document holds both halves:

```json
"wallbox": {
  "unit": 3,
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
**how many independent sources hold it** — so a reader of one fingerprint does
not have to come and find this document to know how much to trust a line. The
words stay beside them, for anybody who disagrees with an interpretation here.

Two properties worth stating, because both are the sort of thing that is
easier to get right once than to notice later:

- The decode runs on the **masked** dump, not the raw one, so a reading can
  never come from a register the document is refusing to publish. The field
  table not listing the serial is then a second line of defence rather than
  the only one.
- A register that did not answer is **absent**, not zero. Holding 21263 did
  not answer here, and publishing it as `0` would have said this wallbox is
  in "network" working mode — a claim about somebody's configuration, made up
  out of a failed read.

## Corrections to earlier claims in this repository

- **The model string is not truncated.** An earlier note here said register
  21216 reads `AC` and stops, and wondered whether the field was
  model-specific. It reads `AC22E-01`; the hand-decode behind that note had
  sliced the wrong window. The survey's own decode, which takes its offsets
  from one table, got it right the first time -- which is the argument for
  the table over decoding by eye.

- **21320/21321 is the charging end time, not a second energy counter.**
- **This wallbox is an AC22E-01, not an AC011E-01.** Register 21224 reads
  `0x3F80`, and the 22080 W maximum and 32.0 A rating agree. Anywhere this
  documentation said AC011E about gerd's site, it was wrong.

## Where the sources disagree, and what settles it

Found 2026-09-09 by searching for other people's work, which is worth doing
periodically: a fourth source turned up naming the **same model** measured
here, and it disagrees in two places.

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
- **Unit 248 for a direct connection**, which this project has never
  measured and had only from one source. [evcc discussion
  #20739](https://github.com/evcc-io/evcc/discussions/20739) adds that a
  direct link is **Modbus RTU at 9600 8N1** over RS485, not Ethernet, and
  that the wallbox must be switched to **EMS mode** — which is consistent
  with `start_mode` reading 1, *start with EMS*, on the unit measured here.

## What is still open

- Register **21313**: measured behaviour, and no name in any of the three
  sources.
- The version string at 21226-21235 is a fragment.
- Holding 21263 did not answer here.
- Register 21263 *input* reads 320, where the AC011E project reads that
  address as a work mode. One of the two is wrong about this model.
- Everything here is one unit, one firmware, one session, through a dongle. A
  second AC22E would settle most of the remaining marks.
