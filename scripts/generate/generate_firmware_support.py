#!/usr/bin/env python3
"""Build the table of which entities each firmware supports, inverter and pack.

    python scripts/generate/generate_firmware_support.py           # write the page
    python scripts/generate/generate_firmware_support.py --check   # or check it

The question it answers is `Todo.md`'s: *do inverters on the same firmware
support the same registers?* So a column is a **platform and firmware**
(`SAPPHIRE-H B001.V000.P023`), every model seen on it pooled, and a row is an
entity the integration can create on the inverter. Where the models in one
column disagree, the cell says **split** and names them: that is the
assumption failing, and the place to look.

Each diagnosis's raw `register_dump` is replayed through the integration's own
decoding -- the field's address, word count and `nan` -- and its own
`capabilities.probe` and `resolve`, so a cell says what that device answered
for the registers the entity reads, not what a hand-kept list claims. A
column is split by transport, because a WiNet-S refuses some blocks and
answers 0 where the inverter answers "unavailable": a difference the dongle
makes is not the firmware's.

What it cannot see it says so: an address no dump reached is *untested*, not
absent, and a battery or meter a house does not have is *not fitted*, not a
firmware that lacks it.

An SBR or SBH pack gets a table of its own, columned by its BCU firmware: it
is a device on its own unit, with firmware of its own. Its evidence is the
diagnosis's `battery_pack` block, which the library already decoded, rather than
the inverter's dump.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field as dataclass_field
import inspect
from pathlib import Path
import re
import sys
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts" / "helpers"))
sys.path.insert(0, str(REPO / "scripts" / "generate"))

from generate_compatibility import _model, _reports  # noqa: E402
from modbus_connection import ModbusExceptionError  # noqa: E402
from modbus_connection.model import Component  # noqa: E402
import review_names  # noqa: E402

from sungrow_modbus import Capability  # noqa: E402
from sungrow_modbus.battery.device import PUBLISHED_NAMES  # noqa: E402
from sungrow_modbus.battery.power import model_for_capacity  # noqa: E402
from sungrow_modbus.capability_test import coverage, procedure  # noqa: E402
from sungrow_modbus.diagnosis_document import OUTPUT_TYPES, capability_test_block  # noqa: E402
from sungrow_modbus.dump import DUMP_BANDS, DUMP_MASKED  # noqa: E402
from sungrow_modbus.hybrid_inverter import capabilities, components, layout, registers  # noqa: E402
from sungrow_modbus.model import SETTLES_NOTHING, present  # noqa: E402

OUTPUT = REPO / "doc" / "firmware_support.md"

#: Capabilities that say what a house has fitted rather than what the
#: firmware can do. A diagnosis without one marks the entities needing it *not
#: fitted*: a house without a battery is no evidence about battery registers.
WIRING = frozenset(
    {
        Capability.BATTERY,
        Capability.SUNGROW_BATTERY,
        Capability.METER_DIRECT,
        Capability.METER_CHANNEL_2,
    }
)

#: Registers that report a part of the installation, by part. Where a diagnosis
#: lacks the part, a register that does not answer is *not fitted* rather
#: than absent; one that does answer is still evidence. The meter registers
#: carry no `requires` -- the integration creates them everywhere -- so this
#: is the only place a meterless house (a cluster slave, a meter on an EMS)
#: is told from a firmware that lacks the block.
PART_FIELDS: dict[str, frozenset[str]] = {
    "meter": frozenset(
        {
            name
            for name in registers.InverterFastInput.declared_fields
            if name.startswith("meter_")
        }
        | {"meter_active_power", "export_power_raw", "load_power"}
    ),
    "communication module": frozenset({"communication_module_firmware_version"}),
    "Sungrow pack": frozenset(
        {"battery_firmware_version", "sungrow_version_4_sungrow_battery"}
    ),
}

#: The domains an owner writes to, where a confirmed write is worth a mark.
WRITABLE = frozenset({"number", "switch", "select", "time"})

#: One diagnosis's answer for one entity, best first: how a column's diagnoses
#: combine is decided by `_cell`.
YES, ZERO, NO, NOT_FITTED, UNTESTED = "yes", "zero", "no", "not fitted", "untested"

MARKS = {
    YES: "✓",
    ZERO: "0?",
    NO: "✗",
    NOT_FITTED: "\u2013",
    UNTESTED: "",
}


@dataclass(frozen=True)
class Reading:
    """One diagnosis, reduced to what the table needs."""

    label: str
    model: str
    platform: str
    firmware: str
    dongle: bool
    dump: dict[str, dict[str, int | None]]
    capabilities: frozenset[Capability]
    #: The parts of `PART_FIELDS` this house has.
    parts: frozenset[str]
    #: Fields whose write the capability test read back as written, over a cable.
    written: frozenset[str]
    #: The document's capability test block, empty where the run only read.
    capability_test: dict[str, Any] = dataclass_field(default_factory=dict)
    #: The document's `export_scale` block, empty where it was not asked.
    export_scale: dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass(frozen=True)
class Column:
    """One platform and firmware, over one kind of link."""

    platform: str
    firmware: str
    dongle: bool

    @property
    def heading(self) -> str:
        """Return the short heading, the firmware and the link."""
        return f"{self.firmware} {'dongle' if self.dongle else 'direct'}"


def _fields() -> dict[str, tuple[str, Any]]:
    """Return {field name: (register space, field)} over every inverter component."""
    found: dict[str, tuple[str, Any]] = {}
    for module in (registers, components):
        for klass in vars(module).values():
            if (
                inspect.isclass(klass)
                and issubclass(klass, Component)
                and klass is not Component
            ):
                for name, field in klass.declared_fields.items():
                    found.setdefault(name, (klass.register_space, field))
    return found


FIELDS = _fields()


class NotRead(Exception):
    """An address the diagnosis's dump never reached: no evidence either way."""


