#!/usr/bin/env python3
"""Find out what a Sungrow installation advertises and answers on a LAN.

Run this on a machine **on the same subnet as the inverter** — not inside the
devcontainer, whose Docker bridge does not carry the LAN's multicast traffic.

It answers three questions that decide how the integration's config flow can
discover devices:

1. Does the WiNet-S dongle advertise itself over mDNS, and under what service
   type and properties? If it does, discovery is free and exact, and no
   address sweep is needed at all.
2. Which hosts on this subnet answer on a Modbus port?
3. Which Modbus unit ids answer behind a given host, and what kind of device
   is each one?

Usage:
    python scripts/discover_probe.py mdns
    python scripts/discover_probe.py sweep 192.168.1.0/24 [--port 502]
    python scripts/discover_probe.py units <host> [--port 502]
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from datetime import UTC, datetime
import hashlib
import ipaddress
import json
from pathlib import Path
import sys
import time

MODBUS_PORTS = (502, 503)

#: Unit ids worth trying before any wider scan, with what convention says they
#: are. A device is still identified by what answers, never by its address.
CANDIDATE_UNITS: dict[int, str] = {
    1: "inverter (default)",
    2: "inverter (slave)",
    3: "inverter slave, or wallbox via WiNet-S",
    4: "inverter (slave)",
    5: "inverter (slave)",
    200: "SBR battery",
    247: "iHomeManager (usually port 503)",
    248: "wallbox (direct RS485-to-TCP)",
}

#: Register to read per device kind, chosen so only that kind answers it.
#: (space, address, count, label)
IDENTITY_PROBES = [
    ("input", 4999, 1, "inverter device type code"),
    ("input", 21200, 4, "wallbox serial"),
    ("input", 10740, 2, "SBR battery block"),
]


async def cmd_mdns(args: argparse.Namespace) -> int:
    """Browse every mDNS service type and report anything Sungrow-shaped."""
    from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf
    from zeroconf.asyncio import AsyncZeroconf

    found: dict[str, dict] = {}

    def on_change(zeroconf, service_type, name, state_change, **kwargs):
        if state_change is not ServiceStateChange.Added:
            return
        info = zeroconf.get_service_info(service_type, name, timeout=2000)
        if info is None:
            return
        props = {
            k.decode(errors="replace") if isinstance(k, bytes) else k: v.decode(
                errors="replace"
            )
            if isinstance(v, bytes)
            else v
            for k, v in (info.properties or {}).items()
        }
        found[name] = {
            "type": service_type,
            "addresses": [str(a) for a in info.parsed_addresses()],
            "port": info.port,
            "properties": props,
        }

    azc = AsyncZeroconf()
    zc: Zeroconf = azc.zeroconf

    # Ask the network which service types exist before browsing any, rather
    # than guessing at a list. A guessed list can only ever produce a
    # provisional negative: a device advertising under a type nobody thought
    # of looks identical to a device advertising nothing.
    discovered_types: set[str] = set()

    def on_type(zeroconf, service_type, name, state_change, **kwargs):
        if state_change is ServiceStateChange.Added:
            discovered_types.add(name)

    meta = ServiceBrowser(zc, "_services._dns-sd._udp.local.", handlers=[on_type])
    print(f"Asking the network which service types exist ({args.seconds:.0f}s)...")
    await asyncio.sleep(args.seconds)
    meta.cancel()

    types = sorted(discovered_types) or [
        # Nothing answered the meta-query; fall back to common types so the
        # run still says something.
        "_http._tcp.local.",
        "_workstation._tcp.local.",
        "_device-info._tcp.local.",
    ]
    print(f"Browsing {len(types)} service type(s) for {args.seconds:.0f}s:")
    for service_type in types:
        print(f"    {service_type}")
    browsers = [ServiceBrowser(zc, t, handlers=[on_change]) for t in types]
    await asyncio.sleep(args.seconds)
    for b in browsers:
        b.cancel()
    await azc.async_close()

    if not found:
        print(
            "Nothing advertised. Either nothing is on this segment, or "
            "multicast is not reaching this host (a Docker bridge will do "
            "that). Run this on the LAN itself."
        )
        return 1
    for name, entry in sorted(found.items()):
        interesting = "sungrow" in (name + str(entry)).lower()
        mark = "  <-- SUNGROW" if interesting else ""
        print(f"\n{name}{mark}")
        print(f"  type      {entry['type']}")
        print(f"  addresses {', '.join(entry['addresses'])}:{entry['port']}")
        for k, v in entry["properties"].items():
            print(f"  {k:<12}{v}")
    return 0


async def _tcp_open(host: str, port: int, timeout: float) -> bool:
    """Return True if a TCP connection to host:port completes."""
    try:
        fut = asyncio.open_connection(host, port)
        _, writer = await asyncio.wait_for(fut, timeout)
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
        return True
    except Exception:
        return False


async def cmd_sweep(args: argparse.Namespace) -> int:
    """Check every address in a subnet for an open Modbus port."""
    net = ipaddress.ip_network(args.subnet, strict=False)
    hosts = list(net.hosts())
    if len(hosts) > args.max_hosts:
        print(
            f"{net} holds {len(hosts)} addresses, over the --max-hosts limit of "
            f"{args.max_hosts}. A /24 sweeps in about a second; a /16 takes "
            f"minutes and floods the segment with ARP. Narrow it, or raise the "
            f"limit deliberately.",
            file=sys.stderr,
        )
        return 2

    sem = asyncio.Semaphore(args.concurrency)

    async def check(ip):
        async with sem:
            if await _tcp_open(str(ip), args.port, args.timeout):
                return str(ip)
            return None

    print(f"Sweeping {len(hosts)} addresses in {net} on port {args.port}...")
    t0 = time.perf_counter()
    results = await asyncio.gather(*(check(ip) for ip in hosts))
    elapsed = time.perf_counter() - t0
    live = [ip for ip in results if ip]
    print(
        f"{len(live)} answered in {elapsed:.1f}s ({len(hosts) / elapsed:.0f} probes/s)"
    )
    for ip in live:
        print(f"  {ip}:{args.port}")
    return 0 if live else 1


def _require_library() -> tuple:
    """Import the device library, or explain where this command actually runs.

    `units`, `capabilities` and `dump` speak Modbus through
    `modbus-connection`, which is installed in the devcontainer and not on a
    host. Saying so beats a ModuleNotFoundError traceback, because the useful
    reply is not "install this" — it is "you want the other script".
    """
    try:
        from modbus_connection import ModbusError, ModbusTcpParams
        from modbus_connection.tmodbus import ModbusConnection
    except ModuleNotFoundError:
        raise SystemExit(
            "This command needs the modbus-connection library, which lives in "
            "the devcontainer.\n\n"
            "  In the devcontainer:  python scripts/discover_probe.py ...\n"
            "  On a host, instead:   python scripts/collect_fingerprint.py <ip>\n\n"
            "collect_fingerprint.py needs nothing installed and reads the same "
            "registers."
        ) from None
    return ModbusError, ModbusTcpParams, ModbusConnection


async def cmd_units(args: argparse.Namespace) -> int:
    """Ask each candidate unit id what it is, using the device library."""
    ModbusError, ModbusTcpParams, ModbusConnection = _require_library()

    print(f"Probing {args.host}:{args.port} for devices...")
    # One connection for every probe: these units share a link in the real
    # integration too, and opening one per probe is what overwhelms a WiNet-S.
    connection = ModbusConnection(
        ModbusTcpParams(host=args.host, port=args.port), timeout=args.timeout
    )
    try:
        for unit_id, convention in CANDIDATE_UNITS.items():
            unit = connection.for_unit(unit_id)
            kinds = []
            for space, address, count, label in IDENTITY_PROBES:
                read = (
                    unit.read_input_registers
                    if space == "input"
                    else unit.read_holding_registers
                )
                try:
                    values = await read(address, count)
                except (ModbusError, TimeoutError, OSError):
                    continue
                if values and any(v not in (0, 0xFFFF) for v in values):
                    kinds.append(f"{label}={list(values)}")
            if kinds:
                found = "; ".join(kinds)
                print(f"  unit {unit_id:>3} ANSWERED ({convention}): {found}")
    finally:
        await connection.close()
    return 0


#: What to read to establish each capability axis. Addresses are protocol
#: addresses, one below the register number in Sungrow's document.
#: (label, space, address, count, axis)
FINGERPRINT = [
    ("device type code (5000)", "input", 4999, 1, "model"),
    ("nominal output power (5001)", "input", 5000, 1, "model"),
    ("output type (5002)", "input", 5001, 1, "phase"),
    ("MPPT1 voltage", "input", 5010, 1, "mppt"),
    ("MPPT2 voltage", "input", 5012, 1, "mppt"),
    ("MPPT3 voltage", "input", 5014, 1, "mppt"),
    ("MPPT4 voltage", "input", 5114, 1, "mppt"),
    ("phase A voltage", "input", 5018, 1, "phase"),
    ("phase B voltage", "input", 5019, 1, "phase"),
    ("phase C voltage", "input", 5020, 1, "phase"),
    ("meter phase A voltage (5741)", "input", 5740, 1, "meter"),
    ("meter phase A current (5744)", "input", 5743, 1, "meter"),
    ("battery voltage", "input", 13019, 1, "battery"),
    ("battery level", "input", 13022, 1, "battery"),
    ("battery temperature", "input", 13024, 1, "battery"),
    ("firmware block (13250, spec V1.1.7+)", "input", 13249, 1, "firmware"),
    # Sungrow states the 6100-6195 block is not forwarded by a WiNet-S over
    # TCP/IP, so whether it answers says which way in we came.
    ("PV power of today (6100, direct-only)", "input", 6099, 2, "transport"),
    ("PV power limitation (13018, V1.1.10+)", "holding", 13017, 1, "firmware"),
]

#: The output type register says what the model cannot.
OUTPUT_TYPE = {0: "single phase", 1: "three phase 3P4L", 2: "three phase 3P3L"}

#: Unavailable, per the specification: U16, U32, S16, S32.
UNAVAILABLE = {0xFFFF, 0x7FFF}


def _classify(values: list[int]) -> str:
    """Say what a read means, using the specification's own convention."""
    if all(v in UNAVAILABLE for v in values):
        return "unavailable"
    return "present"


