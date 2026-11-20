#!/usr/bin/env python3
"""Field tools for a wallbox an inverter manages: watch it, and switch its charge.

What `plans/T003-T004-T020-T039-T040-T059-wallbox.md` (sections 8 and 9) runs on site or
over a VPN, on this tree's library. Every command reads only, except
`charge`, which writes the inverter's EV charger block, watches the car, and
puts back the snapshot it flushed to disk first, checked by read. Nothing
here writes the wallbox's own registers: on a managed wallbox the inverter
owns them (rule 1 of the plan).

    managed_wallbox_field.py --inverter HOST --wallbox HOST block
    managed_wallbox_field.py ... energy
    managed_wallbox_field.py ... watch 40           # the wallbox, 40 samples
    managed_wallbox_field.py ... log               # block beside wallbox, every 5 s
    managed_wallbox_field.py ... session           # every 2 min until the charge stops
    managed_wallbox_field.py ... phase 60          # a phase switch, 60 minutes
    managed_wallbox_field.py ... scan single-phase # holding 33501-33600 to JSON
    managed_wallbox_field.py ... charge on 300     # charging on 5 min, then back

`--inverter` is the inverter's LAN port or its WiNet-S (port 502, unit 1);
through a WiNet-S a read-back after a write can be stale, so `charge` checks
the restore on a fresh session. `--wallbox` is the wallbox's own address (TLS,
port 516, unit 248). Both default to `$SUNGROW_INVERTER` and
`$SUNGROW_WALLBOX`. **Stop other clients first**: two on one path time out,
and the TLS port refuses connections opened in quick succession.

Files (logs, scans, the snapshot) go to the current directory; they carry no
address. Keep them out of the repository (`tmp/` is gitignored).
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

from modbus_connection import ModbusError, ModbusExceptionError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "device-diagnosis/scripts/python")
)

import wallbox_direct

from sungrow_modbus.addresses import reg
from sungrow_modbus.hybrid_inverter import ev_charger as ev
from sungrow_modbus.wallbox import capability_test as wct

#: The inverter's block with the two words below it (33538, 33539), to grid surplus.
BLOCK_FROM = reg(33538)
BLOCK_COUNT = ev.GRID_SURPLUS - BLOCK_FROM + 1
#: The range `scan` reads, in tens.
SCAN_FROM, SCAN_TO = reg(33501), reg(33601)
#: The inverter's energy readings.
PV_POWER = reg(5017)
LOAD_POWER = reg(13008)
EXPORT_POWER = reg(13010)
BATTERY_LEVEL = reg(13023)
BATTERY_POWER = reg(5214)
#: The wallbox's phase registers and the session's energy.
PHASE_SETTING = reg(21204)
PHASES_IN_USE = reg(21225)
PHASE_MODE = reg(21270)
MIN_POWER = reg(21272)
SESSION_ENERGY = reg(21310)
VOLTAGE_A = reg(21302)

LOST = (ModbusError, TimeoutError, OSError)
WORDS = {"on": ev.ON, "off": ev.OFF}


def _now() -> str:
    return time.strftime("%H:%M:%S")


def _s32(low: int, high: int) -> int:
    value = low | high << 16
    return value - (1 << 32) if value & 0x80000000 else value


def _save(path: Path, text: str) -> None:
    """Write a file and flush it to the disk before returning."""
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def _out(line: str, log: Any = None) -> None:
    print(line, flush=True)
    if log is not None:
        log.write(line + "\n")
        log.flush()


class House:
    """The inverter at unit 1 and the wallbox over TLS, each one session."""

    def __init__(self, inverter: str, wallbox: str) -> None:
        """Remember the two addresses; nothing is opened yet."""
        self.inverter_host = inverter
        self.inverter_conn = ModbusConnection(
            ModbusTcpParams(host=inverter, port=502), timeout=8
        )
        self.wallbox_conn = ModbusConnection(wallbox_direct.params(wallbox), timeout=8)
        self.inverter = self.inverter_conn.for_unit(1)
        self.wallbox = self.wallbox_conn.for_unit(wallbox_direct.UNIT)

    async def reopen_inverter(self) -> None:
        """Close the inverter's session and open a fresh one."""
        await self.inverter_conn.close()
        await asyncio.sleep(5)
        self.inverter_conn = ModbusConnection(
            ModbusTcpParams(host=self.inverter_host, port=502), timeout=8
        )
        self.inverter = self.inverter_conn.for_unit(1)

    async def close(self) -> None:
        """Close both sessions."""
        await self.inverter_conn.close()
        await self.wallbox_conn.close()

    async def block(self) -> list[int]:
        """Return the inverter's words 33538-33550 (registers)."""
        return list(await self.inverter.read_holding_registers(BLOCK_FROM, BLOCK_COUNT))

    async def car(self) -> dict[str, Any]:
        """Return the wallbox's status, setting, phase currents and power."""
        w = self.wallbox
        status = (await w.read_input_registers(wct.CHARGING_STATUS_ADDRESS, 1))[0]
        setting = (await w.read_holding_registers(wct.OUTPUT_CURRENT, 1))[0]
        live = await w.read_input_registers(VOLTAGE_A, 8)
        return {
            "status": wct.CHARGING_STATUS.get(status, status),
            "charging": status == wct.CHARGING,
            "setting_a": setting / 10,
            "amps": [live[1] / 10, live[3] / 10, live[5] / 10],
            "watts": live[6] | live[7] << 16,
        }

    async def phases(self) -> dict[str, int]:
        """Return the wallbox's phase setting, phases in use, mode and minimum power."""
        w = self.wallbox
        return {
            "21204": (await w.read_holding_registers(PHASE_SETTING, 1))[0],
            "21225": (await w.read_input_registers(PHASES_IN_USE, 1))[0],
            "21270": (await w.read_input_registers(PHASE_MODE, 1))[0],
            "21272": (await w.read_input_registers(MIN_POWER, 1))[0],
        }

    async def session_wh(self) -> int:
        """Return the session's energy in Wh."""
        words = await self.wallbox.read_input_registers(SESSION_ENERGY, 2)
        return words[0] | words[1] << 16

    async def energy(self) -> dict[str, Any]:
        """Return PV, grid, load and the battery, from the inverter."""
        i = self.inverter
        pv = await i.read_input_registers(PV_POWER, 2)
        export = await i.read_input_registers(EXPORT_POWER, 2)
        load = await i.read_input_registers(LOAD_POWER, 2)
        level = (await i.read_input_registers(BATTERY_LEVEL, 1))[0]
        battery = await i.read_input_registers(BATTERY_POWER, 2)
        return {
            "pv_w": pv[0] | pv[1] << 16,
            "export_w": _s32(*export),
            "load_w": _s32(*load),
            "battery_level_13023": level / 10,
            "battery_w": _s32(*battery),
        }


