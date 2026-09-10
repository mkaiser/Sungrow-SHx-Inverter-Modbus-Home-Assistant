# Sungrow Modbus — working notes

This repo has **two tracks**. Know which one you are touching.

1. **The YAML package** (`legacy/modbus_sungrow.yaml`) — shipping, in use by many
   people, on `main`. Treat as production.
2. **The new Home Assistant integration** (`custom_components/sungrow_modbus` +
   `src/sungrow_modbus`) — on branch `proper-ha-integration`. The
   long-term replacement, currently an MVP.

The integration is intended to **supersede** the YAML package, not sit beside
it forever. Until it reaches parity, the YAML package stays untouched.

Its scope is wider than the YAML package's. Two of the three extra devices
are now done:

- ✅ the **SBR battery** — its own device, 40 registers in three components,
  on unit **200** direct or **2** through a WiNet-S. The earlier claim that it
  is "not reachable via WiNet-S at all" was wrong and is measured: it is
  reachable, under a different number.
- ✅ the **wallbox** (AC011E-01 / AC22E-01) — its own device, 32 registers in
  four components, at unit **3** through a WiNet-S or **248** direct. Read
  only; nothing writes to it.
- ⬜ the **iHomeManager** (port **503**, slave 247) — the only one with an
  official Sungrow register document, and the only one **never measured**.

A wallbox does *not* require an iHomeManager, and cannot be found by sweeping
for one: it answers only behind an endpoint that already answered.

It also covers a **generator the Sungrow cannot see**. A non-Sungrow inverter
behind the same grid meter makes `load_power` low by exactly its output --
the inverter computes load from its own output plus grid import -- so
`external.py` adds it back from entities another integration owns. The one
place a value here comes from Home Assistant rather than Modbus, which is why
it is not in `src/`, and the one place an entity's existence is an **option**
rather than a probed fact.

One config entry is **one Modbus endpoint** (host + port) plus the devices
discovered on it, which is exactly the set sharing one serialized connection.
The config flow probes and identifies devices by what answers, never by unit
id. `doc/integration_plan.md` has the register sources, their licences, and
the milestone order.

## Do not hand-edit

- `legacy/modbus_sungrow_multiple_inverters_{1,2,3}.yaml` are generated from
  `legacy/modbus_sungrow.yaml` by `scripts/generate_second_inverter_config.py`
  and committed by CI. Edit the source, not the output.

## The integration, in one paragraph

Home Assistant 2026.9 modernized Modbus. A device integration runs its own
config flow and asks the `modbus` integration for a *unit*
(`async_get_unit(hass, entry, ModbusTcpParams(...), unit_id)`); everything
pointed at the same host/port then shares one serialized connection, which
matters because a Sungrow inverter accepts few simultaneous sessions. Register
knowledge lives in `src/sungrow_modbus`, a plain Python library on
`modbus-connection` with **no Home Assistant imports**, so it tests without HA
and without hardware. Core's `sofar` integration is the reference
implementation for this pattern — read its real source, not blog posts.

## Commands

