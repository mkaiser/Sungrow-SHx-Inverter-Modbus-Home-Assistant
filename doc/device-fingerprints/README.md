# Capability fingerprints

What a particular Sungrow installation actually answers, recorded by
`python scripts/sungrow_scan/collect.py` — the one entry point, which finds
the devices, asks what no register can answer, runs the block read test and
writes the document. `probe.py capabilities <host> --save doc/device-fingerprints`
is the single phase inside it, for when only that is wanted.

**[devices-wanted.md](devices-wanted.md) says which devices are missing**
and what each one would settle, in the order it would help. If you have
hardware, start there.

These are the evidence the capability model is built from. The register map is
one map for every model, but which parts of it a device answers varies by
model, phase count, wiring, transport and firmware — so a fingerprint from a
real machine is worth more than an inference from the YAML's comments.

## The serial numbers here are not real

Every published file carries a **stand-in** serial, in a field whose name is
the explanation: `serial_anonymized_hashed`. It is derived from the real
serial by hash, so it keeps the same shape — a Sungrow serial is ASCII across ten registers, and the string decoder
is itself under test — and one device always maps to one stand-in, so files
stay diffable across reads and two setups stay distinguishable.

The real serial, the host and the exact time go only to `.testdata/`, which is
gitignored. That split is not optional in the tooling: `RAW_DIR` is fixed, so
`--save doc/device-fingerprints` cannot put a real serial here even if asked to.

## The filename

Derived from what the device said, and from nothing anybody typed except the
contributor's name:

```
sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter
│           │            │  │    │                │              └ a directly-connected meter answered
│           │            │  │    │                └ see below
│           │            │  │    └ the document's own serial_anonymized_hashed
│           │            │  └ who sent it, from --reporter
│           │            └ three phase; the wiring is only named when unusual
│           └ inverter firmware, family dropped: SAPPHIRE-H_B001.V000.P022
└ device type code 0x0E0E
```

**`model-firmware-phases-contributor-standin`, then what is attached.** Every
word before the battery is there for grouping, and each is one question a
reader asks in that order.

**Firmware sits next to the model because it qualifies the model and nothing
else.** Which registers a device answers moves between versions, so
`sh80rt-v112` on its own does not say what to expect of a document and
`sh80rt-v112-b001v000p022` does. Sorting the directory then puts a model
beside its own firmware versions, which is the comparison anybody makes here.
It is the *inverter* firmware of the five recorded, because it carries a build
and a patch number and so separates two machines that share an ARM version.
All five stay in the document.

**The identity word is the document's own `serial_anonymized_hashed`, so a
name can be checked against the file it belongs to.** It was
`sha256(real serial)[:6]` until somebody asked why `anon-00267885816` in a
document and `aa2678` in its name shared four characters and no more — two
derivations of one serial, overlapping by chance, and only one of them
recomputable from what is published. The cost of the change is real and worth
knowing: **the filename now depends on how the stand-in is written**, and
adding the `anon-` prefix once renamed nine files for a reason with nothing to
do with anybody's hardware. Schema 10 settled that format;
`test_the_filename_now_follows_the_stand_in_deliberately` is what fails if it
is unsettled.

It comes before the battery so that every document from one *machine* shares a
prefix. With it last, the directory sorted by whatever happened to be wired
up, which split each machine's pair to opposite ends:

```
sh10rt-v112-b001v000p022-3p-fwitten-anon-94286447746-battery-sbr096-meter    read directly
sh10rt-v112-b001v000p022-3p-fwitten-anon-94286447746-battery-unknown-winet   the same one, via its dongle
sh10rt-v112-b001v000p022-3p-fwitten-anon-52318844021-battery-none            its slave, read directly
sh10rt-v112-b001v000p022-3p-fwitten-anon-52318844021-battery-none-winet      the same slave, via its dongle
```

The contributor name is lowercased and anything outside `a-z0-9-` becomes a
dash, because it lands in a filename in a public repository. Nothing supplied
means `anonymous`, which is a group like any other.