def _block_text(block: list[int]) -> str:
    on = {ev.ON: "on", ev.OFF: "off"}.get(block[2], block[2])
    mode = ev.MODES.get(block[3], block[3])
    user = block[7] / 10
    return f"charging={on} mode={mode} user={user}A grid={block[12]} raw={block}"


async def _loop(
    seconds: float, every: float, step: Callable[[], Awaitable[bool]], log: Any
) -> None:
    """Run `step` every `every` seconds for `seconds`, or until it returns False."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            if not await step():
                return
        except LOST as err:
            _out(f"{_now()} lost: {type(err).__name__}: {err}", log)
            await asyncio.sleep(10)
        await asyncio.sleep(every)


async def cmd_block(house: House, _args: argparse.Namespace) -> int:
    """Print the inverter's block."""
    _out(f"{_now()} {_block_text(await house.block())}")
    return 0


async def cmd_energy(house: House, _args: argparse.Namespace) -> int:
    """Print PV, grid, load and the battery."""
    _out(f"{_now()} {await house.energy()}")
    return 0


async def cmd_watch(house: House, args: argparse.Namespace) -> int:
    """Print the wallbox N times, 1.5 s apart."""
    for _ in range(args.samples):
        _out(f"{_now()} {await house.car()}")
        await asyncio.sleep(1.5)
    return 0


async def cmd_log(house: House, args: argparse.Namespace) -> int:
    """Log the block beside the wallbox every 5 s, for MINUTES."""
    log = args.log

    async def step() -> bool:
        line = f"{_block_text(await house.block())} | {await house.car()}"
        _out(f"{_now()} {line}", log)
        return True

    await _loop(args.minutes * 60, 5, step, log)
    return 0


async def cmd_session(house: House, args: argparse.Namespace) -> int:
    """Every 2 min: the wallbox, the session's energy, the block; until it stops."""
    log = args.log

    async def step() -> bool:
        car = await house.car()
        line = f"{car} session={await house.session_wh()}Wh"
        line += f" | {_block_text(await house.block())}"
        _out(f"{_now()} {line}", log)
        if not car["charging"]:
            _out(f"{_now()} not charging any more", log)
            return False
        return True

    await _loop(args.minutes * 60, 120, step, log)
    return 0


async def cmd_phase(house: House, args: argparse.Namespace) -> int:
    """Every 5 s: block, PV, battery, the wallbox's phases; a changed row is marked."""
    previous: list[Any] = []
    log = args.log

    async def step() -> bool:
        block = await house.block()
        phases = await house.phases()
        energy = await house.energy()
        car = await house.car()
        row = [block, phases]
        mark = "  <== CHANGED" if previous and previous != row else ""
        previous[:] = row
        _out(
            f"{_now()} pv={energy['pv_w']}W level={energy['battery_level_13023']}%"
            f" block={block} | {phases} {car['status']} I={car['amps']}{mark}",
            log,
        )
        return True

    await _loop(args.minutes * 60, 5, step, log)
    return 0


