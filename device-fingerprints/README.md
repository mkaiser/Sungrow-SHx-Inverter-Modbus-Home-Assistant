# Capability fingerprints

## Shared survey logic

The scripts in `scripts/python/` are wrappers around the
[`sungrow-modbus`](https://pypi.org/project/sungrow-modbus/) package, and
Home Assistant's survey button calls the same package API, so a document
reads the same whichever of the two wrote it.

| The package owns | Where |
| --- | --- |
| Document shape, schema number, privacy (stand-in serials, address tail, masked dumps, `NEVER_PUBLISH`) | `fingerprint.assemble_document` (both producers), `publish_document` (the terminal's collected dicts), `attach_control_test` |
| Sections: readings, battery pack, wallbox, firmware, connection | `fingerprint.readings_section`, `battery_pack_section`, `wallbox_section` / `wallbox_from_dump`, `firmware_section`, `connection_block` |
| A wallbox read at its own address, and its filename | `fingerprint.wallbox_document`, `wallbox_label_for` |
| Capability probes, retries, refusal versus no answer | `survey.async_probe_words`, `async_read_retrying`, `failure_state` |
| Every decoded register, with multi-pass reads and field-by-field salvage | `survey.async_decoded_readings` |
| Firmware strings read raw; the battery, slave and wallbox units behind the endpoint | `survey.async_read_firmware`, `async_probe_siblings`; `fingerprint.battery_pack_unit`, `wallbox_unit` |
| The raw register dump, with its budget and single-address fallback | `dump.async_dump` |
| The block read test, with either client | `block_test.measure`, `raw_client.RawClient` |
| The filename | `fingerprint.label_for` |
| Summaries and follow-up recommendations, as data | `survey.summarise`, `next_steps` |

The package prints nothing, asks nothing, and writes no file: progress comes
back through callbacks, and `next_steps(document)` returns recommendations
rather than opening issues. What the scripts add is the interactive
questions, the terminal output and transcript, the connection setup and the
files.

The base package discovers devices over Modbus. mDNS is also supported through
an optional extra:

```text
pip install sungrow-modbus[discovery]
```

Without that extra, `probe.py mdns` gives the install command and the regular
network sweep remains available.

### Trying a library that is not released

The launchers run on the version pinned in the scripts' headers, fetched from
PyPI. To run them on something newer -- this tree, or a wheel built from it --
point `SUNGROW_MODBUS_LIBRARY` at it; uv installs the pin as usual and lays
that over it:

```sh
make scan-local HOST=a.b.c.d            # this tree's src/, no build
make scan-wheel HOST=a.b.c.d            # a fresh wheel: what a release would ship
make controltest-local HOST=a.b.c.d ARGS=--dry-run

SUNGROW_MODBUS_LIBRARY=/path/to/sungrow_modbus-X-py3-none-any.whl ./survey.sh
```

On Windows, `set SUNGROW_MODBUS_LIBRARY=C:\path\to\the.whl` before
`survey.cmd`, so a tester can be sent a wheel (`make wheel` prints
its path). It needs uv. The launcher and the survey's preamble both say the
library is `NOT a release`, and the transcript keeps that line.

What a particular Sungrow installation actually answers, recorded by
`python device-fingerprints/scripts/python/sungrow_survey.py` — the one entry point, which finds
the devices, asks what no register can answer, runs the block read test and
writes the document. `python3 device-fingerprints/scripts/python/probe.py capabilities <host>` is the
single phase inside it, for when only that is wanted; it writes to the current
working directory unless `--save` supplies another directory.

**[devices-wanted.md](devices-wanted.md) says which devices are missing**
and what each one would settle, in the order it would help. If you have
hardware, start there.

These are the evidence the capability model is built from. The register map is
one map for every model, but which parts of it a device answers varies by
model, phase count, wiring, transport and firmware — so a fingerprint from a
real machine is worth more than an inference from the YAML's comments.

## A `control_test` block, where a document has one

Almost none do, and that is not a gap in the evidence — it is the difference
between reading an inverter and writing to one. A fingerprint is produced by
reading; the `control_test` block is produced by `Run control write test` on the
device page, or by `device-fingerprints/scripts/python/sungrow_control_test.py`, and both of those change
settings on a real installation and change them back.

So **the absence of the block means "this run only read"**, never "the writes
failed". That is why schema 19 is a bump rather than a key that quietly
appeared: a reader of an older document has to be able to tell the two apart.

**The block can be older than the document.** A re-survey replaces the
reading and carries the `control_test` block forward unchanged, because a
write test is not repeated just to refresh a reading. The block carries no
date of its own, so the document's `read_at` dates the reading, not the
writes; the commit that added the block dates those.

What is in it, when it is there: for each control, the value the run chose, the
raw register word that came back, the word the specification says should have
been there, and a verdict. Then what the inverter actually did while limits were
applied, what could not be put back (ideally nothing), how long a restart took
if one was done, and a list of what the run could **not** establish. It carries
no serial and no address — there is nothing in it that could, since it is made
of register numbers and the values the run itself picked.

**Check `direct_connection` before you believe the readback table.** Where it is
false the run reached the inverter through a WiNet-S, and a WiNet-S forwards a
write and then answers the register **stale** -- measured against a cable on the
same inverter, and it does not catch up: polled every five seconds for two
minutes it never once reported a value the cable had confirmed. So on those
documents `matched` means the dongle's cache agreed, and `the device kept its
old value` cannot tell a dropped write from a stale read. The run says so above
its own table. Only the behavioural section is unaffected, because watching real
power change needs no readback at all.

The one thing worth reading it for is a verdict of *off by a clean decade*. It
names which side is implicated: the library, if the register map's scale
disagrees with the specification, or the device, if the two agree and the
firmware stored something else anyway. The second is a finding about Sungrow and
is the reason these are published.

## An `export_scale` block, where a document has one

Register 13074, the export power limit, reads in watts on every firmware
measured, but **writes** two ways: most multiply the word they are handed by
ten, some store it as handed. Schema 20 admits a block that records which,
written by `device-fingerprints/scripts/python/sungrow_control_test.py --export-scale
--merge-into <document>`:

| Field | Meaning |
| --- | --- |
| `write_units_per_count` | `10` multiplies, `1` stores as handed, `null` could not be asked |
| `held_w`, `wrote` | the limit the register held, and the one word written to ask |
| `response` | the inverter's reply to that write |
| `mode_lifted` | whether feed-in limitation was switched on for the write and back |
| `left_changed` | whether anything was left different; always `false` so far |
| `reason` | why that write answers the question |
| `read_at` | when the scale was asked, which is often not the document's own reading time |

The write is chosen so that it changes nothing on either firmware: a no-op
under one reading, out of range and refused under the other. The answer is the
**refusal**, not a readback, so unlike the readback table above it holds
through a WiNet-S too. Its absence means the question was not asked.

A `control_test` block at schema 2 carries the same block in
`conditions.export_write_scale`: the factor the run wrote 13074 at.

## Wallbox documents

A file named `...-wallbox-tls` is a wallbox read **at its own LAN address**:
Modbus TCP inside TLS on port 516, unit 248. `sungrow_survey.py` writes one
when it finds a wallbox there. A wallbox read through a WiNet-S (unit 3)
stays a section of the inverter's document, as in gerd's
`...-wallbox-winet-wlan`.

A wallbox document has no `device`: everything is under `wallbox` -- the
unit, the path (`tls`), the stand-in, 32 decoded readings and a dump cut at
the data-point starts the TLS path accepts. Its name is
`<model>-<reporter>-<stand-in>-wallbox-tls`. The stand-in is the one the
dongle document of the same house carries, so the two can be matched.

Masked, as null: input 21200-21205 (the serial) and 21210-21213 (a short
code only the direct path answers, treated like the serial until a second
wallbox shows whether it identifies the unit). It says `"document":
"wallbox"`, which is how the checks and `doc/compatibility.md` leave it out
of the inverter corpus; `tests/test_wallbox_documents.py` holds it to its
masks, to its own filename and to the address rule.

## The serial numbers here are not real

Every published file carries a **stand-in** serial, in a field whose name is
the explanation: `serial_anonymized_hashed`. It is derived from the real
serial by hash, so it keeps the same shape — a Sungrow serial is ASCII across ten registers, and the string decoder
is itself under test — and one device always maps to one stand-in, so files
stay diffable across reads and two setups stay distinguishable.

The real serial and the full address are written to no file but the run's
transcript, which stays with whoever ran it -- beside the script, gitignored
by name inside a checkout. No un-redacted copy of the document exists, so `--save
device-fingerprints` cannot put a real serial here whatever it is asked.

## The filename

Derived from what the device said, and from nothing anybody typed except the
contributor's name:

```
sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan
│           │            │  │    │                │              │     └ the inverter's own LAN port
│           │            │  │    │                │              └ the meter's phase registers (5741) answered
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
sh10rt-v112-b001v000p022-3p-fwitten-anon-94286447746-battery-sbr096-meter-direct-lan  read directly
sh10rt-v112-b001v000p022-3p-fwitten-anon-94286447746-battery-unknown-winet             the same one, via its dongle
sh10rt-v112-b001v000p022-3p-fwitten-anon-52318844021-battery-none-direct-lan           its slave, read directly
sh10rt-v112-b001v000p022-3p-fwitten-anon-52318844021-battery-none-winet                the same slave, via its dongle
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

The last word says how the survey reached the inverter: `direct-lan` for
the inverter's own LAN port, `winet` (or `winet-lan`, `winet-wlan`,
`logger`) **through a communication module**. It is in the filename
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
second it was issued.

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
| `direct_lan` | the inverter's own LAN port | `direct-lan` |
| `winet_lan` | a WiNet-S dongle, wired | `winet-lan` |
| `winet_wlan` | a WiNet-S dongle, over WiFi | `winet-wlan` |
| `winet` | a WiNet-S dongle, medium unknown | `winet` |
| `logger` | a Logger1000/3000 | `logger` |
| `unsure` | not sure — **the default** | falls back to the measurement |

`unsure` overrides nothing: where it is given, the measured verdict decides,
and register 6100 answering still proves a direct path -- `direct-lan`. Where
the measurement cannot say either, the name carries no transport word.

**`meter` is not the transport.** It says the meter's phase registers (input
5741) answered. A WiNet-S does not forward them, so a dongle document never
says `meter`, but a cable document without a wired meter does not say it
either; only `direct-lan` says the path.

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
`CAPACITY_TOLERANCE_FRACTION` of exactly one model, and `battery-sungrow` still
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
`device-fingerprints/` currently holds two such pairs:

