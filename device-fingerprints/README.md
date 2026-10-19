# Capability fingerprints

What a particular Sungrow installation actually answers. The register map is
one map for every model, but which parts of it a device answers varies by
model, phase count, wiring, transport and firmware — so a fingerprint from a
real machine is worth more than an inference from the YAML's comments, and
these documents are the evidence the capability model is built from.

Inverter documents are in [`inverter/`](inverter/), wallbox documents in
[`wallbox/`](wallbox/). `doc/compatibility.md` is generated from them.

**[devices-wanted.md](devices-wanted.md) says which devices are missing**
and what each one would settle, in the order it would help. If you have
hardware, start there.

## Contributing one

If you have a model that is not here — especially an RS, an MG, a T-series, or
anything with a wallbox, an SBR battery or a Logger — a report from it is the
single most useful thing you can send.

**If you have the integration installed**, the device page does it: **Run
capability survey**, then download the document from the notification or
with **Download diagnostics**. Nothing else is needed.

**Otherwise**, get the [device-fingerprints/](./) folder (GitHub's *Code →
Download ZIP* on this branch has it) and run, from inside it:

```bash
scripts/survey.sh            # Linux, macOS
scripts\survey.cmd           # Windows, or double-click it
```

or `scripts/survey.sh 192.168.1.50` if you know the address. The launcher
fetches Python and the `sungrow-modbus` library through
[uv](https://docs.astral.sh/uv/), which keeps them in a cache of its own and
changes nothing else; if uv is not there it asks before installing it, and
answering no prints how to do it by hand. After that first fetch the survey
talks to nothing but your network. It publishes nothing by itself.

It finds the devices, asks a handful of things no register can answer, reads
for 5 to 40 minutes depending on the link, and
ends by printing which file to send. A Sungrow wallbox with a network
connection of its own is found and read too, and gets a file of its own; its
address can be given the same way, alone or beside the inverter's.

**Before you run it**, stop Home Assistant or anything else polling the
inverter, if you can. A Sungrow accepts very few Modbus connections at once,
so a second program reading at the same time makes registers look broken
when they are not. The survey asks about this and carries on either way — a
reading from a busy inverter is still worth having, just thinner. If the
output says the device dropped the connection several times, that is normal
on Sungrow hardware: the survey reconnects around each one.

### It reads, and writes only if you say yes

The survey reads your inverter and writes nothing to it — unless you answer
yes to its last question, which offers the **control test**. That test
checks that the integration writes each setting at the right scale, and to do
it, after the reading is finished, it:

* forces the battery to charge and to discharge, for less than a minute;
* switches feed-in limitation on for a few seconds, where it is off;
* stops the inverter and starts it again: 3 to 4 minutes without PV
  production in daylight, over 6 at night, and anything on the backup output
  loses power.

Every setting it touches is saved to a snapshot file first, and put back and
read back at the end, whatever happens. If something cannot be put back the
run says so, keeps the file, exits 5 and prints the one command that
restores it:

```bash
scripts/survey.sh control 192.168.1.50 --restore <the file it names>
```

The default answer is no. Press Enter, or run it with nobody at the
keyboard, and nothing is written. A survey that ran without it prints the
command that runs it later, into the document just written:

```bash
scripts/survey.sh control <host> --port 502 --unit 1 --merge-into <survey-file>.json
```

`survey.sh control ...` hands everything after `control` to
`sungrow_control_test.py`: `--dry-run` resolves the whole plan and writes
nothing, `--restore <snapshot>` puts back a run that died halfway,
`--start-only` starts a stopped inverter, `--export-scale` asks how this
firmware writes register 13074 with one write that changes nothing.

### What a run writes, and what to send

Two files, both in `device-fingerprints/` — the folder above the launchers,
whichever way the survey was started. Inside a checkout `.gitignore` covers
both by name.

| File | What is in it |
| --- | --- |
| `<label>.json` — **send this one** | What your inverter is and what it answered. The serial is replaced by a stand-in starting `anon-`, and the address is left out except, if you allow it, its last two octets. It does carry the date and time of the reading and the live values read at that moment — power, battery, meter |
| `sungrow-scan-<date>-<time>.log` — **keep this one** | The transcript: everything the run printed, including the **real** serial and addresses. Useful to send *privately* if something went wrong. Never published |

A wallbox at its own address adds a third, `<model>-<reporter>-<stand-in>-wallbox-tls.json`,
to send as well. A control test that could not put everything back leaves a
fourth, `<time>-snapshot.json`, which `--restore` takes and removes.

No un-redacted copy of the document is written, so `--save
device-fingerprints` cannot put a real serial here whatever it is asked.
Look at the file, then attach it to an issue if you are happy to.

### What the last line means

The last line of the run is the exit code and its sentence, because a pasted
transcript loses `$?`. Over several devices the worst one wins.

| Code | Means |
| --- | --- |
| 0 | the scan completed and every device produced a whole document |
| 1 | nothing was collected — no device found, or the link went before the first read. Try giving the address; port 502 is usual, a Logger uses 503 |
| 2 | this cannot run here — an address or `--address-tail` that cannot be used |
| 3 | collected, but something the filename is built from did not read (the device type, the output type, the serial or the readings), so the name under-claims. Worth a second run, and worth sending anyway |
| 4 | collected, but the reported transport contradicts the measurement. Settle that before publishing |
| 5 | the control test left something changed. Run the `--restore` line it printed; it is safe to repeat |

Without the control test nothing here changes anything on your inverter, so
re-running is always safe.

### The questions, and the command that repeats them

In order: whether anything else is polling the inverter, its unit id (only
where it matters), how the reading reaches it, whether a Modbus proxy is in
the path, whether a non-Sungrow inverter shares the meter, whether the last
two octets of the address may be published, who to credit, a comment, the
battery (only where the registers cannot settle it), and last the control
test. A wallbox at its own address is asked three: the address, who to
credit, and a comment.

Every question has a flag, and a flag given is a question not asked
(`scripts/survey.sh --help` lists them). Before it starts reading, the survey
prints the line that repeats the run with every answer and asks nothing —
with the real host on screen, and with `<host>` and `--address-tail` in the
document's `command_line`:

```
python/sungrow_survey.py <host> --address-tail 178.035 --unit 1 --pollers no
  --transport direct_lan --proxy no --other-inverter no --address two_octets
  --reporter mkaiser --comment '' --battery 'Pylontech Force H1, 14.4 kWh'
  --control-test no
```

An empty answer is still written (`--comment ''`), because an absent flag
means "ask". The line is rebuilt from the answers rather than copied from
`sys.argv`, since most of them were typed at prompts. `--port`, `--timeout`
and `--passes` appear only where they differ from the defaults. On a later
run `--address-tail` combines the published tail with the first two octets
of the local IPv4 route, so the survey can be repeated without the complete
address ever being in the document. Documents read before the survey existed
carry the equivalent `probe.sh capabilities <host> ...` line, which repeats
the reading but not the block read test.

### What is in `scripts/`

| File | What it is |
| --- | --- |
| `survey.sh` | the launcher on Linux and macOS |
| `survey.cmd`, `survey.ps1` | the launcher on Windows; the `.cmd` only starts the `.ps1` |
| `python/sungrow_survey.py` | the survey, start to finish. Its PEP 723 header names the library version it runs on |
| `python/sungrow_control_test.py` | the control test, the one file here that writes. The survey runs it only with your yes; `survey.sh control ...` runs it on its own |
| `python/probe.py` | the individual steps — `mdns`, `sweep`, `units`, `capabilities`, `dump` |
| `python/blocks.py` | the block read test from a terminal: which grouped read a device fails. `--client raw` uses the library's strict raw socket, which names the count a padded frame needs |
| `python/wallbox_direct.py` | finds and reads a wallbox at its own address, over TLS on port 516 |

`probe.py capabilities <host>` is the reading on its own, for a maintainer
who wants only that. It writes the document to the current directory, or to
`device-fingerprints/` with a bare `--save`.

## The survey runs on the published library

The scripts are wrappers around the
[`sungrow-modbus`](https://pypi.org/project/sungrow-modbus/) package, and Home
Assistant's survey button calls the same package API, so a document reads the
same whichever of the two wrote it.

| The package owns | Where |
| --- | --- |
| The order a survey reads in, and what a lost step costs (only its own section) | `survey.async_capability_survey`, given a `SurveySource` per producer |
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
rather than opening issues. What the scripts add is the questions, the
terminal output and transcript, the connection setup and the files.

The base package discovers devices over Modbus. mDNS needs an optional extra,
`pip install sungrow-modbus[discovery]`; without it `probe.py mdns` gives the
install command and the network sweep still works.

### Trying a library that is not released

The launchers run on the version pinned in the survey's header, fetched from
PyPI. To run them on something newer — this tree, or a wheel built from it —
point `SUNGROW_MODBUS_LIBRARY` at it; uv installs the pin as usual and lays
that over it:

```sh
make scan-local HOST=a.b.c.d            # this tree's src/, no build
make scan-wheel HOST=a.b.c.d            # a fresh wheel: what a release would ship
make controltest-local HOST=a.b.c.d ARGS=--dry-run

SUNGROW_MODBUS_LIBRARY=/path/to/sungrow_modbus-X-py3-none-any.whl scripts/survey.sh
```

On Windows, `set SUNGROW_MODBUS_LIBRARY=C:\path\to\the.whl` before
`survey.cmd`, so a tester can be sent a wheel (`make wheel` prints its path).
It needs uv. The launcher and the survey's preamble both say the library is
`NOT a release`, and the transcript keeps that line.

## The document

The format is `sungrow_modbus.fingerprint.SCHEMA`, **22**; the comment beside
it says what each number from 17 admits, and `probe.py` keeps the older ones.
A document is read by its own number, which is often older. Sections in
order: `schema`, `command_line`, `read_at`,
`user_inputs`, `ip_address_last_two_octets`, `device`, `firmware`,
`connection`, `readings`, `capability_probes`, then whichever of
`contention`, `register_dump`, `wallbox`, `block_read_test`, `battery_pack`,
`control_test` and `export_scale` the run produced.

### What a person typed, and what a wire said

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

Every one of those keys exists because Modbus cannot answer the question — no
register reports a battery's make; nothing distinguishes a master from a
slave, because the master has the meter and the battery, which reads exactly
like a lone inverter with neither; and a WiNet-S answers the same wired as
over WiFi. They are worth having only if nobody mistakes them for something
the inverter said, which is why `device`, `firmware`, `connection`,
`readings` and `capability_probes` contain only what was read off a wire.

An empty answer means the question was not put, which is a different
statement from `unknown`. `ip_address_last_two_octets` is not a user input:
it is the address that answered. What *is* a user input is the
**permission** to publish it.

**`--proxy`** records whether something multiplexes the connection —
`modbus-proxy`, evcc's proxy, a Home Assistant add-on — as `yes`, `no` or
`unknown`. A proxy holds one connection to the inverter and lends it out, so a
fingerprint taken through one describes the proxy as much as the device: a
component that never drops says the proxy serialises well, and a proxy that
rebuilds every frame can normalise a frame quirk away — the padded frames at
registers 2613 and 2629 are exactly that class of finding. `unknown` is a
real answer.

**`--reporter`** names whoever sent it, and defaults to **anonymous**. Nobody
should have to attach their name to contribute.

### The serial numbers here are not real

Every published file carries a **stand-in** serial, in a field whose name is
the explanation: `serial_anonymized_hashed`. It is `anon-` followed by digits
derived from the real serial by hash, as many as the serial had. One device
always maps to one stand-in, so files stay diffable across reads and two
setups stay distinguishable — and the prefix means it can never be mistaken
for a serial, which no Sungrow serial starts with.

The rest of what is removed before anything is published:

* the serial's ten registers (input 4990-4999) are masked, as null, in the
  raw dump — words carry a serial past any string check;
* anything whose *name* mentions a serial (`NEVER_PUBLISH`), value or key
  list alike, so a probe labelled "wallbox serial" publishes its state and
  not its words;
* a wallbox's serial (input 21201-21206) and the short code at 21211-21214
  that only its own address answers, masked the same way, with a stand-in
  from the same hash in `wallbox.serial_anonymized_hashed`;
* the address, except its last two octets and only with leave.

The real serial and the full address are written to no file but the run's
transcript. `tests/test_no_real_serials.py` checks every tracked file for the
shape of a serial.

### How much of the address

`ip_address_last_two_octets` carries the tail of the address the reading came
from — `178.105`, each octet zero-filled to three digits — and only when its
owner said it could. Otherwise it reads `xxx.xxx`.

It buys one thing: several readings from one house can be told apart. A
master, a slave and two dongles produce four documents whose readings look
alike, and `178.114` against `178.105` is the difference between a set that
can be reasoned about and four files in a heap. **Two octets rather than one,
because the third is the useful half** — several installations on record sit
on `192.168.178` and others on `192.168.176`, which one octet cannot show.
That is also the more revealing half, which is why the survey asks instead of
taking it: run interactively it shows the value it would publish and waits for
a yes, `--address two_octets` says yes up front, and the default is to
withhold.

### What the connection section means

Users mostly do not know how their inverter is attached, and reasonably
confuse a WiNet-S with the inverter's own LAN port — so `connection` is
worked out from what the specification gives, and both signals are recorded
beside the conclusion:

| Register 6100 | 13265 names a module | Route |
| --- | --- | --- |
| answered | no | direct |
| answered | **yes** | **direct**, with a module fitted but not in the path |
| refused | either | through a communication module |
| no answer | either | not determined, and no transport word in the filename |

Sungrow documents 6100-6195 as not forwarded by a WiNet-S or Logger, so an
answer means nothing is in the way — whatever 13265 says. 13265 names the
module that is **fitted**, not the route taken: one inverter names its
WiNet-S on a reading through its own LAN port, and through a dongle it can
answer empty, exactly as an inverter with no module does. It is recorded, and
it decides nothing.

**WiFi versus Ethernet on a WiNet-S cannot be determined over Modbus**:
`connection.wifi_or_ethernet` says so on every document, and only
`user_inputs.transport` says which. One dongle read on both of its addresses
produced identical documents — every capability probe, every decoded field,
and the same TLS certificate on port 443.

**No round-trip time is recorded.** It times the path from whoever reads,
usually a VPN, and says nothing about the inverter or how it is attached.

Where the reported transport and the measurement disagree, the survey **says
so while it is running** and offers to change the answer — the moment
somebody can retype the wrong cable, or put a genuine contradiction in
`--comment`. Given as `--transport`, the answer is kept, the document records
both, and the run exits 4. The disagreement itself is not stored: any reader
can recompute it from `user_inputs.transport` and `connection.verdict`, and a
stored comparison goes stale when the verdict logic changes.

The same machine read both ways shows why the transport matters at all:

| Probe | Its own LAN port | Its WiNet-S |
| --- | --- | --- |
| register 6100 | answered | refused |
| inputs 2612, 2628 (firmware strings) | answered | refused |
| MPPT3/MPPT4 | `0xFFFF`, the specification's sentinel | **`0`** |
| directly wired meter | answers | refused |
| SBR module block | unit **200** | unit **2** |
| wallbox | not forwarded | unit **3** |

Two of those rows are traps. The dongle rewrites the *unavailable sentinel*
to zero, so a two-tracker inverter probes as having four; and through the
inverter's own port a wallbox cannot be seen at all — only through the dongle,
or at the wallbox's own address.

### The block read test

`block_read_test` is the measurement `src/sungrow_modbus/inverter/layout.py`
is changed from: every block read the integration's poll makes, three rounds
of two attempts, run before the reading because it only means anything on an
idle link. `answered` read at least once; `never_answered` failed every
round, and is narrowed (`narrowed`) to the smallest ranges that still fail;
`intermittent` answered sometimes, which is contention, not a fault. `client`
says which client measured, which decides what the rest means: the library
rejects a padded frame, the strict raw socket names the count that would read
it. A range marked `not narrowed` names no register, and a read that only
timed out cannot tell a silent inverter from a lost answer — neither belongs
in `layout.py`.

A document from Home Assistant's **Download diagnostics** carries none; the
survey button's does. A document from Home Assistant also has a `contention`
section, saying whether that entry's own polling was held off during the run.

### A `control_test` block, where a document has one

Almost none do, and that is not a gap in the evidence — it is the difference
between reading an inverter and writing to one. The block is produced by
**Run control write test** on the device page, or by the survey with leave
(or `sungrow_control_test.py --merge-into`), and both change settings on a
real installation and change them back.

So **the absence of the block means "this run only read"**, never "the writes
failed". That is why schema 19 is a bump rather than a key that quietly
appeared. The block has a `schema` of its own, currently 2.

**The block can be older than the document.** A re-survey replaces the
reading and carries the `control_test` block forward unchanged, because a
write test is not repeated just to refresh a reading. The block carries no
date of its own, so the document's `read_at` dates the reading, not the
writes; the commit that added the block dates those.

What is in it: for each control, the value the run chose, the raw register
word that came back, the word the specification says should have been there,
and a verdict. Then what the inverter did while limits were applied, what
could not be put back (ideally nothing), how long a restart took if one was
done, and what the run could **not** establish. It carries no serial and no
address — it is made of register numbers and the values the run itself
picked, and it is checked for the serial before it is attached.

**Check `direct_connection` before you believe the readback table.** Where it
is false the run reached the inverter through a WiNet-S, and a WiNet-S
forwards a write and then answers the register **stale** — measured against a
cable on the same inverter, and it does not catch up. So on those documents
`matched` means the dongle's cache agreed, and `the device kept its old value`
cannot tell a dropped write from a stale read. The run says so above its own
table. Only the behavioural section is unaffected, because watching real power
change needs no readback.

The verdict worth reading it for is *off by a clean decade*. It names which
side is implicated: the library, if the register map's scale disagrees with
the specification, or the device, if the two agree and the firmware stored
something else anyway. The second is a finding about Sungrow and is the reason
these are published.

### An `export_scale` block, where a document has one

Register 13074, the export power limit, reads in watts on every firmware
measured, but **writes** two ways: most multiply the word they are handed by
ten, some store it as handed. Schema 20 admits a block that records which,
written by `sungrow_control_test.py --export-scale --merge-into <document>`:

| Field | Meaning |
| --- | --- |
| `write_units_per_count` | `10` multiplies, `1` stores as handed, `null` could not be asked |
| `held_w`, `wrote` | the limit the register held, and the one word written to ask |
| `response` | the inverter's reply to that write |
| `mode_lifted` | whether feed-in limitation was switched on for the write and back |
| `left_changed` | whether anything was left different |
| `reason` | why that write answers the question |
| `read_at` | when the scale was asked, which is often not the document's own reading time |

The write is chosen so that it changes nothing on either firmware: a no-op
under one reading, out of range and refused under the other. The answer is the
**refusal**, not a readback, so unlike the readback table above it holds
through a WiNet-S too. Its absence means the question was not asked. A
`control_test` block carries the factor its run wrote 13074 at in
`conditions.export_write_scale`.

### Wallbox documents

A file named `...-wallbox-tls` is a wallbox read **at its own LAN address**:
Modbus TCP inside TLS on port 516, unit 248. `sungrow_survey.py` writes one
when it finds a wallbox there. A wallbox read through a WiNet-S (unit 3)
stays a section of the inverter's document, as in gerd's
`...-wallbox-winet-wlan`.

A wallbox document has no `device`: everything is under `wallbox` — the
unit, the path (`tls`), the stand-in, the decoded readings and a dump cut at
the data-point starts the TLS path accepts. Its name is
`<model>-<reporter>-<stand-in>-wallbox-tls`, and the stand-in is the one the
dongle document of the same house carries, so the two can be matched. It
says `"document": "wallbox"`, which is how the checks and
`doc/compatibility.md` leave it out of the inverter corpus;
`tests/test_wallbox_documents.py` holds it to its masks, to its own filename
and to the address rule.

## The filename

Derived from the document alone, and from nothing anybody typed except the
contributor's name and their transport answer. `fingerprint.label_for`
builds it, and `tests/test_document_filenames.py` holds every committed
document to the name it derives.

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

**`model-firmware-phases-contributor-standin`, then the battery, meter,
wallbox and transport words.** Every word before the battery is there for
grouping, in the order a reader asks.

**Firmware sits next to the model because it qualifies the model and nothing
else.** Which registers a device answers moves between versions, so
`sh80rt-v112` on its own does not say what to expect and
`sh80rt-v112-b001v000p022` does. It is the *inverter* firmware of the five
recorded, because it carries a build and a patch number and so separates two
machines that share an ARM version. All five stay in the document. A
firmware that did not read leaves the word out rather than writing
`unknown`, which would sort as though it were a version.

**The identity word is the document's own `serial_anonymized_hashed`**, so
anybody holding only the published file can check that the name belongs to
it. The cost is that the filename depends on how the stand-in is written;
`test_the_filename_now_follows_the_stand_in_deliberately` is what fails if
that changes. It comes before everything attached, so every document from
one *machine* shares a prefix and sorts together:

```
sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan             a slave, read directly
sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-winet                  the same slave, via its dongle
sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan     its master, read directly
sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-winet                the same master, via its dongle
```

The contributor name is lowercased and anything outside `a-z0-9-` becomes a
dash, because it lands in a filename in a public repository. Nothing supplied
means `anonymous`. `probe.py capabilities --label` overrides the whole name;
the survey has no such flag.

A name already taken by a reading from a *different* address gets the
address tail appended — `-178-041` — or, where the tail is withheld, a number,
so two paths that derive the same name cannot silently replace each other.

### The phase word

Register 5002 reports `0` single, `1` 3P4L, or `2` 3P3L. **L is Line**, as in
a conductor — the specification glosses `3P4L` as "three-phase four-wire".

| Register 5002 | Conductors | Word |
| --- | --- | --- |
| 0 — Single | one phase and neutral | `1p` |
| 1 — 3P4L | three phases **and neutral** — an ordinary domestic supply | `3p` |
| 2 — 3P3L | three phases, **no neutral** | `3p3w` |

Only the unusual wiring is named, because only the unusual wiring changes what
a reading means. **3P3L has to be named**, and this is the register table
entry that settles it:

```
22. A-B line voltage / phase A voltage   5019  U16  0.1V
    Refer to Output type (address: 5002)
    0: phase voltage; 1: phase voltage; 2: line voltage
```

With no neutral there is no phase-to-neutral voltage to report, so on 3P3L
registers 5019-5021 carry **line** voltages — A-B, B-C, C-A — about 1.73×
higher. Same registers, different measurement; a fingerprint that did not say
so would look like a scaling bug. `w` rather than the specification's `L`,
because a lowercase L beside a digit reads as a one. The document keeps the
exact value in `output_type`.

### The transport word

The last word says how the survey reached the inverter. It is in the filename
because it changes what answers (see the table above), and because the same
inverter read both ways otherwise derives the same name.

The contributor's answer decides it, because only a person knows the medium.
The menu is **numbered**, and typing the value works too. Enter gives **not
sure**, deliberately: a default is what somebody gets for pressing Enter, and
this is the one field no measurement can correct.

| Value | Means | Filename word |
| --- | --- | --- |
| `direct_lan` | the inverter's own LAN port | `direct-lan` |
| `winet_lan` | a WiNet-S dongle, wired | `winet-lan` |
| `winet_wlan` | a WiNet-S dongle, over WiFi | `winet-wlan` |
| `winet` | a WiNet-S dongle, medium unknown | `winet` |
| `logger` | a Logger1000/3000 | `logger` |
| `unsure` | not sure — **the default** | falls back to the measurement |

`unsure` overrides nothing: the measured verdict decides, so register 6100
answering still gives `direct-lan`, and a refusal gives `winet`. Where the
measurement cannot say either, the name carries no transport word. What a
reader should take from `winet-lan` against `winet-wlan` is which cable, not
any expectation that different registers answer — they do not.

**`meter` is not the transport.** It says the meter's phase registers (input
5741) answered. A WiNet-S does not forward them, so a dongle document never
says `meter`, but a cable document without a wired meter does not say it
either; only `direct-lan` says the path.

### The battery word

Every state is prefixed `battery-`, so the words sort together and read as one
field.

| Word | What was seen | What it means |
| --- | --- | --- |
| `battery-sbr096` / `battery-sbh200` / … | the module block answered at unit 200 **or** at unit 2, and the capacity matches one model | a Sungrow pack, and which **model** |
| `battery-sungrow` | the module block answered, capacity unreadable or unmatched | certainly Sungrow, model unclear |
| `battery-thirdparty` | battery registers answered, no module block did, **connection is direct** | not a Sungrow pack — unit 200 would have answered |
| `battery-unknown` | the same silence, **behind a dongle** | cannot be told either way |
| `battery-none` | battery registers reported the unavailable sentinel, **or all answered zero** | no battery attached — the zero case is a cluster slave, whose battery belongs to the master |
| `battery-unreadable` | the reads failed | something is wrong, and that is worth recording |

**The model, size included**, because the pack corroborates it: on an SBR096
the per-module arrays at 10765-10788 hold eight slots — eight being SBR256,
the largest there is — and exactly three are filled, three 3.2 kWh modules
for 9.6 kWh, which is what register 5639 reports (960 at 0.01 kWh). The size
is named when the capacity lands within `CAPACITY_TOLERANCE_FRACTION` of
exactly one model. Register 5639 is the source; the module arrays corroborate
it only on a direct connection, since through a WiNet-S just 10740-10751 are
forwarded. Address 10744 is not capacity: two SBR096 read 96 and 98 there
while 5639 said 960 on both.

**Unit 2 counts as well as unit 200.** A WiNet-S forwards the pack to unit 2
— the specification says only "the battery communication address will be the
WiNet internal forwarding address" — and so, measured, do some inverters on
their own LAN port. Unit 2 is also where a *slave* inverter lives, so the
device type code is read there too: a slave answers it and a battery does
not.

**The two middle rows look identical over the wire and are not the same
fact.** The specification puts the module block at unit 200 only on a direct
path, so a silent unit 200 is evidence on a direct connection and **no
evidence whatsoever** behind a dongle, where calling it third-party would be
inventing a fact.

Capacity is only consulted once the module block has established the pack is
a Sungrow one. It is not a general signal: the reference Pylontech reports
**0** there.

`battery-none` earns a word where a missing meter does not: a hybrid inverter
is *sold* to have a battery, so its absence is information. A missing wallbox
is the overwhelming default and would only lengthen every name.

The battery's **make** cannot be derived — nothing in the specification
exposes a type, brand or manufacturer register — so it goes in `--battery`
and lands in the document as `user_inputs.battery`.

## Two documents from one machine

Several files can come from one inverter, and the reason is always the path.
The survey says so when two addresses report the same serial.

* **gerd's SH8.0RT-V112**, read over its own LAN port and through its
  WiNet-S. These differ substantially: the dongle refuses the two firmware
  blocks at input 2612 and 2628, reports fields as `0` that the cable
  declares unavailable, moves the battery from unit 200 to unit 2 and reveals
  a wallbox at unit 3 that the cable cannot see.
* **fwitten's SH10RT-V112 master and slave**, each read over its own LAN port
  and through its dongle — the four names above.
* **bar12's SH10RT-20**, read at two addresses that are *both* the WiNet-S —
  its Ethernet port (`…-winet-lan`) and its WiFi (`…-winet-wlan`), on
  firmware P020. These are **identical** in everything measured, and both are
  published so that the identity is something a reader can check. Then over
  the inverter's own LAN port (`…-meter-direct-lan`) and the dongle's WiFi,
  both on P023, which differ the way gerd's do. The two WiFi readings, P020
  and P023, are a pair that differs only in firmware.