A Sungrow pack names its model rather than its family, so the battery word of
such a file reads `battery-sbr096`. Why that is a measurement and not a guess
is under [What the battery word means](#what-the-battery-word-means).

### The phase word, and why the wiring is usually left out

Register 5002 reports `0` single, `1` 3P4L, or `2` 3P3L. **L is Line**, as in
a conductor — the specification's own worked example glosses `3P4L` as
"three-phase four-wire".

| Register 5002 | Conductors | Word |
| --- | --- | --- |
| 0 — Single | one phase and neutral | `1p` |
| 1 — 3P4L | three phases **and neutral** — an ordinary domestic supply | `3p` |
| 2 — 3P3L | three phases, **no neutral** | `3p3w` |

Only the unusual wiring is named, because only the unusual wiring changes what
a reading means. Spelling out `3p4w` on every file was saying "normal" at
length.

**3P3L has to be named**, and this is the register table entry that settles
it:

```
22. A-B line voltage / phase A voltage   5019  U16  0.1V
    Refer to Output type (address: 5002)
    0: phase voltage; 1: phase voltage; 2: line voltage
```

With no neutral there is no phase-to-neutral voltage to report, so on 3P3L
registers 5019-5021 carry **line** voltages — A-B, B-C, C-A — about 1.73×
higher. Same registers, different measurement. A fingerprint that did not say
so would look like a scaling bug.

`w` is used rather than the specification's `L` because a lowercase L beside a
digit reads as a one: `3p4l` was read as "three p forty-one" the first time
somebody looked at one of these filenames. The document always keeps the exact
value in its `output_type` field.

## The transport word

A `winet` after the battery says the reading came **through a communication
module** rather than the inverter's own LAN port. It is in the filename
because it changes what answers: read directly, this project's reference
master/slave pair reports a wired meter, answers register 6100 and hangs the
connection up on the firmware block at 13250; read through the WiNet-S
dongles in front of the same two inverters, the meter block and 6100 are
refused outright and 13250 answers 0.

It also prevents a collision. The same inverter read both ways has the same
serial, the same phases and the same battery, so it produced the same
filename — and the second document silently overwrote the first, which is how
this was found.

**The medium comes from the contributor, because Modbus cannot tell.** A
WiNet-S answers identically wired and over WiFi. One dongle read on both of
its addresses produced *identical* documents — all 22 capability probes, all
104 decoded fields, and the same TLS certificate on port 443 down to the
second it was issued. Only round-trip latency differed, and over a VPN even
that is nearly swamped: 24.3 ms median wired against 25.7 ms on WiFi, though
the spread trebled.

So the document records it as `user_inputs.transport`. Run the script with
no arguments and it asks; `--transport` sets it directly:

The menu is **numbered**, and typing the value itself works too, so a
command someone was told to run still runs. Enter gives **not sure**, which is
deliberate: a WiNet-S is the commonest fitting and was tempting as the
default, but a default is what somebody gets for pressing Enter, and this is
the one field no measurement can correct. Pre-filling the likeliest answer
would turn a guess into a record.

| Value | Means | Filename word |
| --- | --- | --- |
| `direct_lan` | the inverter's own LAN port | — |
| `winet_lan` | a WiNet-S dongle, wired | `winet-lan` |
| `winet_wlan` | a WiNet-S dongle, over WiFi | `winet-wlan` |
| `winet` | a WiNet-S dongle, medium unknown | `winet` |
| `logger` | a Logger1000/3000 | `logger` |
| `unsure` | not sure — **the default** | falls back to the measurement |

`unsure` overrides nothing: where it is given, the measured verdict decides,
and register 6100 answering still proves a direct path.

The medium is in the filename only because leaving it out lost a file. What a
reader should take from `winet-lan` against `winet-wlan` is which cable, not
any expectation that different registers answer — they do not.

**What the measurement can still settle.** Register 6100 decides and register
13265 only corroborates, which is the reverse of how this was first written:

| Register 6100 | 13265 names a module | Route |
| --- | --- | --- |
| answered | no | direct |
| refused | no | through a WiNet-S |
| refused | yes | through a WiNet-S |
| **answered** | **yes** | **direct** |

Sungrow documents 6100-6195 as not forwarded by a WiNet-S or Logger, so
answering it means nothing is in the way — whatever 13265 says. The last row
is what settles the module string's role: that inverter has a WiNet-S fitted
*and* answers on its own LAN port, so 13265 names a dongle on a reading that
never went through it. It reports what is **attached**, not the route taken.

Which leaves 13265 unable to conclude anything either way — two measured
dongles return it **empty**, exactly as an inverter with no module does. It
is recorded, and it decides nothing.

The same machine read both ways is the clearest illustration of why the
transport matters at all:

| Probe | Its own LAN port | Its WiNet-S |
| --- | --- | --- |
| register 6100 | answered | refused |
| MPPT3/MPPT4 | `0xFFFF`, the specification's sentinel | **`0`** |
| directly wired meter | answers | refused |
| SBR module block | unit **200** | unit **2** |
| wallbox | not forwarded | unit **3** |

Two of those rows are traps. The dongle rewrites the *unavailable sentinel*
to zero, so a two-tracker inverter probes as having four; and the wallbox is
reachable **only** through the dongle, so a direct-LAN setup cannot see it at
all.

Where the reported transport and the measurement disagree, the script
**says so while it is running**, because that is the moment it can be acted
on: somebody who has just typed the wrong cable can retype it, and somebody
whose hardware really contradicts the specification has found the interesting
case and can put it in `--comment`. A measurement that concluded nothing does
not count as disagreeing.

It is deliberately not a field. Schema 5 stored it and schema 6 removed it: a
comparison of two values that are both in the same file is neither what a
person typed nor what a wire said, it goes stale the moment the verdict logic
changes, and any reader can recompute it from `user_inputs.transport` and
`connection.verdict`.

`--label` overrides it. It used to default to the **serial number**, falling
back to the host — the two things the publishable document exists not to
carry, handed over in the filename instead.

The identity word is the document's own stand-in serial, so anybody holding
only the published file can check that the name belongs to it. What it is
*not* is a hash of the real serial: that could not be recomputed from what is
published, which is the whole reason it changed.

## What the battery word means

Every state is prefixed `battery-`, so the words sort together and read as one
field rather than as unrelated tokens.

| Word | What was seen | What it means |
| --- | --- | --- |
| `battery-sbr096` / `battery-sbh200` / … | the module block answered at unit 200 **or** at unit 2, and the capacity matches one model | a Sungrow pack, and which **model** |
| `battery-sungrow` | unit 200 answered, capacity unreadable or unmatched | certainly Sungrow, family unclear |
| `battery-thirdparty` | battery registers answered, unit 200 did not, **connection is direct** | not a Sungrow pack — unit 200 would have answered |
| `battery-unknown` | the same silence, **behind a dongle** | cannot be told either way |
| `battery-none` | battery registers reported the unavailable sentinel, **or all answered zero** | no battery attached — the zero case is a master/slave slave, whose battery belongs to the master |
| `battery-unreadable` | the reads were refused | something is wrong, and that is worth recording |

**The model, size included** — which reverses what this file used to say.
The objection was that a size claims a module count the reported capacity does
not support. Measuring an SBR096 answered it: the per-module arrays at
10765-10788 each hold **eight** slots, eight being SBR256 and the largest SBR
there is, and exactly three were filled — three 3.2 kWh modules for 9.6 kWh.

Three signals agree on that pack, taken from two different devices:

| Where | Reads | Means |
| --- | --- | --- |
| inverter, register 5639 | 960 | 9.6 kWh at 0.01 kWh per count |
| battery, unit 200 arrays from 10765 | 3 of 8 slots filled | three modules, so 3 × 3.2 kWh |

A third reading was listed here and has been withdrawn. Address 10744 on that
pack read `96`, which looked like the capacity in 0.1 kWh — until a second
SBR096 read `98` there while register 5639 still said 960. So 10744 is
something that merely happened to equal 96 on one machine, almost certainly
state of health, and the agreement was a coincidence. Register 5639 is the
documented capacity and is what the label uses; the module arrays corroborate
it where they are reachable, which is only on a direct connection — through a
WiNet-S just 10740-10751 are forwarded and the arrays are refused.

So the size is named when the capacity lands within
`CAPACITY_TOLERANCE_KWH` of exactly one model, and `battery-sungrow` still
covers the case where it matches none. The module arrays are corroboration
rather than the source: their layout is not in any Sungrow document here, and
`battery.py`'s table is.

**Unit 2 counts as well as unit 200.** A WiNet-S forwards the pack to unit 2
— the specification says "the battery communication address will be the WiNet
internal forwarding address" without saying what it is — and so, measured, do
some inverters on their own LAN port. Unit 2 is also where a *slave* inverter
lives, so the device type code is read alongside the module block: a slave
answers it and a battery does not. Without this, a fingerprint of a perfectly
ordinary SBR came back as `battery-unknown`.

**The two middle rows look identical over the wire and are not the same
fact.** The specification puts the per-module block at unit 200 only on a
direct path: "if the data is obtained through TCP/IP forwarding via the
Ethernet port on WiNet, the battery communication address will be the WiNet
internal forwarding address", and Logger is not supported at all. So a silent
unit 200 is evidence on a direct connection and **no evidence whatsoever**
behind a dongle, where calling it third-party would be inventing a fact.

Capacity is only consulted once unit 200 has established the pack is a Sungrow
one. It is not a general signal: the reference Pylontech reports **0** there,
so treating capacity as a battery identifier on its own would call a 14.4 kWh
pack no battery at all.

`battery-none` earns a word where a missing meter does not: a hybrid inverter
is *sold* to have a battery, so its absence is information, and it is a common
state because people fit the inverter first. A missing wallbox is the
overwhelming default and would only lengthen every name.

The battery's **make** still cannot be derived — nothing in the specification
exposes a type, brand or manufacturer register — so it goes in `--battery` and
lands in the document as `user_inputs.battery`.

## What a person typed, and what a wire said

Everything a contributor supplied lives in **`user_inputs`**, first in the
file. Nothing else in the document came from a person.

```json
"user_inputs": {
  "battery": "Sungrow SBR096, 9.6 kWh",
  "comment": "master with battery",
  "modbus_proxy": "no",
  "reporter": "gerd",
  "transport": "winet_lan"
}
```

The boundary matters more than it looks. Every one of those keys exists
because Modbus cannot answer the question — no register reports a battery's
make; nothing distinguishes a master from a slave, because the difference is
that the master has the meter and the battery, which reads exactly like a lone
inverter with neither; and a WiNet-S answers the same wired as over WiFi. They
are worth having anyway: a fingerprint that says `SBR096` beats one that says
"a Sungrow pack of 9.6 kWh". They are only worth having if nobody mistakes
them for something the inverter said.

That distinction used to live in four key *names* — `battery_reported_by_hand`
in `device`, `reported_by_hand` in `connection` — scattered across three
sections, which asks a reader to know the convention before they can trust
anything. Since schema 5 the section is the convention, and `device`,
`firmware`, `connection`, `readings` and `capability_probes` contain only what
was read off a wire.

`ip_address_last_two_octets` is not in there, deliberately: it is the address
that answered, so it is observed rather than claimed. What *is* a user input
is the **permission** — see below.

## Two documents from one machine

Several files can come from one inverter, and the reason is always the path.
`doc/device-fingerprints/` currently holds two such pairs:

* **gerd's SH8.0RT-V112**, read over its own LAN port and through its
  WiNet-S. These differ substantially: the dongle refuses the two firmware
  blocks at input 2612 and 2628, reports eight fields as `0` that the cable
  declares unavailable, moves the battery from unit 200 to unit 2 and reveals
  a wallbox at unit 3 that the cable cannot see.
* **bar12's SH10RT-20**, read at two addresses that are *both* behind a
  communication module. These are **identical** in everything measured: same
  device, same firmware, no differing capability probe, no field present in
  one and absent in the other, the same dump coverage. Both are published
  anyway, so that identity is something a reader can check rather than a
  claim to be taken on trust.

A filename ends in the address tail — `-178-041` — when a name is already
taken by a reading from a *different* address. Without that, two paths whose
contributor answered "not sure" for the transport derive the same name and the
second silently replaces the first.

## The command that reproduces it

`command_line` is the whole invocation, so a reading can be repeated — by its
owner, or by somebody asking "what did you actually run?".

It names the `capabilities` phase even when the reading came from
`collect.py`, which is deliberate: that command repeats *this reading* with
these answers, where `collect.py <host>` would ask the questions again
interactively. The field is what to run, not a record of what was typed.

```
scripts/sungrow_scan/probe.py capabilities <host> --port 502 --unit 1 --timeout 10
  --passes 8 --transport direct_lan --proxy no --reporter mkaiser
  --battery 'Pylontech Force H1, 14.4 kWh' --comment '...' --dump
```

Two deliberate things about it.

**The host is a placeholder.** The document is built around not carrying the
address, so quoting the real command would undo that in its first line;
`ip_address_last_octet` stays the single considered exception. `--save` is
left out for the same reason — it is a local path, and it says nothing about
the reading.

**It is rebuilt from the parsed arguments, not copied from `sys.argv`.** Most
of these are collected by answering prompts, where there is no command line at
all — so reconstructing it is what lets an interactive session publish
something runnable. Documents written before schema 8 recorded only the tool
name; their lines are rebuilt from what each file itself preserves, which is
why some are missing `--port` and friends. A flag nobody can show was used is
left out rather than filled in at its default.

## How much of the address

`ip_address_last_two_octets` carries the tail of the address the reading came
from — `178.105` — and only when its owner said it could. Otherwise it reads
`xxx.xxx`.

It buys one thing, and it is worth having: several readings from one house can
be told apart. A master, a slave and two dongles produce four documents whose
readings look alike, and `178.114` against `178.105` is the difference between
a set that can be reasoned about and four files in a heap.

**Two octets rather than one, because the third is the useful half** — on the
record so far, three installations sit on `192.168.178` and two on
`192.168.176`, which one octet cannot show. That is also the more revealing
half, which is exactly why the script asks instead of taking it. Run
interactively it shows the value it would publish and waits for a yes;
`--address two_octets` says yes up front, and the default is to withhold.

Documents written before schema 9 published only the last octet, so they now
read `xxx.041` — precisely what was published before and not one digit more.
The full addresses are sitting in the raw files next door, and recovering them
would be taking consent nobody gave.

## Is a proxy in the way

`--proxy` records whether something is multiplexing the connection —
`modbus-proxy`, evcc's proxy, a Home Assistant add-on — and the answers are
`yes`, `no` and `unknown`.

It earns its line because it changes how nearly every other one should be
read. A proxy exists precisely because a Sungrow accepts very few sessions at
once, and it works by holding one connection to the inverter and lending it
out. So a fingerprint taken through one describes the proxy as much as the
device:

- a component that never drops says the proxy is serialising well, not that
  this inverter is generous with connections;
- the latency samples gain a hop, on top of already saying more about the
  network than about the device;
- a proxy rebuilds every request and response, so a frame quirk can be
  normalised away — or introduced. The padded frames at registers 2613 and
  2629 are exactly that class of finding, and they are why
  [`scripts/layout.py`](../../scripts/layout.py) exists.

`unknown` is a real answer and the default. Somebody who does not know what a
Modbus proxy is almost certainly has not installed one — but "probably not" is
not a measurement, and an empty value means the question was never put, which
is different again.

## Who reported it

`--reporter` names whoever sent it, and defaults to **anonymous**. A
fingerprint is worth having either way, and nobody should have to attach their
name to contribute one.

It is `reporter` rather than `provided_by` because the field names a person,
where "provided by" described the transaction they were part of.

## Two files, and why

| File | Where | What is in it |
| --- | --- | --- |
| `<label>.json` | here, committed | Everything publishable: model, phase count, firmware, how the connection was made, and per register both whether it answered and what it said |
| `<label>.raw.json` | `.testdata/`, gitignored | The same read with the **real** serial, the host and the exact time |

It used to be three: a `capabilities` file saying *which* registers answered
and a `readings` file with the values, which carried the same register labels
twice and had to be kept in step. One document says both per register.

The raw destination in `probe.py` is fixed, not a parameter, so `--save
doc/device-fingerprints` cannot put a real serial here even if asked to. An earlier
version made the destination a choice and the documentation told people to
choose this directory.

Fixed does not mean one path: in a checkout it is `.testdata/fingerprints`,
which `.gitignore` covers, and anywhere else — a contributor who unpacked the
zip — it is `sungrow-scan-private/`. A *hidden* directory holding somebody's
serial and address, created inside the folder they were told to send back, is
how a private file gets forwarded by accident.

## What the connection field means

Users mostly do not know how their inverter is attached, and reasonably
confuse a WiNet-S with the inverter's own LAN port — so it is worked out from
two signals the specification gives rather than asked:

- **registers 6100-6195** are documented "WiNet-S/S2 and Logger is not
  supported", so if they answer we are not behind one;
- **register 13265**, Communication Module Firmware Information, names the
  module if there is one. A direct-LAN inverter has none and returns the
  specification's UTF-8 unavailable, which decodes to an empty string.

Both are recorded, not only the conclusion, because the conclusion is a
reading of them and somebody may later read them differently. Where the two
disagree the verdict says so rather than picking one.

**WiFi versus Ethernet on a WiNet-S cannot be determined over Modbus.**
Nothing in the protocol reports it. Round-trip latency is the only hint — a
direct LAN link answers in about 2 ms with almost no spread, where WiFi is
tens of milliseconds and jitters — so the measurement is recorded as evidence
and no conclusion is drawn from it.

## Contributing one

If you have a model that is not here — especially an RS, an MG, a T-series, or
anything with a wallbox, an SBR battery or a Logger — a report from it is the
single most useful thing you can send.

Download [scripts/sungrow_scan/portable.py](../../scripts/sungrow_scan/portable.py)
and run it against your inverter:

```bash
python collect_fingerprint.py 192.168.1.50
```

It needs **nothing installed** — plain Python 3.9 or newer, no packages — and
it **only reads**: the two Modbus read function codes are the only ones the
file implements, and you are welcome to check before running it. It writes one
JSON file and publishes nothing by itself.

Look at the file, then attach it to an issue if you are happy to. Your serial
number is replaced with a stand-in and your inverter's address is not in it.

If the output says the device hung up several times, that is normal on Sungrow
hardware — the script reconnects around each one, so the report is still
complete.

Maintainers working in this repo can use `python
scripts/sungrow_scan/collect.py` instead, which runs every phase and writes
the private `.raw.json` alongside — or `probe.py capabilities <host> --save
doc/device-fingerprints` for the reading on its own.
