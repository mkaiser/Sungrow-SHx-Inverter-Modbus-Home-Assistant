# How the pieces fit together

Six layers, and the interesting thing about them is where the boundaries are
rather than what is in each one. Two of the boundaries are load-bearing:

- **The library owns register knowledge and nothing else.** It never opens a
  socket, never imports Home Assistant, and is testable without either.
- **Home Assistant's own `modbus` integration owns the connection.** One per
  host and port, shared, serialized — which matters because a Sungrow accepts
  very few Modbus sessions at once.

## At runtime

```mermaid
flowchart TD
    user["user<br/>dashboards, automations, scripts, Developer Tools"]
    core["Home Assistant core<br/>entity registry, recorder and statistics<br/>auth: admin / user / read-only"]

    subgraph integration["custom_components/sungrow_modbus &mdash; the integration, delivered by HACS"]
        direction TB
        flow["config_flow<br/>probe, identify, scan the LAN,<br/>ask about entity ids<br/><br/>config_flow_schemas: the forms it shows,<br/>separated from the decisions about showing them"]
        survey["survey &mdash; both parts, one progress bar<br/><br/>part A: probe every capability,<br/>publish a document that carries a<br/>stand-in serial and at most two octets<br/><br/>part B control_test (in the library): write each<br/>control, check the raw word against a hand-typed<br/>scale, watch what the inverter does, put it back<br/><br/>repairs: a run that did not finish restoring<br/>becomes a fix flow somebody can click<br/>download: a signed, short-lived link"]
        coord["coordinator<br/>four for the inverter, one per tier:<br/>realtime 5s, fast 10s, medium 60s, slowest 600s<br/><br/>one more per extra device that answered:<br/>the SBR pack on medium, the wallbox on fast<br/>with its slow blocks every 30th poll"]
        ent["entity<br/>sensor, binary_sensor,<br/>number, switch, select<br/><br/>a diagnostics-only entry: the survey and<br/>control test buttons and three sensors"]
        mig["migration<br/>claim the YAML entity_id,<br/>or take a modern id then rename"]
        svc["services<br/>start_inverter, stop_inverter,<br/>run_control_test: audience set per entry,<br/>admins only by default<br/>run_survey: anyone"]
        diag["diagnostics<br/>the downloadable report"]
        gen["sensor_descriptions.py: source, tested against the entity map<br/>derived/number/switch/select: generated from<br/>the library's derived module and scripts/generate/tables"]
        hand["battery_descriptions.py, wallbox_descriptions.py,<br/>external_descriptions.py<br/>source: none of them is in the entity map"]
        ext["external<br/>add back a generator the Sungrow cannot see,<br/>from entities another integration owns"]
    end

    lib["sungrow_modbus &mdash; the library, installed from PyPI<br/>no Home Assistant imports anywhere<br/><br/>inverter/: device, registers, components (block reads, per tier),<br/>layout (registers read alone), capabilities, faults,<br/>derived and smoothing, export_scale<br/>battery/: the SBR pack &mdash; device, registers, discovery, power<br/>wallbox/: the charge point &mdash; device, registers, discovery, document<br/>top level: addresses, discovery (identify, LAN sweep, reverse DNS),<br/>dump, survey_document, survey, block_test, control_test"]

    subgraph modbus["homeassistant.components.modbus &mdash; owns the connection"]
        direction TB
        newpath["connection.py<br/>modbus-connection, tmodbus backend<br/><br/>ONE connection per host and port,<br/>shared by every unit on it,<br/>serialized behind a lock,<br/>closed when the last entry unloads"]
        oldpath["modbus.py<br/>pymodbus<br/><br/>the legacy YAML platform's path,<br/>which modbus_sungrow.yaml still uses"]
    end

    device["the inverter's endpoint, port 502<br/>inverter on unit 1, or 2 for a cluster slave<br/>SBR on 200 direct, 2 through a WiNet-S<br/>wallbox on 3, through a WiNet-S only<br/><br/>a WiNet-S forwards less than a cable"]
    wbdev["the wallbox's own address, port 516<br/>Modbus inside TLS, unit 248<br/>read only when the wallbox_host option is set"]

    user <--> core
    core <--> integration
    integration -- "async_get_unit gives back a ModbusUnit" --> newpath
    integration -- "SungrowInverter takes that unit" --> lib
    lib -- "reads and writes registers through it" --> newpath
    newpath -- "TCP" --> device
    newpath -- "TLS" --> wbdev
    oldpath -- "TCP, a second connection to the same inverter" --> device
```