* **gerd's SH8.0RT-V112**, read over its own LAN port and through its
  WiNet-S. These differ substantially: the dongle refuses the two firmware
  blocks at input 2612 and 2628, reports eight fields as `0` that the cable
  declares unavailable, moves the battery from unit 200 to unit 2 and reveals
  a wallbox at unit 3 that the cable cannot see.
* **bar12's SH10RT-20**, read on 2026-09-08 at two addresses that are *both*
  the WiNet-S — its Ethernet port (`…-winet-lan`) and its WiFi
  (`…-winet-wlan`). These are **identical** in everything measured: same
  device, same firmware, no differing capability probe, no field present in
  one and absent in the other, the same dump coverage. Both are published
  anyway, so that identity is something a reader can check rather than a
  claim to be taken on trust. They were filed as transport "not sure" until
  the owner moved the cable from the dongle into the inverter on 2026-10-08,
  which settled which was which.
* **bar12 again on 2026-10-08**, over the inverter's own LAN port (`…-meter-direct-lan`)
  and the dongle's WiFi, both on firmware P023. These differ the way gerd's
  do — 6100, 2612/2628, MPPT3/4 as 0 against 0xFFFF, the meter phases, the SBR
  at unit 2 against 200 — so the pattern now holds on two models. The two WiFi
  readings, P020 and P023, are the first pair that differs only in firmware.

