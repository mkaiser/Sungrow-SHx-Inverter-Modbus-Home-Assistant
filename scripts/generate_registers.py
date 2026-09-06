#!/usr/bin/env python3
"""Generate the inverter's register map from the YAML package.

99 read registers is too many to transcribe by hand: a mistyped address or a
scale off by ten produces a plausible-looking number, which is the failure
mode this project can least afford. So the `Component` classes are derived
from [doc/legacy_entity_map.json](../doc/legacy_entity_map.json), which is
itself derived from `modbus_sungrow.yaml` and validated against a real
registry.

The output is **committed source**, not configuration read at runtime, and
`--check` runs in CI so it cannot drift from the YAML.

A Component reads one register space, and the integration polls one Component
per interval, so the classes are the cross product of the two: the tier
decides how often, the space decides which function code.

    python scripts/generate_registers.py            # write the module
    python scripts/generate_registers.py --check    # fail if it is stale
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO = Path(__file__).resolve().parent.parent
ENTITY_MAP = REPO / "doc" / "legacy_entity_map.json"
OUTPUT = REPO / "src" / "sungrow_modbus" / "registers.py"

#: Poll interval in seconds to the name used for its Component classes. These
#: are the YAML's own tiers, which are what users are used to.
TIERS: dict[int, str] = {
    5: "Realtime",
    10: "Fast",
    60: "Medium",
    600: "Slowest",
}

SPACES = {"input": "Input", "holding": "Holding"}

HEADER = '''"""Sungrow inverter registers, generated from the YAML package.

Do not edit by hand: `scripts/generate_registers.py` writes this file from
[doc/legacy_entity_map.json](../../doc/legacy_entity_map.json), and CI checks
that it matches. Hand-written register knowledge — the identity block, decoded
enumerations, derived values — lives in `components.py` instead.

Addresses are protocol addresses, one below the register number printed in
Sungrow's documentation and in the YAML's comments. Sungrow sends 32-bit
values low word first, which the YAML spells `swap: word` and this spells
`word_order="little"`.

Each class is one poll interval in one register space, because a Component
reads a single space and the integration gives each interval its own
coordinator.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, int32, integer, string, uint32

'''


def _load() -> list[dict[str, Any]]:
    """Return the modbus-layer read entities, in address order."""
    entities = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    return sorted(
        (
            e
            for e in entities
            if e["layer"] == "modbus"
            and e.get("address") is not None
            # Switches are writes; milestone 2 is read-only.
            and e["domain"] != "switch"
        ),
        key=lambda e: e["address"],
    )


def _field(entity: dict[str, Any]) -> str:
    """Return the field expression for one entity."""
    address = entity["address"]
    data_type = entity.get("data_type")
    scale = entity.get("scale")
    nan = entity.get("nan_value")
    unit = entity.get("unit_of_measurement")

    parts: list[str] = [str(address)]
    keywords: list[str] = []

    if data_type == "string":
        parts.append(str(entity.get("count", 1)))
        return f"string({', '.join(parts)})"

    if data_type in {"uint32", "int32"}:
        if scale not in (None, 1):
            keywords.append(f"scale={scale}")
        # Sungrow sends the low word first throughout.
        if entity.get("swap") == "word":
            keywords.append('word_order="little"')
        factory = data_type
    elif scale is not None and scale != 1:
        parts.append(str(scale))
        keywords.append(f"signed={data_type == 'int16'}")
        factory = "gauge"
    else:
        keywords.append(f"signed={data_type == 'int16'}")
        factory = "integer"

    if nan is not None:
        keywords.append(f"nan={nan}")
    if unit:
        keywords.append(f'unit="{unit}"')

    return f"{factory}({', '.join(parts + keywords)})"


def _class_name(tier: int, space: str) -> str:
    """Return the Component class name for a tier and register space."""
    return f"Inverter{TIERS[tier]}{SPACES[space]}"


def _attribute(tier: int, space: str) -> str:
    """Return the attribute the device holds that Component under."""
    return f"{TIERS[tier].lower()}_{space}"


def render() -> str:
    """Return the whole generated module."""
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for entity in _load():
        tier = entity.get("scan_interval")
        space = entity.get("input_type")
        if tier not in TIERS or space not in SPACES:
            continue
        grouped.setdefault((tier, space), []).append(entity)

    lines = [HEADER]
    for tier in sorted(TIERS):
        for space in ("input", "holding"):
            entities = grouped.get((tier, space))
            if not entities:
                continue
            name = _class_name(tier, space)
            lines.append(f"\nclass {name}(Component):")
            lines.append(
                f'    """{len(entities)} {space} registers, polled every {tier}s."""\n'
            )
            lines.append(f'    register_space = "{space}"\n')
            for entity in entities:
                field = entity["entity_id"].split(".", 1)[1]
                lines.append(f"    {field} = {_field(entity)}")
                lines.append(
                    f'    """{entity["name"]} (reg {entity["address"] + 1})."""'
                )
            lines.append("")

    # The device composes these by attribute name, and the integration gives
    # each interval its own coordinator, so both mappings are generated too.
    lines.append("\n#: Attribute name on the device to the Component it holds.")
    lines.append("COMPONENTS: dict[str, type[Component]] = {")
    for tier in sorted(TIERS):
        for space in ("input", "holding"):
            if (tier, space) in grouped:
                name = _class_name(tier, space)
                lines.append(f'    "{_attribute(tier, space)}": {name},')
    lines.append("}")

    lines.append("\n#: Poll interval in seconds to the components read at it.")
    lines.append("TIERS: dict[int, tuple[str, ...]] = {")
    for tier in sorted(TIERS):
        attributes = [
            f'"{_attribute(tier, space)}"'
            for space in ("input", "holding")
            if (tier, space) in grouped
        ]
        if attributes:
            lines.append(f"    {tier}: ({', '.join(attributes)},),")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _formatted(text: str) -> str:
    """Return the text as ruff would format it.

    The generator and the formatter have to agree, or `--check` reports a file
    as stale immediately after it was written — the generator emits a long
    call on one line, ruff wraps it, and the two never match. Formatting here
    makes the generated file the same artefact either way.
    """
    for command in (
        # Import order first, then formatting: the fixer can leave lines the
        # formatter would rewrap.
        [
            "ruff",
            "check",
            "--fix",
            "--select",
            "I",
            "--stdin-filename",
            OUTPUT.name,
            "-",
        ],
        ["ruff", "format", "--stdin-filename", OUTPUT.name, "-"],
    ):
        result = subprocess.run(
            command, input=text, capture_output=True, text=True, check=False
        )
        if result.returncode not in (0, 1):
            raise SystemExit(f"{command[1]} failed:\n{result.stderr}")
        text = result.stdout
    return text


def main() -> int:
    """Write the module, or check the committed one is current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = _formatted(render())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"{OUTPUT.relative_to(REPO)} is stale.\n"
                "Run scripts/generate_registers.py and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT.relative_to(REPO)} matches the entity map")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