async def cmd_scan(house: House, args: argparse.Namespace) -> int:
    """Read holding 33501-33600 (registers) and the wallbox's phases, to JSON."""
    words: dict[int, Any] = {}
    for start in range(SCAN_FROM, SCAN_TO, 10):
        try:
            ten = await house.inverter.read_holding_registers(start, 10)
            for i, word in enumerate(ten):
                words[start + i + 1] = word
        except ModbusExceptionError:
            for address in range(start, start + 10):
                try:
                    words[address + 1] = (
                        await house.inverter.read_holding_registers(address, 1)
                    )[0]
                except ModbusExceptionError as err:
                    words[address + 1] = f"refused: {err}"[:40]
        await asyncio.sleep(0.3)
    data = {
        "label": args.label,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "addresses": "register numbers (protocol + 1)",
        "inverter_holding": words,
        "wallbox_phases": await house.phases(),
        "wallbox": await house.car(),
    }
    path = Path(f"scan_{args.label}.json")
    await asyncio.to_thread(_save, path, json.dumps(data, indent=1))
    unused = [a for a, w in words.items() if w == 0xFFFF]
    _out(f"{path}: {len(words)} words, {len(unused)} read 65535; the rest:")
    _out("  ".join(f"{a}:{w}" for a, w in words.items() if w != 0xFFFF))
    return 0


async def cmd_charge(house: House, args: argparse.Namespace) -> int:
    """Write charging on or off, watch the car, then put the snapshot back."""
    snapshot = (await house.inverter.read_holding_registers(ev.CHARGING, 1))[0]
    path = Path("charge_snapshot.json")
    text = json.dumps({"register": ev.CHARGING + 1, "word": snapshot})
    await asyncio.to_thread(_save, path, text)
    _out(f"{_now()} snapshot: charging word {snapshot}; {await house.car()}")
    try:
        await house.inverter.write_register(ev.CHARGING, WORDS[args.state])
        _out(f"{_now()} wrote charging {args.state}")

        async def step() -> bool:
            _out(f"{_now()} {_block_text(await house.block())} | {await house.car()}")
            return True

        await _loop(args.seconds, 3, step, None)
    finally:
        await _restore(house, snapshot)
    for _ in range(5):
        _out(f"{_now()} after: {await house.car()}")
        await asyncio.sleep(3)
    await asyncio.to_thread(path.unlink)
    return 0


async def _restore(house: House, snapshot: int) -> None:
    """Write the snapshot back until a fresh session reads it. Never gives up."""
    attempt = 0
    while True:
        attempt += 1
        try:
            held = (await house.inverter.read_holding_registers(ev.CHARGING, 1))[0]
            if held != snapshot:
                await house.inverter.write_register(ev.CHARGING, snapshot)
                _out(f"{_now()} wrote back charging word {snapshot}")
            await house.reopen_inverter()
            now = (await house.inverter.read_holding_registers(ev.CHARGING, 1))[0]
            _out(f"{_now()} restore check {attempt}: {now}")
            if now == snapshot:
                return
        except LOST as err:
            _out(f"{_now()} restore attempt {attempt} lost: {type(err).__name__}")
            await house.reopen_inverter()
        await asyncio.sleep(5)


#: The commands that keep a log file in the current directory.
LOGGED = ("log", "session", "phase")

COMMANDS = {
    "block": cmd_block,
    "energy": cmd_energy,
    "watch": cmd_watch,
    "log": cmd_log,
    "session": cmd_session,
    "phase": cmd_phase,
    "scan": cmd_scan,
    "charge": cmd_charge,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inverter", default=os.environ.get("SUNGROW_INVERTER"))
    parser.add_argument("--wallbox", default=os.environ.get("SUNGROW_WALLBOX"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("block", help="the inverter's EV charger block")
    sub.add_parser("energy", help="PV, grid, load, battery")
    sub.add_parser("watch", help="the wallbox, N samples").add_argument(
        "samples", type=int, nargs="?", default=40
    )
    for name, default, text in (
        ("log", 60.0, "block beside wallbox every 5 s"),
        ("session", 100.0, "every 2 min until the charge stops"),
        ("phase", 60.0, "a phase switch, every 5 s"),
    ):
        sub.add_parser(name, help=text).add_argument(
            "minutes", type=float, nargs="?", default=default
        )
    sub.add_parser("scan", help="holding 33501-33600 to JSON").add_argument("label")
    charge = sub.add_parser("charge", help="WRITES: charging on/off, then back")
    charge.add_argument("state", choices=sorted(WORDS))
    charge.add_argument("seconds", type=float)
    return parser


async def _main(args: argparse.Namespace) -> int:
    house = House(args.inverter, args.wallbox)
    try:
        return await COMMANDS[args.command](house, args)
    finally:
        await house.close()


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and run one command."""
    args = _parser().parse_args(argv)
    if not args.inverter or not args.wallbox:
        _parser().error("--inverter and --wallbox (or the environment) are required")
    if args.command not in LOGGED:
        args.log = None
        return asyncio.run(_main(args))
    name = f"{args.command}_{time.strftime('%Y%m%d-%H%M')}.log"
    with Path(name).open("a", encoding="utf-8") as args.log:
        return asyncio.run(_main(args))


if __name__ == "__main__":
    sys.exit(main())