| Command | What it does |
| --- | --- |
| `make help` | Every command below as a shortcut. `make check` is the CI gate, `make dev` and `make sim` the dev loop, `make gen` rewrites every generated file |
| `scripts/setup.sh` | Install HA, the device library (editable) and tooling |
| `scripts/develop.sh` | Boot HA on <http://localhost:8123> against `config/` |
| `scripts/simulate.sh` | Regenerate the register seed and serve it on :5020 |
| `scripts/fetch_references.sh` | Clone HA core + libs into `.reference/` (gitignored) |
| `scripts/sungrow_scan/collect.py` | **The one entry point for a survey**: finds the devices, asks what no register can answer, runs the block read test, reads every register, writes the document and a transcript, and prints a maintainer-facing summary. Exit code says what happened (`0` fine, `3` the filename under-claims, `4` the transport is disputed, `1`/`2` nothing collected) |
| `scripts/make_scan_zip.py` | Build `sungrow_scan.zip`; `--verify` unpacks it and runs it with a bare Python, `--against 5020` runs the whole survey against the simulator |
| `scripts/sungrow_scan/probe.py` | Probe for Sungrow devices: `mdns`, `sweep <cidr>` (502, 503 for a Logger or iHomeManager, 516 for an iHomeManager's TLS port — found, not readable), `units <host>`, `capabilities <host>`, `dump <host>`. Uses the library where it is installed and `portable.py`'s client where it is not, so the whole directory runs from a zip |
| `scripts/sync_version.py` | Single source of truth for the version; `--check` in CI, `--set X.Y.Z` to release |
| `scripts/generate_entity_map.py` | Derive `doc/legacy_entity_map.json` from the YAML package; `--check` in CI |
| `scripts/generate_numbers.py` | Write the `number` descriptions from the write table in `scripts/writes.py`; `--check` in CI |
| `scripts/generate_switches.py` | Write the `switch` descriptions from the write table; `--check` in CI |
| `scripts/generate_selects.py` | Write the `select` descriptions and their option labels from the write table; `--check` in CI |
| `scripts/generate_strings.py` | Write the entity names to the convention in `scripts/naming.py`; `--check` in CI |
| `scripts/influx_migration.py` | Print Grafana regexes and rewrite recipes for InfluxDB users; connects to nothing |
| `scripts/seed_migration_testbed.py` | Make the dev instance look like a house that ran the YAML package for years, so the migration can be reviewed in the GUI |
| `scripts/generate_compatibility.py` | Build `doc/compatibility.md` from the committed fingerprints; `--check` in CI |
| `scripts/generate_scan_plan.py` | Record the library's block reads and register decoding into `scripts/sungrow_scan/scan_plan.json`, so the scanner works without it. Covers the inverter, the SBR pack and the wallbox — the last two marked with the **role** whose unit they answer on rather than a number, because that moves with the transport; `--check` in CI |
| `scripts/sungrow_scan/portable.py` | The stdlib-only Modbus client, register decoder and plan loader the other two build on, and a one-file report users run against their own inverter |
| `scripts/sungrow_scan/blocks.py` | The block read test: which read inside a component fails, and whether it is a fault or contention. `--client library` fails where the integration does; `--client raw` names the count a padded frame needs; `--narrow-budget` bounds the narrowing, which is unaffordable on a link where reads time out |
| `scripts/review_names.py` | Lay the entity names out for the open naming decision — grouped by subject, each with the entity id it produces and its legacy name; `--markdown` writes `doc/entity_name_review.md` |
| `scripts/make_brand_icon.py` | Regenerate the integration's `brand/` icons (`--preview` renders a check sheet) |
| `pytest` | Device library + integration tests, no network needed |
| `ruff check . && ruff format .` | Lint and format |

`doc/development.yaml` is the copy-paste runbook — commands, the optional
secrets, the dev login, port forwarding to the desktop and to the LAN.
`doc/development.md` is the fuller guide. `doc/integration_plan.md` is the
plan of record, including the migration work that is still open.

## Things that will bite you

These each cost real debugging time. They are not guesses — each was hit and
verified in a container.

- **Home Assistant 2026.9 requires Python ≥ 3.14.2.** The
  `mcr.microsoft.com/devcontainers/python` images only go to 3.13, which is
  why the devcontainer uses `python:3.14-bookworm`.
- **Core's `modbus` drives `modbus-connection` with the _tmodbus_ backend,
  not pymodbus.** `import homeassistant.components.modbus` fails outright
  without `modbus-connection[tmodbus]`. `requirements_dev.txt` mirrors the
  exact pins from `homeassistant/components/modbus/manifest.json`; bump them
  together.
- **The version in `pyproject.toml` must equal the `requirements` entry in
  `custom_components/sungrow_modbus/manifest.json`.** HA checks the installed
  version on every start and will try to pip-install the package if they
  differ. Never edit either by hand: `python scripts/sync_version.py --set X.Y.Z`
  moves both, `--check` is enforced in CI, in pytest and at release.
- **The integration's domain is also the library's import name.** Both are
  `sungrow_modbus`. So `config/custom_components` is a **symlink** to the
  repo's `custom_components/`, the way a real install looks. Putting
  `custom_components/` on `PYTHONPATH` instead — which `scripts/develop.sh` used
  to do, and which worked until the domain was renamed — exposes the
  *integration* as top-level `sungrow_modbus`, shadowing the library, and
  `from sungrow_modbus import TIERS` then imports the integration from inside
  itself. Home Assistant reports it as a circular import while loading the
  config flow, a long way from the cause.
- **`--set` must re-install the library, not just edit the files.** Bumping
  the version does not touch an installed editable package's metadata, and
  Home Assistant compares the manifest pin against what is *installed*. Left
  alone it asks pip for a version that is not on PyPI yet and the config flow
  dies with `RequirementsNotFound` at the moment somebody clicks Add
  integration. `scripts/sync_version.py --set` now does the re-install, and
  `--check` fails on the drift.
- **Addresses are protocol addresses**, one below the register number in
  Sungrow's document and in the YAML comments (`address: 4989 # reg 4990`).
- **Ask the inverter, do not infer.** Register 5002 reports the output type
  (0 single, 1 3P4L, 2 3P3L); 5000 is the device type code. Sungrow's own
  protocol document also warns that some measuring points are *not*
  forwarded by WiNet-S over TCP/IP, so capability varies by transport too.
- **WiFi versus Ethernet on a WiNet-S is not determinable.** Settled against a
  controlled pair — one dongle, read wired then over WiFi — with a nil
  structural diff. Latency cannot stand in either: direct-LAN medians span
  2.0-61.5 ms and WiNet medians 24.3-48.3 across four houses, and one house's
  direct link is slower than its own dongle. Register 6100 does distinguish
  direct from dongle, 9/9 — and register 13265 names the module that is
  *fitted*, which is not the same as the module in the path.
- **`swap: word` in the YAML means `word_order="little"`** in the library.
  Sungrow sends 32-bit values low word first.
- **A first boot in a fresh container logs ~20 setup errors** while HA
  downloads component requirements, and the UI 404s. The next boot is clean
  in ~2s. Not a bug.
- **Not every register answers.** An SH10RT returns 0xFFFF for MPPT3/4, and
  battery blocks are absent without storage. A poll losing one block is
  normal; that is what `UpdateReport` is for.
- **Some registers come back in a padded frame.** At 2612 and 2628 the
  inverter sends a frame sized for **15 registers while declaring the correct
  byte count** — `mbap_len` 33 against `byte_count` 22 for a request of 11.
  The data is right; the frame is not, and `modbus-connection` validates
  against the MBAP length and rejects the whole answer. Asking for exactly 15
  makes the two agree, which is why `layout.COUNTS` works and why it is a
  workaround rather than a correction. Because the library pools neighbours
  into one block read, those two fields failed the whole 58-register
  `slowest_input` request and left **36 unrelated entities permanently
  empty**.
- **A lenient Modbus client will tell you the register is fine.** The first
  diagnosis of the above was wrong for a day because a raw-socket probe trusts
  `byte_count` and reads these registers perfectly, while the shipping stack
  cannot read them at all. `scripts/sungrow_scan/blocks.py` is deliberately as strict
  as the shipping stack, and reports both numbers plus the count that
  reconciles them. Add to `scripts/layout.py` only from *its* measurement.
- **A failed read does not always fail quickly, and that changes what a
  diagnostic costs.** Three houses refuse an unmapped register with exception
  0x02 in milliseconds. On a fourth, read over a VPN, the same reads instead
  produced `Response timeout after 10.0 seconds` and `Connection lost before
  response was received` — so with `--attempts 3` every failed read cost 30
  seconds. Worth stating what this does **not** establish: from this end a
  silent inverter and a tunnel that lost the answer look identical, so a
  timeout is not evidence about the register the way an exception 0x02 is.
  Either way the cost is real. Narrowing a failing block walks a binary tree
  over it, about 29 reads for fifteen registers — free on the first three
  links, a quarter of an hour on the fourth. Four such blocks outran a
  survey's own cap and the run was killed **before writing a document**.
  Hence `blocks.NARROW_BUDGET`, which bounds the whole narrowing phase,
  divides it across the blocks that failed, and marks what it did not reach
  rather than reporting a wide range as if it were narrow. When reading a
  survey taken over a slow link: check for `not narrowed` before believing a
  range, and do not put a timeout-only finding in `scripts/layout.py`.
- **A WiNet-S does not forward input 2612 or 2628** — the sub-controller and
  battery firmware strings. Both refuse with exception 0x02, three attempts
  out of three, and both read perfectly over a cable on the same machine.
  Replicated across two houses, two inverter models (SH8.0RT-V112, SH10RT-20)
  and two dongle firmwares (P043, P040), against two direct-LAN readings where
  all 27 blocks answer — so this is what the dongle does, not what one machine
  does. It is therefore **not** a `layout.ISOLATE` case: isolating them would
  cost every direct-LAN user a per-field read for a dongle's behaviour and
  still leave a dongle user without the fields. It belongs in capability
  gating by transport. The same pairing shows a dongle forwarding **1020 of
  1510** dumped addresses where a cable forwards 1461, twice, to the address.
- **A WiNet-S also answers an empty string where the inverter refuses the
  read.** Measured on one SH10RT-V112 read both ways within six minutes, with
  nothing else polling: input 13249, 13264 and 13279 — the inverter, module
  and battery firmware strings — **fail 3/3 on the inverter's own LAN port**
  and answer through its dongle, with every character 0x00. So `present()`
  maps them to None and the fields are absent either way; the cable refuses
  the read, the dongle invents an empty answer for it. The same pair refuses
  2612 and 2628 through the dongle while the cable reads them, so the two
  paths fail *complementary* sets of blocks. Consequence for capability
  probing: **"the block answered" is not evidence.** A dongle can answer
  without knowing, which is what `ZERO_MEANS_ABSENT` handles for numbers and
  the emptiness check in `present()` handles for strings.
- **A WiNet-S answers 0 where the inverter answers 0xFFFF**, which invents
  capabilities: measured on one inverter read both ways, the dongle granted
  MPPT3, MPPT4 and a second meter channel that its own LAN port correctly
  refused — ten entities reporting zero forever. `ZERO_MEANS_ABSENT` in
  `capabilities.py` is the guard. It costs a real third tracker its entities
  until sunrise, which is affordable only because capabilities are re-probed
  every poll and the entry reloads when they **grow**; nothing ever removes an
  entity, so granting on zero has no recovery at all.
- **An open port 502 is not an inverter, and unit 1 is not always where it
  is.** Both halves measured on 2026-09-09 at one house, by sweeping the /24
  rather than assuming. Of five endpoints answering on 502, four were the two
  inverters and their two dongles — and one of those four answers on unit
  **2**, because a cluster slave's own device address is 2 and unit 1 there
  times out. `identify()` asked unit 1 and gave up, so that inverter was
  reported absent; it now sweeps `IDENTIFY_UNITS` (1, then 2-5) and returns
  which unit answered, paying the extra probes only where the first fails.
  The fifth endpoint was **not a Sungrow at all**: it refuses input 4989 on
  every unit with exception 0x02, ignores the unit id entirely, and answers
  only registers 0-19. So identify by what answers, never by an open port —
  and `identify`'s error names the exception type, because a refusal and a
  timeout lead to different next steps. Nothing answered on **port 503** on
  that subnet, so the iHomeManager still has no measurement at any house.
- **Which unit ids answer depends on the transport.** On one SH8.0RT the SBR
  answered unit 200 on the LAN port and unit **2** through the dongle, while
  the wallbox answered unit 3 *only* through the dongle. One config entry is
  one endpoint, so a house like that may need two entries to see everything.
  Re-measured on the same machine on 2026-09-08, both paths within four
  minutes — the pair is in `doc/device-fingerprints/`. Replicated the same
  day at a second house, on an SH10RT-20 whose SBR answers unit **2** through
  its dongle and nothing at 200.
- **A wallbox with its own LAN cable still has no Modbus endpoint of its
  own.** Measured at that site, where the owner confirms a cable into the
  wallbox: a full sweep of the /24 found Modbus TCP on exactly two addresses,
  the inverter and its dongle. Nothing answered on 503 either, so no
  iHomeManager. The wallbox is reachable **only** as unit 3 behind the
  dongle's endpoint, and never at 248. So a config flow cannot find a wallbox
  by sweeping for it; it has to ask the endpoints it already has.
- **A wallbox is only reachable through the endpoint that already answered.**
  Measured at a site whose wallbox has its own LAN cable: a full sweep of the
  /24 found Modbus TCP on two addresses, the inverter and its dongle, and the
  wallbox answered only as unit 3 behind the dongle -- never at 248, never on
  an address of its own. Its registers are undocumented by Sungrow;
  `doc/wallbox_registers.md` is what three independent measurements agree on,
  and the survey now decodes 32 of them into every fingerprint. One register,
  21313, is nameable by nobody.
- **A WiNet-S serves Modbus over TLS on port 516, and it works.** Measured
  2026-09-09, and it corrects what the web says: this was written up from
  [discussion #571](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/571)
  as an *iHomeManager* port, and it is not one. Swept across a house with
  **no iHomeManager at all** (503 found nothing on the whole /24), 516 was
  open on **both WiNet-S dongles and neither inverter's own LAN port**. So it
  is a dongle feature.

  It is genuinely Modbus, genuinely TLS, and readable: TLS 1.2,
  ECDHE-RSA-AES256-GCM-SHA384, with a Sungrow self-signed certificate
  (`CN=sun`, issuer `CN=OT.SUNGROW`, valid 2024-2054), and a request for
  input 4989 through the tunnel returned `A22A` — the start of the inverter's
  serial. A plain socket on 516 gets the connection accepted and then closed,
  which is why it looks dead without a TLS client.

  **It is not a workaround for what a dongle will not forward.** Inputs 2612
  and 2628 refuse with exception 0x02 over TLS exactly as they do on 502, and
  the SBR's cell block refuses on both. Same firmware behaviour behind a
  different wrapper. Two rows of that comparison read "no answer" and
  `SSLEOFError` and are **not** evidence about the registers — they are
  session exhaustion from opening connections too quickly, which is what a
  Sungrow does.

  **Replicated at a second site on 2026-09-09**, on a different dongle
  firmware: bar12's WiNet-S answers 516 on both of its interfaces, TLS 1.2
  with the same cipher, and a read through the tunnel returned the serial
  that house's fingerprints publish as `anon-81257679535`, plus module
  firmware `WINET-SV200.001.00.P040` — where the first measurement was
  P043-era. (The stand-in, not the serial: a real one does not belong in a
  public file, which is the whole design of the fingerprint documents.) So this is what a WiNet-S does, not what
  one firmware does. Rapid reconnects exhaust it exactly as they do on 502,
  which is worth knowing before reading anything into a failed handshake.

  **The certificate looks shared across devices, and that matters.** Subject
  `CN=sun,OU=sun,O=OT,L=NJ,ST=JS,C=CN`, issuer `CN=OT.SUNGROW`, valid
  2024-10-24 to 2054-10-17 — *identical to the second* on two unrelated
  houses. A thirty-year window and matching timestamps is what a certificate
  baked into a firmware image looks like rather than one generated per unit.
  If so, the private key ships with every dongle and this TLS authenticates
  nothing: it encrypts the link and proves nothing about who is on the other
  end. **Not yet proven**, and the distinction is worth keeping: the two
  hashes that were compared are two *interfaces of one dongle*, which is the
  same device. A certificate hash from a third site would settle it, and is a
  five-second thing to ask a contributor for.

  `collect.py` sweeps 516 and reports it, because the survey has no TLS
  client. Reading it would need one — and, on the evidence above, verifying
  the certificate would achieve nothing.
- **HACS reads the *default branch* unless there is a stable release**, so a
  pre-release-only repository whose integration is not on the default branch
  cannot be added to HACS at all. Read out of HACS's source, not assumed:
  `version_to_download()` in `repositories/base.py` consults
  `data.last_version` -- set only from the first release that is **not** a
  pre-release -- then a user-selected tag, then `default_branch`. It never
  consults `data.prerelease`; `show_beta` only changes which versions are
  offered *after* registration. `repositories/integration.py` then looks for
  the first directory under `custom_components` at that ref and raises
  *"Repository structure for main is not compliant"* when there is none --
  which is this repository exactly, since `main` is the YAML package. So
  "cut a release" is not the same as "available in HACS", and the fix is
  either the default branch or a stable version, never a `show_beta` hint to
  the user.
- **An empty string is a reading of nothing, not a reading of "".** Sungrow
  fills a UTF-8 field it cannot answer with 0x00, and unlike 0xFFFF that is
  not declared per field, so it decodes to `""` and sails through as a value.
  `present()` in `model.py` maps it to None — without it a capability probe
  counts an absent Sungrow battery's firmware string as evidence of one.

## Hard constraint: migration must preserve history

The integration replaces the YAML package, so existing users must keep their
recorder history and their dashboards. Both are keyed by `entity_id`.

The YAML package produces `sensor.total_dc_power`. An integration entity with
`_attr_has_entity_name = True` produces `sensor.<device name>_total_dc_power`.
Get this wrong and years of history and every dashboard card break silently.

The intended shape is a choice at setup: keep the legacy ids, or take modern
ids and migrate the data across. How that works is **settled and asserted**
in `tests/test_recorder_migration.py`; `doc/integration_plan.md` has the
detail. In short:

- A registry rename carries raw history *and* long-term statistics, and a
  `total_increasing` sum keeps climbing across it.
- But a rename onto an id the recorder already knows is **refused** with only
  a log line, which is exactly the YAML case. So the mechanism is to claim the
  legacy `entity_id` at entity creation — history then simply continues, no
  recorder API involved. Modern ids are that plus one rename afterwards.
- Adoption needs the legacy id free in the registry *and* in the state
  machine, or the registry silently appends `_2`.
- **Both directions are reversible.** A rename moves the row, so the round
  trip returns history to the legacy id; where that id is still occupied,
  archive the occupant under another name first. Nothing is copied, nothing
  is deleted. There is no raw-state import API, so staging history in a
  temporary copy is not possible — and not needed.
- Every ported entity must keep the **unit class** and `state_class` of the
  YAML entry it replaces. Get the unit class wrong and long-term statistics
  freeze flat — repeating the last value forever — while raw history keeps
  filling, so nothing looks broken. Check this per entity while porting.

## Hard constraint: a real serial number is never published

**No real device serial goes into anything this repository tracks.** Not a
fingerprint, not a test fixture, not a docstring, not a commit message, not a
comment explaining a bug. This repository is public, and most of the serials
that pass through it belong to **other people** who lent a VPN or sent a
reading.

A serial is a device's identity. Sungrow's own support uses it to identify an
installation, it is printed on the unit's case, and it is the one field in a
fingerprint that could tie a published reading to a household. That is why
the survey was built around removing it rather than around asking people to
be careful:

- every published document carries a **stand-in**, in a field named for what
  it is: `serial_anonymized_hashed`. Derived by hash, so one device always
  maps to one stand-in and files stay diffable, and the shape is preserved so
  the string decoder stays under test;
- the real serial, the host and the exact time go only to `.testdata/`, which
  is gitignored;
- `RAW_DIR` in `probe.py` is **fixed**, so `--save doc/device-fingerprints`
  cannot write a real serial there even when asked to;
- `NEVER_PUBLISH = ("serial",)` filters anything whose *name* mentions a
  serial, values and key lists alike — added after `sungrow_inverter_serial`
  reached a published document's `fields_read_individually`;
- a wallbox's serial sits two registers below the model name, so
  `wallbox.probe_units` reads the **name**, keeping a serial out of a
  capability probe entirely. It is masked at the publishing boundary too,
  after `A25A…` was once published as the words `[16690, 13633]`.

**And the source tree is checked, because for a while it was not.** Those
protections all guard *documents*. Over one session six real serials reached
test fixtures and docstrings — three houses' worth belonging to other people —
and were a `git push` away from publication. Every one was a fixture or an
illustration and not one needed to be real.
`tests/test_no_real_serials.py` now asserts it over every tracked file: it
matches the **shape** of a serial rather than embedding real ones, and
requires each hit to be on a list of strings known to be invented. A new
serial in a fixture fails the suite until somebody adds it there deliberately,
which is the moment to ask where it came from.

So when a test needs a serial, use an obviously fake one — `A123456789`, or
`A987654321` where two must differ. When prose needs to name a device, use
the stand-in its fingerprints publish. Neither costs anything: nothing in
this project depends on a serial being real.

The same applies to **addresses**. A published document carries
`ip_address_last_two_octets` and only when its owner agreed to that; the full
address stays in `.testdata/`. And to **consent**: a stand-in serial is not
consent, so ask an owner before publishing readings from their installation.

## Local-only context

Connection details for the maintainer's own inverter are deliberately **not**
in this repo — it is public. They live in his own `secrets.yaml`
(`sungrow_modbus_host_ip`, `sungrow_modbus_device_address`). Use the simulator
on `localhost:5020` unless you specifically need real hardware.

The container **can** reach a LAN inverter outbound with no setup — the Docker
bridge NATs, so it follows the host's routing. Multicast does not cross it, so
mDNS must run on the host. See `real_hardware` in `doc/development.yaml`.
