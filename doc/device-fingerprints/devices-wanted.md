# Devices wanted

**Hand-written, unlike [compatibility.md](../compatibility.md).** That file is
generated and answers *"what has been measured?"* — every model the library
knows, with a row saying tested or untested. This one answers the different
question: **which measurements are missing, and what would each one settle?**

The reason there is a wanted list at all is that Sungrow publishes no release
notes and the register specification has been proven unreliable in both
directions. It says register 13018 exists from V1.1.10; one measured house
answers it and another does not. It says nothing about inputs 2612 and 2628
refusing through a WiNet-S, which they do at every house measured so far. And
it does not mention that a dongle answers **0** where the inverter answers the
specification's "unavailable" — which invented ten entities at one house
before `ZERO_MEANS_ABSENT` caught it.

So capability is measured rather than read. One command does it:

```bash
python scripts/sungrow_scan/collect.py
```

It reads and never writes, takes 5–40 minutes depending on the link, and
produces two files: one to send, and one to keep because it holds the real
serial and address. See [Contributing one](README.md#contributing-one).

## Where the coverage is today

Nine documents, four houses, and the honest summary is that **one axis is
almost entirely unmeasured**:

| Axis | Covered | Missing |
| --- | --- | --- |
| Inverter model | **4 of 42** — SH10RT, SH10RT-20, SH10RT-V112, SH8.0RT-V112 | every model outside the RT family, and 12 of the 16 RTs |
| Phase / output type | three phase 3P4L only | **single phase**, and three phase 3P3L |
| ARM and DSP firmware | **one string each** on all nine — `ARM_SAPPHIRE-H_V11_V01_B`, `MDSP_…` | anything else at all |
| Inverter firmware | **two** — `B001.V000.P020` and `P022`; unknown at the third house, which refuses the block that reports it | a third |
| WiNet-S firmware | **two** — `P040` and `P043` | a third |
| SBR BCU firmware | **two** — `22011.01.27` and `.30` | a third |
| Transport | direct LAN, WiNet-S wired, WiNet-S WiFi | a Logger, a Modbus proxy in the path |
| Battery | **1 of 14** — SBR096 | every other SBR size, every SBH, third-party packs other than one Pylontech |
| Wallbox | 1 — AC22E-01 | AC011E-01, AC007-00 |
| iHomeManager | **none** | any |
| Sungrow Logger | **none** | any |

**The firmware rows, read correctly.** A first draft of this file said every
document reports the same firmware and that nothing here demonstrates the
variation fingerprinting exists for. That was wrong, and wrong in an
instructive way: it was written from `firmware.arm` alone, which is one of
**five** firmware fields a document carries. Three of the five do vary, and
the inverter's version is in every filename — `b001v000p020` beside
`b001v000p022` — where it had been sitting in plain sight.

So the variation is measured, and it has already paid for itself. The
2612/2628 refusal through a WiNet-S is what it looks like when a rule
survives a firmware change: it holds across **two dongle firmwares** and
**two inverter firmwares**, which is why it is written down as what a dongle
does rather than what one machine does. A finding that appeared on only one
firmware would deserve much less confidence, and there would be no way to
know without this.

What is genuinely thin is the *spread*: two versions per field, from three
houses, all within one model family. A third value on any of them is worth
having — and an ARM or DSP string that is not the one above would be the most
interesting of the lot, being the two fields nothing has ever varied.

One gap worth naming: **fwitten's inverter firmware is unknown**, not absent.
That house refuses input 13249, which is the block reporting it, so four of
the nine documents carry no inverter version at all and their filenames have
no firmware word. A reading of those registers from a machine in that family
would fill in a third of the table.

## Wanted, in the order it would help

### 1. Any single-phase inverter — RS, K or MG family

**Nothing single-phase has ever been measured**, and 18 of the 42 models are.
This is the biggest gap by number of users behind it.

It would settle what the capability model currently *derives* rather than
knows: `compatibility.md` marks the whole RS family as missing
`three_phase`, `mppt3`, `meter_channel_2`, `firmware_versions` and
`battery_start_power`, and every one of those is an inference from the family
rather than a reading. An RS or K fingerprint either confirms the lot or
finds the first exception.

Worth having even if the integration then reports fewer entities than the
YAML package did on the same machine — that difference *is* the finding.

### 2. A third value on any firmware field

Not "a second" — there are already two of the inverter's, two of the
WiNet-S's and two of the SBR BCU's. What is missing is a *third*, and above
all **any** ARM or DSP string other than `ARM_SAPPHIRE-H_V11_V01_B` and
`MDSP_SAPPHIRE-H_V11_V01_B`, which have never varied across nine documents
and four houses.

A reading from a machine of an already-recorded model is worth as much as a
new model here — more, in fact, because the model is then held constant and
the firmware is the only thing that moved. That is the comparison that says
whether a capability belongs to the hardware or to the version.

### 3. An iHomeManager — port **503**, unit **247**

The only one of these devices with an **official Sungrow register document**,
and the only one with **no measurement whatsoever**. A sweep of one house's
whole /24 on port 503 found nothing at all.

It also changes what the *inverter* answers, which makes it two findings in
one: issues [#647](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/647)
and [#651](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/651)
report registers 5741-5746 going silent when one is installed. Nobody has
confirmed that against a machine.

If you have one, the survey needs pointing at port 503:

```bash
python scripts/sungrow_scan/probe.py sweep 192.168.1.0/24 --port 503
```

**Port 516 turned out to be something else.** Reported in [discussion
#571](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/571)
as an iHomeManager port, so it was added to the sweep — and then measured on
2026-09-09 at a house with **no iHomeManager at all**, where it was open on
**both WiNet-S dongles and neither inverter's own LAN port**. It is a dongle
port.

It is real Modbus over real TLS: TLS 1.2, a Sungrow self-signed certificate
(`CN=sun`, issuer `CN=OT.SUNGROW`), and a read of input 4989 through the
tunnel returned the inverter's serial. It is also **not a way round the
dongle's forwarding limits** — 2612 and 2628 refuse with exception 0x02 over
TLS exactly as on 502. So it is not a lead for milestone 5 after all, and not
a workaround for anything; it is one more thing a WiNet-S does. The survey
sweeps it and says so, because a user told their dongle has nothing on 516
would be told something false.

So an iHomeManager is still **entirely unmeasured**, and 503 remains the
only port it is documented on.

An **official protocol document exists** and is named
`iHM.Communication.Protocol` — referenced by
[Jam3s97/sungrow_ihomemanager](https://github.com/Jam3s97/sungrow_ihomemanager),
which is **GPL-3.0** and therefore cannot be copied into this MIT repo. The
document itself is the licence-clean route to the same registers, and finding
a copy of it would unblock milestone 5 more than any single fingerprint.

### 3b. A WiNet-S certificate hash, from anywhere

Five seconds, no scan, and it settles a question this project cannot answer
from two houses. A WiNet-S serves Modbus over TLS on **port 516**, and its
certificate looks like one baked into the firmware rather than generated per
unit: subject `CN=sun`, issuer `CN=OT.SUNGROW`, valid 2024-10-24 to
2054-10-17 — the same to the second at two unrelated sites.

If it *is* one certificate for every dongle then its private key ships with
every dongle, and the TLS there encrypts the link while proving nothing about
what is on the other end. Worth knowing before anybody builds on it.

What is missing is a hash from a third site. The two compared so far are two
interfaces of one dongle, which is the same device:

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

Also on port 503, also documented — *Logger Communication Protocol AW0
1.0.2.9* — and also entirely unmeasured. It fronts a whole installation,
which is the shape the one-config-entry-per-endpoint model was designed for,
so a fingerprint would test that design rather than only add a device.

### 5. An SBH pack, or any SBR that is not 9.6 kWh

Two things at once.

The **SBH** needs its protocol document before it can be ported at all, and a
fingerprint would show what it answers on the SBR's addresses — the two are
assumed similar and that has never been checked.

Any **SBR other than an SBR096** would close a question left open on purpose.
The pack's four position registers pack a module and a cell into one word,
`(module << 8) | cell`, proved on a three-module pack where every high byte is
1, 2 or 3. An SBR128 has four modules and should show a high byte of **4**.
Until one does, the encoding is proved for one pack size.

### 6. A wallbox that is not an AC22E-01

Sungrow publishes **no register document** for these; everything in
[wallbox_registers.md](../wallbox_registers.md) is what four independent
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

A wallbox is found only through an endpoint that already answered, never by
sweeping for it, so the survey picks one up automatically when it is behind
an inverter you scan.

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

## What a fingerprint is worth even when nothing is new

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
  regular poller does not even look intermittent. Four documents were
  discarded for this, and their testimony said the opposite.
- **A reading whose `bands_not_reached` is non-empty, used as evidence about
  coverage.** The dump has a time budget, and a slow link exhausts it: one
  document reached 816 addresses where a faster path on the *same house*
  reached all 1510. That is the budget, not the transport.