def _masked(space: str, address: int) -> bool:
    """Whether the dump blanks this address, as it does the serial's words."""
    return any(
        space == masked_space and start <= address < start + count
        for masked_space, start, count in DUMP_MASKED
    )


def _words(dump: dict[str, dict[str, int | None]], name: str) -> list[int | None]:
    """Return the raw words a field occupies, or raise `NotRead`.

    `NotRead` too where the dump cannot speak for the field: an address it
    masks, and a field whose frame comes padded (`layout.COUNTS`), which only
    a read of exactly that count decodes -- a dump's 32-word block and its
    single-address fallback both fail there, on a device that has the data.
    """
    space, field = FIELDS[name]
    band = dump.get(space) or {}
    addresses = range(field.address, field.address + field.count)
    if name in layout.COUNTS or any(_masked(space, a) for a in addresses):
        raise NotRead(name)
    keys = [str(address) for address in addresses]
    if not all(key in band for key in keys):
        raise NotRead(name)
    return [band[key] for key in keys]


def _decode(dump: dict[str, dict[str, int | None]], name: str) -> object:
    """Return a field's value as the integration would see it, or None.

    None where any word went unanswered, where the field's `nan` matched, or
    where a string is all NUL -- the three ways a device says it has nothing
    there. `NotRead` where the dump never asked.
    """
    words = _words(dump, name)
    if any(word is None for word in words):
        return None
    return present(FIELDS[name][1].decode([int(w) for w in words if w is not None]))


def _reader(dump: dict[str, dict[str, int | None]]) -> Callable[[str], object]:
    """Return `capabilities.probe`'s `read`, skipping a field never read."""

    def read(name: str) -> object:
        try:
            return _decode(dump, name)
        except (NotRead, KeyError) as err:
            # probe() skips a capability whose read raises AttributeError.
            raise AttributeError(name) from err

    return read


def _firmware(document: dict, dump: dict[str, dict[str, int | None]]) -> str:
    """Return the platform-prefixed firmware, from 13250 or else from 2582."""
    inverter = (document.get("firmware") or {}).get("inverter")
    if inverter:
        return str(inverter)
    try:
        value = _decode(dump, "sungrow_version_1")
    except NotRead:
        value = None
    return str(value).strip() if value else ""


def _capabilities(
    document: dict, dump: dict[str, dict[str, int | None]], firmware: str
) -> frozenset[Capability]:
    """Return what the integration would grant this device, from its dump."""
    device = document.get("device") or {}
    raw = str(device.get("device_type_code") or "")
    code = int(raw, 16) if raw.startswith("0x") else None
    # Published as words ("single phase"), and 5002 is what lifts or imposes
    # the family table's THREE_PHASE, so it has to reach `resolve` as a code.
    codes = {text: code for code, text in OUTPUT_TYPES.items()}
    output_type = codes.get(str(device.get("output_type")))
    found = capabilities.resolve(
        code, output_type, capabilities.probe(_reader(dump)), firmware
    )
    probes = document.get("capability_probes") or {}
    pack = (probes.get("unit 200 SBR battery module block") or {}).get("state")
    try:
        capacity = _decode(dump, "battery_capacity_high_precision")
    except NotRead:
        capacity = None
    return capabilities.with_sungrow_battery(
        found,
        pack_found=pack == "present",
        capacity_kwh=float(capacity) if isinstance(capacity, int | float) else None,
    )


