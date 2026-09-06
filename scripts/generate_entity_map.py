#!/usr/bin/env python3
"""Derive the YAML package's entity map, which the port is built against.

`modbus_sungrow.yaml` is the specification for what the integration has to
reproduce, but it is a 2,400-line configuration file rather than something a
port can be checked against. This turns it into data: for every entity the
package defines, the `entity_id` a user actually has, the `unique_id` it is
registered under, and the properties the replacement must match.

Two of those properties decide whether a migration succeeds, so they are
extracted deliberately rather than incidentally:

* the **entity_id**, because history, dashboards and InfluxDB are all keyed by
  it, and an integration entity that does not claim it starts a new series;
* the **unit and state class**, because a replacement entity in a different
  unit class silently freezes long-term statistics flat while raw history
  keeps filling.

The entity_id is computed with Home Assistant's own `slugify`, not a
re-implementation, because a near-miss here is a silently orphaned history.

    python scripts/generate_entity_map.py            # write the map
    python scripts/generate_entity_map.py --check    # fail if it is stale

The output is committed. It is generated rather than hand-written so it cannot
drift from the YAML, and committed rather than derived at runtime so the
register map stays source rather than configuration.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any

import yaml

from homeassistant.util import slugify

REPO = Path(__file__).resolve().parent.parent
YAML_PACKAGE = REPO / "legacy" / "modbus_sungrow.yaml"
OUTPUT = REPO / "doc" / "legacy_entity_map.json"

#: Properties a replacement entity has to match, or has to know about. Order
#: is the order they appear in the output.
CARRIED = (
    "device_class",
    "state_class",
    "unit_of_measurement",
    "precision",
    "input_type",
    "address",
    "count",
    "data_type",
    "scale",
    "swap",
    "nan_value",
    "scan_interval",
    "write_type",
)


def _load() -> dict[str, Any]:
    """Read the YAML package, tolerating its `!secret` references."""
    loader = yaml.SafeLoader
    loader.add_constructor("!secret", lambda ldr, node: ldr.construct_scalar(node))
    return yaml.load(YAML_PACKAGE.read_text(encoding="utf-8"), Loader=loader)


def _entry(domain: str, layer: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Turn one YAML entity into a map entry."""
    name = str(raw["name"])
    entry: dict[str, Any] = {
        "entity_id": f"{domain}.{slugify(name)}",
        "unique_id": raw.get("unique_id"),
        "name": name,
        "domain": domain,
        "layer": layer,
    }
    for key in CARRIED:
        if key in raw:
            entry[key] = raw[key]
    return entry


def collect() -> list[dict[str, Any]]:
    """Return every entity the YAML package defines, in file order."""
    document = _load()
    entries: list[dict[str, Any]] = []

    for hub in document.get("modbus", []):
        for raw in hub.get("sensors", []) or []:
            entries.append(_entry("sensor", "modbus", raw))
        for raw in hub.get("switches", []) or []:
            entries.append(_entry("switch", "modbus", raw))

    # A top-level `sensor:` block holds the filter platform entities.
    for raw in document.get("sensor", []) or []:
        if isinstance(raw, dict) and "name" in raw:
            entry = _entry("sensor", raw.get("platform", "sensor"), raw)
            if "entity_id" in raw:
                entry["filters_source"] = raw["entity_id"]
            entries.append(entry)

    for block in document.get("template", []) or []:
        for domain, raws in block.items():
            if not isinstance(raws, list):
                continue
            for raw in raws:
                if isinstance(raw, dict) and "name" in raw:
                    entries.append(_entry(domain, "template", raw))

    return entries


def audit(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Report the things that would break a migration if left unnoticed."""
    by_entity_id: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        by_entity_id[entry["entity_id"]].append(entry["name"])

    # Two entities slugifying to one id means Home Assistant appended `_2` to
    # whichever registered second — so the id in this map is wrong for one of
    # them, and adopting it would attach a replacement to the wrong history.
    collisions = {
        entity_id: names for entity_id, names in by_entity_id.items() if len(names) > 1
    }

    missing_unique_id = [e["entity_id"] for e in entries if not e.get("unique_id")]

    # A statistics-bearing entity with no unit cannot be checked for the unit
    # class trap, so it needs looking at by hand.
    unitless_totals = [
        e["entity_id"]
        for e in entries
        if e.get("state_class") in {"total", "total_increasing"}
        and not e.get("unit_of_measurement")
    ]

    return {
        "entities": len(entries),
        "by_layer": {
            layer: sum(1 for e in entries if e["layer"] == layer)
            for layer in sorted({e["layer"] for e in entries})
        },
        "by_domain": {
            domain: sum(1 for e in entries if e["domain"] == domain)
            for domain in sorted({e["domain"] for e in entries})
        },
        "with_state_class": sum(1 for e in entries if e.get("state_class")),
        "entity_id_collisions": collisions,
        "without_unique_id": missing_unique_id,
        "state_class_without_unit": unitless_totals,
    }


def build() -> dict[str, Any]:
    """Return the whole map, ready to be written."""
    entries = collect()
    return {
        "generated_from": YAML_PACKAGE.name,
        "generated_by": "scripts/generate_entity_map.py",
        "summary": audit(entries),
        "entities": entries,
    }


def main() -> int:
    """Write the map, or check that the committed one is current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the committed map differs from what the YAML implies",
    )
    args = parser.parse_args()

    rendered = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not OUTPUT.exists():
            print(f"{OUTPUT} has not been generated yet", file=sys.stderr)
            return 1
        if OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"{OUTPUT.relative_to(REPO)} is stale.\n"
                "Run scripts/generate_entity_map.py and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT.relative_to(REPO)} matches {YAML_PACKAGE.name}")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    summary = build()["summary"]
    print(f"Wrote {OUTPUT.relative_to(REPO)}: {summary['entities']} entities")
    for layer, count in summary["by_layer"].items():
        print(f"  {layer:<10} {count}")
    if summary["entity_id_collisions"]:
        print(f"\n  {len(summary['entity_id_collisions'])} entity_id collision(s):")
        for entity_id, names in summary["entity_id_collisions"].items():
            print(f"    {entity_id}  <- {names}")
    if summary["state_class_without_unit"]:
        print(
            f"\n  {len(summary['state_class_without_unit'])} entities carry a "
            "state class with no unit; check these by hand."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
