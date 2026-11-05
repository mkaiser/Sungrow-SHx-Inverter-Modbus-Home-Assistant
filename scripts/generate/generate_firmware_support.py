#!/usr/bin/env python3
"""Build the table of which inverter entities each firmware supports.

    python scripts/generate/generate_firmware_support.py           # write the page
    python scripts/generate/generate_firmware_support.py --check   # or check it

The question it answers is `Todo.md`'s: *do inverters on the same firmware
support the same registers?* So a column is a **platform and firmware**
(`SAPPHIRE-H B001.V000.P023`), every model seen on it pooled, and a row is an
entity the integration can create on the inverter. Where the models in one
column disagree, the cell says **split** and names them: that is the
assumption failing, and the place to look.

Each survey's raw `register_dump` is replayed through the integration's own
decoding -- the field's address, word count and `nan` -- and its own
`capabilities.probe` and `resolve`, so a cell says what that device answered
for the registers the entity reads, not what a hand-kept list claims. A
column is split by transport, because a WiNet-S refuses some blocks and
answers 0 where the inverter answers "unavailable": a difference the dongle
makes is not the firmware's.

What it cannot see it says so: an address no dump reached is *untested*, not
absent, and a battery or meter a house does not have is *not fitted*, not a
firmware that lacks it.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
import inspect
from pathlib import Path
import sys
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts" / "helpers"))
sys.path.insert(0, str(REPO / "scripts" / "generate"))

from generate_compatibility import _model, _reports  # noqa: E402
from modbus_connection.model import Component  # noqa: E402
import review_names  # noqa: E402

from sungrow_modbus import Capability  # noqa: E402
from sungrow_modbus.dump import DUMP_MASKED  # noqa: E402
from sungrow_modbus.hybrid_inverter import capabilities, components, layout, registers  # noqa: E402
from sungrow_modbus.model import present  # noqa: E402
from sungrow_modbus.survey_document import OUTPUT_TYPES  # noqa: E402

OUTPUT = REPO / "doc" / "firmware_support.md"

#: Capabilities that say what a house has fitted rather than what the
#: firmware can do. A survey without one marks the entities needing it *not
#: fitted*: a house without a battery is no evidence about battery registers.
WIRING = frozenset(
    {
        Capability.BATTERY,
        Capability.SUNGROW_BATTERY,
        Capability.METER_DIRECT,
        Capability.METER_CHANNEL_2,
    }
)

#: Registers that report a part of the installation, by part. Where a survey
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

#: One survey's answer for one entity, best first: how a column's surveys
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
    """One survey, reduced to what the table needs."""

    label: str
    model: str
    platform: str
    firmware: str
    dongle: bool
    dump: dict[str, dict[str, int | None]]
    capabilities: frozenset[Capability]
    #: The parts of `PART_FIELDS` this house has.
    parts: frozenset[str]
    #: Fields whose write the control test read back as written, over a cable.
    written: frozenset[str]


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
    """An address the survey's dump never reached: no evidence either way."""


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
    """Return the fields the control test wrote and read back as written.

    Over a cable only: through a WiNet-S a read-back can be stale, so only
    the behavioural leg is evidence there, and that is `CONFIRMED_ON_FIRMWARE`.
    """
    test = document.get("control_test") or {}
    conditions = test.get("conditions") or {}
    if dongle or conditions.get("simulated") or conditions.get("dry_run"):
        return frozenset()
    return frozenset(
        str(entry["field"])
        for entry in test.get("readback") or []
        if entry.get("verdict") == "matched" and entry.get("field")
    )


def _readings() -> tuple[list[Reading], list[str]]:
    """Return every survey that can be placed, and the labels of those that cannot."""
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
    """Return what a survey says about a capability the integration probes.

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
    """Return what one survey says about one entity."""
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


def _cell(answers: list[tuple[Reading, str]], write: bool) -> str:
    """Combine one column's surveys into a cell.

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


def _columns(readings: list[Reading]) -> dict[Column, list[Reading]]:
    """Group the readings by platform, firmware and link, in a stable order."""
    grouped: dict[Column, list[Reading]] = defaultdict(list)
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
    return lines


