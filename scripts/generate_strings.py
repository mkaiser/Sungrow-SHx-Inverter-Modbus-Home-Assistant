#!/usr/bin/env python3
"""Generate the entity names in `strings.json`, to the convention.

The convention itself, and the reasoning behind it, is in
[scripts/naming.py](naming.py). This applies it to every description the
integration defines and writes the result where Home Assistant reads names
from — `strings.json`, and its English copy under `translations/`.

English is the source language, so `en.json` is a copy rather than a
translation; every other language is a real translation of it, and none of
them is generated here.

    python scripts/generate_strings.py            # write the names
    python scripts/generate_strings.py --check    # fail if they are stale
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from naming import modern_name

REPO = Path(__file__).resolve().parent.parent
COMPONENT = REPO / "custom_components" / "sungrow_modbus"
STRINGS = COMPONENT / "strings.json"
TRANSLATION = COMPONENT / "translations" / "en.json"


def descriptions() -> list[tuple[str, str, str]]:
    """Return (domain, key, legacy name) for every entity the integration has."""
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
    from custom_components.sungrow_modbus.switch_descriptions import SWITCH_DESCRIPTIONS
    from custom_components.sungrow_modbus.wallbox_descriptions import (
        WALLBOX_BINARY_DESCRIPTIONS,
        WALLBOX_DESCRIPTIONS,
    )

    # A specification addition has no legacy name, so its name comes from the
    # entity map, where it was written down from V1.1.11. Falling back to the
    # key instead loses whatever the key cannot carry -- "Feed-in" came out as
    # "Feed in", because a slug has no hyphens.
    added = {
        entity["entity_id"].split(".", 1)[1]: entity["name"]
        for entity in json.loads(
            (REPO / "doc" / "legacy_entity_map.json").read_text(encoding="utf-8")
        )["entities"]
        if entity["layer"] == "specification"
    }

    # The battery's entities go through the same convention as everything
    # else, deliberately. They are hand-written rather than generated, which
    # is exactly the case where a naming rule stops being enforced by
    # accident -- so they are named in `naming.OVERRIDES` like any other
    # exception and checked by `test_naming_convention.py` like any other
    # name.
    entries = [
        ("sensor", d)
        for d in (
            *SENSOR_DESCRIPTIONS,
            *DERIVED_SENSORS,
            *BATTERY_DESCRIPTIONS,
            *WALLBOX_DESCRIPTIONS,
            *EXTERNAL_SENSORS,
        )
    ]
    entries += [
        ("binary_sensor", d)
        for d in (*DERIVED_BINARY_SENSORS, *WALLBOX_BINARY_DESCRIPTIONS)
    ]
    entries += [("number", d) for d in NUMBER_DESCRIPTIONS]
    entries += [("switch", d) for d in SWITCH_DESCRIPTIONS]
    entries += [("select", d) for d in SELECT_DESCRIPTIONS]
    return [
        (
            domain,
            d.key,
            d.legacy_name or added.get(d.key) or d.key.replace("_", " ").capitalize(),
        )
        for domain, d in entries
    ]


def names() -> dict[str, dict[str, str]]:
    """Return the modern name of every entity, by domain and translation key."""
    result: dict[str, dict[str, str]] = {}
    for domain, key, legacy in descriptions():
        result.setdefault(domain, {})[key] = modern_name(key, legacy)
    return result


def option_labels() -> dict[str, dict[str, str]]:
    """Return each select's option labels, from the same table as its values.

    A label and the register value behind it come from one row, so the two
    cannot drift -- which is the whole reason the options are not written into
    strings.json by hand.
    """
    from writes import SELECTS

    return {
        row["key"]: {option["slug"]: option["label"] for option in row["options"]}
        for row in SELECTS
    }


def render() -> str:
    """Return strings.json with its `entity` block regenerated."""
    document = json.loads(STRINGS.read_text(encoding="utf-8"))
    labels = option_labels()
    entity: dict[str, dict[str, dict[str, object]]] = {}
    for domain, entries in sorted(names().items()):
        entity[domain] = {}
        for key, name in sorted(entries.items()):
            block: dict[str, object] = {"name": name}
            if domain == "select" and key in labels:
                block["state"] = labels[key]
            entity[domain][key] = block
    document["entity"] = entity
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    """Write the names, or check the committed ones are current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render()
    if args.check:
        stale = [
            path
            for path in (STRINGS, TRANSLATION)
            if not path.exists() or path.read_text(encoding="utf-8") != rendered
        ]
        if stale:
            print(
                f"{', '.join(str(p.relative_to(REPO)) for p in stale)} is stale.\n"
                "Run scripts/generate_strings.py and commit the result.",
                file=sys.stderr,
            )
            return 1
        print("entity names match the descriptions")
        return 0

    STRINGS.write_text(rendered, encoding="utf-8")
    TRANSLATION.parent.mkdir(parents=True, exist_ok=True)
    TRANSLATION.write_text(rendered, encoding="utf-8")
    print(f"Wrote {sum(len(v) for v in names().values())} entity names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