A filename ends in the address tail — `-178-041` — when a name is already
taken by a reading from a *different* address. Without that, two paths whose
contributor answered "not sure" for the transport derive the same name and the
second silently replaces the first. bar12's September pair carried such tails
until their transport was established; none in this directory does now.

## The command that reproduces it

`command_line` is the whole invocation, so a reading can be repeated — by its
owner, or by somebody asking "what did you actually run?". The host is shown
as `***.***.<third>.<fourth>`: the first two octets stay private while the
published tail identifies the address to reuse.

`sungrow_survey.py` takes a flag for every question it asks, and asks only
those whose flag is missing. The line it publishes gives all of them, so it
repeats the survey -- block read test included -- **without a single
question**. An empty answer is still written (`--comment ''`), because an
absent flag means "ask". The launchers pass every argument through, so
`survey.sh` and `survey.cmd` take the same flags. `--control-test yes` or
`no` answers the control-test question too, so a replay asks nothing.

```
device-fingerprints/scripts/python/sungrow_survey.py <host> --unit 1 --pollers no
  --transport direct_lan --proxy no --other-inverter no --address hidden
  --reporter mkaiser --comment '' --battery 'Pylontech Force H1, 14.4 kWh'
```

When the address is published, the command also carries
`--address-tail <third>.<fourth>`. On a later run that flag combines the
published tail with the first two octets of the local IPv4 route, so the
survey can be restarted without putting the complete address in the document.
The launcher scripts and run artifacts are in `device-fingerprints/scripts/`;
the Python implementations are in its `python/` subdirectory.

