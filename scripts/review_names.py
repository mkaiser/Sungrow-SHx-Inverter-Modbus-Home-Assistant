#!/usr/bin/env python3
"""Lay the entity names out so somebody can judge them.

    python scripts/review_names.py            # the table, to read
    python scripts/review_names.py --markdown # the same, for a document

`doc/integration_plan.md` carries this as an open decision: *are the entity
names right?* With `has_entity_name` a name supplies the entity id, and it
does so **at creation** -- so a rename later leaves an existing install's id
alone and only diverges it from a fresh one, which is a support problem rather
than a data one (`tests/test_entity_naming.py` pins that). Cheap now,
awkward later. `scripts/naming.py` already enforces consistency -- one
spelling of SoC, no name repeating the device's own -- and consistency is not
the question. The question is whether
each name is the right words for the thing, and nothing but a person reading
them can answer that.

Reading `strings.json` is the wrong way to do it: 160 names in alphabetical
order, with no units, no domains and no sight of what a migrating user
currently calls the same reading. So this prints what the judgement needs --
the modern name, the entity id it produces, the unit, and the legacy name
beside it -- grouped by what the entity is *about* rather than by domain,
because that is how a reader notices two names for one idea.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from naming import LEGACY_ONLY_SENSORS

REPO = Path(__file__).resolve().parent.parent
DESCRIPTIONS = REPO / "custom_components" / "sungrow_modbus"
STRINGS = DESCRIPTIONS / "strings.json"


def _units() -> dict[str, str]:
    """Map every `UnitOfX.MEMBER` written in the descriptions to its value.

    Resolved from Home Assistant where it is importable, and from a written
    table where it is not, so this script keeps running outside the
    devcontainer -- which is the reason it parses the descriptions rather
    than importing them in the first place.
    """
    table = {"PERCENTAGE": "%", "UnitOfTemperature.CELSIUS": "°C"}
    try:
        from homeassistant import const
    except ModuleNotFoundError:  # pragma: no cover - outside the container
        return {
            "UnitOfPower.WATT": "W",
            "UnitOfPower.KILO_WATT": "kW",
            "UnitOfEnergy.WATT_HOUR": "Wh",
            "UnitOfEnergy.KILO_WATT_HOUR": "kWh",
            "UnitOfElectricPotential.VOLT": "V",
            "UnitOfElectricCurrent.AMPERE": "A",
            "UnitOfFrequency.HERTZ": "Hz",
            **table,
        }
    for name in dir(const):
        enum = getattr(const, name)
        if not (
            isinstance(enum, type)
            and issubclass(enum, str)
            and name.startswith("UnitOf")
        ):
            continue
        for member in enum:
            table[f"{name}.{member.name}"] = str(member.value)
    table["PERCENTAGE"] = const.PERCENTAGE
    return table


#: Written once, because it is read for every row.
UNITS = _units()

#: How a name becomes an object id, which is the whole reason this matters.
#: Home Assistant slugifies the *name*, having already prefixed the device.
DEVICE = "sh10rt"


def _slug(name: str) -> str:
    """Return the object id Home Assistant derives from a name."""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", name.lower())).strip("_")


#: Which platform a description class belongs to. Taken from the class name
#: rather than the file, because `derived_descriptions.py` declares both
#: sensors and binary sensors -- and because the platform decides the entity
#: id's prefix, which is the thing this whole review is about.
PLATFORMS: dict[str, str] = {
    "SungrowSensorDescription": "sensor",
    "SungrowBinarySensorDescription": "binary_sensor",
    "SungrowNumberDescription": "number",
    "SungrowSelectDescription": "select",
    "SungrowSwitchDescription": "switch",
}


def _descriptions() -> list[dict]:
    """Return every entity description, read from the source rather than run.

    Importing them would pull in Home Assistant; parsing the call sites gets
    the same fields and keeps this runnable anywhere.
    """
    found: list[dict] = []
    for path in sorted(DESCRIPTIONS.glob("*_descriptions.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func).split(".")[-1]
            if called not in PLATFORMS:
                continue
            entry: dict[str, object] = {
                "source": path.stem,
                "platform": PLATFORMS[called],
            }
            for keyword in node.keywords:
                if keyword.arg is None:
                    continue
                try:
                    entry[keyword.arg] = ast.literal_eval(keyword.value)
                except ValueError:
                    written = ast.unparse(keyword.value)
                    # An enum or a constant. `UnitOfPower.WATT` printed as
                    # "WATT", which somebody reviewing the units reasonably
                    # queried -- Home Assistant shows `W`, because that is the
                    # member's *value*. The member name is an implementation
                    # detail of the constant, and this sheet is read as though
                    # it were the entity.
                    entry[keyword.arg] = UNITS.get(written, written.split(".")[-1])
            if "translation_key" in entry:
                found.append(entry)
    return found


def _names() -> dict[tuple[str, str], str]:
    """Return {(domain, translation_key): name} from the committed strings.

    Keyed by **both**, because one key can name two entities: nine readings
    are a sensor and a writable number at once -- `battery_max_soc` among
    them -- and keying by the translation key alone silently filed all nine
    under `sensor.`, in a review whose entire subject is the entity id.
    """
    import json

    document = json.loads(STRINGS.read_text(encoding="utf-8"))
    names: dict[tuple[str, str], str] = {}
    for domain, entities in document.get("entity", {}).items():
        for key, value in entities.items():
            if isinstance(value, dict) and "name" in value:
                names[(domain, key)] = value["name"]
    return names


#: What each entity is about, matched in order against its key. Grouped this
#: way because a reader judging names needs the neighbours in view: two names
#: for one idea are invisible in an alphabetical list and obvious here.
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
    ("backup", "Backup power"),
    ("phase", "Per phase"),
    ("firmware", "Identity and firmware"),
    ("serial", "Identity and firmware"),
    ("model", "Identity and firmware"),
    ("device_type", "Identity and firmware"),
    ("ems", "Control"),
    ("power_limit", "Control"),
    ("limitation", "Control"),
    ("start_stop", "Control"),
    ("temperature", "Temperatures"),
    ("energy", "Energy totals"),
    ("total_", "Energy totals"),
)


def _topic(key: str) -> str:
    """Return the heading a key belongs under."""
    for fragment, heading in TOPICS:
        if fragment in key:
            return heading
    return "Everything else"


def main() -> int:
    """Print the review sheet."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()

    names = _names()
    rows: dict[str, list[tuple[str, str, str, str, str]]] = {}
    # Sensors modern mode does not create, held back into their own section.
    # Nineteen of these names need no judgement at all -- the entity exists
    # only for an entry carrying the YAML package's history -- and one of
    # them, `Active power limitation raw`, sorts directly beside the binary
    # sensor that replaced it, which is worse than useless to somebody
    # reviewing a list.
    dropped: list[tuple[str, str, str, str, str]] = []
    for entry in _descriptions():
        key = str(entry["translation_key"])
        domain = str(entry["platform"])
        name = names.get((domain, key), "(no name in strings.json)")
        unit = str(entry.get("native_unit_of_measurement") or "")
        legacy = str(entry.get("legacy_name") or "")
        row = (domain, name, f"{domain}.{DEVICE}_{_slug(name)}", unit, legacy)
        if domain == "sensor" and key in LEGACY_ONLY_SENSORS:
            dropped.append((*row[:4], LEGACY_ONLY_SENSORS[key]))
            continue
        rows.setdefault(_topic(key), []).append(row)

    total = sum(len(group) for group in rows.values())
    if args.markdown:
        print("# The entity names, for review\n")
        print(
            f"**{total} entities**, which is everything modern mode creates. "
            "The **entity id**\ncolumn is what a dashboard and years of "
            "history are keyed to, and a name supplies\nit -- but only at "
            "creation. Rename later and anybody who already has the entity\n"
            "keeps the id they were born with; only the label changes. So the "
            "cost of a late\nrename is **divergence** between houses set up "
            "before and after, not lost\nhistory, and where that matters a "
            "registry rename moves the early one across.\n"
        )
        print(
            "The **legacy name** is what a migrating user calls the same "
            "reading today, and\na **←** marks the ones that differ.\n"
        )
        print(
            f"A further {len(dropped)} sensors exist **only in legacy mode** "
            "and are listed at the\nend. Their names need no judgement: "
            "they are the YAML package's, kept so that\nhistory keyed to "
            "them carries on, and modern mode replaces each with something\n"
            "better.\n"
        )
    for heading in sorted(rows):
        group = sorted(rows[heading], key=lambda row: row[1])
        if args.markdown:
            print(f"\n## {heading} ({len(group)})\n")
            print("| Name | Entity id | Unit | Legacy name |")
            print("| --- | --- | --- | --- |")
            for _domain, name, entity_id, unit, legacy in group:
                changed = " **←**" if legacy and legacy != name else ""
                print(f"| {name} | `{entity_id}` | {unit} | {legacy}{changed} |")
            continue
        print(f"\n{heading} ({len(group)})")
        print("-" * 72)
        for _domain, name, entity_id, unit, legacy in group:
            mark = "  <-- renamed" if legacy and legacy != name else ""
            print(f"  {name:<44} {unit:<8} {entity_id}")
            if legacy and legacy != name:
                print(f"    {'was: ' + legacy:<44}{mark}")
    if dropped:
        if args.markdown:
            print(f"\n## Legacy mode only ({len(dropped)})\n")
            print(
                "Not created in modern mode. Each is a second copy of "
                "something a user\nalready has, so the column on the right "
                "is where the reading went instead.\n"
            )
            print("| Name | Entity id | Replaced in modern mode by |")
            print("| --- | --- | --- |")
            for _domain, name, entity_id, _unit, replacement in sorted(
                dropped, key=lambda row: row[1]
            ):
                print(f"| {name} | `{entity_id}` | `{replacement}` |")
        else:
            print(f"\nLegacy mode only ({len(dropped)})")
            print("-" * 72)
            for _domain, name, _entity_id, _unit, replacement in sorted(
                dropped, key=lambda row: row[1]
            ):
                print(f"  {name:<44} -> {replacement}")

    if not args.markdown:
        print(f"\n{total} entities in modern mode. Renamed from the YAML: ", end="")
        print(
            sum(
                1
                for group in rows.values()
                for _d, name, _e, _u, legacy in group
                if legacy and legacy != name
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
