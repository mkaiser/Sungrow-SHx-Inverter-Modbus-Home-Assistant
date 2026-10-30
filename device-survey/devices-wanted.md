# Devices wanted

**Hand-written, unlike [compatibility.md](../doc/compatibility.md)**, which
is generated and says what has been measured. This list says **which
measurements are still missing, and what each one would settle**. Sungrow
publishes no release notes and its register specification is wrong in both
directions, so what a device can do is measured, not read.

**How to send one:** run the survey and attach the document it writes to the
survey issue on GitHub.

```bash
device-survey/scripts/survey.sh    # Windows: device-survey\scripts\survey.cmd
```

It reads, takes 5–40 minutes, and writes two files: one to send, and one to
keep because it holds the real serial and address. Its last question offers
the control test, which writes; the default is no. See
[Contributing one](README.md#contributing-one).

## Most wanted

In the order it would help. Each line names what one survey settles;
details are under [Why each one](#why-each-one).

| # | Device or situation | What one survey settles |
| --- | --- | --- |
| 1 | **Any single-phase inverter** (RS, K or MG family) | Nothing single-phase has ever been read; 18 of the 42 models are. Every capability the RS family is given today is an inference |
| 2 | **An iHomeManager** (unit 247, port 502, 503 or 504) | The first reading of the device at all. Its Modbus TCP must be opened in the app first, see [item 3](#3-an-ihomemanager--port-502-503-or-504-unit-247) |
| 3 | **An SH-T (SH15T, SH20T…) on its own LAN port**, with the control test, in daylight | Every T so far was read through a WiNet-S. Settles the export limit's write scale (register 13074) on P071, the PV cut on P071, and an SBH pack on a direct link |
| 4 | **A Sungrow Logger1000, 3000 or 4000** | The first reading. Answer *a Logger* to the transport question so the survey also reads the Logger itself |
| 5 | **A wallbox other than the one already read**, an AC011E-01 above all | Which of its registers identify a unit and which are a model constant, and a scale another source reads differently |
| 6 | **A charging car**, at any house with a Sungrow wallbox | What input 21313 does over a session, and whether 21308/21310 are signed. Two runs a few minutes apart while charging |
| 7 | **Version 1 between `.95.03` and `.95.12`, or a `.95.14` that is not 10 kW** | Where the export limit's write scale changes ([#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)) |
| 8 | **An SBR other than SBR096, SBR128 or SBR160** | Battery sizes nobody has read, and the module-position encoding beyond three modules |
| 9 | **A second master/slave cluster** | Whether a slave's address 2 is a rule or one house's convention |
| 10 | **Any inverter behind a Modbus proxy** | What a proxy does to the readings; no document has one |
| — | **A WiNet-S certificate hash**, five seconds, no survey | Whether every WiNet-S shares one TLS certificate, see [item 3b](#3b-a-winet-s-certificate-hash-from-anywhere) |

## Not needed any more

Already read several times over. Please send one of these **only** if it
differs from what is in [`inverter/`](inverter/) in one of the ways below:

- an **SH10RT, SH10RT-20 or SH10RT-V112 on P023**, on either path (five
  houses);
- an **SH8.0RT-V112 on P022** or an **SH6.0RT-V112 on P023**;
- an **SBR096** behind any of those.

It is still worth sending when it brings **a firmware update** since your
last survey (that is how a silent change is noticed), **the first control
test** for its model and firmware, **both paths** of one machine minutes
apart, or a **battery size** nobody has read.

## Where the coverage is today

26 documents from 10 houses: 11 inverters, 12 of them with a control test,
and one wallbox read at its own address.

| Axis | Covered | Missing |
| --- | --- | --- |
| Inverter model | **7 of 42**: SH10RT, SH10RT-20, SH6.0RT-V112, SH8.0RT-V112, SH10RT-V112, SH15T, SH20T | every model outside RT and T |
| Product family | RT and T | RS, MG, RL, K, CX |
| Phase / output type | three phase 3P4L only | **single phase**, and three phase 3P3L |
| Inverter firmware | `B001.V000.P020`, `P022`, `P023`, `B000.V000.P071` | a fifth |
| Version 1 | `SAPPHIRE-H_01011.95.03`, `.95.12`, `.95.13`, `.95.14`, `PEARL-H_01011.01.45` | see item 7 above |
| Communication module | WiNet-S `P040`, `P043`, `P044`, `P045`; WiNet-S2 `P032`, `P033` | a Logger |
| Battery | SBR096, SBR128, SBR160, SBH200, SBH400, one Pylontech | the other SBR and SBH sizes, other third-party packs |
| Transport | direct LAN, WiNet-S and WiNet-S2, wired and WiFi | a Logger, a Modbus proxy, **a T on its own LAN port** |
| Wallbox | AC22E-01 | AC011E-01, AC007-00 |
| iHomeManager | none | any |
| Sungrow Logger | none | any |

## Why each one

### 1. Any single-phase inverter — RS, K or MG family

**Nothing single-phase has ever been measured**, and 18 of the 42 models are.
This is the biggest gap by number of users behind it.

It would settle what the capability model currently *derives* rather than
knows: `compatibility.md` marks the whole RS family as missing
`three_phase`, `mppt3`, `meter_channel_2`, `firmware_versions` and
`battery_start_power`, and every one of those is an inference from the family
rather than a reading. An RS or K survey either confirms the lot or
finds the first exception.

Worth having even if the integration then reports fewer entities than the
YAML package did on the same machine — that difference *is* the finding.

### 2. A machine between Version 1 `.95.03` and `.95.12`, or a `.95.14` that is not 10 kW

Specifically, and for a reason: issue
[#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)
reports that after a firmware update, writing the **export power limit**
(register 13074) behaves as though the value were a percentage in units of
0.1% rather than watts — write 700, get 7000 W. The reporter is on Version 1
`01011.95.14`. On gerd's `.95.13` the register reads **8000 on an 8 kW
machine** and matches its own maximum at 5622, so it is plainly watts there.

**There is a `.95.14` machine here, and it changes how the issue reads.**
bar12's SH10RT-20 updated itself to `.95.14` (inverter `B001.V000.P023`)
between two surveys. On `.95.14`, 13074 still *reads* in watts: 10000 against
a maximum of 10000 at 5622. It still *writes* in tens of watts, as it did on
`.95.12`. So "write 700, get 7000 W" is the write asymmetry described in
the wiki's `.wiki/wiki/entities/register-13074.md`. The reference
house has it on `.95.12` and gerd on `.95.13`, so `.95.14` is not where it
starts. And the issue's two
explanations are already told apart on a machine that is not 10 kW: gerd's
8 kW inverter held word 60 as **600 W**, where "0.1 % of rated power" would
have given 480. The unit is 10 W.

What is left is *where* it starts. The one machine that stores the word 1:1 is
fwitten's pair on **`.95.03`**, the oldest Version 1 measured. Every
machine on `.95.12` or later multiplies. That fits "after a firmware update",
but it is one cluster against three houses, and a cluster is also the obvious
other difference. A hypothesis, not a finding.

Two things would settle it, and neither needs a write that changes
anything:

- **A machine between `.95.03` and `.95.12`, with its 13074 write scale
  asked**, which is what would place the change. A reading cannot: the read
  side is watts on every firmware seen. `survey.sh control <host>
  --export-scale` asks with one write that changes nothing on either
  firmware, and the integration asks the same on its first export-limit
  write.
- **A `.95.14` machine that is not 10 kW.** The two explanations in that
  thread — "the register is 0.1% of rated power" and "the register is in
  units of 10 W" — predict *identical* numbers on a 10 kW inverter, where
  100.0% and 10000 W coincide, and every reporter so far appears to have
  one. On an 8 kW machine they diverge: writing 700 would mean 5600 W under
  the percentage reading and 7000 W under the other.

Beyond that, a new value on any firmware field in the table above is still
worth having. Not ARM or DSP, for the reason above.

A reading from a machine of an already-recorded model is worth as much as a
new model here — more, in fact, because the model is then held constant and
the firmware is the only thing that moved. That is the comparison that says
whether a capability belongs to the hardware or to the version.

### 3. An iHomeManager — port **502, 503 or 504**, unit **247**

A device with a documented register map and **no measurement
whatsoever**. A sweep of one house's whole /24 on port 503 found nothing at
all.

**There is a lead.** The contributor of the SH20T in
[#772](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/772)
wrote in the survey's own comment field that *"iHomeManager and AC22E-01 is
installed too"*. Their document does not measure either, and could not: it is
a Home Assistant diagnostics download, so it describes the **one endpoint**
the integration is configured against and nothing else on the network. An
iHomeManager is a separate endpoint and is not reachable through an inverter.

So what is wanted from that house specifically is a `sungrow_survey.py` run
that reaches both the iHomeManager and the inverter's **own LAN port**. The
first is item 3; the second settles the 5741-5746 question below, which a
WiNet-S cannot, since every WiNet-S refuses those registers anyway. Their
AC22E-01 is a second wallbox, which item 6 asks for.

**Not port 503 alone.** Sungrow's V1.0.2 document gives it 502, 503 and
504, and **each port takes one TCP connection**: a port another client holds
looks closed. Four sweeps have found nothing on 503; that is weaker evidence
than it looks, because none of them would have recognised one sitting on
502. The survey sweeps 502 and 503; pass `--port 504` with the address for
the third.

It also changes what the *inverter* answers, which makes it two findings in
one: issues [#647](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/647)
and [#651](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/651)
report registers 5741-5746 going silent when one is installed. Nobody has
confirmed that against a machine.

**Its Modbus TCP is off until you open it**, in the iSolarCloud app:
*iHomeManager settings → Forwarding channel settings*, open port 502, 503 or
504 (Sungrow's *iHomeManager Modbus Transfer User Guide*, 2025). Leave the
optional SSL off: the survey speaks plain Modbus TCP to it.

If you have one, the survey finds it and reads it: every register Sungrow
documents, then the gaps between them, into a document of its own. The
iHomeManager documents **no serial number**, so any text the survey finds in
a gap is treated as one: masked, and published only as a stand-in. Send the
document; the transcript stays with you.

**Port 516 is not an iHomeManager's.** Reported in [discussion
#571](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/571)
as one, it is open at a house with **no iHomeManager at all**, on **both
WiNet-S dongles and neither inverter's own LAN port** — and on a wallbox with
a network connection of its own.

It is real Modbus over real TLS: TLS 1.2, a Sungrow-signed certificate
(`CN=sun`, issuer `CN=OT.SUNGROW`), and real registers through the tunnel.
On a dongle it is **not a way round the forwarding limits** — 2612 and 2628
refuse with exception 0x02 over TLS exactly as on 502. The survey sweeps it,
reads a wallbox there, and reports a dongle's without reading it, because a
user told their dongle has nothing on 516 would be told something false.

So an iHomeManager is still **entirely unmeasured**. The survey reads it from
Sungrow's V1.0.2 document (`sungrow_modbus.ihomemanager`), compared with an
MIT template in
[cross_reference_modbus_manager.md](../doc/cross_reference_modbus_manager.md);
what is missing is a device to check it against.

### 3b. A WiNet-S certificate hash, from anywhere

Five seconds, no scan, and it settles a question this project cannot answer
from one house. A WiNet-S serves Modbus over TLS on **port 516**, and so does
a wallbox at its own address, and the certificate looks like one baked into
the firmware rather than generated per unit: subject `CN=sun`, issuer
`CN=OT.SUNGROW`, valid 2024-10-24 to 2054-10-17 — byte-identical between the
dongle and the wallbox at one house.

If it *is* one certificate for every device then its private key ships with
every one, and the TLS there encrypts the link while proving nothing about
what is on the other end. The integration already treats it that way.

What is missing is a hash from another site:

```bash
python - <<'EOF'
import hashlib, socket, ssl
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
raw = socket.create_connection(("YOUR.DONGLE.IP", 516), 8)
with ctx.wrap_socket(raw, server_hostname="x") as tls:
    print(hashlib.sha256(tls.getpeercert(True)).hexdigest())
EOF
```

It reads nothing off the inverter and identifies nobody — a certificate hash
is the same number for every device that shares one, which is the whole
question.

### 4. A Sungrow Logger1000 / 3000 / 4000

Also at unit 247, also documented — *Logger Communication Protocol AW0
1.0.2.9* — and also entirely unmeasured. It fronts a whole installation,
which is the shape the one-config-entry-per-endpoint model was designed for,
so a survey would test that design rather than only add a device.

The survey reads one: it names the model by its type code (0x0705
Logger3000, 0x0710 Logger1000, 0x0718 Logger4000), decodes the identity
block and publishes the rest of the 8000 block raw, with any text masked.
A Logger gives the inverters behind it unit ids of their own on its
endpoint, so the survey stops at the first inverter; **answer "a
Logger1000/3000" to the transport question** and it then reads the Logger at
unit 247 too. Say on the tracker which unit ids your Logger lists.

### 5. An SBH pack **on a direct connection**, or any SBR that is not 9.6 kWh

Two things at once.

The **SBH** half is now half-answered, by the SH20T of
[#772](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/772),
whose SBH400-V11 is the first SBH this project has ever read. What it
settles: an SBH **does** answer on the SBR's addresses, at unit 2 behind a
WiNet-S2, and the values decode with the SBR's scales — 588.3 V, 100 %, 98 %
health and 18.0 °C, each agreeing with what the inverter separately reports
about the same pack. That is the assumption named above, checked at last.

What it does **not** settle is everything that needs a direct connection. A
WiNet-S forwards only 10740-10751 and refuses the per-module arrays from
10765, so the module and cell layout — the part that would need the SBH's
protocol document — is still unread. An SBH on an inverter's own LAN port is
what would finish this.

**A second SBH, read the same way.** jm493's SH15T, with an
SBH200 behind a *wired* WiNet-S2. It agrees on everything above: the pack
answers at unit 2 with the SBR's scales (299.6 V, 97 % health, 12.5 °C
against the inverter's 12.0 °C, −15.1 A while the inverter reports 3758 W into
the battery), and the cell and module blocks are refused. One thing does
**not** agree: the pack says **85.5 %** and the inverter 80.0 %. bar12's SBR
disagrees too, by less and the other way (pack 65-66 %, inverter 67-68 %), so
the two are separate measurements rather than one value copied.
The pack's current also settles a sign: it follows the inverter's
`battery_power`, positive while discharging. Same BCU firmware as the SBH400,
`SBHBCU-S_22011.04.11`. It also reads **over** its rating, as the SBH400
did: 20.27 kWh on a 20.0 kWh pack, +1.35 %, inside the 2 % window, so it is
named. Two of two SBHs reading high is now a pattern, not one reading. Still
behind a dongle, so the cell layout is still unread.

Packs read **over** their rating as well as under it — that SBH400 reports
**40.55 kWh** against its 40.0 — which is why `model_for_capacity` matches
within a fraction of the rating either way, rather than assuming a pack only
reads a little under as it degrades. Declined a name, a full pack falls
through to what its BMS reports — 0 A — and would be offered the 5000 W
fallback for a pack its datasheet rates at 23760 W.

Any **SBR other than an SBR096** would close a question left open on purpose.
The pack's four position registers pack a module and a cell into one word,
`(module << 8) | cell`, proved on a three-module pack where every high byte is
1, 2 or 3. An SBR128 has four modules and should show a high byte of **4**.
Until one does, the encoding is proved for one pack size.

### 6. A wallbox that is not an AC22E-01

Sungrow publishes **no register document** for these; everything in
[wallbox_registers.md](../doc/wallbox_registers.md) is what four independent
sources agree on, and one register, 21313, is nameable by nobody. The library
knows two other device type codes — `0x20DA` for the AC011E-01 and `0x20ED`
for the AC007-00 — from other projects rather than from a reading.

An **AC011E-01** in particular would settle a live disagreement. A fourth
source measuring an AC22E-01 gives the output current setting a scale of
0.01 A where this project reads 0.1 A, and the reading here wins on physical
grounds — 0.01 puts the setting below the device's own 6 A floor. But that
argument is about *this* model, and the other source's map is largely
AC011E-based, so 0.01 may be right there and the register may simply differ
between models.

The survey picks one up by itself: behind a WiNet-S it answers at unit 3 on
the dongle's endpoint, and at its own address the sweep finds it on port 516
and writes a wallbox document of its own.

### 7. A second inverter in a master/slave cluster

Measured once, at one house, and it produced two rules the config flow now
depends on: a cluster slave's own device address is **2**, and a slave answers
0 for the battery registers where a standalone inverter answers 0xFFFF.

Both come from a single site. A second cluster would confirm them — or find
that the address is a convention rather than a rule, which would matter,
because discovery now probes for it.

### 8. Any inverter behind a Modbus proxy

`modbus-proxy`, evcc's proxy, a Home Assistant add-on. The survey asks
whether one is in the path and records the answer as testimony, because it
changes what a measurement means: a proxy holds one connection and lends it
out, so blocks that never drop describe the proxy rather than the inverter,
and it rebuilds every frame — which can hide or create the padded-frame quirk
at 2612 and 2628.

No document has one, so what a proxy does to these readings is unknown.

## What a survey is worth even when nothing is new

Two readings of the same model on the same firmware are still worth having,
in two cases that have both already paid for themselves:

- **Both transports on one machine**, taken minutes apart. Four such pairs
  exist and every one produced a rule: which measuring points a WiNet-S
  forwards, which unit ids move with the transport, and that a dongle answers
  0 where the inverter answers 0xFFFF. Nothing but a controlled pair
  establishes any of it.
- **The same machine twice, months apart.** Firmware updates arrive silently.
  A second reading of a machine already in this directory is how a change in
  what it answers would ever be noticed.

## What is deliberately not wanted

- **Readings from an installation whose owner has not agreed.** A stand-in
  serial is not consent. The documents here are published, and each names its
  reporter.
- **A document taken while something else was polling.** Contention is not a
  register fault, and the two are hard to tell apart from the result — a
  regular poller does not even look intermittent, and testimony saying
  nothing else was polling can be wrong.
- **A reading whose `bands_not_reached` is non-empty, used as evidence about
  coverage.** The dump has a time budget, and a slow link exhausts it: one
  document reached 816 addresses where a faster path on the *same house*
  reached all 1510. That is the budget, not the transport.