def _dongle(document: dict) -> bool | None:
    """Return whether a communication module was in the path, None if unknown."""
    verdict = str((document.get("connection") or {}).get("verdict") or "")
    if verdict.startswith("direct"):
        return False
    if verdict.startswith("through"):
        return True
    reported = str((document.get("user_inputs") or {}).get("transport") or "")
    if reported.startswith("direct"):
        return False
    if reported.startswith("winet"):
        return True
    return None


def _parts(
    document: dict, dongle: bool, granted: frozenset[Capability]
) -> frozenset[str]:
    """Return which parts of `PART_FIELDS` the house has, as far as can be told.

    A communication module from the verdict, which names one fitted beside a
    cable; a Sungrow pack from its own unit answering.
    """
    verdict = str((document.get("connection") or {}).get("verdict") or "")
    probes = document.get("capability_probes") or {}
    pack = (probes.get("unit 200 SBR battery module block") or {}).get("state")
    found = set()
    if Capability.METER_DIRECT in granted:
        found.add("meter")
    if dongle or "communication module fitted" in verdict:
        found.add("communication module")
    if pack == "present":
        found.add("Sungrow pack")
    return frozenset(found)


def _written(document: dict, dongle: bool) -> frozenset[str]:
    """Return the fields the capability test wrote and read back as written.

    Over a cable only: through a WiNet-S a read-back can be stale, so only
    the behavioural leg is evidence there, and that is `CONFIRMED_ON_FIRMWARE`.
    """
    test = capability_test_block(document) or {}
    conditions = test.get("conditions") or {}
    if dongle or conditions.get("simulated") or conditions.get("dry_run"):
        return frozenset()
    return frozenset(
        str(entry["field"])
        for entry in test.get("readback") or []
        if entry.get("verdict") == "matched" and entry.get("field")
    )


def _readings() -> tuple[list[Reading], list[str]]:
    """Return every diagnosis that can be placed, and the labels of the rest."""
    readings: list[Reading] = []
    skipped: list[str] = []
    for label, document in _reports():
        dump = document.get("register_dump") or {}
        dongle = _dongle(document)
        firmware = _firmware(document, dump)
        platform, _, version = firmware.partition("_")
        if not dump.get("input") or dongle is None or not version:
            skipped.append(label)
            continue
        granted = _capabilities(document, dump, firmware)
        readings.append(
            Reading(
                label=label,
                model=_model(document)[0],
                platform=platform,
                firmware=version,
                dongle=dongle,
                dump=dump,
                capabilities=granted,
                parts=_parts(document, dongle, granted),
                written=_written(document, dongle),
                capability_test=dict(capability_test_block(document) or {}),
                export_scale=document.get("export_scale") or {},
            )
        )
    return readings, skipped


def _reads(description: object) -> tuple[str, ...]:
    """Return the register fields an entity reads."""
    depends = tuple(getattr(description, "depends_on", ()) or ())
    if depends:
        return depends
    names = [
        getattr(description, "field", None),
        getattr(description, "minute_field", None),
    ]
    return tuple(name for name in names if name and name in FIELDS)


def _capability_answer(reading: Reading, capability: Capability) -> str:
    """Return what a diagnosis says about a capability the integration probes.

    YES where the integration granted it. Otherwise the probe's own registers
    decide between absent and *cannot tell*: an all-zero answer is absent to
    the integration (`ZERO_MEANS_ABSENT`, `MODE_CODES_ONLY`) but is also what
    a real tracker reads at night and what a dongle answers for "unavailable".
    """
    if capability in reading.capabilities:
        return YES
    probe_fields = capabilities.PROBES.get(capability, ())
    try:
        values = [_decode(reading.dump, name) for name in probe_fields]
    except NotRead:
        return UNTESTED
    zero_absent = capability in (
        capabilities.ZERO_MEANS_ABSENT | capabilities.MODE_CODES_ONLY
    )
    if values and zero_absent and all(value == 0 for value in values):
        return ZERO
    return NO


def _answer(reading: Reading, description: object) -> str:
    """Return what one diagnosis says about one entity."""
    fields = _reads(description)
    if not fields:
        return UNTESTED
    required = getattr(description, "requires", None)
    required = capabilities.CONTROL_REQUIRES.get(required, required)
    try:
        values = [_decode(reading.dump, name) for name in fields]
    except NotRead:
        return UNTESTED
    if required in WIRING:
        if required not in reading.capabilities:
            return NOT_FITTED
        answer = YES
    elif required is not None:
        answer = _capability_answer(reading, required)
    else:
        answer = YES
    if answer == YES and any(value is None for value in values):
        answer = NO
    if answer == NO and any(
        name in PART_FIELDS[part] and part not in reading.parts
        for name in fields
        for part in PART_FIELDS
    ):
        return NOT_FITTED
    return answer


