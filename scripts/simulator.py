#!/usr/bin/env python3
"""Serve the Sungrow register seed over Modbus TCP.

Lets the integration be developed and tested without an inverter. Run
scripts/simulate.sh to regenerate the seed and start this, or point it at an
existing seed file.

The seed only names the registers the YAML package reads. Those are served
inside a dense block spanning the whole address range, because the client
pools neighbouring registers into one request and would otherwise ask for
addresses between two sensors that the server considers invalid.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from pymodbus.server import StartAsyncTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SEED = REPO / "scripts" / "simulator_registers.json"

_LOGGER = logging.getLogger("sungrow.simulator")


#: Registers to bridge between two seeded addresses before starting a new
#: block. Comfortably above the client's own 16-register pooling gap, so a
#: pooled read never lands on an address the server considers invalid, while
#: the far-apart register bands stay separate instead of being joined by
#: thousands of filler registers.
MAX_GAP = 64


def _block(values: dict[str, list[int]]) -> list[SimData]:
    """Build dense SimData blocks covering every seeded address."""
    if not values:
        # A device must still answer something, or every read is an exception.
        return [SimData(address=0, count=1, values=0, datatype=DataType.REGISTERS)]

    registers: dict[int, int] = {}
    for address, words in values.items():
        for offset, word in enumerate(words):
            registers[int(address) + offset] = word

    blocks: list[SimData] = []
    start = previous = min(registers)
    for address in [*sorted(registers)[1:], None]:
        if address is not None and address - previous <= MAX_GAP:
            previous = address
            continue
        dense = [registers.get(a, 0) for a in range(start, previous + 1)]
        blocks.append(SimData(address=start, values=dense, datatype=DataType.REGISTERS))
        _LOGGER.debug("block of %d registers at %d..%d", len(dense), start, previous)
        if address is None:
            break
        start = previous = address

    served = sum(len(b.values) for b in blocks)  # type: ignore[arg-type]
    _LOGGER.info(
        "serving %d registers in %d block(s), %d seeded",
        served,
        len(blocks),
        len(registers),
    )
    return blocks


def build_device(seed: Path, unit_id: int) -> SimDevice:
    """Load the seed into a simulated device with separate register spaces."""
    data = json.loads(seed.read_text(encoding="utf-8"))
    coils = [SimData(address=0, count=16, values=False, datatype=DataType.BITS)]
    discrete = [SimData(address=0, count=16, values=False, datatype=DataType.BITS)]
    holding = _block(data.get("holding", {}))
    inputs = _block(data.get("input", {}))
    return SimDevice(id=unit_id, simdata=(coils, discrete, holding, inputs))


async def serve(host: str, port: int, device: SimDevice) -> None:
    """Run until interrupted."""
    _LOGGER.info("Sungrow Modbus simulator listening on %s:%d", host, port)
    await StartAsyncTcpServer(device, address=(host, port))


def main() -> None:
    """Parse arguments and start the server."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5020)
    parser.add_argument("--unit-id", type=int, default=1)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    if not args.seed.exists():
        raise SystemExit(
            f"{args.seed} not found - run scripts/gen_simulator_registers.py first"
        )

    device = build_device(args.seed, args.unit_id)
    try:
        asyncio.run(serve(args.host, args.port, device))
    except KeyboardInterrupt:
        _LOGGER.info("stopped")


if __name__ == "__main__":
    main()