def _fake_serial(real: str) -> str:
    """Return a stand-in serial of the same shape, stably derived from the real one.

    Shape is preserved because the string decoder is itself under test: a
    Sungrow serial is ASCII across ten registers, and a fake of a different
    length would stop the published reading exercising that. Deriving it from
    a hash rather than at random means one machine always maps to one
    stand-in, so published files stay diffable across reads and two setups
    stay distinguishable — without the real serials leaving the building.
    """
    if not real:
        return real
    digest = hashlib.sha256(real.encode("ascii", "replace")).hexdigest()
    digits = "".join(str(int(c, 16) % 10) for c in digest)
    prefix = "".join(c for c in real[:2] if c.isalpha()).upper() or "A0"
    return (prefix + digits)[: len(real)]


def _readings(raw: dict, fingerprint: dict) -> dict:
    """Return the values in a form that can be published.

    What makes the raw file private is the serial, the host and the exact
    time: a timestamped set of live power, battery and meter readings is a
    statement about when somebody was at home. Replace the serial, drop the
    host, and round the time to the day, and what is left is a decoding
    fixture — real values from real hardware, which is what proves a scale
    factor or a word order right in a way synthesised numbers cannot.
    """
    published = {
        "serial": _fake_serial(str(raw.get("serial", ""))),
        "serial_is_a_stand_in": True,
        "read_on": str(raw["read_at"])[:10],
        "unit": raw["unit"],
        "registers": raw["registers"],
    }
    for key in ("device_type_code", "output_type"):
        if key in fingerprint:
            published[key] = fingerprint[key]
    return published