def _confirmed(column: Column, readings: list[Reading], description: object) -> bool:
    """Whether a write to this entity is confirmed on this column's firmware."""
    required = getattr(description, "requires", None)
    versions = capabilities.CONFIRMED_ON_FIRMWARE.get(required, frozenset())
    if f"{column.platform}_{column.firmware}" in versions:
        return True
    field = getattr(description, "field", None)
    return any(field in reading.written for reading in readings)


#: How far the diagnosis tests an entity, weakest first.
READ, WRITTEN, WATCHED = "read", "written", "watched"


def _dumped(name: str) -> bool:
    """Whether the raw dump reaches every word of a field and can decode it."""
    if name not in FIELDS or name in layout.COUNTS:
        return False
    space, field = FIELDS[name]
    return all(
        any(
            band_space == space and start <= address < start + count
            for band_space, start, count, _why in DUMP_BANDS
        )
        and not _masked(space, address)
        for address in range(field.address, field.address + field.count)
    )


def _coverage(domain: str, description: object) -> str:
    """Return how far the diagnosis tests an entity, whatever any one house did.

    *read* where the raw dump reaches its registers, so a column can answer
    for it; *written* where the capability test's readback walk writes it and
    checks the raw word; *watched* where a behavioural check writes it and
    judges what the inverter did. Empty where none of them reaches it.
    """
    fields = _reads(description)
    levels = []
    if fields and all(_dumped(name) for name in fields):
        levels.append(READ)
    if domain in WRITABLE:
        own = {
            getattr(description, "field", None),
            getattr(description, "minute_field", None),
        }
        if own & coverage.WRITTEN:
            levels.append(WRITTEN)
        if own & coverage.WATCHED:
            levels.append(WATCHED)
    return " + ".join(levels)


def _cell(answers: list[tuple[Any, str]], write: bool) -> str:
    """Combine one column's diagnoses into a cell.

    Untested and not-fitted readings say nothing about the firmware, so they
    drop out first; what remains either agrees or is a **split**.
    """
    evidence = [(r, a) for r, a in answers if a not in (UNTESTED, NOT_FITTED)]
    if not evidence:
        if any(a == NOT_FITTED for _, a in answers):
            return MARKS[NOT_FITTED]
        return MARKS[UNTESTED]
    states = {a for _, a in evidence}
    if len(states) == 1:
        mark = MARKS[states.pop()]
        return f"{mark} W" if write and mark == MARKS[YES] else mark
    by_state: dict[str, set[str]] = defaultdict(set)
    for reading, answer in evidence:
        by_state[answer].add(reading.model)
    parts = [
        f"{MARKS[state]} {', '.join(sorted(by_state[state]))}"
        for state in (YES, ZERO, NO)
        if state in by_state
    ]
    return "**split**: " + "; ".join(parts)


def _columns(readings: list[Any]) -> dict[Column, list[Any]]:
    """Group the readings by platform, firmware and link, in a stable order."""
    grouped: dict[Column, list[Any]] = defaultdict(list)
    for reading in readings:
        grouped[Column(reading.platform, reading.firmware, reading.dongle)].append(
            reading
        )
    return dict(
        sorted(
            grouped.items(),
            key=lambda kv: (kv[0].platform, kv[0].firmware, kv[0].dongle),
        )
    )


def _rows() -> list[tuple[str, str, str, object]]:
    """Return (topic, domain, name, description) for every inverter entity."""
    names = review_names._names()
    rows = []
    for device, domain, description in review_names._descriptions():
        if device is not review_names.INVERTER:
            continue
        key = str(getattr(description, "translation_key", None) or description.key)  # type: ignore[attr-defined]
        unit = str(getattr(description, "native_unit_of_measurement", None) or "")
        name = names.get((domain, key), key)
        topic = review_names._topic(
            review_names.Row(review_names.INVERTER, domain, key, name, "", unit, "")
        )
        rows.append((topic, domain, name, description))
    return rows


def _escape(text: str) -> str:
    """Return text safe inside a table cell."""
    return text.replace("|", "\\|")


def _matrix(
    columns: dict[Column, list[Reading]],
) -> list[tuple[str, str, list[str]]]:
    """Return (topic, row label, one cell per column) for every inverter entity."""
    matrix = []
    for topic, domain, name, description in _rows():
        write = domain in WRITABLE
        cells = [
            _cell(
                [(r, _answer(r, description)) for r in members],
                write and _confirmed(column, members, description),
            )
            for column, members in columns.items()
        ]
        label = name if domain == "sensor" else f"{name} *({domain})*"
        matrix.append((topic, label, cells))
    return sorted(matrix, key=lambda row: (row[0], row[1]))


