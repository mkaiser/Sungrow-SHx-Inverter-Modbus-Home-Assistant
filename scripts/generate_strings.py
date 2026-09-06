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
    from custom_components.sungrow_modbus.derived_descriptions import (
        DERIVED_BINARY_SENSORS,
        DERIVED_SENSORS,
    )
    from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS

    entries = [("sensor", d) for d in (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS)]
    entries += [("binary_sensor", d) for d in DERIVED_BINARY_SENSORS]
    return [
        (domain, d.key, d.legacy_name or d.key.replace("_", " ").capitalize())
        for domain, d in entries
    ]


def names() -> dict[str, dict[str, str]]:
    """Return the modern name of every entity, by domain and translation key."""
    result: dict[str, dict[str, str]] = {}
    for domain, key, legacy in descriptions():
        result.setdefault(domain, {})[key] = modern_name(key, legacy)
    return result


def render() -> str:
    """Return strings.json with its `entity` block regenerated."""
    document = json.loads(STRINGS.read_text(encoding="utf-8"))
    document["entity"] = {
        domain: {key: {"name": name} for key, name in sorted(entries.items())}
        for domain, entries in sorted(names().items())
    }
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