A wallbox at its own address is asked three questions, so its line carries
`--address`, `--reporter` and `--comment`. Older documents carry the
equivalent `probe.py capabilities <host> ...` line, which repeats the reading
but not the block read test.

Two deliberate things about it.

**The host is a placeholder.** The document is built around not carrying the
address, so quoting the real command would undo that in its first line;
`ip_address_last_octet` stays the single considered exception. `--save` is
left out for the same reason — it is a local path, and it says nothing about
the reading.

**It is rebuilt from the answers, not copied from `sys.argv`.** Most of these
are collected by answering prompts, where there is no command line at all —
so reconstructing it is what lets an interactive session publish something
runnable. The survey prints the same line, with the real host, before it
starts reading. Documents written before schema 8 recorded only the tool
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
- a proxy rebuilds every request and response, so a frame quirk can be
  normalised away — or introduced. The padded frames at registers 2613 and
  2629 are exactly that class of finding, and they are why
  [`src/sungrow_modbus/layout.py`](../../src/sungrow_modbus/layout.py) exists.

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

## What a run writes

| File | Where | What is in it |
| --- | --- | --- |
| `<label>.json` | the current working directory for `probe.py capabilities`; committed here by copying it | Everything publishable: model, phase count, firmware, how the connection was made, the time of the reading, and per register both whether it answered and what it said |
| `sungrow-scan-<time>.log` | beside the launcher in `device-fingerprints/`, gitignored | The transcript, with the **real** serial and addresses. Never published |

The document is the only reading written. Apart from the serial, which it
replaces with a stand-in, it leaves out only the first two octets of the
address -- and the last two as well unless its owner allowed them -- so an
un-redacted copy would add nothing worth a second private file to forward by
mistake.

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
Nothing in the protocol reports it, so only `user_inputs.transport` says it.

**No round-trip time is recorded.** Documents carried `connection.latency_ms`
until 2026-10-09, and it was removed from all of them: it timed the path from
whoever read the inverter, usually over a VPN, and said nothing about the
inverter or how it is attached. The same dongle varied more between two nights
than a cable and a dongle did within one.

## Contributing one

If you have a model that is not here — especially an RS, an MG, a T-series, or
anything with a wallbox, an SBR battery or a Logger — a report from it is the
single most useful thing you can send.

If you have the integration installed, the device page runs the survey and
offers the document for download — nothing else is needed.