def _coverage_by_row() -> dict[tuple[str, str], str]:
    """Return {(topic, row label): coverage} for every inverter entity."""
    return {
        (topic, name if domain == "sensor" else f"{name} *({domain})*"): _coverage(
            domain, description
        )
        for topic, domain, name, description in _rows()
    }


def _exception_names(klass: type) -> set[str]:
    """Return the names of `klass` and every subclass of it."""
    names = {klass.__name__}
    for child in klass.__subclasses__():
        names |= _exception_names(child)
    return names


#: The exception names a diagnosis records that are the device declining, and so
#: evidence the register is not there. Anything else -- a link failure, a busy
#: device, or an older diagnosis that did not record the type -- settles nothing
#: (`.wiki/wiki/concepts/failed-read-is-not-refusal.md`).
REFUSALS = frozenset(
    _exception_names(ModbusExceptionError)
    - {klass.__name__ for klass in SETTLES_NOTHING}
    - {ModbusExceptionError.__name__}
)

#: A per-module field, and the slot it reports.
MODULE_FIELD = re.compile(r"_module_(\d+)$")


@dataclass(frozen=True)
class PackReading:
    """One diagnosis's reading of a battery pack, on the pack's own unit."""

    label: str
    model: str
    platform: str
    firmware: str
    dongle: bool
    values: dict[str, object]
    #: Published component name to the exception it failed with, None where
    #: the diagnosis recorded no type.
    silent: dict[str, str | None]


def _pack_model(capacity: object) -> str:
    """Return the pack's model from the inverter's capacity register."""
    if not isinstance(capacity, int | float):
        return "unknown"
    model = model_for_capacity(float(capacity))
    return model.name if model else f"{capacity:g} kWh, no single model"


def _silent(readings: dict) -> dict[str, str | None]:
    """Return {component: exception name or None} for what did not answer."""
    silent: dict[str, str | None] = {}
    for entry in readings.get("components_that_did_not_answer") or []:
        name, _, rest = str(entry).partition(" (")
        silent[name] = rest.rstrip(")") or None
    return silent


def _pack_readings() -> tuple[list[PackReading], list[str]]:
    """Return the pack readings that can be placed, and the labels of the rest.

    The firmware is the BCU string the inverter reports at 13280. A diagnosis that
    names a pack firmware but read no pack is left out, and one with neither
    is a house without a Sungrow pack.
    """
    readings: list[PackReading] = []
    skipped: list[str] = []
    for label, document in _reports():
        pack = document.get("battery_pack") or {}
        firmware = str((document.get("firmware") or {}).get("battery") or "")
        if not pack and not firmware:
            continue
        platform, _, version = firmware.partition("_")
        unit = pack.get("unit")
        if not pack or not version or unit not in (2, 200):
            skipped.append(label)
            continue
        block = pack.get("readings") or {}
        capacity = ((document.get("readings") or {}).get("values") or {}).get(
            "battery_capacity_high_precision"
        )
        readings.append(
            PackReading(
                label=label,
                model=_pack_model(capacity),
                platform=platform,
                firmware=version,
                dongle=unit == 2,
                values=block.get("values") or {},
                silent=_silent(block),
            )
        )
    return readings, skipped


def _pack_answer(reading: PackReading, description: object) -> str:
    """Return what one diagnosis says about one pack entity."""
    field = str(getattr(description, "field", ""))
    component = PUBLISHED_NAMES[str(getattr(description, "component", ""))]
    if component in reading.silent:
        return NO if reading.silent[component] in REFUSALS else UNTESTED
    if field not in reading.values:
        return UNTESTED
    slot = MODULE_FIELD.search(field)
    if slot and reading.values.get(f"cell_type_module_{slot.group(1)}") == 0:
        # An empty slot reads 0 V; the cell type names the fitted ones.
        return NOT_FITTED
    if reading.values[field] is None:
        return NO
    return YES


def _pack_matrix(
    columns: dict[Column, list[PackReading]],
) -> list[tuple[str, str, list[str]]]:
    """Return ("", row label, one cell per column) for every pack entity, in order."""
    names = review_names._names()
    matrix = []
    for device, domain, description in review_names._descriptions():
        if device is not review_names.BATTERY:
            continue
        key = str(getattr(description, "translation_key", None) or description.key)  # type: ignore[attr-defined]
        cells = [
            _cell([(r, _pack_answer(r, description)) for r in members], write=False)
            for members in columns.values()
        ]
        matrix.append(("", names.get((domain, key), key), cells))
    return matrix


