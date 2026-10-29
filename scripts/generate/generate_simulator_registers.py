#!/usr/bin/env python3
"""Derive a Modbus register seed for the simulator from the register records.

Seeded from what is already committed rather than from a second hand-kept
list that would drift: every modbus sensor and switch in
`legacy/modbus_sungrow.yaml`, plus every specification-layer register in
`doc/legacy_entity_map.json` the YAML never read, contributes its address,
width and a plausible value. That is enough for the integration to read
something sensible back during development.

Writes scripts/dev/simulator_registers.json, which is committed: the tests read
it to prove every ported register decodes, so it is a fixture rather than a
scratch file.

    python scripts/generate/generate_simulator_registers.py          # write it
    python scripts/generate/generate_simulator_registers.py --check  # is it stale?
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "legacy" / "modbus_sungrow.yaml"
TARGET = REPO / "scripts" / "dev" / "simulator_registers.json"

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
    # Running, on both sides of register 13000. The address is in two of
    # Sungrow's tables -- read-only over 0x04 where it is the running state,
    # read/write over 0x03/0x06/0x10 where it is Start/Stop. A stopped input
    # side makes the control test refuse to run at all.
    #
    # Note the value: **0x0000 means Running**, not stopped, per the map in
    # `inverter.derived.RUNNING_STATES`. The obvious guess is wrong.
    12999: 0x0000,
    # Bounds the inverter is supposed to state about itself. Without them the
    # control test correctly declines to guess, which is worth seeing once but
    # not worth having as the only thing the simulator can show.
    5621: 0,  # export power limit minimum, 10 W per count
    5622: 1000,  # export power limit maximum -> 10 kW
    5627: 50,  # BDC rated power, 100 W per count -> 5 kW
}

#: The fault and alarm words, input 13050-13079: no flag set, which is what
#: every surveyed inverter read. The default's 1 would be bit 0 -- a fan alarm
#: on the simulator for ever. Input only: the same addresses on the holding
#: side are the EMS mode and the battery limits.
FAULT_WORDS: dict[int, list[int]] = {
    address: [0, 0] for address in range(13049, 13079, 2)
}

#: Registers that exist only in the holding space and that no sensor reads, so
#: nothing above would ever create them.
#:
#: Register 13000 is the case that matters. It is in **two** of Sungrow's
#: tables: read-only over function code 0x04, where reading it gives the running
#: state, and read/write over 0x03/0x06/0x10, where it is Start/Stop. Only the
#: first is a sensor, so without this the one piece of this project that can
#: turn an inverter off could be exercised only against somebody's house.
HOLDING_ONLY: dict[int, list[int]] = {
    12999: [0xCF],  # Start/Stop, currently "started"
}

STRINGS = {
    4953: "SAPPHIRE-H_01011.95.12",  # ARM software
    4968: "SAPPHIRE-H_03011.95.12",  # DSP software
    4989: "A123456789",  # inverter serial
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


def _apply_fixtures(spaces: dict[str, dict[int, list[int]]]) -> None:
    """Overwrite the defaults where a plausible value matters more than a zero.

    Four passes, in this order, because each is narrower than the last:
    `STRINGS` gives the text fields something readable, `OVERRIDES` pins
    individual registers a probe would otherwise misread, `HOLDING_ONLY`
    adds words that exist on the holding side alone -- 12999 among them, which
    is what makes the control test's restart phase exercisable offline -- and
    `FAULT_WORDS` clears the input-side fault and alarm words.
    """
    for address, text in STRINGS.items():
        for space in spaces.values():
            if address in space:
                space[address] = _string_words(text, len(space[address]))

    for address, value in OVERRIDES.items():
        words = value if isinstance(value, list) else [value]
        for space in spaces.values():
            if address in space:
                space[address] = words

    for address, words in HOLDING_ONLY.items():
        spaces["holding"][address] = list(words)

    for address, words in FAULT_WORDS.items():
        spaces["input"][address] = list(words)


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

    # Registers the specification defines, or hardware was observed to answer,
    # and the YAML never read. Their one source is the entity map, so they
    # cannot drift from the descriptions generated beside them.
    entity_map = json.loads(
        (REPO / "doc" / "legacy_entity_map.json").read_text(encoding="utf-8")
    )
    for entry in entity_map["entities"]:
        if (
            entry["layer"] not in {"specification", "observed"}
            or entry.get("address") is None
        ):
            continue
        space = "input" if entry.get("input_type") == "input" else "holding"
        data_type = entry.get("data_type", "uint16")
        width = int(entry.get("count", WIDTHS.get(data_type, 1)))
        spaces[space][int(entry["address"])] = _default_value(entry, width)

    _apply_fixtures(spaces)
    return {
        name: {str(address): words for address, words in sorted(space.items())}
        for name, space in spaces.items()
    }


def main() -> int:
    """Write the seed, or check the committed one is current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    seed = collect()
    rendered = json.dumps(seed, indent=2) + "\n"
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != rendered:
            print(
                f"{TARGET.relative_to(REPO)} is stale.\n"
                "Run scripts/generate/generate_simulator_registers.py and commit "
                "the result.",
                file=sys.stderr,
            )
            return 1
        return 0
    TARGET.write_text(rendered, encoding="utf-8")
    counts = ", ".join(f"{len(v)} {k}" for k, v in seed.items())
    print(f"Wrote {TARGET.relative_to(REPO)} ({counts} registers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
