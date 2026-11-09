# Diagnosis reference

For developers and the curious: what the diagnosis runs on, what each part of a
document means, and how its filename is built. Running a diagnosis is in
[README.md](README.md).

## The diagnosis runs on the published library

The scripts are wrappers around the
[`sungrow-modbus`](https://pypi.org/project/sungrow-modbus/) package, and Home
Assistant's diagnosis button calls the same package API, so a document reads the
same whichever of the two wrote it.

| The package owns | Where |
| --- | --- |
| The order a diagnosis reads in, and what a lost step costs (only its own section) | `diagnosis.async_capability_diagnosis`, given a `DiagnosisSource` per producer |
| Document shape, schema number, privacy (stand-in serials, address tail, masked dumps, `NEVER_PUBLISH`) | `diagnosis_document.assemble_document` (both producers), `publish_document` (the terminal's collected dicts), `attach_capability_test` |
| Sections: readings, battery pack, wallbox, firmware, connection | `diagnosis_document.readings_section`, `battery_pack_section`, `wallbox_section` / `wallbox_from_dump`, `firmware_section`, `connection_block` |
| A wallbox read at its own address, and its filename | `diagnosis_document.wallbox_document`, `wallbox_label_for` |
| An SG string inverter's document, its masks and its filename | `string_inverter.document`, `section`, `mask`, `label_for` |
| Capability probes, retries, refusal versus no answer | `diagnosis.async_probe_words`, `async_read_retrying`, `failure_state` |
| Every decoded register, with multi-pass reads and field-by-field salvage | `diagnosis.async_decoded_readings` |
| Firmware strings read raw; the battery, slave and wallbox units behind the endpoint | `diagnosis.async_read_firmware`, `async_probe_siblings`; `diagnosis_document.battery_pack_unit`, `wallbox_unit` |
| The raw register dump, with its budget and single-address fallback | `dump.async_dump` |
| The block read test, with either client | `block_test.measure`, `raw_client.RawClient` |
| The filename | `diagnosis_document.label_for` |
| Summaries and follow-up recommendations, as data | `diagnosis.summarise`, `next_steps` |

The package prints nothing, asks nothing, and writes no file: progress comes
back through callbacks, and `next_steps(document)` returns recommendations
rather than opening issues. What the scripts add is the questions, the
terminal output and transcript, the connection setup and the files.

The base package discovers devices over Modbus. mDNS needs an optional extra,
`pip install sungrow-modbus[discovery]`; without it `probe.py mdns` gives the
install command and the network sweep still works.

### The header is the whole install

Module-level imports in `scripts/` are the standard library, the sibling
modules, `sungrow_modbus` and `modbus_connection`, and the PEP 723 header must
declare every one -- `[tmodbus]` included, since the library depends on bare
`modbus-connection`. `tests/test_diagnosis_dependencies.py` reads the imports and
the header and holds them to each other.

The diagnosis can use only what the pinned wheel has. The pin is the version
`pyproject.toml` declares, moved by `scripts/release/sync_version.py`, so
between releases the PyPI wheel lags the tree.
`scripts/release/check_pinned_library.py` reads the diagnosis's and the capability
test's imports beside the integration's, so `--wheel` gates a release and the
no-argument form says what PyPI lacks. The capability test has no launcher of
its own: the diagnosis imports it, and `diagnosis.sh tests ...` starts it.

### Trying a library that is not released

The launchers run on the version pinned in the diagnosis's header, fetched from
PyPI. To run them on something newer — this tree, or a wheel built from it —
point `SUNGROW_MODBUS_LIBRARY` at it; uv installs the pin as usual and lays
that over it:

```sh
make scan-local HOST=a.b.c.d            # this tree's src/, no build
make scan-wheel HOST=a.b.c.d            # a fresh wheel: what a release would ship
make controltest-local HOST=a.b.c.d ARGS=--dry-run

SUNGROW_MODBUS_LIBRARY=/path/to/sungrow_modbus-X-py3-none-any.whl scripts/diagnosis.sh
```

On Windows, `set SUNGROW_MODBUS_LIBRARY=C:\path\to\the.whl` before
`diagnosis.cmd`, so a tester can be sent a wheel (`make wheel` prints its path).
It needs uv. The tree and PyPI share a version number, so the diagnosis's
preamble tells them apart by `direct_url.json`: the launcher and the preamble
both say the library is `NOT a release`, and the transcript keeps that line.
Unset, the launchers behave exactly as a contributor's.

## The document

The format is `sungrow_modbus.diagnosis_document.SCHEMA`, **26**; the comment beside
it says what each number from 17 admits, and `probe.py` keeps the older ones.
A document is read by its own number, which is often older. Sections in
order: `schema`, `command_line`, `read_at`,
`user_inputs`, `ip_address_last_two_octets`, `device`, `firmware`,
`connection`, `readings`, `capability_probes`, then whichever of
`steps_lost`, `contention`, `register_dump`, `wallbox`, `block_read_test`, `battery_pack`,
`capability_test`, `plausibility` and `export_scale` the run produced, and last
`features`.
Up to schema 24 the `capability_test` block is called `control_test`.

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
diagnosis taken through one describes the proxy as much as the device: a
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
That is also the more revealing half, which is why the diagnosis asks instead of
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

**`connection.link_drops`** counts the connections the device closed while
the terminal diagnosis read it, each re-opened by the backend (`probe.LINK_DROPS`).
It is there only when the diagnosis was counting, so `0` means none rather than
"not counted"; Home Assistant's documents leave it out, because its own
coordinators share the link. Many drops usually mean another client is
polling, but not always: an inverter's own LAN port has dropped a dozen times
with nothing else connected.

**`steps_lost`** names each diagnosis step the link lost (`identity`,
`readings`, `probes`, `connection`, `register dump`, `battery`, `wallbox`,
as `sungrow_modbus.diagnosis.Step` names them), with the exception's type. That
step's section is absent because the link failed, not because the device had
nothing there. It is written only when a step was lost, so from schema 24 its
absence means none was. A lost `battery` step keeps the filename from saying
`battery-thirdparty`: the pack never got the chance to answer.

**No round-trip time is recorded.** It times the path from whoever reads,
usually a VPN, and says nothing about the inverter or how it is attached.

Where the reported transport and the measurement disagree, the diagnosis **says
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

`block_read_test` is the measurement `src/sungrow_modbus/hybrid_inverter/layout.py`
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
diagnosis button's does. A document from Home Assistant also has a `contention`
section, saying whether that entry's own polling was held off during the run.

### A `capability_test` block, where a document has one

Almost none do, and that is not a gap in the evidence — it is the difference
between reading an inverter and writing to one. The block is produced by
an extended test on the device page (**Diagnosis: start**), or by the diagnosis with leave
(or `sungrow_capability_test.py --merge-into`), and both change settings on a
real installation and change them back.

So **the absence of the block means "no write test was kept"**, never "the
writes failed". That is why schema 19 is a bump rather than a key that quietly
appeared. The block has a `schema` of its own: 2 for one run, 3 for several
runs folded together.

**The block can be older than the document.** A new diagnosis replaces the
reading and carries the `capability_test` block forward unchanged, because a
write test is not repeated just to refresh a reading. A schema-2 block carries
no date of its own, so the document's `read_at` dates the reading, not the
writes; the commit that added the block dates those.

**A schema-3 block is several runs, each dated.** One run answers only the
checks its moment allowed: the site import limit needs a charge drawn from the
grid, which PV covers at noon; the PV cut needs PV; the charge ceiling needs a
charging battery. Home Assistant keeps every finished run for the inverter's
firmware (up to 50, for 30 days; **Diagnosis: tests, clear history** empties
it) and folds them (`sungrow_modbus.capability_test.ledger`):

- `runs`: every run's schema-2 block whole, each with its `read_at`, and
  `readings_changed`, the readings that differed from the document's own;
- `readback`, `effects`, `conditions`, `outcome`, `not_established`: the
  schema-2 keys, holding the strongest row per field and per check, so a
  reader of a schema-2 block reads this one unchanged. `outcome` is the worst
  of any run: a 5 in any run is a 5 here;
- `summary`: per field and check, the verdict shown, which run gave it, and
  whether it is established. A run carries `revisions`, the revision of each
  check's logic it ran (`coverage.CHECK_REVISIONS`; none means 1). Once a
  check's revision rises, rows from older runs are left out of the summary
  for it as soon as a run on the new one answers it; until then the check is
  `outdated` and not established, so Home Assistant measures it again;
- `still_missing`: what no run has established yet, with what the latest run
  said about why;
- `contradictions`: a field or check one run found off by a decade and
  another found right. Read every run of it; the fold does not choose.

Runs fold only when they share the transport and are all real, or all
simulated. A run on the other path, or a new firmware, starts the collection
again. A read-only diagnosis made while runs are kept carries them, dated.

The terminal folds the same way: `sungrow_capability_test.py --merge-into`
adds its run to the runs the document carries, dating a schema-2 block found
there by the document's `read_at`, and refuses a run on the other transport
unless `--replace` puts it in their place.

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

**Some rows in `effects` are judged by the register's answer, not by power**
(`capability_test/writepath.py`): `... write path` (the register's own word
written back to it), `forced-charging window 2 encoding` (written elsewhere and
read back, only with the schedule off and over a cable), `EMS mode options`
(each documented option once, `conditions.ems_mode_options` names each answer)
and `upper bound of <field>` (a step above the maximum: `the inverter did as it
was told` means refused, `the device clamped it` stored the maximum, `nothing
measurable happened` stored the value above it). `conditions.feed_in_ratio`
holds register 13088 before and during the export check, recorded and not
judged.

### A `plausibility` block, where a document has one

From schema 26, written by Home Assistant while auto repeat runs: each minute
between runs, the polled readings are checked against each other
(`sungrow_modbus.capability_test.plausibility`). One row per check under
`checks`, with its `verdict` (none yet, `matched`, `off by a clean decade`,
`right magnitude, wrong direction`, `could not tell`, `off by something else`
or, for a third or fourth tracker, `nothing measurable happened`), a `detail`
with the median ratio or the events, and what it `needs`. `observations`,
`first` and `last` date the collection. No reading is in it.

A ratio that is merely off -- losses, reactive power -- is `could not tell`,
never a finding: only a clean decade or an inverted sign is. Through a WiNet-S
the checks still hold, because they compare readings, not writes.

### The `features` section

From schema 25 a document ends with **`features`**, one row per feature set
in `sungrow_modbus.features.FEATURE_SETS`: `feature`, `name`, `state` and
`why`, the lines of evidence the state rests on. It is computed from the
document's own sections and recomputed whenever a capability test block is
attached, so it never says more than they do:

| State | From |
| --- | --- |
| `confirmed` | a readback that matched **over a cable**, or a behavioural check the inverter obeyed |
| `wrong scale` | a readback off by a decade or of the wrong slope, or an effect on a decade-wrong value or in the wrong direction |
| `write refused` | the device answered a write with an exception, through any link |
| `inconclusive` | tested, settled nothing, including any readback through a WiNet-S |
| `readable` | a decoded reading or the raw dump answered for its registers; nothing wrote to them |
| `not available` | the capability test's preflight did not grant the set's capability |
| `not read` | nothing in the document speaks for it |

A finding outranks a match within one set. A simulated or dry run is no
evidence, so its rows can say no more than `readable`.

### An `export_scale` block, where a document has one

Register 13074, the export power limit, reads in watts on every firmware
measured, but **writes** two ways: most multiply the word they are handed by
ten, some store it as handed. Schema 20 admits a block that records which,
written by `sungrow_capability_test.py --export-scale --merge-into <document>`:

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
`capability_test` block carries the factor its run wrote 13074 at in
`conditions.export_write_scale`.

### Wallbox documents

A file named `...-wallbox-tls` is a wallbox read **at its own LAN address**:
Modbus TCP inside TLS on port 516, unit 248. `sungrow_diagnosis.py` writes one
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

### String inverter documents

An SG (a PV inverter with no battery) answers the hybrid identity block and
the PV registers up to 5035, and none of the hybrid map past them, so
`sungrow_diagnosis.py` reads it by its own map (`string_inverter_direct.py`)
when input 5000 names one. It says `"document": "string_inverter"` and is
committed to `device-diagnosis/results/string_inverter/`.

Its `device` carries the type code, the model, the output type and the
stand-in; `firmware` the ARM and DSP versions only. Everything else is under
`string_inverter`: the unit, the map's source, the decoded readings and the
raw dump of `dump.SG_BANDS`, with the serial's ten words (input 4990-4999)
blanked as on a hybrid. The map is unmeasured, so the dump is the evidence.
Its name is `<model>-<1p|3p>-<reporter>-<stand-in>`. Nothing writes to an SG:
no capability test, no block read test, no capability probes.

## The filename

Derived from the document alone, and from nothing anybody typed except the
contributor's name and their transport answer. `diagnosis_document.label_for`
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
the diagnosis has no such flag.

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
higher. Same registers, different measurement; a diagnosis that did not say
so would look like a scaling bug. `w` rather than the specification's `L`,
because a lowercase L beside a digit reads as a one. The document keeps the
exact value in `output_type`.

### The transport word

The last word says how the diagnosis reached the inverter. It is in the filename
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
The diagnosis says so when two addresses report the same serial.

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
