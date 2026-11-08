#!/usr/bin/env python3
"""Lay the entity names out so somebody can judge them.

    python scripts/helpers/review_names.py            # the table, to read
    python scripts/helpers/review_names.py --markdown # the same, for a document
    python scripts/helpers/review_names.py --texts    # every other text, EN and DE

`Todo.md` carries this as an open decision: *are the entity
names final?* With `has_entity_name` a name supplies the entity id, and it
does so **at creation** -- so a rename later leaves an existing install's id
alone and only diverges it from a fresh one, which is a support problem rather
than a data one (`tests/test_entity_naming.py` pins that). Cheap now,
awkward later. `scripts/generate/tables/naming.py` already enforces consistency -- one
spelling of SoC, no name repeating the device's own -- and consistency is not
the question. The question is whether
each name is the right words for the thing, and nothing but a person reading
them can answer that.

Reading `strings.json` is the wrong way to do it: some three hundred names in
alphabetical order, with no units, no domains, no devices and no sight of what
a migrating user currently calls the same reading. So this prints what the
judgement needs -- the modern name, the entity id it produces, the unit, and
the legacy name beside it -- per device, and on the inverter grouped by what
the entity is *about* rather than by domain, because that is how a reader
notices two names for one idea.

The descriptions are imported, the way the platforms import them, rather than
parsed: a description built by a helper or in a loop -- an SG's trackers, an
SBR's modules -- has no call site to parse, and a sheet that silently leaves
them out is the one thing this must not be.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import functools
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generate" / "tables"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from naming import (
    GERMAN,
    GERMAN_TEXTS,
    LEGACY_ONLY_SENSORS,
    NAME_DISCUSSION,
    text_leaves,
)

REPO = Path(__file__).resolve().parents[2]
STRINGS = REPO / "custom_components" / "sungrow_modbus" / "strings.json"
DATASHEET = REPO / "scripts" / "generate" / "tables" / "datasheet_names.json"
LEGACY_MAP = REPO / "doc" / "legacy_entity_map.json"

#: The entity map's layers that are the YAML package itself. The others are
#: what the specification and the diagnoses added, which the YAML never had.
YAML_LAYERS = frozenset({"modbus", "template", "filter"})


@dataclass(frozen=True)
class Device:
    """One device an entry can create, and the name its ids are built on."""

    heading: str
    #: A representative device name. Home Assistant prefixes every entity id
    #: with the slug of the device's name, which is the model unless the
    #: owner named the inverter -- so the prefix differs between houses, and
    #: one real model stands in for all of them.
    example: str
    note: str


INVERTER = Device(
    "Hybrid inverter",
    "SH10RT",
    "The inverter's own device, named after the model unless the owner named it.",
)
BATTERY = Device(
    "SBR battery",
    "SBR096",
    "A device of its own under the inverter, named after the pack its "
    "capacity matches, `Battery` where none does. Per-module entities exist "
    "for the fitted modules only, and are disabled by default.",
)
WALLBOX = Device(
    "Wallbox",
    "AC22E-01",
    "A device of its own under the inverter, named after the model it "
    "reports, `Wallbox` where it reports none.",
)
STRING_INVERTER = Device(
    "SG string inverter",
    "SG5.0RS",
    "An entry of its own, never beside a hybrid. Trackers and phases exist "
    "only where the model serves them, so this is every one a model can have.",
)
DEVICES = (INVERTER, BATTERY, WALLBOX, STRING_INVERTER)


@dataclass(frozen=True)
class Row:
    """One entity, as the review needs to see it."""

    device: Device
    domain: str
    key: str
    name: str
    entity_id: str
    unit: str
    legacy: str
    #: The id the YAML package gave the same entity, which a migrating user
    #: keeps. Empty where the YAML had none.
    legacy_id: str = ""
    #: The German name (`naming.GERMAN`), shipped in `translations/de.json`.
    german: str = ""
    #: Sungrow's name for the register, with its number; empty where the
    #: entity is derived or the device has no Sungrow datasheet.
    datasheet: str = ""


def _slug(name: str) -> str:
    """Return the object id Home Assistant derives from a name."""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", name.lower())).strip("_")


def _descriptions() -> list[tuple[Device, str, object]]:
    """Return (device, domain, description) for everything an entry can create.

    The same tuples, and the same split between devices, as the platforms'
    `async_setup_entry`.
    """
    from custom_components.sungrow_modbus.battery_descriptions import (
        BATTERY_DESCRIPTIONS,
    )
    from custom_components.sungrow_modbus.derived_descriptions import (
        DERIVED_BINARY_SENSORS,
        DERIVED_SENSORS,
    )
    from custom_components.sungrow_modbus.external_descriptions import EXTERNAL_SENSORS
    from custom_components.sungrow_modbus.number_descriptions import NUMBER_DESCRIPTIONS
    from custom_components.sungrow_modbus.select_descriptions import SELECT_DESCRIPTIONS
    from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS
    from custom_components.sungrow_modbus.string_inverter_descriptions import (
        STRING_INVERTER_BINARY_DESCRIPTIONS,
        STRING_INVERTER_DESCRIPTIONS,
    )
    from custom_components.sungrow_modbus.switch_descriptions import SWITCH_DESCRIPTIONS
    from custom_components.sungrow_modbus.time_descriptions import TIME_DESCRIPTIONS
    from custom_components.sungrow_modbus.wallbox_descriptions import (
        WALLBOX_BINARY_DESCRIPTIONS,
        WALLBOX_DESCRIPTIONS,
    )

    groups: tuple[tuple[Device, str, tuple[object, ...]], ...] = (
        (INVERTER, "sensor", (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS)),
        (INVERTER, "sensor", EXTERNAL_SENSORS),
        (INVERTER, "binary_sensor", DERIVED_BINARY_SENSORS),
        (INVERTER, "number", NUMBER_DESCRIPTIONS),
        (INVERTER, "switch", SWITCH_DESCRIPTIONS),
        (INVERTER, "select", SELECT_DESCRIPTIONS),
        (INVERTER, "time", TIME_DESCRIPTIONS),
        (BATTERY, "sensor", BATTERY_DESCRIPTIONS),
        (WALLBOX, "sensor", WALLBOX_DESCRIPTIONS),
        (WALLBOX, "binary_sensor", WALLBOX_BINARY_DESCRIPTIONS),
        (STRING_INVERTER, "sensor", STRING_INVERTER_DESCRIPTIONS),
        (STRING_INVERTER, "binary_sensor", STRING_INVERTER_BINARY_DESCRIPTIONS),
    )
    return [
        (device, domain, description)
        for device, domain, descriptions in groups
        for description in descriptions
    ]


@functools.cache
def _names() -> dict[tuple[str, str], str]:
    """Return {(domain, translation_key): name} from the committed strings.

    Keyed by **both**, because one key can name two entities: nine readings
    are a sensor and a writable number at once -- `battery_max_soc` among
    them -- and keying by the translation key alone silently filed all nine
    under `sensor.`, in a review whose entire subject is the entity id.
    """
    document = json.loads(STRINGS.read_text(encoding="utf-8"))
    names: dict[tuple[str, str], str] = {}
    for domain, entities in document.get("entity", {}).items():
        for key, value in entities.items():
            if isinstance(value, dict) and "name" in value:
                names[(domain, key)] = value["name"]
    return names


#: The buttons have no descriptions, only a translation key each: the diagnosis
#: on every entry, the capability test on a hybrid only (`button.py`).
BUTTONS: tuple[tuple[Device, str], ...] = (
    (INVERTER, "run_diagnosis"),
    (INVERTER, "run_capability_test"),
    (STRING_INVERTER, "run_diagnosis"),
)


def _row(
    device: Device,
    domain: str,
    key: str,
    unit: str,
    legacy: str,
    legacy_id: str = "",
    datasheet: str = "",
) -> Row:
    """Return the row for one entity, its id built as Home Assistant builds it."""
    name = _names().get((domain, key), "(no name in strings.json)")
    entity_id = f"{domain}.{_slug(device.example)}_{_slug(name)}"
    return Row(
        device,
        domain,
        key,
        name,
        entity_id,
        unit,
        legacy,
        legacy_id,
        GERMAN[key],
        datasheet,
    )


@functools.cache
def _registers() -> dict[str, dict[str, tuple[str, int]]]:
    """Return {device table: {field: (space, register)}} for the two inverters.

    Sungrow's register number, the one its datasheets print: the address the
    map holds plus one.
    """
    from sungrow_modbus.hybrid_inverter.registers import COMPONENTS as HYBRID
    from sungrow_modbus.string_inverter.registers import COMPONENTS as STRING

    tables: dict[str, dict[str, tuple[str, int]]] = {}
    for name, components in (("hybrid", HYBRID), ("sg", STRING)):
        fields: dict[str, tuple[str, int]] = {}
        for klass in components.values():
            for field, spec in klass.declared_fields.items():
                fields.setdefault(field, (klass.register_space, spec.address + 1))
        tables[name] = fields
    return tables


def _datasheet(device: Device, field: str | None) -> str:
    """Return Sungrow's name for the register an entity reads, and its number.

    Empty for a derived entity and for a device without a Sungrow datasheet;
    a register no datasheet lists says so, because that is worth knowing.
    """
    table = {INVERTER: "hybrid", STRING_INVERTER: "sg"}.get(device)
    if table is None or field is None:
        return ""
    where = _registers()[table].get(field)
    if where is None:
        return ""
    space, register = where
    names: dict[str, str] = json.loads(DATASHEET.read_text(encoding="utf-8"))[table]
    name = names.get(f"{space}:{register}", "*not in the datasheet*")
    return f"{name} ({register})"


def _legacy_ids() -> dict[tuple[str, str], str]:
    """Return {(domain, description key): legacy entity id} for every claim.

    Asked of the migration itself, so the sheet shows the id a migrating user
    actually keeps and cannot disagree with what the migration claims.
    """
    from custom_components.sungrow_modbus.migration import (
        DESCRIPTIONS,
        legacy_entity_id,
    )

    return {
        (domain, description.key): entity_id
        for domain, description in DESCRIPTIONS
        if (entity_id := legacy_entity_id(domain, description)) is not None
    }


def _not_ported() -> list[tuple[str, str]]:
    """Return (entity id, name) for each YAML entity no description claims.

    From the entity map rather than a list, so an entity a change stops
    claiming turns up here instead of vanishing from the sheet.
    """
    claimed = set(_legacy_ids().values())
    entities = json.loads(LEGACY_MAP.read_text(encoding="utf-8"))["entities"]
    return sorted(
        (entity["entity_id"], entity["name"])
        for entity in entities
        if entity["layer"] in YAML_LAYERS
        and entity["domain"] != "attribute"
        and entity["entity_id"] not in claimed
    )


#: What each inverter entity is about, matched in order against its key.
#: Grouped this way because a reader judging names needs the neighbours in
#: view: two names for one idea are invisible in an alphabetical list and
#: obvious here. Only the inverter is split: every other device is small
#: enough to read whole, and is a topic in itself.
TOPICS: tuple[tuple[str, str], ...] = (
    ("battery", "The battery"),
    ("bms", "The battery"),
    ("mppt", "The PV trackers"),
    ("pv", "The PV trackers"),
    ("meter", "The meter"),
    ("grid", "The grid"),
    ("export", "The grid"),
    ("import", "The grid"),
    ("load", "The house"),
    ("consum", "The house"),
    ("backup", "Backup power"),
    ("phase", "Per phase"),
    ("firmware", "Identity and firmware"),
    ("version", "Identity and firmware"),
    ("software", "Identity and firmware"),
    ("serial", "Identity and firmware"),
    ("model", "Identity and firmware"),
    ("device_type", "Identity and firmware"),
    ("ems", "Control"),
    ("power_limit", "Control"),
    ("limitation", "Control"),
    ("start_stop", "Control"),
    ("forced_charging", "Control"),
    ("discharge_window", "Control"),
    ("weekend_discharge", "Control"),
    ("fault", "Faults and alarms"),
    ("alarm", "Faults and alarms"),
    ("temperature", "Temperatures"),
    ("run_", "Actions"),
)

#: Units that make an entity an energy total. Matched on the unit rather than
#: the key, because `total_dc_power` is a power and filed itself under the
#: energy totals by its `total_`.
ENERGY_UNITS = frozenset({"Wh", "kWh", "MWh"})


def _topic(row: Row) -> str:
    """Return the heading an inverter entity belongs under."""
    for fragment, heading in TOPICS:
        if fragment in row.key:
            return heading
    if row.unit in ENERGY_UNITS:
        return "Energy totals"
    if row.unit in {"W", "kW"}:
        return "Power"
    return "Everything else"


def _rows() -> tuple[list[Row], list[tuple[Row, str]]]:
    """Return every reviewable entity, and set the legacy-only sensors aside.

    The second list is sensors modern mode does not create. Their names need
    no judgement at all -- the entity exists only for an entry carrying the
    YAML package's history -- and one of them, `Active power limitation raw`,
    sorts directly beside the binary sensor that replaced it, which is worse
    than useless to somebody reviewing a list.
    """
    legacy_ids = _legacy_ids()
    rows: list[Row] = []
    dropped: list[tuple[Row, str]] = []
    for device, domain, description in _descriptions():
        key = str(getattr(description, "translation_key", None) or description.key)  # type: ignore[attr-defined]
        unit = str(getattr(description, "native_unit_of_measurement", None) or "")
        legacy = str(getattr(description, "legacy_name", None) or "")
        legacy_id = legacy_ids.get((domain, description.key), "")  # type: ignore[attr-defined]
        field = getattr(description, "field", None)
        row = _row(
            device, domain, key, unit, legacy, legacy_id, _datasheet(device, field)
        )
        if device is INVERTER and domain == "sensor" and key in LEGACY_ONLY_SENSORS:
            dropped.append((row, LEGACY_ONLY_SENSORS[key]))
            continue
        rows.append(row)
    rows += [_row(device, "button", key, "", "") for device, key in BUTTONS]
    return rows, dropped


#: What each part of `strings.json` is, for the headings of the texts.
TEXT_GROUPS: dict[str, str] = {
    "config": "Setup flow",
    "options": "Options flow",
    "issues": "Repairs",
    "services": "Actions",
    "exceptions": "Error messages",
    "selector": "Selector options",
    "entity": "Select states",
}


def _quote(label: str, text: str) -> str:
    """Return a text as a block quote, paragraphs and list items kept."""
    lines = text.split("\n")
    lines[0] = f"**{label}** {lines[0]}"
    return "\n".join(f"> {line}".rstrip() for line in lines)


REVIEW_DOC = Path(__file__).resolve().parents[2] / "doc" / "entity_names.md"
TEXTS_DOC = REVIEW_DOC.parents[1] / "plans" / "text_translation_review.md"


def _render(markdown: bool) -> str:
    """Return the review sheet, as markdown or as plain text."""
    out: list[str] = []

    def print(*parts: object, **_kw: object) -> None:  # noqa: A001
        """Collect a line instead of writing it, so the sheet can be compared."""
        out.append(" ".join(str(p) for p in parts))

    rows, dropped = _rows()
    by_device = {
        device: [row for row in rows if row.device is device] for device in DEVICES
    }
    if markdown:
        counts = ", ".join(
            f"{device.heading} {len(by_device[device])}" for device in DEVICES
        )
        print("# The entity names\n")
        print(
            f"**{len(rows)} entities** that modern mode can create ({counts}).\n\n"
            "The **entity id**\ncolumn is what a dashboard and years of "
            "history are keyed to, and a name supplies\nit -- but only at "
            "creation. Rename later and anybody who already has the entity\n"
            "keeps the id they were born with; only the label changes. So the "
            "cost of a late\nrename is **divergence** between houses set up "
            "before and after, not lost\nhistory, and where that matters a "
            "registry rename moves the early one across.\n"
        )
        print(
            "Each id begins with its **device's name**, which differs between "
            "houses; one\nreal model stands in for each device below. "
            "**YAML** and **YAML entity id** are\nwhat the YAML package "
            "calls the same entity: a user who migrates keeps that\nid, and a "
            "fresh install gets the entity id. A **←** marks a YAML name the\n"
            "**English** one differs from.\n"
        )
        print(
            "**Datasheet** is Sungrow's own name for the register, with its "
            "number: the hybrid's\n*Communication Protocol of Residential "
            "Hybrid Inverter* V1.1.11, the SG's *Modbus\nRegister Protokoll* "
            "V1.1.58 (`scripts/generate/tables/datasheet_names.json`). Empty\n"
            "for a derived entity and for the battery and wallbox, which have "
            "no Sungrow\ndatasheet here.\n"
        )
        print(
            "**Deutsch** is the German name for each, decided beside the "
            "English one and\nshipped in `translations/de.json`; entity ids "
            "stay English in every\nlanguage. The names live in `GERMAN` in\n"
            "`scripts/generate/tables/naming.py`, with the German word each "
            "recurring idea\nmust use (`GERMAN_TERMS`). Every other text in "
            "`strings.json` -- the setup and\noptions flows, repairs, actions "
            "and error messages -- is in\n"
            "[text_translation_review.md](../plans/text_translation_review.md), "
            "English above German.\n"
        )
        print(
            "A name with an open question has it **To discuss** under its "
            "table: what the\nentity is and the names to choose from "
            "(`NAME_DISCUSSION` in `naming.py`).\n"
        )
        print(
            f"A further {len(dropped)} sensors exist **only in legacy mode** "
            "and are listed at the\nend. Their ids are the YAML package's, "
            "kept so that history keyed to them\ncarries on, and modern mode "
            "replaces each with something better.\n"
        )

    def discuss(group: list[Row]) -> None:
        """List the open questions on a table's names, beneath it."""
        open_rows = [row for row in group if row.key in NAME_DISCUSSION]
        if not open_rows:
            return
        print("\n**To discuss**\n")
        for row in open_rows:
            print(f"- **{row.name}** / **{row.german}**: {NAME_DISCUSSION[row.key]}")

    def table(group: list[Row], level: str, heading: str) -> None:
        group = sorted(group, key=lambda row: (row.name, row.entity_id))
        if markdown:
            print(f"\n{level} {heading} ({len(group)})\n")
            print(
                "| Datasheet | YAML | English | Deutsch | Entity id | "
                "YAML entity id | Unit |"
            )
            print("| --- | --- | --- | --- | --- | --- | --- |")
            for row in group:
                changed = " **←**" if row.legacy and row.legacy != row.name else ""
                legacy_id = f"`{row.legacy_id}`" if row.legacy_id else ""
                print(
                    f"| {row.datasheet} | {row.legacy}{changed} | {row.name} | "
                    f"{row.german} | `{row.entity_id}` | {legacy_id} | {row.unit} |"
                )
            discuss(group)
            return
        print(f"\n{heading} ({len(group)})")
        print("-" * 72)
        for row in group:
            print(f"  {row.name:<44} {row.unit:<8} {row.entity_id}")
            if row.datasheet:
                print(f"    {'sungrow: ' + row.datasheet}")
            print(f"    {'de: ' + row.german}")
            if row.legacy and row.legacy != row.name:
                print(f"    {'was: ' + row.legacy:<44}  <-- renamed")
            if row.legacy_id:
                print(f"    {'yaml: ' + row.legacy_id}")
            if row.key in NAME_DISCUSSION:
                print(f"    discuss: {NAME_DISCUSSION[row.key]}")

    for device in DEVICES:
        group = by_device[device]
        if markdown:
            print(f"\n## {device.heading} ({len(group)})\n")
            print(f"{device.note} Ids shown for `{device.example}`.")
        else:
            print(f"\n{'=' * 72}\n{device.heading} ({len(group)}), as {device.example}")
        if device is not INVERTER:
            table(group, "###", "Everything")
            continue
        topics: dict[str, list[Row]] = {}
        for row in group:
            topics.setdefault(_topic(row), []).append(row)
        for heading in sorted(topics):
            table(topics[heading], "###", heading)

    # `LEGACY_ONLY_SENSORS` names each replacement as `domain.translation_key`,
    # which is a handle, not an id: shown as the entity it resolves to.
    by_handle = {f"{row.domain}.{row.key}": row for row in rows}

    def replaced_by(handle: str) -> str:
        row = by_handle[handle]
        return f"{row.name} (`{row.entity_id}`)"

    if dropped:
        if markdown:
            print(f"\n## Legacy mode only ({len(dropped)})\n")
            print(
                "Not created in modern mode. Each is a second copy of "
                "something a user\nalready has, so the column on the right "
                "is where the reading went instead,\nwith its modern-mode "
                "id.\n"
            )
            print(
                "| Datasheet | YAML | English | Deutsch | YAML entity id | "
                "Replaced in modern mode by |"
            )
            print("| --- | --- | --- | --- | --- | --- |")
            for row, replacement in sorted(dropped, key=lambda pair: pair[0].name):
                legacy_id = (
                    f"`{row.legacy_id}`" if row.legacy_id else "(not in the YAML)"
                )
                print(
                    f"| {row.datasheet} | {row.legacy} | {row.name} | {row.german} | "
                    f"{legacy_id} | {replaced_by(replacement)} |"
                )
            discuss([row for row, _replacement in dropped])
        else:
            print(f"\nLegacy mode only ({len(dropped)})")
            print("-" * 72)
            for row, replacement in sorted(dropped, key=lambda pair: pair[0].name):
                print(f"  {row.name:<44} -> {replaced_by(replacement)}")

    not_ported = _not_ported()
    if markdown:
        print(f"\n## Not ported ({len(not_ported)})\n")
        print(
            "Entities of the YAML package that the integration does not "
            "create. Why, and\nwhat replaces each, is in "
            "[integration_migration.md](integration_migration.md),\nwhich "
            "also covers the package's scenes and automations: they are not "
            "entities\nof the integration, and go when the file goes.\n"
        )
        print("| Legacy entity id | Legacy name |")
        print("| --- | --- |")
        for entity_id, name in not_ported:
            print(f"| `{entity_id}` | {name} |")
    else:
        print(f"\nNot ported ({len(not_ported)})")
        print("-" * 72)
        for entity_id, name in not_ported:
            print(f"  {entity_id:<44} {name}")

    if not markdown:
        print(f"\n{len(GERMAN_TEXTS)} further texts: run with --texts.")
        renamed = sum(1 for row in rows if row.legacy and row.legacy != row.name)
        print(f"\n{len(rows)} entities in modern mode. Renamed from the YAML:", renamed)

    return "\n".join(out) + "\n"


