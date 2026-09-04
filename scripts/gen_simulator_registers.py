#!/usr/bin/env python3
"""Derive a Modbus register seed for the simulator from modbus_sungrow.yaml.

The YAML package is the most complete description of the SHx register map we
have, so the simulator is seeded from it rather than from a second hand-kept
list that would drift. Every modbus sensor in the package contributes its
address, width and a plausible value, which is enough for the integration to
read something sensible back during development.

Writes scripts/simulator_registers.json (gitignored).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "modbus_sungrow.yaml"
TARGET = REPO / "scripts" / "simulator_registers.json"

# Registers per data type. Anything not listed occupies a single register.
WIDTHS = {"uint16": 1, "int16": 1, "uint32": 2, "int32": 2, "float32": 2}

# Values chosen so the derived sensors land in a believable range for an
# SH10RT on a sunny afternoon rather than reading zero everywhere.
OVERRIDES: dict[int, int | list[int]] = {
    4951: [2, 0],  # protocol version, low word first
    4999: 0x0E03,  # device type code -> SH10RT
    5000: 100,  # rated output, x100 -> 10 kW
    5016: [7000, 0],  # total DC power, W
    5007: 285,  # inverter temperature, x0.1 -> 28.5 C
    13033: [4200, 0],  # total active power, W
}

STRINGS = {
    4953: "SAPPHIRE-H_01011.95.12",  # ARM software
    4968: "SAPPHIRE-H_03011.95.12",  # DSP software
    4989: "A2340600123",  # inverter serial
    2581: "SAPPHIRE-H_01011.95.12",
    2596: "SAPPHIRE-H_03011.95.12",
    2612: "SUBCTL-S_04011.01.01",
}


class _SecretLoader(yaml.SafeLoader):
    """Load the package without needing a real secrets.yaml."""


def _secret(loader: yaml.SafeLoader, node: yaml.Node) -> str:
    return f"!secret {loader.construct_scalar(node)}"  # type: ignore[arg-type]


_SecretLoader.add_constructor("!secret", _secret)


def _string_words(text: str, registers: int) -> list[int]:
    """Encode an ASCII string into null-padded 16-bit registers."""
    raw = text.encode("ascii")[: registers * 2].ljust(registers * 2, b"\x00")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, registers * 2, 2)]


def _default_value(entry: dict[str, Any], width: int) -> list[int]:
    """Return a plausible raw value for one sensor."""
    if entry.get("data_type") == "string":
        return [0] * width
    # Signed types get a small positive value; a zero everywhere would hide
    # scaling mistakes behind a plausible-looking result.
    return [1] + [0] * (width - 1)


def collect() -> dict[str, dict[str, list[int]]]:
    """Walk the YAML package and build the seed."""
    document = yaml.load(SOURCE.read_text(encoding="utf-8"), Loader=_SecretLoader)
    spaces: dict[str, dict[int, list[int]]] = {"input": {}, "holding": {}}

    for hub in document.get("modbus", []):
        for entry in hub.get("sensors", []) + hub.get("switches", []):
            address = entry.get("address")
            if address is None:
                continue
            space = "input" if entry.get("input_type") == "input" else "holding"
            data_type = entry.get("data_type", "uint16")
            width = int(entry.get("count", WIDTHS.get(data_type, 1)))
            spaces[space][int(address)] = _default_value(entry, width)

    for address, text in STRINGS.items():
        for space in spaces.values():
            if address in space:
                space[address] = _string_words(text, len(space[address]))

    for address, value in OVERRIDES.items():
        words = value if isinstance(value, list) else [value]
        for space in spaces.values():
            if address in space:
                space[address] = words

    return {
        name: {str(address): words for address, words in sorted(space.items())}
        for name, space in spaces.items()
    }


def main() -> None:
    """Write the seed."""
    seed = collect()
    TARGET.write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")
    counts = ", ".join(f"{len(v)} {k}" for k, v in seed.items())
    print(f"Wrote {TARGET.relative_to(REPO)} ({counts} registers)")


if __name__ == "__main__":
    main()