Otherwise, get the [device-fingerprints/](./) folder
(GitHub's *Code → Download ZIP* on this branch has it) and run, from inside it:

```bash
./survey.sh            # Linux, macOS
survey.cmd             # Windows, or double-click it
```

or `./survey.sh 192.168.1.50` if you know the address. The launcher fetches
Python and the `sungrow-modbus` library through
[uv](https://docs.astral.sh/uv/), and asks before installing uv if it is not
there. It finds the device, asks a few things no register can answer, and ends
by printing which file to send. It publishes nothing by itself.

The survey **reads**, and writes only if you allow it. Its last question
offers the **control test**, which checks that the integration writes each
setting at the right scale: a forced charge and discharge of the battery for
less than a minute, feed-in limitation switched on for a few seconds, and a
stop and restart of the inverter (3 to 4 minutes without production in
daylight, over 6 at night). Every setting it touches is saved first and put
back and read back at the end. The default answer is no, and with no answer
nothing is written.

Look at the file, then attach it to an issue if you are happy to. Your serial
number is replaced with a stand-in and your inverter's address is not in it.
The log it writes alongside holds both, and stays with you.

If the output says the device hung up several times, that is normal on Sungrow
hardware — the survey reconnects around each one, so the report is still
complete.

Maintainers can use `python3 device-fingerprints/scripts/python/probe.py capabilities <host>` for the reading on its
own. When `--save` is omitted, the JSON is written to the current working
directory. A survey that ran without the control test prints the command that
runs it later, into the document just written:

```bash
./survey.sh control <host> --port 502 --unit 1 --merge-into <survey-file>.json
```

`./survey.sh control ...` hands everything after `control` to the control
test: `--dry-run` writes nothing, `--restore <snapshot>` puts back a run that
died halfway.
Sungrow device survey
=====================

Thank you for helping. This reads your inverter and writes one small file
describing what it can do, so the Home Assistant integration can be made to
work with your setup rather than guessed at.


What to run
-----------

On Linux or a Mac, in a terminal in this folder:

    ./survey.sh

On Windows, double-click survey.cmd.

That is all of it. It will find the inverter on your network, ask you a
handful of questions, read for a minute or two, and finish by printing which
file to send back.

The survey needs Python and the integration's own Python library, `sungrow-modbus`.
The launcher gets both through uv (https://docs.astral.sh/uv/), which keeps
them in a cache of its own and changes nothing else on your machine. If uv is
not installed, the launcher says so and asks before installing it. Answer no
and it prints how to do it by hand instead.

If you already know the address, save it the search:

    ./survey.sh 192.168.1.50          (or: survey.cmd 192.168.1.50)

A Sungrow wallbox with a network cable or WiFi of its own is found and read
too, and gets a file of its own. Its address can be given the same way, alone
or beside the inverter's.

Before it starts reading, the survey prints one line that repeats it with
all your answers and asks nothing, e.g.

    ./survey.sh 192.168.1.50 --unit 1 --pollers no --transport winet_wlan ...

Run that line to read the same inverter again later. The same line is in the
file it writes, as "command_line", with the address left out.
`./survey.sh --help` lists the flags.


It reads, and writes only if you say yes
----------------------------------------

The survey reads your inverter and writes nothing to it -- unless you answer
yes to its last question, which offers the control test. That test checks
that the integration writes each setting at the right scale, and to do it,
after the reading is finished, it:

  * forces the battery to charge and to discharge, for less than a minute;
  * switches feed-in limitation on for a few seconds, where it is off;
  * stops the inverter and starts it again. That takes 3 to 4 minutes in
    daylight and over 6 at night, with no PV production meanwhile, and
    anything on the backup output loses power.

Every setting it touches is saved to a file first, and put back and read
back at the end, whatever happens. If something cannot be put back, the run
says so, keeps that file, and prints the one command that restores it:

    ./survey.sh control 192.168.1.50 --restore <the file it names>

The default answer is no. Press Enter, or run it with nobody at the
keyboard, and nothing is written.

The survey never sends anything anywhere. The launcher goes to the internet
once, to fetch uv and the library the first time; after that the files the
survey writes stay on your machine until you send one.


What gets written, and what to send
-----------------------------------

Two files, both in this folder. The run tells you which is which, and so does this:

  <name>.json                       SEND THIS ONE
                                    What your inverter is and what it
                                    answered. Your serial number is replaced
                                    by a stand-in starting "anon-", and your
                                    address is left out except, if you allow
                                    it, its last two numbers. It does carry
                                    the date and time of the reading, and
                                    the live values read at that moment --
                                    power, battery, meter.

  sungrow-scan-<date>.log           KEEP THIS ONE
                                    Everything the run printed, including
                                    your real serial number and addresses.
                                    Useful to send *privately* if something
                                    went wrong. Do not post it anywhere.

If you would rather not publish even the last two numbers of your address,
answer "no" when it asks -- the file then says xxx.xxx and is still useful.


Before you run it
-----------------

Stop Home Assistant, or anything else polling the inverter, if you can. A
Sungrow inverter accepts very few Modbus connections at once, so a second
program reading at the same time makes registers look broken when they are
not. The scan asks about this and will carry on either way -- a reading from
a busy inverter is still worth having, it is just thinner.


If something goes wrong
-----------------------

The last line of the run says what happened and what it means. Common ones:

  "nothing was collected"   -- it found no inverter. Try giving the address:
                               ./survey.sh 192.168.1.50
                               Port 502 is usual; a Logger uses 503.

  "this cannot run here"    -- the network you typed could not be read.

  a code of 3 or 4          -- it collected a report, but something about it
                               is uncertain and the run says which. Worth
                               sending anyway, with that line quoted.

  a code of 5               -- the control test could not put something
                               back. Run the --restore line it printed; it
                               is safe to repeat.

Without the control test nothing here changes anything on your inverter,
so re-running is always safe.


What is in this directory
-------------------------

  survey.sh              the launcher on Linux and macOS
  survey.cmd             the launcher on Windows; survey.ps1 does the work
  sungrow_survey.py      the survey itself, start to finish. Its header names
                         the library version it runs on
  probe.py               the individual steps -- find, identify, read, dump
  blocks.py              the block read test: which grouped read a device
                         refuses. --client raw uses the library's strict
                         raw socket, which names the count a padded frame
                         needs

  sungrow_control_test.py
                         the control test, the one file here that writes.
                         The survey runs it only with your yes;
                         ./survey.sh control ... runs it on its own

This directory is part of
https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant
and carries the same licence.