Two backends ship inside core's one `modbus` integration, and the YAML package
rides the other one. That is not a curiosity: it is why running the YAML
package and the integration at the same time produces `Connection lost`
before a response was received, and why the integration says so in the error
rather than leaving people looking at their network.

## How the modules are cut, and why

The integration is cut along **what a piece decides**, not along size. Three
lines are worth knowing before moving anything across them.

**Decisions and data are separated where the data got big.**
`config_flow_schemas.py` holds the `voluptuous` schemas, the option lists and
the prose Home Assistant renders above them; `config_flow.py` holds the steps
that decide which of those to show. The split keeps the flow readable as flow
logic. `_alpha_placeholders` stays in `config_flow.py` although it only
produces text: it reads `DEVICES_MODE_OFFERED` at call time so a test can
patch the flag there. The same instinct puts the `*_descriptions.py` files
beside the platforms that consume them.

**Anything reachable without Home Assistant lives in the library.** That is why
the control test's engine is `sungrow_modbus.control_test` and not here: it has
to run from a terminal against an inverter with no Home Assistant anywhere, and
the Home Assistant half of it is only a snapshot store, a shutdown hook, a
progress callback and the options that say what a run may do.

**One thing is polled by one coordinator, and coordinators that differ only in
a noun share a base.** `SungrowSubDeviceCoordinator` holds what the SBR pack
and the wallbox have in common -- reached through the inverter's connection,
hung off it with `via_device`, identified by *its* serial because neither
reports a usable one, and turning a `ModbusError` into an `UpdateFailed` that
names which device failed. An SBR reports no serial at all; a wallbox's own
(input 21201-21206) is shown as its `serial_number` but never used as the
identifier, and published only as a stand-in. The two subclasses are left
holding only what genuinely differs: how a model name is found, and how often
each block is worth reading.

**`PARALLEL_UPDATES` is 1 on the write platforms, and 0 everywhere else.**
Everything on one endpoint is serialized behind one connection, so two writes
issued at once queue, and the second one's timeout starts while it is still
waiting. And these registers **interlock**: `battery_min_soc` and
`battery_max_soc` are refused if they cross, so their order matters. `sensor`
and `binary_sensor` are 0 because the coordinator polls; `button` is 0
because a press schedules the run and the runner refuses a second.

**And `async_setup_entry` reads as a list of steps.** Connect and identify
(`_async_connect`); build and first-refresh the tier coordinators
(`_async_tier_coordinators`); resolve capabilities from that first poll; probe
for a pack (`_async_battery`) and a wallbox (`_async_wallbox`); register the
inverter's device so a sub-device can hang off it
(`_async_register_inverter`); assemble the runtime data and the survey runner;
drop correction entities the options no longer ask for; claim the legacy ids
(`_async_take_over_legacy_ids`); raise a repair if a control test left
registers changed (`_async_check_control_test`); and forward the platforms --
all five for an ordinary entry, button and sensor for a diagnostics-only one.
Each step is a named function that can be read on its own, which is the only
way a setup path stays reviewable as it grows.

Every option is read during setup, so the update listener reloads the entry on
any change -- except one setup never reads: the export limit's measured write
scale, which the entity stores in `data` mid-write. `_built_from` is what tells
the two apart.

## Three devices, and why the unit ids are not settings