def render() -> str:
    """Return the whole page."""
    readings, skipped = _readings()
    columns = _columns(readings)
    matrix = _matrix(columns)
    splits = [
        (label, list(columns)[i])
        for _topic, label, cells in matrix
        for i, cell in enumerate(cells)
        if cell.startswith("**split**")
    ]
    lines = [
        "# Entities by firmware",
        "",
        "**Generated — do not edit.** `scripts/generate/generate_firmware_support.py`",
        "builds this from the surveys in",
        "[device-survey/results/](../device-survey/results/), and CI checks that it",
        "matches. [compatibility.md](compatibility.md) has the surveys themselves,",
        "one row each.",
        "",
        "The question: **do inverters on the same firmware support the same",
        "registers?** A column is one platform and firmware, every model seen on",
        "it pooled, so a cell marked **split** is a place where models on one",
        "firmware disagree, and names them. A row is an entity the integration",
        "can create on the inverter; the battery pack, the wallbox and SG string",
        "inverters are not in this table.",
        "",
        "Each survey's raw register dump is replayed through the integration's",
        "own decoding and capability probe, so a cell is what the device",
        "answered for the registers that entity reads.",
        "",
        "## What the surveys say so far",
        "",
    ]
    if splits:
        lines += [
            f"**{len(splits)} cell(s) split**: models on one firmware disagree.",
            "",
            *(
                f"- {label}, in {column.platform} {column.heading}"
                for label, column in splits
            ),
        ]
    else:
        lines += [
            "**No cell is split.** Wherever two models on one firmware were both",
            "surveyed, they answered every entity's registers alike, once what a",
            "house has fitted is set aside. The assumption holds on this evidence;",
            "it is tested only where a column pools more than one model.",
        ]
    lines += [
        "",
        "What moves between firmware versions of one platform, over one kind of link:",
        "",
        *_firmware_differences(list(columns), matrix),
        "",
        "## Reading the table",
        "",
        "| Mark | Means |",
        "| --- | --- |",
        "| ✓ | Answered with a value. |",
        "| ✓ W | Answered, and a write was confirmed on this firmware: read back"
        " over a cable by the [control test](../.wiki/wiki/concepts/control-test.md),"
        " or its effect watched (`CONFIRMED_ON_FIRMWARE`). A writable entity"
        " without the W has not had its write confirmed here. |",
        '| ✗ | Answered "unavailable", refused, or did not answer. |',
        "| 0? | Answered only zeros where the integration reads zero as absent"
        ' (MPPT3 at night, a dongle\'s stand-in for "unavailable"): cannot tell. |',
        f"| {MARKS[NOT_FITTED]} | Not fitted: needs a part (battery, meter,"
        " dual-channel meter, communication module, Sungrow pack) none of these"
        " houses has. |",
        "| *(empty)* | Untested: no dump reached these registers, or a dump cannot"
        " read them (the masked serial; the padded firmware strings at 2613 and"
        " 2629). |",
        "",
        "A **dongle** column was read through a WiNet-S or Logger, which refuses",
        'some blocks and answers 0 where the inverter answers "unavailable";',
        "compare a dongle column with a dongle column.",
        "",
        "## Columns",
        "",
        "| Column | Platform | Firmware | Link | Models | Surveys |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for index, (column, members) in enumerate(columns.items(), 1):
        models = ", ".join(sorted({r.model for r in members}))
        lines.append(
            f"| {index} | {column.platform} | {column.firmware} | "
            f"{'dongle' if column.dongle else 'direct'} | {models} | {len(members)} |"
        )
    if skipped:
        lines += [
            "",
            "Left out, with no register dump, no firmware or no way to tell the link:",
            "",
            *(f"- `{label}`" for label in skipped),
        ]

    header = (
        "| Entity | " + " | ".join(str(i) for i in range(1, len(columns) + 1)) + " |"
    )
    rule = "| --- |" + " --- |" * len(columns)
    current = None
    for topic, label, cells in matrix:
        if topic != current:
            lines += ["", f"## {topic}", "", header, rule]
            current = topic
        lines.append(f"| {_escape(label)} | " + " | ".join(cells) + " |")
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
        print(f"{OUTPUT.relative_to(REPO)} matches the surveys")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