def _render_texts() -> str:
    """Return every other text of `strings.json`, English above German."""
    out: list[str] = []

    def print(*parts: object, **_kw: object) -> None:  # noqa: A001
        """Collect a line instead of writing it, so the document can be compared."""
        out.append(" ".join(str(p) for p in parts))

    texts = text_leaves(json.loads(STRINGS.read_text(encoding="utf-8")))
    print("# The texts, for review\n")
    print(
        f"**{len(texts)} texts**: everything in `strings.json` that is not an "
        "entity name, by its\npath -- the setup and options flows, repairs, "
        "actions and error messages.\nEach is shown in English and with its "
        "German, which lives in\n"
        "`scripts/generate/tables/german_texts.json` and ships in\n"
        "`translations/de.json`. The entity names are in\n"
        "[entity_names.md](../doc/entity_names.md).\n"
    )
    print(
        "A `{placeholder}` is filled in by the integration and stays as "
        "written; backticks\nand bold are kept.\n"
    )
    heading = ""
    for path, english in texts.items():
        group = TEXT_GROUPS[path.split(".", 1)[0]]
        if group != heading:
            heading = group
            count = sum(
                1 for other in texts if TEXT_GROUPS[other.split(".", 1)[0]] == group
            )
            print(f"\n## {group} ({count})\n")
        print(f"### `{path}`\n")
        print(_quote("EN", english))
        print()
        print(_quote("DE", GERMAN_TEXTS[path]))
        print()
    return "\n".join(out).rstrip("\n") + "\n"


def main() -> int:
    """Print the review sheet, or check the committed copy against it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument(
        "--texts",
        action="store_true",
        help="print the other texts of strings.json, English and German",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the two review documents match what this would write",
    )
    args = parser.parse_args()

    if args.check:
        # Gated because it drifted. The committed sheet claimed **139
        # entities, which is everything modern mode creates** long after the
        # number was 186 -- the wallbox, the pack and the derived values had
        # arrived and nothing compared the file to the code. A document that
        # states a wrong number confidently is worse than no document.
        stale = 0
        for doc, want, flag in (
            (REVIEW_DOC, _render(markdown=True), "--markdown"),
            (TEXTS_DOC, _render_texts(), "--texts"),
        ):
            where = doc.relative_to(doc.parents[1])
            if not doc.exists() or doc.read_text(encoding="utf-8") != want:
                print(
                    f"{where} is stale. Run: python scripts/helpers/"
                    f"review_names.py {flag} > {where}",
                    file=sys.stderr,
                )
                stale += 1
            else:
                print(f"{where} is current")
        return 1 if stale else 0

    if args.texts:
        sys.stdout.write(_render_texts())
        return 0
    sys.stdout.write(_render(markdown=args.markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