def _firmware_differences(
    columns: list[Column], matrix: list[tuple[str, str, list[str]]]
) -> list[str]:
    """Return the lines naming each entity whose answer moves with firmware.

    Within one platform and one link, so neither the model family nor the
    dongle can be what differs. Untested, not-fitted and cannot-tell cells
    are no answer, and a write mark is not a difference in what the device
    answers.
    """
    groups: dict[tuple[str, bool], list[int]] = defaultdict(list)
    for index, column in enumerate(columns):
        groups[(column.platform, column.dongle)].append(index)
    lines: list[str] = []
    for (platform, dongle), indexes in sorted(groups.items()):
        if len(indexes) < 2:
            continue
        link = "dongle" if dongle else "direct"
        versions = ", ".join(columns[i].firmware for i in indexes)
        moved = []
        for _topic, label, cells in matrix:
            answered = {
                i: cells[i].removesuffix(" W")
                for i in indexes
                if cells[i] not in (MARKS[UNTESTED], MARKS[NOT_FITTED], MARKS[ZERO])
            }
            if len(set(answered.values())) > 1:
                moved.append(
                    f"  - {label}: "
                    + ", ".join(
                        f"{columns[i].firmware} {mark}" for i, mark in answered.items()
                    )
                )
        lines.append(
            f"- **{platform}, {link}** ({versions}): "
            + (f"{len(moved)} differ." if moved else "nothing differs.")
        )
        lines += moved
    return lines or ["- No platform has two firmware versions over one link yet."]


def _summary(
    columns: list[Column], matrix: list[tuple[str, str, list[str]]], what: str
) -> list[str]:
    """Return a part's answer: the split cells, then what moves with firmware."""
    splits = [
        (label, columns[i])
        for _topic, label, cells in matrix
        for i, cell in enumerate(cells)
        if cell.startswith("**split**")
    ]
    lines = ["### What the diagnoses say so far", ""]
    if splits:
        lines += [
            f"**{len(splits)} cell(s) split**: {what} on one firmware disagree.",
            "",
            *(
                f"- {label}, in {column.platform} {column.heading}"
                for label, column in splits
            ),
        ]
    else:
        lines += [
            f"**No cell is split.** Wherever two {what} on one firmware were both",
            "diagnosed, they answered every entity's registers alike, once what a",
            "house has fitted is set aside. The assumption holds on this evidence;",
            f"it is tested only where a column pools more than one of the {what}.",
        ]
    return [
        *lines,
        "",
        "What moves between firmware versions of one platform, over one kind of link:",
        "",
        *_firmware_differences(columns, matrix),
    ]