One entry can hold three kinds of device, and **which unit id each answers
on moves with the transport**, so none of them is asked for:

| Device | Unit | Found by |
| --- | --- | --- |
| Inverter | **1**, or **2** for a cluster slave on its own LAN port | `identify()` sweeping 1 to 5. A dongle presents whatever is behind it as unit 1 regardless, so the address is only the role on a direct path |
| SBR pack | **200** direct, **2** through a WiNet-S | `battery.probe_units`, discriminating against a slave inverter — which also sits at 2 and answers a device type code where a pack does not |
| Wallbox | **3** through a WiNet-S, **248** at its own address over TLS on port 516 | `wallbox.probe_units`, reading the model *name* rather than the code or the serial. Its own address is the `wallbox_host` option, checked by the options flow before it is saved; with it set, the endpoint is not asked as well |

Each extra device gets its **own device registry entry**, hung off the
inverter with `via_device`, identified by the *inverter's* serial plus a
suffix. Neither reports a usable serial of its own: an SBR has none anywhere
in its registers, and a wallbox has one this project deliberately never reads.
So the wallbox's device and entity ids are the same whichever path reaches it,
and moving it from the dongle to its own address keeps its history.

A wallbox never answers through the inverter's own LAN port, and its own
address speaks Modbus only inside TLS on 516, with no port 502 -- so the
config flow's sweep of 502 and 503 does not find it. Sub-devices are probed
again whenever the entry's endpoint changes, so a move from a dongle to a
cable keeps the pack and loses a dongle-carried wallbox unless `wallbox_host`
points at it; the move step says so before it happens.

The pack is polled on the inverter's *medium* interval. The wallbox fires on
the *fast* one and reads only its live block, refreshing identity, ratings and
settings every 30th firing (`SLOW_EVERY`).

## What one config entry is

**One inverter, reached through one endpoint** — a host and a port — plus
the devices discovered on it. That is exactly the set of devices sharing one
serialized connection, which is the only grouping that makes the contention
manageable, and it is why the config flow probes and identifies devices by
what answers rather than by unit id.

The unique id is the inverter's serial; the endpoint is the owner's choice.
Reconfigure, or Add integration finding the same serial at another address,
moves the entry there (`async_step_move`) with every entity id and its history
intact, and refuses an endpoint that answers with a different serial.

An entry is one of two modes (`CONF_MODE`). **Devices** is the integration:
entities, migration, controls. **Diagnostics only** connects, identifies and
polls, but creates only the survey and control test buttons and three survey
sensors -- enough for a device page -- and never asks the entity-id question.
It can be promoted from the options flow. While `DEVICES_MODE_OFFERED` is
`False`, new entries can only be diagnostics: the menu still offers devices
mode and its step explains why it is not yet available, and the promotion
toggle is greyed.

## At build time

The inverter's register map and its sensor descriptions are source, held by
tests to the record of what the YAML package produces. A mistyped address or a
scale off by ten gives a plausible-looking wrong number, which is the failure
this project can least afford, so every field is checked against that record
rather than trusted.

```mermaid
flowchart LR
    map["doc/legacy_entity_map.json<br/>record of the YAML package:<br/>entity_id, unique_id, unit, state class"]

    subgraph tables["scripts/generate/tables: judgement, one fact per table"]
        direction TB
        writes["writes.py<br/>what is writable,<br/>and what is held back"]
        naming["naming.py<br/>the naming convention"]
    end

    subgraph source["source, edited by hand"]
        direction TB
        regs["src/sungrow_modbus/inverter/registers.py"]
        layout["src/sungrow_modbus/inverter/layout.py<br/>where hardware<br/>contradicts the YAML"]
        sensors["sensor_descriptions.py"]
    end

    subgraph generated["generated, committed, --check in CI"]
        direction TB
        descs["derived, number, switch<br/>and select descriptions"]
        strings["strings.json<br/>translations/en.json"]
    end

    map -. "tests" .-> regs
    map -. "tests" .-> sensors
    layout -. "tests" .-> regs
    writes -. "tests" .-> regs
    map --> descs
    writes --> descs
    naming --> strings
    descs --> strings
    sensors --> strings
```

