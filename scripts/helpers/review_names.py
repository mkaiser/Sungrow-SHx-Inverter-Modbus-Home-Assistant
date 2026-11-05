#!/usr/bin/env python3
"""Lay the entity names out so somebody can judge them.

    python scripts/helpers/review_names.py            # the table, to read
    python scripts/helpers/review_names.py --markdown # the same, for a document

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

from naming import LEGACY_ONLY_SENSORS

REPO = Path(__file__).resolve().parents[2]
STRINGS = REPO / "custom_components" / "sungrow_modbus" / "strings.json"
LEGACY_MAP = REPO / "doc" / "legacy_entity_map.json"

#: The entity map's layers that are the YAML package itself. The others are
#: what the specification and the surveys added, which the YAML never had.
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


#: The buttons have no descriptions, only a translation key each: the survey
#: on every entry, the control test on a hybrid only (`button.py`).
BUTTONS: tuple[tuple[Device, str], ...] = (
    (INVERTER, "run_survey"),
    (INVERTER, "run_control_test"),
    (STRING_INVERTER, "run_survey"),
)


def _row(
    device: Device, domain: str, key: str, unit: str, legacy: str, legacy_id: str = ""
) -> Row:
    """Return the row for one entity, its id built as Home Assistant builds it."""
    name = _names().get((domain, key), "(no name in strings.json)")
    entity_id = f"{domain}.{_slug(device.example)}_{_slug(name)}"
    return Row(device, domain, key, name, entity_id, unit, legacy, legacy_id)


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
        row = _row(device, domain, key, unit, legacy, legacy_id)
        if device is INVERTER and domain == "sensor" and key in LEGACY_ONLY_SENSORS:
            dropped.append((row, LEGACY_ONLY_SENSORS[key]))
            continue
        rows.append(row)
    rows += [_row(device, "button", key, "", "") for device, key in BUTTONS]
    return rows, dropped


REVIEW_DOC = Path(__file__).resolve().parents[2] / "doc" / "entity_name_review.md"


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
        print("# The entity names, for review\n")
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
            "houses; one\nreal model stands in for each device below. The "
            "**legacy name** and **legacy\nentity id** are what the YAML "
            "package calls the same entity: a user who\nmigrates keeps that "
            "id, and a fresh install gets the entity id. A **←**\nmarks a "
            "name that differs.\n"
        )
        print(
            f"A further {len(dropped)} sensors exist **only in legacy mode** "
            "and are listed at the\nend. Their names need no judgement: "
            "they are the YAML package's, kept so that\nhistory keyed to "
            "them carries on, and modern mode replaces each with something\n"
            "better.\n"
        )

    def table(group: list[Row], level: str, heading: str) -> None:
        group = sorted(group, key=lambda row: (row.name, row.entity_id))
        if markdown:
            print(f"\n{level} {heading} ({len(group)})\n")
            print("| Name | Entity id | Unit | Legacy name | Legacy entity id |")
            print("| --- | --- | --- | --- | --- |")
            for row in group:
                changed = " **←**" if row.legacy and row.legacy != row.name else ""
                legacy_id = f"`{row.legacy_id}`" if row.legacy_id else ""
                print(
                    f"| {row.name} | `{row.entity_id}` | {row.unit} | "
                    f"{row.legacy}{changed} | {legacy_id} |"
                )
            return
        print(f"\n{heading} ({len(group)})")
        print("-" * 72)
        for row in group:
            print(f"  {row.name:<44} {row.unit:<8} {row.entity_id}")
            if row.legacy and row.legacy != row.name:
                print(f"    {'was: ' + row.legacy:<44}  <-- renamed")
            if row.legacy_id:
                print(f"    {'yaml: ' + row.legacy_id}")

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
            print("| Name | Legacy entity id | Replaced in modern mode by |")
            print("| --- | --- | --- |")
            for row, replacement in sorted(dropped, key=lambda pair: pair[0].name):
                legacy_id = (
                    f"`{row.legacy_id}`" if row.legacy_id else "(not in the YAML)"
                )
                print(f"| {row.name} | {legacy_id} | {replaced_by(replacement)} |")
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
        renamed = sum(1 for row in rows if row.legacy and row.legacy != row.name)
        print(f"\n{len(rows)} entities in modern mode. Renamed from the YAML:", renamed)

    return "\n".join(out) + "\n"


def main() -> int:
    """Print the review sheet, or check the committed copy against it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify doc/entity_name_review.md matches what this would write",
    )
    args = parser.parse_args()

    if args.check:
        # Gated because it drifted. The committed sheet claimed **139
        # entities, which is everything modern mode creates** long after the
        # number was 186 -- the wallbox, the pack and the derived values had
        # arrived and nothing compared the file to the code. A document that
        # states a wrong number confidently is worse than no document.
        want = _render(markdown=True)
        have = REVIEW_DOC.read_text(encoding="utf-8")
        if want != have:
            print(
                f"{REVIEW_DOC.relative_to(REVIEW_DOC.parents[1])} is stale. "
                "Run: python scripts/helpers/review_names.py --markdown > "
                f"{REVIEW_DOC.relative_to(REVIEW_DOC.parents[1])}",
                file=sys.stderr,
            )
            return 1
        print(f"{REVIEW_DOC.relative_to(REVIEW_DOC.parents[1])} is current")
        return 0

    sys.stdout.write(_render(markdown=args.markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
