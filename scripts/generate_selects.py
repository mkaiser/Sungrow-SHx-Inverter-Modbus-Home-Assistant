#!/usr/bin/env python3
"""Generate the `select` descriptions from the write table.

python scripts/generate_selectes.py            # write the module
python scripts/generate_selectes.py --check    # fail if it is stale
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from writes import SELECTS

REPO = Path(__file__).resolve().parent.parent
ENTITY_MAP = REPO / "doc" / "legacy_entity_map.json"
OUTPUT = REPO / "custom_components" / "sungrow_modbus" / "select_descriptions.py"

TIER_NAMES = {5: "realtime", 10: "fast", 60: "medium", 600: "slowest"}

HEADER = '''"""Select descriptions, generated from the write table.

Do not edit by hand: `scripts/generate_selectes.py` writes this file from
`scripts/writes.py`, and CI checks that it matches.

Each is one holding register carrying 0xAA or 0x55. The specification states
both values for all three, so there is nothing to infer -- the `on` and `off`
codes travel with the description rather than being assumed.
"""

from __future__ import annotations

from homeassistant.const import EntityCategory

from .entity import SungrowSelectDescription

SELECT_DESCRIPTIONS: tuple[SungrowSelectDescription, ...] = (
'''


def _by_unique_id(domain: str) -> dict[str, dict]:
    """Return the YAML's entities of one domain, by unique_id."""
    entities = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    return {
        e["unique_id"]: e
        for e in entities
        if e["domain"] == domain and e.get("unique_id")
    }


def _registers() -> dict[str, dict]:
    """Return the modbus sensor rows, by field name."""
    entities = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    return {
        e["entity_id"].split(".", 1)[1]: e
        for e in entities
        if e["layer"] == "modbus"
        and e["domain"] == "sensor"
        and e.get("address") is not None
    }


def render() -> str:
    """Return the whole generated module."""
    registers = _registers()
    legacy = _by_unique_id("select")
    lines = [HEADER]

    for row in SELECTS:
        register = registers[row["field"]]
        entry = legacy[row["legacy_unique_id"]]
        component = f"{TIER_NAMES[register['scan_interval']]}_{register['input_type']}"
        key = row["key"]
        slugs = [option["slug"] for option in row["options"]]
        values = {option["slug"]: option["value"] for option in row["options"]}

        lines.append("    SungrowSelectDescription(")
        lines.append(f'        key="{key}",')
        lines.append(f'        component="{component}",')
        lines.append(f'        field="{row["field"]}",')
        lines.append(f'        translation_key="{key}",')
        lines.append(f'        legacy_name="{entry["name"]}",')
        lines.append(f'        legacy_unique_id="{row["legacy_unique_id"]}",')
        lines.append('        legacy_platform="template",')
        lines.append(f"        options={slugs!r},")
        lines.append(f"        values={values!r},")
        lines.append("        entity_category=EntityCategory.CONFIG,")
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines) + "\n"


def _formatted(text: str) -> str:
    """Return the text as ruff would format it."""
    for command in (
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
    """Write the descriptions, or check the committed ones are current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = _formatted(render())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"{OUTPUT.relative_to(REPO)} is stale.\n"
                "Run scripts/generate_selectes.py and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT.relative_to(REPO)} matches the write table")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO)}: {len(SELECTS)} selects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