A solid arrow is `scripts/generate/descriptions.py`, whose `--check` runs in CI
**and** in pytest, so a generated file cannot drift from what it was derived
from. A dotted arrow is a test: `tests/test_registers.py` holds every field of
`registers.py` to its entity-map entry — address, type, scale, word order,
poll interval — and to `layout.py`'s isolation;
`tests/test_sensor_descriptions.py` holds every sensor to the YAML entity it
replaces — legacy name and id, unit, state class, category, component; and
`tests/test_writes.py` holds the writable set to `writes.py`. So a hand edit
is free, and a hand edit that breaks one of those properties fails on its own
commit.

The tables are where judgement lives, and each records why rather than just
what: `writes.py` says why a register is exposed or held back, `naming.py`
states the convention a test then enforces, and `layout.py` carries
measurements from real hardware where the YAML turned out to be wrong about a
register's length or a block's readability.

**The battery and wallbox maps have no entity-map record.** The SBR's
registers are in an opt-in file a user copy-pastes, and the wallbox's are in
no Sungrow document at all, so `battery/registers.py`, `wallbox/registers.py`
and their description modules are checked like this:

| Hand-written | Checked against |
| --- | --- |
| `battery/registers.py` | `legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml`, address and scale per field — all forty of its sensors |
| `wallbox/registers.py` | the raw words and the readings in a committed survey: the document decoder must reproduce the readings, and the components must read the same values from the same words |
| `battery_descriptions.py`, `wallbox_descriptions.py` | every `field` resolves to a real field or property; no key collides across devices |

That is the same discipline as the inverter's map: where nothing generates a
file, a test or a measurement says whether it is right.

## Why the library has no Home Assistant imports

It is a plain Python package on `modbus-connection`, so the register map, the
capability probing, the derived arithmetic and the smoothing all test without
Home Assistant and without an inverter — which is most of the test suite, and
runs in about a second. Core's `sofar` integration is the reference
implementation for this shape.

Inside it, **one subpackage per kind of device** -- `inverter/`, `battery/`,
`wallbox/` -- each holding that device's map (`registers`), the object that
reads it (`device`) and whatever only that device needs: how it is found on a
unit, its capabilities, its derived values. What spans devices sits at the
top: `addresses`, `discovery`, `dump`, the survey (`survey_document`, `survey`)
and the two tests (`block_test`, `control_test`). A change that concerns one
device belongs in its subpackage; a second device that needs it is the cue to
move it up.

It also means the library is useful on its own: `device-survey/scripts/python/probe.py`
drives it directly to survey an installation, with no Home Assistant
anywhere in the process.

The survey is cut the same way. The library holds everything a capability
document is made of -- the probes, the decoded-readings algorithm, each
section's shape and the privacy rules that apply to it (`survey_document.py`,
`survey.py`) -- and prints, prompts and writes nothing. It also holds the **order** a survey
reads in, `survey.async_capability_survey`: each producer hands it a source
that knows how to collect each step -- raw from a terminal, from what the
coordinators already polled in Home Assistant -- and the library takes the
steps in one order and catches a step the link loses, so a dropped dump
costs the dump and not the document. The terminal scripts
add questions, a progress bar, a transcript and the file;
`custom_components/sungrow_modbus/survey_document.py` adds what only Home
Assistant knows: the owner's answers from the entry's options, what its own
coordinators were doing, the progress entity, and the guard on part B. A
change to what a document *says* therefore belongs in `src/`, where both
producers pick it up.

Where time enters a polled value, in `inverter/smoothing.py`, it takes the
clock as an argument rather than reading one — which is what lets a
sixty-second delay be tested without waiting sixty seconds.