#: The raw reading never goes anywhere else, whatever --save is pointed at.
#: An earlier version wrote all three files to the chosen directory, so
#: `--save doc/fingerprints` — which is what the documentation told people to
#: run — put the real serial number into a directory that gets committed to a
#: public repository. The destination is no longer a choice.
RAW_DIR = Path(".testdata/fingerprints")


def _save(directory: Path, label: str, raw: dict, fingerprint: dict) -> list[Path]:
    """Write the publishable files where asked, and the raw one out of harm's way.

    The raw file carries the real serial, the host and the exact time, so it
    always lands in the gitignored `.testdata/`. The fingerprint records only
    *which* registers answered, which is what the capability table is built
    from and is stable between reads. The readings are the values with the
    serial replaced and the host dropped — publishable, and useful as a
    decoding fixture in a way the fingerprint is not.
    """
    written = []
    directory.mkdir(parents=True, exist_ok=True)
    for suffix, payload in (
        ("capabilities", fingerprint),
        ("readings", _readings(raw, fingerprint)),
    ):
        path = directory / f"{label}.{suffix}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        written.append(path)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"{label}.raw.json"
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")
    written.append(raw_path)
    return written


async def cmd_capabilities(args: argparse.Namespace) -> int:
    """Print one device's capability fingerprint, for comparing setups."""
    ModbusError, ModbusTcpParams, ModbusConnection = _require_library()

    conn = ModbusConnection(
        ModbusTcpParams(host=args.host, port=args.port), timeout=args.timeout
    )
    unit = conn.for_unit(args.unit)
    raw: dict[str, object] = {
        "host": args.host,
        "port": args.port,
        "unit": args.unit,
        "read_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "registers": {},
    }
    fingerprint: dict[str, object] = {
        "read_at": raw["read_at"],
        "registers": {},
    }
    print(f"{args.host}:{args.port} unit {args.unit}")
    try:
        try:
            serial = await unit.read_input_registers(4989, 10)
            text = b"".join(int(v).to_bytes(2, "big") for v in serial)
            decoded = text.decode("ascii", "replace").strip("\x00")
            raw["serial"] = decoded
            print(f"  {'serial':<38}{decoded}")
        except (ModbusError, TimeoutError, OSError) as err:
            print(f"  {'serial':<38}unreadable ({type(err).__name__})")

        for label, space, address, count, _axis in FINGERPRINT:
            read = (
                unit.read_input_registers
                if space == "input"
                else unit.read_holding_registers
            )
            try:
                values = list(await read(address, count))
            except (ModbusError, TimeoutError, OSError) as err:
                fingerprint["registers"][label] = "refused"
                print(f"  {label:<38}refused ({type(err).__name__})")
                continue
            raw["registers"][label] = values
            fingerprint["registers"][label] = _classify(values)
            if all(v in UNAVAILABLE for v in values):
                print(f"  {label:<38}unavailable (0x{values[0]:04X})")
                continue
            note = ""
            if label.startswith("device type"):
                note = f"  -> 0x{values[0]:04X}"
                # The model and phase are capability facts, not private ones.
                fingerprint["device_type_code"] = f"0x{values[0]:04X}"
            elif label.startswith("output type"):
                note = f"  -> {OUTPUT_TYPE.get(values[0], 'unknown')}"
                fingerprint["output_type"] = OUTPUT_TYPE.get(values[0], "unknown")
            print(f"  {label:<38}{values}{note}")

        # Devices that live on their own unit ids behind the same endpoint.
        for label, other_unit, address in (
            ("SBR battery module block", 200, 10740),
            ("wallbox serial", 3, 21200),
            ("wallbox serial (direct)", 248, 21200),
        ):
            try:
                values = list(
                    await conn.for_unit(other_unit).read_input_registers(address, 2)
                )
            except (ModbusError, TimeoutError, OSError):
                fingerprint["registers"][f"unit {other_unit} {label}"] = "no answer"
                print(f"  unit {other_unit:<4} {label:<32} no answer")
                continue
            raw["registers"][f"unit {other_unit} {label}"] = values
            fingerprint["registers"][f"unit {other_unit} {label}"] = "present"
            print(f"  unit {other_unit:<4} {label:<32} {values}")
    finally:
        await conn.close()

    if args.save:
        label = args.label or str(raw.get("serial") or args.host).replace(".", "_")
        for path in _save(Path(args.save), label, raw, fingerprint):
            print(f"  wrote {path}")
    return 0


