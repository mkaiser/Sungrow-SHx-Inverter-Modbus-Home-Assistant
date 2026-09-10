# Cross-reference: TCzerny/ha-modbus-manager

A register-by-register comparison against
[TCzerny/ha-modbus-manager](https://github.com/TCzerny/ha-modbus-manager),
read at commit `1faff77`. It is a **template-driven** integration — one YAML
file per device family, no register code — covering fourteen devices, five of
them Sungrow: SHx hybrid, SG string, SBR/SBH battery, AC011E wallbox and
**iHomeManager**.

It matters for three reasons, in ascending order:

1. Its SHx template is derived from this repository's YAML package and says so
   in its first line, so the overlap is not independent evidence. Where it
   *diverges*, though, it usually diverges because somebody measured
   something.
2. It is **MIT**, the same licence as this repository. That is the first
   licence-clean map of the **iHomeManager** — until now the only route was
   Sungrow's own PDF, because the one other project implementing it is
   GPL-3.0. See the register-sources table in
   [integration_plan.md](integration_plan.md).
3. Its `docs/` directory ships **seven Sungrow protocol PDFs**, including
   *Communication Protocol of Residential and Small Industrial Hybrid
   Inverter* **V1.1.16 (2026-07-03)** and both iHomeManager revisions. This
   repository's audit is pinned to **V1.1.11**; five revisions have landed
   since.

Everything below cites register **numbers**, one above the protocol address,
per the convention in [CLAUDE.md](../CLAUDE.md). Findings are tagged by
provenance:

| Tag | Means |
| --- | --- |
| **spec** | Verified here against the V1.1.16 PDF text, not taken on trust |
| **template** | In their template only, absent from V1.1.16 — source unstated |
| **field** | Their issue tracker or a user report, no document behind it |

## Verdict per device

| Device | Ours | Theirs | Net |
| --- | --- | --- | --- |
| SHx inverter | 110 addresses (YAML + library) | 175 | 73 theirs-only, 8 ours-only, **zero decode conflicts** |
| SBR/SBH battery | 40 | 50 | 10 theirs-only, all strings, 9 of them serials |
| AC011E wallbox | 32 | 25 | 8 ours-only, 1 theirs-only, 1 worth checking |
| iHomeManager | 0 | 53 | The whole device |
| Logger1000 | 0 | 0 | Neither project has one |

On the 100-odd addresses both projects read, **space, register, sign and
width agree everywhere.** The only flagged row was notational — `count: 2`
written out for an int32 the library derives. That is a useful negative
result: two independently maintained maps of the same inverter do not
disagree about a single field.

## The inverter

### Confirmed by V1.1.16 and missing here

Four groups, all input registers unless noted, all **spec**:

- **Backup voltage, current and frequency.** 5720-5722 backup current per
  phase (S16, 0.1 A), 5731-5733 backup voltage (U16, 0.1 V), 5734 backup
  frequency (U16, 0.01 Hz). This repository reads backup *power* — 5723-5725
  per phase and 5726 total — and stops there, so an off-grid house can see
  what the backup port delivers but not at what voltage. Same block, same
  capability gate.
- **The fault and alarm bitfields — and the block is far bigger than their
  template shows.** They expose five: 13066 battery fault, 13068 battery
  alarm, 13070 BMS alarm, 13072 BMS protection, 13074 BMS fault 1. V1.1.16
  has **fourteen** consecutive U32s at 13052-13079: grid-side fault, system
  fault 1 and 2, DC-side fault, permanent fault, BDC-side fault, BDC-side
  permanent fault, then those five, then BMS fault 2 (13076) and BMS alarm 2
  (13078). Twenty-eight registers, and **Appendix 4 defines every bit** — six
  pages of it, so the flag names are **spec** rather than the
  **template**-provenance they looked like.

  That makes this a bigger piece than "add five registers", and its own
  decision: ~450 named bits do not map onto Home Assistant entities without a
  choice about representation, and taking five of fourteen because that is
  what a derived template happened to carry would be the wrong cut. Left out
  deliberately — see the open item at the end.

  (Note the space trap again: **input** 13052 is grid-side fault, **holding**
  13052 is the battery's forced charge/discharge power, which this repository
  already writes.)
- **13029 self-consumption of today** (U16, 0.1 %).
- **Holding 13017 forced startup under low SoC standby** (0xAA / 0x55).
  Added in **V1.1.7** — and the audit in `integration_plan.md` counted seven
  register additions between V1.1.2 and V1.1.11 and resolved all seven,
  without this one. It is an eighth. Their template gates it to non-RS
  models.

Two more, lower value but real and **spec**: **holding 33042** charge cutoff
voltage wide-range and **holding 33274** load rated power. Their template
carries both commented out, which is worth reading as a signal.

### The historical energy arrays

**Spec**, and 46 registers of it: monthly PV generation 6227-6238, yearly PV
generation 6258-6280, monthly export 6596-6607, yearly export 6616-6635.
Their template enumerates each month and each year as its own entity, with
the years hard-coded 2019-2029.

Worth having a view on before somebody asks: these are the inverter's own
retained history, and Home Assistant already keeps that in the recorder for
anything it has polled. The case for reading them is a fresh install wanting
history from before the install; the case against is 46 entities that never
change and a year list that expires. If they land here they belong behind an
explicit option, not a capability probe.

### In their template, absent from V1.1.16

These are the interesting ones, because a template is not a document.

- **Holding 33500 master/slave mode, 33501 master/slave role, 33502 slave
  count.** Role decodes 160 master, 161-164 slave 1-4. This bears directly on
  the finding in CLAUDE.md that one endpoint at one house answers on unit
  **2** because a cluster slave's own device address is 2 and unit 1 times
  out. If 33501 reads on that endpoint, `identify()` could *report* that it
  is talking to a slave rather than only discovering it by sweeping
  `IDENTIFY_UNITS`. Unverified against any document and untested here; the
  VPN master/slave pair is the machine that would settle it, and it is a
  two-register read.
- **Holding 33541-33550, a wallbox control block on the inverter.** Charging
  mode (160 fast / 161 PV surplus / 162 quantity and time / 163 user
  defined), charging quantity in kWh, charging duration, user-defined
  charging current, charge start and end time, and surplus-from-grid mode.
  This repository treats the wallbox as read-only and reaches it as a unit
  behind an endpoint. If this block is real it is a **write** path to the
  wallbox through the inverter, which is a different design decision than
  "nothing writes to it".

  Their own documentation qualifies it: with an iHomeManager present,
  "inverter 33540-33549 stay frozen" and the mode lives on the iHM instead.
  So the block would be live only in the RS485-charger-to-inverter topology,
  which is the topology measured at both wallbox houses here.
- **Holding 31204 active power limitation and 31205 active power limit
  ratio**, gated in their template to the single-phase RS models, against
  13089/13090 for RT and T. **Field, and settled against the spec: do not
  follow it.** V1.1.16's remarks column on 13089 and 13090 reads "MG5-12RL
  and SH3-10RL are not supported. SH50~125CX are not supported." The RS
  models are **not** in that exclusion — they are precisely the family their
  template redirects. So 13089/13090, which the library already writes, is
  the documented method for an RS, and the exclusions belong in `ABSENT_IN`
  instead. Recorded here because reading the register rows without the
  remarks column produced the opposite conclusion first.
- **Holding 30230 global MPP scan (manual).**
- **Holding 21263 working mode on the wallbox** — see below.

Their **31222** feed-in limitation value wide-range (U16, 0.01 kW) *is*
**spec**, and this repository already reads it.

### Ours and not theirs

Eight addresses, and the interesting four are the version strings at
**2582, 2597, 2613 and 2629**. Their template does not read any of them —
which is also why nothing in that project has met the padded-frame defect
documented in CLAUDE.md, where registers 2612 and 2628 return an
`mbap_len` of 33 against a `byte_count` of 22 and a strict client rejects the
whole block. They read the firmware strings at 13250/13265/13280 instead,
count 15, exactly as this repository does.

## The specification itself

The bigger find is the PDF, not the template. Against **V1.1.16**:

**`DEVICE_TYPES` is missing fourteen models.** `tests/test_device_types.py`
pins the V1.1.11 appendix at 35 entries and records the seven `SH*K` codes
Sungrow dropped as a decision. Both halves still hold — no name disagrees on
any of the 35, and the seven are still absent from the appendix — but
V1.1.12 through V1.1.16 added:

| Code | Model | MPPT | Strings per MPPT |
| --- | --- | --- | --- |
| 0x0D41 | SH3RL | 2 | 1;1 |
| 0x0D42 | SH3.6RL | 2 | 1;1 |
| 0x0D43 | SH4RL | 2 | 1;1 |
| 0x0D2B | SH5RL | 2 | 1;1 |
| 0x0D2C | SH6RL | 2 | 1;1 |
| 0x0D2D | SH8RL | 3 | 1;1;1 |
| 0x0D2E | SH10RL | 3 | 1;1;1 |
| 0x0D31 | MG7.5RL | 3 | 1;1;1 |
| 0x0D2F | MG12RL | 3 | 1;1;1 |
| 0x0E51 | SH50CX | 10 | 2;2;2;2;2 |
| 0x0E52 | SH80CX | 10 | 2×10 |
| 0x0E39 | SH100CX | 10 | 2×10 |
| 0x0E3A | SH110CX | 10 | 2×10 |
| 0x0E3D | SH125CX | 10 | 2×10 |

The **SH\*CX** series is a new shape, not just new codes: ten MPPTs where
every model this repository knows has two to four, and two strings per MPPT.
The library reads MPPT1-4 and probes 3 and 4 for presence; a CX house would
report a quarter of its trackers. Their template does not map the CX series
either, and says so.

One caveat to carry: **the SH50CX row is internally inconsistent in the
PDF** — MPPT column 10, string list five entries. Their template comment
reads "MPPT 5-10", so they read it the same way. A CX reading would settle
it; do not encode 10 for SH50CX on the strength of that row.

Also in the changelog and worth noting: **V1.1.15 "fix 33274 register range
error"**, so any earlier reading of load rated power is suspect.

### The remarks column

The register tables carry a remarks column, and it is where the per-model
capability facts live. Read out of V1.1.16 and now in `ABSENT_IN`:

| Register | Remark |
| --- | --- |
| 13088 feed-in limitation ratio | MG5-12RL, SH3-10RL, SH50~125CX not supported |
| 13089/13090 active power limitation and ratio | MG5-12RL, SH3-10RL, SH50~125CX not supported — **RS is not excluded** |
| 13200-13207 meter channel 2 | SH3.0-10RS, MG5-12RL, SH3-10RL, SH50~125CX not supported |
| 13250-13369 firmware information | SH3.0-10RS, MG5-12RL, SH3-10RL, SH50~125CX not supported |
| 13017 forced startup | SH50~125CX not supported |
| 13018 PV power limitation | Only SHT supported |
| 13001 DO configuration | SH3.0-10RS not supported; CX uses a dedicated DO for the diesel generator and has no enumeration 3 |
| 33208 forced charging | MG5-12RL, SH3-10RL, SH50~125CX not supported |

Two of those had been recorded here from older, narrower wordings — the YAML's
"MG5-6RL is not supported" and V1.1.9's "MG5-10RL" — which named the models
that existed when they were written. The family list has grown twice since.

And **Note 1**, which is a gate this repository does not model: registers
5603-5607 are "valid only when a three-phase meter is connected. Data is
invalid for single-phase meters." Not absent — *invalid*. A single-phase
meter presumably answers something, so this is not a 0xFFFF case and probing
cannot see it.

### Note 2, which confirms a measurement officially

The remark under the battery fault block:

> If the data is obtained through the RS485 port of the inverter, the address
> is the battery communication address. For example, if 4 batteries in
> parallel are connected, the communication address of the batteries is
> 200-203. If the data is obtained through TCP/IP forwarding via the Ethernet
> port on WiNet, the battery communication address **will be the WiNet
> internal forwarding address**, which is displayed in the "Device List" on
> the embedded Web of WiNet. **Logger is not supported.**

Three things this repository did not have in writing:

1. **The unit id through a dongle is a WiNet-internal forwarding address.**
   CLAUDE.md records this as measured — 200 on a cable, 2 through the dongle,
   at two houses — and notes the earlier "not reachable via WiNet-S at all"
   claim was wrong. Sungrow documents the mechanism, and it is the same
   mechanism the other project's COM1 logger exports show from the inside.
   The design consequence already holds: identify by what answers, never by
   unit id.
2. **Parallel packs are 200-203.** Nothing here reads a second pack; a
   four-pack house is a shape the battery device has never been pointed at.
3. **"Logger is not supported."** A Logger1000 does *not* forward battery
   data, so Milestone 8 gets a whole inverter installation and not the
   batteries behind it. Worth knowing before designing it, and it is exactly
   the kind of thing that would otherwise be discovered by a contributor
   whose battery entities never appear.

## The wallbox

Ours is the fuller map — 32 registers against 25 — which is what a
measurement through a charging session that ended buys over a template.
Theirs adds nothing we lack except one register, and it is a genuine
question:

**Register 21263.** This repository reads it as `rated_current`, U16 0.1 A,
measured at 32.0 A on an AC22E-01, in the **input** space. Their template
writes it as a **holding** select, `Working Mode`, options 0 network / 2 plug
and play / 6 EMS. Different address spaces, so both can be true and probably
are — Sungrow mirrors settings across spaces routinely, and
`integration_plan.md` already records one false collision of exactly this
kind at 13018. But it is one read to confirm, and if holding 21263 is the
working mode then EMS mode is a **precondition** for Modbus control of the
charger, which is worth telling a user in the config flow rather than
letting them discover.

**Register 21313 is still nameable by nobody.** They do not have it.

Their wiring documentation also **explains a measurement here that had no
explanation**. CLAUDE.md records that the wallbox answers as unit 3 behind
the dongle and "never at 248", at a site where the wallbox has its own LAN
cable. Their topology table gives the reason: **248 is the charger's own
RS485 slave id**, reachable only through a serial or RTU-over-TCP gateway
wired to the charger's own RS485 port — never over Modbus TCP, on any
address. And on the charger's own IP, field reports have port 502 closed and
**516 open with TLS**. So the wallbox's LAN jack is for an EMS, not for us;
the two observations that looked like a puzzle are two different transports.

## The battery

Ten registers theirs-only, and **nine of them are serial numbers**: 10711 the
pack serial and 10822-10894 the eight module serials, each a UTF-8 string
entity. Under the hard constraint in CLAUDE.md those do not get read here at
all, let alone published, and `NEVER_PUBLISH` would filter them by name if
they were. Their template creates them as entities on the user's own
instance, which is a different and defensible choice — but it is why the
count differs, not a gap.

The tenth is real and worth taking: **10721, the BCU firmware string.**

Their documentation is where this gets interesting, because it disagrees with
itself and this repository can settle it.

Their SBR template header states `requires_connection_type: ["LAN",
"RS485"]` with `config_flow_note: "Requires LAN or RS485 connection. WiNet-S
is not supported."` — the same claim CLAUDE.md records as measured wrong.
Their own `README_sungrow_sbr_battery.md` then contradicts the template:
"internal address **200** is often forwarded as **2**", with instructions to
read the forwarded id out of the WiNet-S device list, and a note that unit
200 "usually times out even though the battery is reachable". That is exactly
the measurement here, at two houses, on two dongle firmwares. Ours is the
correct claim and theirs is the stale one; the template should be the thing
that changes.

**Where they are ahead of us, on evidence we do not have:** that same
document carries COM1 logger exports from an **SH20T + SBH150 + WiNet-S2**,
showing the dongle polling the pack internally on RTU slave 200 (`FC04`,
start 10665, count 120) and re-exposing a *filtered* subset on the forwarded
TCP unit. Their conclusion — treat a WiNet-S as a summary battery view, and
expect no cell detail at 10756+ or module detail at 10821+ — is the same
conclusion `battery_device.py` reached from the outside by measuring the cell
block refuse through a dongle at one house and answer with zeros at another.
Two independent routes to one finding, and theirs names the mechanism.

The design still differs, in our favour: they gate the cell block on a
`connection_type` the **user declares** at setup, so a user who picks wrong
gets either poll errors or missing entities. `has_cell_data()` probes it
instead, which handles both dongle behaviours and needs nothing from the
user.

Three unmapped candidates from their field reports, offered with "semantics
unconfirmed" and no naming: **10735-10739** a stable metadata block,
**10749-10750** raw diagnostic words, and **19938**, guessed as a BMS current
limit at 0.1 A. All **field**. The scanner here could read all six on the
next SBR survey at no extra cost, which is the cheapest way to find out.

## The iHomeManager

This is the find. The device has never been measured at any house, no
endpoint has ever answered on 503 across four surveyed subnets, and it is the
only remaining unstarted device milestone. Their template is 53 addressed
registers at **slave 247**, and their `docs/` carries the V1.0.1 and V1.0.2
PDFs behind it.

**Identity and inventory:** 8000 device type code, 8001 protocol number
(string), 8003 protocol version (U32), 8005 total devices connected, 8006
devices in fault, 8318 application software version (string).

**Aggregates, which is what an EMS is for:** 8145 total nominal active power,
8147 total battery rated capacity, 8149 battery charge/discharge limit,
8151-8154 battery max/min charge and discharge power, 8155 total active
power, 8157 meter active power, 8159 load power, 8161 battery power, 8163
battery SoC, 8176 grid import energy, 8178 grid export energy. Scales are
0.1 kW / 0.1 kWh / 10 W, coarser than the inverter's own.

**Its meter, GRID.CT:** 8554 output type (0 single, 1 3P4L, 2 3P3L — the same
encoding as inverter 5002), 8555-8557 phase voltages, 8558 grid frequency,
8559-8563 per-phase active power, and a second channel at 8565-8574 for a
PROD.CT.

**Controls:** 8024 EMS mode (0 AI, 1 self-consumption, 2 time plan, 4 VPP, 5
compulsory), 8025 charge/discharge command, 8026 charge/discharge power (U32,
word-swapped), 8028-8031 feed-in limitation enable, value and ratio, 8047
power on/off, 8051-8052 active power limitation and ratio.

**Its EV charger block:** 8552 charging status (1 idle, 2 standby, 3
charging, 6 completed), 8048 charging modes, 8049 charger enable, 8050 grid
power draw — all **spec**. Plus 8594-8600 total and per-phase charger active
power, which is **field**: not in the PDF, found by a live scan in their
issue #86.

Four facts from this that change the design here, not just add registers:

1. **An iHomeManager is not a gateway.** Their template header, quoting
   Sungrow: iHM "only supports system energy dispatch-related data forwarding
   and does not support data forwarding for connected devices (including
   inverters, WiNet-S/S2)". So it is one endpoint with one device on it, and
   it cannot be found by probing units behind an inverter's endpoint. The
   one-entry-per-endpoint model handles that correctly and for free.
2. **Port 502 *or* 503.** CLAUDE.md records the iHM as port 503. Their
   documentation says 502 on some units, 503 "if 502 is busy", SSL off, and
   the installer has to enable Modbus TCP at all. So sweeping 503 was never
   going to be sufficient, and the sweeps that found nothing on 503 are
   weaker evidence than they looked.
3. **Nothing here can recognise one.** Both identification paths ask for the
   inverter serial at input 4990 — `identify()` in
   [probe.py](../scripts/sungrow_scan/probe.py), across units 1-5, and
   `_async_identify` in
   [config_flow.py](../custom_components/sungrow_modbus/config_flow.py),
   which fails with `no_serial_number`. An iHM has no such register and
   would refuse with exception 0x02, indistinguishable to either from the
   not-a-Sungrow endpoint recorded in CLAUDE.md that answers only registers
   0-19. Recognising one needs its own probe: **input 8000, device type
   code, on unit 247**, on 502 as well as 503. That is a small change, and
   it is the one that makes the milestone reachable before anybody has the
   hardware in hand.
4. **No energy counter on the charger block.** Their issue #86 scanned
   8574-8773 during a ~4 kW session and found nothing accumulating, so
   session and lifetime kWh have to be integrated from `charger_active_power`
   rather than read. Also: the protocol's own table of contents lists a
   "§3.4 Charger Control" section that is **missing from the V1.0.2 PDF**, so
   the published read-write table is known to be incomplete.

One register documented and exposed by nobody: **8032, external VPP
heartbeat.**

## The Logger

Nothing to cross-reference. Their repository has no Logger1000/3000/4000
template, and its only "logger" is Python logging. Their wallbox
documentation does use the word for the WiNet-S — "port 502/516 on the WiNet
dongle is a different device: that is the inverter logger" — which is a
naming collision, not a device. Milestone 8 stays where it is, on Sungrow's
*Logger Communication Protocol AW0 1.0.2.9* and
[discussion #262](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/262).

## The SG series

Their `sungrow_sg_dynamic.yaml` maps the SG string inverters — 100 addresses,
of which 78 appear nowhere in the hybrid map. Out of scope, with one thing
worth keeping: it carries **MPPT5-12 at 5117-5137** and **per-string currents
at 7013-7020**. If the SH\*CX series with its ten trackers is ever supported,
that is the shape its MPPT registers are likely to take, and the SG template
is a better starting guess than the hybrid one.

## Corroborations

Independent confirmation of things measured here, from other people's houses:

- The SBR forwarded as unit **2** through a WiNet-S rather than 200, and unit
  200 timing out on that path.
- The wallbox at unit **3** behind the inverter's or the dongle's endpoint.
- A WiNet-S being a **filtering, non-transparent** Modbus proxy rather than a
  bridge — which is the mechanism behind three separate findings in
  CLAUDE.md: the blocks a dongle refuses, the empty strings it invents, and
  the zeros it answers where the inverter says 0xFFFF.
- Sungrow Modbus endpoints allowing roughly **one client per port**, and
  rapid reconnects being refused. Their reason for not implementing TLS on
  516 is that the iHM already holds that session on the charger — the same
  session exhaustion that produced the `SSLEOFError` rows in the TLS
  comparison here.

## Worth reporting back

Four things this repository knows that would save that project real
debugging, all measured and none of it in their tracker:

1. Their **SBR template's "WiNet-S is not supported"** contradicts their own
   README and is wrong; the pack is reachable, under a different unit id.
2. The **padded-frame defect at registers 2612 and 2628** — declared byte
   count 22 against an MBAP length of 33 — and that asking for exactly 15
   registers reconciles them. They do not read those registers, so they have
   not hit it, but they will if they add the version strings.
3. That a **WiNet-S answers 0 where the inverter answers 0xFFFF**, inventing
   MPPT3, MPPT4 and a second meter channel. Their template gates those on a
   user-declared `connection_type`, which will grant them on a dongle that
   lies.
4. That **register 6100 distinguishes a direct connection from a dongle**,
   9/9 — which is the probe that would replace their `connection_type`
   question with a measurement.

## What this changed

Landed with this document:

- **`DEVICE_TYPES` from 42 to 56 entries**, the V1.1.16 appendix plus the
  seven withdrawn SH\*K codes, with `tests/test_device_types.py` re-pinned to
  V1.1.16.
- **`family_for` no longer classifies by code range.** It reads the model name
  out of `DEVICE_TYPES`, because the ranges were built on the assumption that
  "new models land inside those blocks" and the interleaved 0x0D2x block
  falsified it. `Family` gains `RL` and `CX`. Two new tests cover it: one
  asserting every model in the table classifies to *something* — the check
  the range table did not have, which is why nine models resolved to None in
  silence — and one asserting the specific wrong answer a widened MG range
  would have given, that SH5RL to SH10RL are single-phase.
- **`ABSENT_IN` rebuilt from the V1.1.16 remarks column**, including the RS
  correction above — and **one retraction**. MG was listed as having no third
  phase, with no source cited, which is the one line in that table that did
  not quote the comment or remark it came from. Their datasheet-derived model
  table gives `phases: 3` for MG5RL through MG12RL, and Appendix 1 lists MPPT
  and strings but not phases, so the specification does not settle it.
  Register 5002 governs a real device either way; what changed is the claim
  `compatibility.md` publishes about a model nobody has read. **One MG
  fingerprint settles it** — added to the queue below.
- **Nine registers into `SPECIFICATION_ADDITIONS`**: forced startup under low
  SoC (holding 13017), self-consumption of today (13029), and the backup
  port's three currents, three voltages and frequency.
- **An iHomeManager probe.** `identify()` now falls back to input 8000 on unit
  247 where no inverter unit answers, so the device is *findable*. `collect.py`
  reports it and deliberately does **not** survey it — every block the survey
  reads is an inverter's, and pointing them at unit 247 would write a document
  full of refusals. The probe costs one read, and only at an address where
  every inverter unit has already failed.

Deliberately not done:

- **The fault block.** Fourteen U32s and roughly 450 spec-defined bits, which
  needs a representation decision before any of it is worth reading. Taking
  the five another project happens to expose would be the wrong cut.
- **31204/31205**, for the reason above: the spec settles it the other way.
- **The 46 monthly and yearly energy registers**, and the wallbox write path
  at holding 33541-33550 — unverified, and frozen when an iHomeManager is
  present.
- **SH\*CX support beyond the names.** Ten MPP trackers against a register map
  that stops at four, no reading from one, and an appendix row that
  contradicts itself on the tracker count.

Queued as measurements rather than code, because each is one read on hardware
that already exists: **whether an MG\*RL is three-phase**, from register 5002
on any MG at all; master/slave role at holding 33500-33502 against the
master/slave pair; the SBR's BCU firmware string at 10721 and the other
project's three unnamed candidates (10735-10739, 10749-10750, 19938); and
whether holding 21263 on the wallbox is a working-mode setting mirroring the
rated current this repository reads in the input space.
