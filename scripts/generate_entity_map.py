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


#: Registers the specification defines that the YAML package never read.
#:
#: These are the *only* entities here that do not come from
#: `modbus_sungrow.yaml`, and they are marked `layer: "specification"` so that
#: stays visible: they have no `unique_id` and no legacy entity, because there
#: is no history of them to migrate. Everything downstream — the register map,
#: the entity descriptions, the names, the simulator seed — picks them up from
#: this table exactly as it picks the rest up from the YAML.
#:
#: **Addresses are protocol addresses, one below the register number the
#: specification prints.** Every value below was read from *Communication
#: Protocol of Residential and Small Industrial Hybrid Inverter* **V1.1.16
#: (2026-07-03)** rather than inferred: a guessed scale produces a plausible
#: wrong number, which is the failure this project can least afford.
SPECIFICATION_ADDITIONS: list[dict[str, Any]] = [
    # V1.1.7, reg 13088, U16, 0-1000, 0.1%. Not the same thing as the active
    # power limit ratio at reg 13090, which the YAML already reads: the
    # specification is explicit that feed-in limitation controls the grid
    # connection point and power limiting controls the inverter's AC output.
    {
        "name": "Feed-in limitation ratio",
        "domain": "sensor",
        "input_type": "holding",
        "address": 13087,
        "data_type": "uint16",
        "scale": 0.1,
        "unit_of_measurement": "%",
        "precision": 1,
        "state_class": "measurement",
        "nan_value": 0xFFFF,
        "scan_interval": 10,
    },
    # V1.1.10, reg 13018, U16, 0xAA limit / 0x55 allow. A mode, not a power,
    # and "Only SHT are supported" -- the reference SH10RT answers 0xFFFF.
    {
        "name": "PV power limitation raw",
        "domain": "sensor",
        "input_type": "holding",
        "address": 13017,
        "data_type": "uint16",
        "nan_value": 0xFFFF,
        "scan_interval": 10,
    },
    # V1.1.7, reg 13017, U16, 0xAA forced startup. Note the address: this is
    # one *below* the PV power limitation above, which is reg 13018 -- and
    # input 13017 is a different measurement again, "optimized power of load"
    # in watts. Register and space together, always.
    #
    # Added to the specification in V1.1.7 alongside the seven additions this
    # project's V1.1.11 audit resolved, and missed by that audit. V1.1.16
    # excludes only SH50~125CX.
    {
        "name": "Forced startup under low SoC raw",
        "domain": "sensor",
        "input_type": "holding",
        "address": 13016,
        "data_type": "uint16",
        "nan_value": 0xFFFF,
        "scan_interval": 10,
    },
    # V1.1.16 reg 13029, U16, 0.1%. What share of today's generation was used
    # on site rather than exported. A ratio the inverter keeps itself, not a
    # counter -- so `measurement`, not `total_increasing`.
    {
        "name": "Self-consumption of today",
        "domain": "sensor",
        "input_type": "input",
        "address": 13028,
        "data_type": "uint16",
        "scale": 0.1,
        "unit_of_measurement": "%",
        "precision": 1,
        "state_class": "measurement",
        "nan_value": 0xFFFF,
        "scan_interval": 600,
    },
]

#: The backup port's voltage, current and frequency -- regs 5720-5722 (S16,
#: 0.1 A), 5731-5733 (U16, 0.1 V) and 5734 (U16, 0.01 Hz).
#:
#: The YAML package reads the backup port's **power** at regs 5723-5726 and
#: stops, so an off-grid house can see what the backup output delivers but
#: not at what voltage or frequency. Same block, same battery capability
#: gate; 0x7FFF is the specification's unavailable sentinel for S16 and
#: 0xFFFF for U16.
SPECIFICATION_ADDITIONS += [
    {
        "name": f"Backup phase {phase} current",
        "domain": "sensor",
        "input_type": "input",
        "address": address,
        "data_type": "int16",
        "scale": 0.1,
        "unit_of_measurement": "A",
        "device_class": "current",
        "state_class": "measurement",
        "precision": 1,
        "nan_value": 0x7FFF,
        "scan_interval": 10,
    }
    for phase, address in (("A", 5719), ("B", 5720), ("C", 5721))
]

SPECIFICATION_ADDITIONS += [
    {
        "name": f"Backup phase {phase} voltage",
        "domain": "sensor",
        "input_type": "input",
        "address": address,
        "data_type": "uint16",
        "scale": 0.1,
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "precision": 1,
        "nan_value": 0xFFFF,
        "scan_interval": 10,
    }
    for phase, address in (("A", 5730), ("B", 5731), ("C", 5732))
]

SPECIFICATION_ADDITIONS += [
    {
        "name": "Backup frequency",
        "domain": "sensor",
        "input_type": "input",
        "address": 5733,
        "data_type": "uint16",
        "scale": 0.01,
        "unit_of_measurement": "Hz",
        "device_class": "frequency",
        "state_class": "measurement",
        "precision": 2,
        "nan_value": 0xFFFF,
        "scan_interval": 10,
    }
]

#: V1.1.9, regs 13200-13207, S32, 1 W each. "Only valid when the inverter is
#: connected to a dual-channel meter (e.g. DTSU666-20)." S32 is little-endian
#: across the two registers, which is the `swap: word` the YAML uses
#: everywhere else, and 0x7FFFFFFF is the specification's "unavailable" for a
#: signed 32-bit value.
SPECIFICATION_ADDITIONS += [
    {
        "name": f"Meter channel 2 {what} active power",
        "domain": "sensor",
        "input_type": "input",
        "address": address,
        "data_type": "int32",
        "scale": 1,
        "swap": "word",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "nan_value": 0x7FFFFFFF,
        "scan_interval": 10,
    }
    for what, address in (
        ("total", 13199),
        ("phase A", 13201),
        ("phase B", 13203),
        ("phase C", 13205),
    )
]


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

    # Last, so the YAML's own entities keep their order and their indices.
    for raw in SPECIFICATION_ADDITIONS:
        entries.append(_entry(raw["domain"], "specification", raw))

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

    # Only the YAML's own entities need one. A specification addition has no
    # YAML entity behind it, so there is nothing to migrate through and
    # nothing missing.
    missing_unique_id = [
        e["entity_id"]
        for e in entries
        if not e.get("unique_id") and e["layer"] != "specification"
    ]

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