async def cmd_dump(args: argparse.Namespace) -> int:
    """Read a raw register range, block by block, and record what answered.

    The fingerprint checks registers we already know about. This is for the
    ones we do not: the documented gaps in the wallbox map at 21231-21261 and
    21267-21299, or any range a new model might answer. A block that fails is
    retried one register at a time, so one bad address does not hide the
    fifteen good ones beside it.
    """
    ModbusError, ModbusTcpParams, ModbusConnection = _require_library()

    conn = ModbusConnection(
        ModbusTcpParams(host=args.host, port=args.port), timeout=args.timeout
    )
    unit = conn.for_unit(args.unit)
    read = (
        unit.read_input_registers
        if args.space == "input"
        else unit.read_holding_registers
    )
    found: dict[int, int] = {}
    unavailable: list[int] = []
    refused: list[int] = []

    print(
        f"{args.host}:{args.port} unit {args.unit}, {args.space} "
        f"{args.start}-{args.start + args.count - 1} (protocol addresses)"
    )
    try:
        for block_start in range(args.start, args.start + args.count, args.block):
            size = min(args.block, args.start + args.count - block_start)
            try:
                values = list(await read(block_start, size))
            except (ModbusError, TimeoutError, OSError):
                values = None
            if values is None:
                for address in range(block_start, block_start + size):
                    try:
                        single = list(await read(address, 1))
                    except (ModbusError, TimeoutError, OSError):
                        refused.append(address)
                        continue
                    if single[0] in UNAVAILABLE:
                        unavailable.append(address)
                    else:
                        found[address] = single[0]
                continue
            for offset, value in enumerate(values):
                address = block_start + offset
                if value in UNAVAILABLE:
                    unavailable.append(address)
                else:
                    found[address] = value
    finally:
        await conn.close()

    for address, value in sorted(found.items()):
        print(f"  {address:<8}(reg {address + 1:<8}) 0x{value:04X}  {value}")
    print(
        f"  {len(found)} answered, {len(unavailable)} unavailable, "
        f"{len(refused)} refused"
    )

    if args.save:
        directory = Path(args.save)
        directory.mkdir(parents=True, exist_ok=True)
        label = args.label or f"{args.host.replace('.', '_')}-{args.space}-{args.start}"
        path = directory / f"{label}.dump.json"
        path.write_text(
            json.dumps(
                {
                    "host": args.host,
                    "port": args.port,
                    "unit": args.unit,
                    "space": args.space,
                    "read_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "values": {str(a): v for a, v in sorted(found.items())},
                    "unavailable": sorted(unavailable),
                    "refused": sorted(refused),
                },
                indent=2,
            )
            + "\n"
        )
        print(f"  wrote {path}")
    return 0