def _column_key(
    columns: dict[Column, list[Any]],
    prefix: str,
    links: tuple[str, str],
    skipped: list[str],
    why: str,
) -> list[str]:
    """Return a part's column key, and the diagnoses it could not place."""
    lines = [
        "### Columns",
        "",
        "| Column | Platform | Firmware | Link | Models | Diagnoses |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for index, (column, members) in enumerate(columns.items(), 1):
        models = ", ".join(sorted({r.model for r in members}))
        lines.append(
            f"| {prefix}{index} | {column.platform} | {column.firmware} | "
            f"{links[column.dongle]} | {models} | {len(members)} |"
        )
    if skipped:
        lines += ["", f"Left out, {why}:", "", *(f"- `{label}`" for label in skipped)]
    return lines


def _tables(
    matrix: list[tuple[str, str, list[str]]],
    count: int,
    prefix: str,
    covered: Callable[[str, str], str],
) -> list[str]:
    """Return the part's tables, one per topic where the rows carry one."""
    header = (
        "| Entity | Diagnosis | "
        + " | ".join(f"{prefix}{i}" for i in range(1, count + 1))
        + " |"
    )
    rule = "| --- | --- |" + " --- |" * count
    lines: list[str] = []
    current = None
    for topic, label, cells in matrix:
        if topic != current or not lines:
            lines += ["", f"### {topic or 'Entities'}", "", header, rule]
            current = topic
        lines.append(
            f"| {_escape(label)} | {covered(topic, label)} | "
            + " | ".join(cells)
            + " |"
        )
    return lines


#: A tenfold factor, as the measurements table writes it.
TIMES_TEN = "\N{MULTIPLICATION SIGN}10"

#: An effect verdict's mark in the measurements table, in the order shown.
EFFECT_MARKS = {
    procedure.CONFIRMED: "✓",
    procedure.EFFECT_SCALED: TIMES_TEN,
    procedure.SIGN_INVERTED: "±",
    procedure.NO_EFFECT: "✗",
    procedure.INCONCLUSIVE: "?",
}


def _export_factor(reading: Reading) -> int | None:
    """Return how this firmware writes 13074 (10 or 1), None if never asked."""
    conditions = reading.capability_test.get("conditions") or {}
    for block in (reading.export_scale, conditions.get("export_write_scale") or {}):
        factor = block.get("write_units_per_count")
        if factor in (1, 10):
            return int(factor)
    return None


def _agreed(values: list[tuple[Reading, str]]) -> str:
    """Return one cell from per-diagnosis marks: the mark, or a split by model."""
    if not values:
        return ""
    marks = {mark for _, mark in values}
    if len(marks) == 1:
        return marks.pop()
    by_mark: dict[str, set[str]] = defaultdict(set)
    for reading, mark in values:
        by_mark[mark].add(reading.model)
    return "**split**: " + "; ".join(
        f"{mark} {', '.join(sorted(models))}"
        for mark, models in sorted(by_mark.items())
    )


def _tally(verdicts: list[str]) -> str:
    """Return a count per effect verdict, `✓ 3, ? 1`, best first."""
    counts = dict.fromkeys(EFFECT_MARKS.values(), 0)
    for verdict in verdicts:
        if verdict in EFFECT_MARKS:
            counts[EFFECT_MARKS[verdict]] += 1
    return ", ".join(f"{mark} {n}" for mark, n in counts.items() if n)


def _cable_readback(reading: Reading) -> list[dict[str, Any]]:
    """Return the readback rows that are evidence: over a cable, on hardware."""
    conditions = reading.capability_test.get("conditions") or {}
    if reading.dongle or conditions.get("simulated") or conditions.get("dry_run"):
        return []
    return [
        row
        for row in reading.capability_test.get("readback") or []
        if row.get("verdict") not in (None, procedure.SKIPPED)
    ]


def _measured(columns: dict[Column, list[Reading]]) -> list[str]:
    """Return the section of what the capability test measured, per column."""
    count = len(columns)
    header = "| Measurement | " + " | ".join(str(i) for i in range(1, count + 1)) + " |"
    rows: list[tuple[str, list[str]]] = []
    marks = {10: TIMES_TEN, 1: "1:1"}
    rows.append(
        (
            "Export power limit write scale (13074)",
            [
                _agreed(
                    [
                        (r, marks[factor])
                        for r in members
                        if (factor := _export_factor(r)) is not None
                    ]
                )
                for members in columns.values()
            ],
        )
    )
    cells = []
    for members in columns.values():
        rows_read = [row for r in members for row in _cable_readback(r)]
        matched = sum(row.get("verdict") == procedure.MATCH for row in rows_read)
        cells.append(f"{matched}/{len(rows_read)}" if rows_read else "")
    rows.append(("Settings read back as written, over a cable", cells))
    cells = []
    for members in columns.values():
        seconds = [
            float(restart["running_after"])
            for r in members
            if (restart := r.capability_test.get("restart") or {}).get("verdict")
            == procedure.CONFIRMED
            and isinstance(restart.get("running_after"), int | float)
        ]
        if not seconds:
            cells.append("")
        elif round(min(seconds)) == round(max(seconds)):
            cells.append(f"{min(seconds):.0f} s")
        else:
            cells.append(f"{min(seconds):.0f}\u2013{max(seconds):.0f} s")
    rows.append(("Restart: running again after", cells))
    for check in coverage.EFFECT_FIELDS:
        rows.append(
            (
                f"Behaviour: {check}",
                [
                    _tally(
                        [
                            str(effect.get("verdict"))
                            for r in members
                            for effect in r.capability_test.get("effects") or []
                            if effect.get("check") == check
                        ]
                    )
                    for members in columns.values()
                ],
            )
        )
    findings = sorted(
        {
            (index, str(row.get("field")), str(row.get("verdict")))
            for index, members in enumerate(columns.values(), 1)
            for r in members
            for row in _cable_readback(r)
            if row.get("verdict") != procedure.MATCH
        }
    )
    lines = [
        "### What the capability test measured",
        "",
        "Findings about the firmware rather than about one entity, from every",
        "diagnosis whose run had the capability test, in the columns above. The",
        "13074 write scale is asked by a write the device refuses or accepts,",
        "so it holds through a dongle too; a readback counts over a cable only,",
        "because a WiNet-S answers a written register stale. A behaviour cell",
        "counts that check's runs: "
        + ", ".join(f"{mark} {verdict}" for verdict, mark in EFFECT_MARKS.items())
        + ". An empty cell is a column no run measured.",
        "",
        header,
        "| --- |" + " --- |" * count,
        *(f"| {label} | " + " | ".join(cells) + " |" for label, cells in rows),
    ]
    if findings:
        lines += [
            "",
            "Readbacks over a cable that did not match:",
            "",
            *(
                f"- column {index}: `{field}`, {verdict}"
                for index, field, verdict in findings
            ),
        ]
    return lines


def render() -> str:
    """Return the whole page."""
    readings, skipped = _readings()
    columns = _columns(readings)
    matrix = _matrix(columns)
    covered = _coverage_by_row()
    packs, packs_skipped = _pack_readings()
    pack_columns = _columns(packs)
    pack_matrix = _pack_matrix(pack_columns)
    lines = [
        "# Entities by firmware",
        "",
        "**Generated — do not edit.** `scripts/generate/generate_firmware_support.py`",
        "builds this from the diagnoses in",
        "[device-diagnosis/results/](../device-diagnosis/results/),"
        " and CI checks that it",
        "matches. [compatibility.md](compatibility.md) has the diagnoses themselves,",
        "one row each.",
        "",
        "The question: **do devices on the same firmware support the same",
        "registers?** A column is one platform and firmware, every model seen on",
        "it pooled, so a cell marked **split** is a place where models on one",
        "firmware disagree, and names them. A row is an entity the integration",
        "can create: first on the inverter, then on an SBR or SBH battery pack.",
        "The wallbox and SG string inverters are not in this page.",
        "",
        "## Reading the tables",
        "",
        "| Mark | Means |",
        "| --- | --- |",
        "| ✓ | Answered with a value. |",
        "| ✓ W | Answered, and a write was confirmed on this firmware: read back"
        " over a cable by the [capability test]"
        "(../.wiki/wiki/concepts/capability-test.md),"
        " or its effect watched (`CONFIRMED_ON_FIRMWARE`). A writable entity"
        " without the W has not had its write confirmed here. |",
        '| ✗ | Answered "unavailable", refused, or did not answer. |',
        "| 0? | Answered only zeros where the integration reads zero as absent"
        ' (MPPT3 at night, a dongle\'s stand-in for "unavailable"): cannot tell. |',
        f"| {MARKS[NOT_FITTED]} | Not fitted: needs a part (battery, meter,"
        " dual-channel meter, communication module, Sungrow pack, a pack module)"
        " none of these houses has. |",
        "| *(empty)* | Untested: no diagnosis reached these registers, or none can"
        " read them (the masked serial; the padded firmware strings at 2613 and"
        " 2629). |",
        "",
        "The **Diagnosis** column says how far a diagnosis can test the entity on"
        " any inverter, before a column says what one did:",
        "",
        "| Diagnosis | Means |",
        "| --- | --- |",
        f"| {READ} | The raw register dump reaches its registers, so the columns"
        " can answer for it. |",
        f"| {WRITTEN} | The capability test writes it and checks the raw word it"
        " reads back against the specification's scale. |",
        f"| {WATCHED} | A behavioural check of the capability test writes it and"
        " watches what the inverter does. |",
        "| *(empty)* | No part of the diagnosis reaches it: a column can only be"
        " empty there. |",
        "",
        "A **dongle** column was read through a WiNet-S or Logger, which refuses",
        'some blocks and answers 0 where the inverter answers "unavailable";',
        "compare a dongle column with a dongle column.",
        "",
        "## Inverters",
        "",
        "Each diagnosis's raw register dump is replayed through the integration's",
        "own decoding and capability probe, so a cell is what the inverter",
        "answered for the registers that entity reads.",
        "",
        *_summary(list(columns), matrix, "models"),
        "",
        *_column_key(
            columns,
            "",
            ("direct", "dongle"),
            skipped,
            "with no register dump, no firmware or no way to tell the link",
        ),
        "",
        *_measured(columns),
        *_tables(
            matrix, len(columns), "", lambda topic, label: covered[(topic, label)]
        ),
        "",
        "## Battery packs",
        "",
        "A pack is a device on its own unit with firmware of its own, so a column",
        "is its **BCU firmware**, the battery firmware string the inverter reports",
        "at register 13280. Over the inverter's LAN port the pack answers on unit",
        "200; through a WiNet-S, on unit 2. The model is the one the inverter's",
        "capacity register (5639) matches. A cell is the diagnosis's own decoded",
        "reading of the pack: a component the pack refused with an exception is",
        "absent, one lost to the link is untested.",
        "",
        *_summary(list(pack_columns), pack_matrix, "pack models"),
        "",
        *_column_key(
            pack_columns,
            "B",
            ("unit 200 (cable)", "unit 2 (dongle)"),
            packs_skipped,
            "with a battery firmware but no pack reading, or no battery firmware",
        ),
        *_tables(pack_matrix, len(pack_columns), "B", lambda _topic, _label: READ),
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    """Write the page, or check the committed one is current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"{OUTPUT.relative_to(REPO)} is stale.\n"
                "Run scripts/generate/generate_firmware_support.py and commit the "
                "result.",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT.relative_to(REPO)} matches the diagnoses")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