def main() -> int:
    """Parse arguments and run the requested probe."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_mdns = sub.add_parser("mdns", help="see what the LAN advertises over mDNS")
    p_mdns.add_argument("--seconds", type=float, default=8.0)
    p_mdns.set_defaults(func=cmd_mdns)

    p_sweep = sub.add_parser("sweep", help="find hosts with a Modbus port open")
    p_sweep.add_argument("subnet", help="for example 192.168.1.0/24")
    p_sweep.add_argument("--port", type=int, default=502)
    p_sweep.add_argument("--timeout", type=float, default=1.0)
    p_sweep.add_argument("--concurrency", type=int, default=512)
    p_sweep.add_argument("--max-hosts", type=int, default=4096)
    p_sweep.set_defaults(func=cmd_sweep)

    p_units = sub.add_parser("units", help="find Modbus units behind one host")
    p_units.add_argument("host")
    p_units.add_argument("--port", type=int, default=502)
    p_units.add_argument("--timeout", type=float, default=3.0)
    p_units.set_defaults(func=cmd_units)

    p_caps = sub.add_parser(
        "capabilities", help="fingerprint one device, for comparing test setups"
    )
    p_caps.add_argument("host")
    p_caps.add_argument("--port", type=int, default=502)
    p_caps.add_argument("--unit", type=int, default=1)
    p_caps.add_argument("--timeout", type=float, default=5.0)
    p_caps.add_argument(
        "--save",
        nargs="?",
        const=".testdata/fingerprints",
        help="write <label>.raw.json and <label>.capabilities.json to this "
        "directory (default .testdata/fingerprints, which is gitignored)",
    )
    p_caps.add_argument(
        "--label", help="name the files after this instead of the serial"
    )
    p_caps.set_defaults(func=cmd_capabilities)

    p_dump = sub.add_parser(
        "dump", help="read a raw register range, to explore undocumented gaps"
    )
    p_dump.add_argument("host")
    p_dump.add_argument("--start", type=int, required=True, help="protocol address")
    p_dump.add_argument("--count", type=int, default=64)
    p_dump.add_argument("--space", choices=("input", "holding"), default="input")
    p_dump.add_argument("--unit", type=int, default=1)
    p_dump.add_argument("--block", type=int, default=16)
    p_dump.add_argument("--port", type=int, default=502)
    p_dump.add_argument("--timeout", type=float, default=5.0)
    p_dump.add_argument("--save", nargs="?", const=".testdata/dumps")
    p_dump.add_argument("--label")
    p_dump.set_defaults(func=cmd_dump)

    args = parser.parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
