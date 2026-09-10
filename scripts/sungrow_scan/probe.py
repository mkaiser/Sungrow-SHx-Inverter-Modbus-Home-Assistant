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
    python scripts/sungrow_scan/probe.py mdns
    python scripts/sungrow_scan/probe.py sweep 192.168.1.0/24 [--port 502]
    python scripts/sungrow_scan/probe.py units <host> [--port 502]
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
import shlex
import sys
import time
from typing import NamedTuple

MODBUS_PORTS = (502, 503)

#: Unit ids worth trying before any wider scan, with what convention says they
#: are. A device is still identified by what answers, never by its address.
CANDIDATE_UNITS: dict[int, str] = {
    1: "inverter (default)",
    # Measured on two WiNet-S dongles: the SBR answers here, not at 200. The
    # specification says as much -- "the battery communication address will be
    # the WiNet internal forwarding address" -- without saying what it is.
    2: "inverter slave, or an SBR battery via WiNet-S",
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
    """Browse every mDNS service type and report anything Sungrow-shaped.

    The one command in this file that needs a third-party package and cannot
    fall back: `zeroconf` implements multicast DNS-SD, which the standard
    library does not. Everything else here works from an unpacked zip, so a
    traceback from this one would read as "the directory is broken" -- hence
    a sentence naming the alternative, which is the sweep.
    """
    try:
        from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf
        from zeroconf.asyncio import AsyncZeroconf
    except ModuleNotFoundError:
        print(
            "mDNS discovery needs the zeroconf package, which is not installed.\n\n"
            "  Sweep the network instead:  "
            f"python {_script_name()} sweep 192.168.1.0/24\n\n"
            "A sweep finds an inverter that mDNS would have found and several\n"
            "it would not: a WiNet-S announces itself, an inverter's own LAN\n"
            "port does not announce anything at all."
        )
        return 1

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

    # One rewriting line rather than ten printed ones: the old version put a
    # percentage into the report every 10%, which is both less informative
    # than a bar and permanent clutter in a redirected log.
    bar = _Progress(f"probing {net}", len(hosts))
    hits = 0

    async def counted(ip):
        nonlocal hits
        result = await check(ip)
        if result:
            hits += 1
        bar.step(f"{hits} open" if hits else "")
        return result

    print(f"Sweeping {len(hosts)} addresses in {net} on port {args.port}...")
    print(
        f"{args.concurrency} at a time, {args.timeout:.0f}s timeout. Over a VPN, "
        f"lower the concurrency and raise the timeout: 512 connections at once "
        f"through a tunnel queue behind each other, and a host that answers in "
        f"200ms gets reported closed.",
        flush=True,
    )
    t0 = time.perf_counter()
    results = await asyncio.gather(*(counted(ip) for ip in hosts))
    elapsed = time.perf_counter() - t0
    bar.finish()
    live = [ip for ip in results if ip]
    print(
        f"{len(live)} answered in {elapsed:.1f}s ({len(hosts) / elapsed:.0f} probes/s)"
    )
    for ip in live:
        print(f"  {ip}:{args.port}")
    return 0 if live else 1


def have_library() -> bool:
    """Whether the device library is importable in this run.

    Asked rather than assumed, and said out loud in the output, because the
    two stacks are not equivalent for every purpose: `modbus-connection`
    rejects a padded frame exactly as the integration does, which is the
    behaviour a block read test is measuring. A survey's *readings* are
    identical either way -- `tests/test_portable_readings.py` requires it --
    but a reader of a document should still know which client took it.
    """
    try:
        import modbus_connection  # noqa: F401

        import sungrow_modbus  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def _require_library() -> tuple:
    """Return the Modbus stack this run will use, preferring the library.

    This used to refuse to run without `modbus-connection` and point at the
    other script. It no longer has to: `portable.py` grew a client with the
    same shape -- `for_unit`, `read_input_registers`,
    `read_holding_registers`, `close` -- so every command here works with
    nothing installed, which is what makes this directory shippable as a zip.

    The library is still preferred where it exists. It is the client the
    integration uses, so a refusal it reports is a refusal a user will
    actually see, and it is the one whose block pooling the plan was recorded
    from.
    """
    try:
        from modbus_connection import ModbusError, ModbusTcpParams
        from modbus_connection.tmodbus import ModbusConnection
    except ModuleNotFoundError:
        from portable import ModbusError, PortableConnection, PortableParams

        return ModbusError, PortableParams, PortableConnection
    return ModbusError, ModbusTcpParams, ModbusConnection


def _modbus_error() -> type[Exception]:
    """Return the exception class a failed read raises on this run's stack.

    Every `except (ModbusError, TimeoutError, OSError)` in this file needs
    it, and which class it is depends on which client is installed. Asking
    here rather than importing at each site is what let the fallback be one
    change instead of five -- and the first attempt missed two of the five,
    which a zip user would have met as a ModuleNotFoundError three seconds
    into a survey.
    """
    try:
        from modbus_connection import ModbusError
    except ModuleNotFoundError:
        from portable import ModbusError

    return ModbusError


def _model_for(device_type_code: int | None) -> str | None:
    """Name an inverter from its device type code, library or not."""
    if have_library():
        from sungrow_modbus import model_for

        return model_for(device_type_code)
    from portable import load_plan, model_for

    return model_for(load_plan(), device_type_code)


class BatteryMatch(NamedTuple):
    """A Sungrow pack matched by capacity, in one shape for both stacks."""

    name: str
    capacity_kwh: float


def _battery_model_for_capacity(capacity_kwh: float | None) -> BatteryMatch | None:
    """Name a Sungrow pack from its rated capacity, library or not."""
    if have_library():
        from sungrow_modbus import model_for_capacity

        model = model_for_capacity(capacity_kwh)
        if model is None:
            return None
        return BatteryMatch(model.name, model.capacity_kwh)
    from portable import battery_model_for_capacity, load_plan

    row = battery_model_for_capacity(load_plan(), capacity_kwh)
    if row is None:
        return None
    return BatteryMatch(row["name"], row["capacity_kwh"])


async def cmd_units(args: argparse.Namespace) -> int:
    """Ask each candidate unit id what it is, using the device library."""
    ModbusError, ModbusTcpParams, ModbusConnection = _require_library()

    total = len(CANDIDATE_UNITS) * len(IDENTITY_PROBES)
    print(f"Probing {args.host}:{args.port} for devices.")
    print(
        f"{len(CANDIDATE_UNITS)} unit ids x {len(IDENTITY_PROBES)} probes = {total} "
        f"reads, up to {args.retries} attempts each at a {args.timeout:.0f}s timeout. "
        f"Worst case {total * args.retries * args.timeout / 60:.0f} min if nothing "
        f"answers at all.\n"
    )
    # One connection for every probe: these units share a link in the real
    # integration too, and opening one per probe is what overwhelms a WiNet-S.
    connection = ModbusConnection(
        ModbusTcpParams(host=args.host, port=args.port), timeout=args.timeout
    )
    answered = 0
    try:
        for index, (unit_id, convention) in enumerate(CANDIDATE_UNITS.items(), 1):
            print(
                f"[{index}/{len(CANDIDATE_UNITS)}] unit {unit_id} -- {convention}",
                flush=True,
            )
            unit = connection.for_unit(unit_id)
            kinds = []
            for space, address, count, label in IDENTITY_PROBES:
                read = (
                    unit.read_input_registers
                    if space == "input"
                    else unit.read_holding_registers
                )
                # Retried, because a device that accepts one Modbus session at
                # a time drops this one whenever something else is polling it,
                # and a single timeout would be published as "no such device".
                values, error = None, None
                for attempt in range(1, args.retries + 1):
                    try:
                        values = list(await read(address, count))
                        break
                    except (ModbusError, TimeoutError, OSError) as err:
                        error = err
                        if attempt < args.retries:
                            await asyncio.sleep(1.0)
                # Every outcome is printed, not just the useful ones. A silent
                # unit and a unit that refused the address are different
                # facts, and only saying "ANSWERED" left the difference
                # invisible -- which is what sent this session off to write
                # throwaway probes beside the script instead of using it.
                if values is None:
                    print(f"      {label:<32} -- {type(error).__name__}")
                elif any(v not in (0, 0xFFFF) for v in values):
                    print(f"      {label:<32} == {values}")
                    kinds.append(f"{label}={values}")
                else:
                    print(f"      {label:<32} -- answered, but empty: {values}")
            if kinds:
                answered += 1
                print(f"  --> unit {unit_id} IS A DEVICE: {'; '.join(kinds)}\n")
            else:
                print(f"  --> unit {unit_id}: nothing here\n")
    finally:
        await connection.close()
    print(f"{answered} of {len(CANDIDATE_UNITS)} candidate unit ids answered.")
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
    # 0.01 kWh per count. Only meaningful for telling SBR from SBH once unit
    # 200 has established that the pack is a Sungrow one at all.
    ("battery capacity (5639)", "input", 5638, 1, "battery"),
    ("firmware block (13250, spec V1.1.7+)", "input", 13249, 1, "firmware"),
    # Sungrow states the 6100-6195 block is not forwarded by a WiNet-S over
    # TCP/IP, so whether it answers says which way in we came.
    ("PV power of today (6100, direct-only)", "input", 6099, 2, "transport"),
    ("PV power limitation (13018, V1.1.10+)", "holding", 13017, 1, "firmware"),
]

#: Firmware strings, which decide more than the model does: which registers a
#: device answers moves between versions, so a fingerprint without them cannot
#: be compared to another taken a year later.
#:
#: `communication module` is also the second of the two connection signals.
#: A direct-LAN inverter has no module and returns the specification's UTF-8
#: unavailable, which is an empty string; anything behind a WiNet-S names it.
FIRMWARE: list[tuple[str, str, int, int]] = [
    ("arm", "input", 4953, 15),
    ("dsp", "input", 4968, 15),
    ("inverter", "input", 13249, 15),
    ("communication_module", "input", 13264, 15),
    ("battery", "input", 13279, 15),
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


#: What a stand-in serial always starts with, and cannot occur in a real one.
#: `_fake_serial` writes it; `_derive_label` requires it before putting the
#: value in a filename.
STAND_IN_PREFIX = "anon-"


def _fake_serial(real: str) -> str:
    """Return a stable stand-in for a serial, that cannot be read as one.

    Deriving it from a hash rather than at random means one machine always
    maps to one stand-in, so published files stay diffable across reads and
    two setups stay distinguishable -- without the real serials leaving the
    building.

    **It used to keep the real serial's leading letters**, on the reasoning
    that a Sungrow serial is ASCII across ten registers and a stand-in of the
    same shape keeps the published reading exercising the string decoder.
    That was a bad trade: `A123456789` became `A5155200572`, which is not a
    serial and looks exactly like one. Somebody quoting it into an issue, or
    searching for it, or comparing it against a label on a wall, gets a
    plausible wrong answer -- and the field being called
    `serial_anonymized_hashed` does not help once the value has been copied
    out of it.

    So the value says what it is. `anon-` cannot appear in a Sungrow serial,
    which makes the string self-describing wherever it ends up, and the digits
    after it are the same stable derivation as before.
    """
    if not real:
        return real
    digest = hashlib.sha256(real.encode("ascii", "replace")).hexdigest()
    digits = "".join(str(int(c, 16) % 10) for c in digest)
    # As many digits as the real serial had, so two setups stay as
    # distinguishable as they were, behind a prefix no Sungrow serial can
    # carry.
    return f"{STAND_IN_PREFIX}{digits[: len(real)]}"


#: Bumped when the shape changes, so a reader can tell a document written
#: before the two files were merged from one written after. 4 added `comment`
#: and `ip_address_last_octet`, the latter a zero-filled string, not a number.
#: 5 gathered everything a person typed into one `user_inputs` section at the
#: top, so that the boundary between what a device said and what somebody
#: claimed is a structural property of the file rather than something a reader
#: has to know from suffixes on four scattered keys. 6 added `read_at_local`
#: and dropped `transport_disagrees_with_measurement`, which was neither a
#: user input nor a measurement but a comparison of the two. 7 added
#: `modbus_proxy`, which changes how the whole document should be read. 8
#: replaced `collected_by`, which named the tool, with `command_line`, which
#: is the whole invocation and reproduces the reading -- **with the host
#: replaced by a placeholder**, because the document exists not to carry it.
#: 9 replaced `ip_address_last_octet` with `ip_address_last_two_octets`, which
#: is only filled in when its owner said it could be: the third octet is what
#: separates one contributor's network from another's, so it is asked for
#: rather than taken, and withheld as `xxx.xxx` otherwise. 10 prefixed the
#: stand-in serial with `anon-`, because keeping the real serial's leading
#: letters turned `A123456789` into `A5155200572` -- not a serial, and
#: indistinguishable from one. 11 renamed `provided_by` to `reporter`: the
#: field names a person, and "provided by" described the transaction rather
#: than them. 12 changed what the *filename* says about a device, which is
#: recorded here because a document is found by its name: the identity word
#: is now the document's own `serial_anonymized_hashed` rather than
#: `sha256(real serial)[:6]`, so a name can be checked against the file
#: -- the two used to be different derivations of one serial that shared
#: four characters by chance -- and a firmware word follows it, because which
#: registers a device answers moves between versions and the version was in
#: the file but not in the name anybody sorts by. 12 also stopped publishing
#: the *values* of a probe named for a serial: `unit 3 wallbox serial` was
#: carrying `[16690, 13633]`, which decodes to `A25A`. 13 added the `wallbox`
#: section: the whole register space of a wallbox that answered, masked at its
#: own serial, because Sungrow publishes no register document for these at all
#: and a document saying only "a wallbox answered" recorded none of what it
#: holds. 14 decoded that dump in place -- 32 named readings, each carrying the
#: register it came from and how many independent sources hold it, so the
#: section says what the wallbox *is* and what it is *doing* rather than only
#: which addresses answered. 16 added `block_read_test`: which of the
#: integration's block reads this device answered, which never did, and which
#: answered only sometimes. That measurement is the one `scripts/layout.py` is
#: ever changed from, and until now it existed only in the transcript -- the
#: file a contributor is told to keep, because it carries their real address.
#: So a submitted document carried no block evidence at all. 15 added
#: `battery_pack`, which closes the same
#: gap for the SBR: the survey probed unit 200 and unit 2 with a
#: two-register read, recorded "present", and stopped -- so no document
#: anywhere carried a single battery reading, and whether a WiNet-S withholds
#: the per-module cell data stayed open on one path's evidence until somebody
#: read nine registers by hand. It is `battery_pack` and not `battery`
#: because that key already holds what the owner *typed* about their
#: battery, and the first attempt overwrote their testimony with a
#: measurement.
SCHEMA = 16

#: Keys of the connection block that carry a claim rather than a measurement.
#: They are moved into `user_inputs`, so the published `connection` holds only
#: what was read off the wire.
CLAIMED_CONNECTION_KEYS = ("reported_by_hand",)

#: Whether a Modbus proxy is in the path, as the contributor understands it.
#: `unknown` is a real answer and the default: somebody who does not know what
#: a Modbus proxy is almost certainly has not installed one, but "probably
#: not" is not a measurement and must not be recorded as one.
PROXY_ANSWERS: dict[str, str] = {
    "yes": "yes -- modbus-proxy, evcc's proxy, a Home Assistant add-on",
    "no": "no, this talks straight to the inverter",
    "unknown": "I do not know what that is",
}

#: Where the contributors are. Used only to render a local time beside the UTC
#: one, so that two readings taken minutes apart can be told apart and ordered
#: without a reader doing timezone arithmetic in their head.
LOCAL_ZONE = "Europe/Berlin"


class Reading(NamedTuple):
    """Everything one pass over a device produced, for a caller to summarise.

    `cmd_capabilities` used to build all of this and then throw it away behind
    `return 0`, so anything wanting to report on a run had to read the
    registers again. The summary in `collect.py` renders from `document`
    specifically: every claim it makes is then a value that was actually
    published, rather than a third source of truth that could drift from both.
    """

    raw: dict
    fingerprint: dict
    document: dict
    written: list[Path]
    missing: list[str]


#: This script's own path, as a fingerprint records it. One constant because
#: it is written into every document and asserted in the tests, and because it
#: has already moved once: `scripts/discover_probe.py` until 2026-09-08.
SCRIPT = "scripts/sungrow_scan/probe.py"


def _run_command(script: str) -> str:
    """Return a command for a sibling script that will actually work.

    Three ways the obvious version was wrong, all of them found by somebody
    following it: it named an absolute `/workspaces/...` path, which is this
    container's and nobody else's; it said `python`, which on most systems is
    `python3` or nothing at all; and it pointed at a file that was not
    executable, so the shebang was no help either.

    So: relative to the working directory when the script is underneath it,
    and `python3`, which is the name that exists everywhere this runs.
    """
    here = Path(__file__).resolve().parent / script
    try:
        shown = here.relative_to(Path.cwd())
    except ValueError:
        shown = here
    return f"python3 {shown}"


def _script_name() -> str:
    """Return this script the way the person running it would type it.

    `command_line` exists so a reading can be repeated, so it has to name the
    path that actually works where the reading was taken. Inside the checkout
    that is the repository path; unpacked from the zip there is no `scripts/`
    directory above it and the command is `python probe.py`. Printing the
    repository path there would be an instruction that fails.
    """
    here = Path(__file__).resolve()
    if here.parent.name == "sungrow_scan" and here.parent.parent.name == "scripts":
        return SCRIPT
    return here.name


#: Flags that shape what was collected, in the order they read best. `--save`
#: and `--label` are left out on purpose: they are local paths and a filename,
#: and they say nothing about the reading.
INVOCATION_FLAGS = (
    ("--port", "port"),
    ("--unit", "unit"),
    ("--timeout", "timeout"),
    ("--passes", "passes"),
    ("--transport", "transport"),
    ("--proxy", "proxy"),
    ("--reporter", "reporter"),
    ("--battery", "battery"),
    ("--comment", "comment"),
)


def _invocation(args: object | None) -> str:
    """Return the command that would reproduce this reading.

    Rebuilt from the parsed arguments rather than copied from `sys.argv`, for
    a reason that matters more than tidiness: most of these documents are
    collected by answering prompts, where there is no command line at all.
    Reconstructing it means an interactive session still publishes something
    somebody can run -- their own reading, repeated, or a contributor's setup
    reproduced on request.

    **The host is a placeholder.** The whole document is built around not
    carrying the address, so quoting the real command would undo that in the
    first line; `ip_address_last_octet` is the deliberate exception and stays
    the only one. Values are shell-quoted, so a comment with spaces or an
    apostrophe pastes back intact.
    """
    script = _script_name()
    if args is None:
        return f"{script} capabilities <host>"

    parts = [script, "capabilities", "<host>"]
    for flag, attribute in INVOCATION_FLAGS:
        value = getattr(args, attribute, None)
        if value is None or value == "":
            continue
        if isinstance(value, float):
            value = f"{value:g}"
        parts += [flag, shlex.quote(str(value))]
    if getattr(args, "dump", False):
        parts.append("--dump")
    return " ".join(parts)


def _address_tail(raw: dict) -> str:
    """Return the address tail if its owner allowed it, else `xxx.xxx`.

    Observed rather than claimed -- this is the address that answered -- so it
    stays out of `user_inputs`. What *is* a user input is the permission, and
    without it the value is withheld rather than guessed at.
    """
    if raw.get("address_detail") != "two_octets":
        return ADDRESS_HIDDEN
    return _last_two_octets(str(raw.get("host", ""))) or ADDRESS_HIDDEN


def _local_time(read_at: str) -> str:
    """Render a UTC timestamp in the contributors' own timezone, with offset.

    Falls back to the UTC string unchanged if the zone database is missing,
    which it can be on a slim container -- a wrong local time would be worse
    than an honest UTC one, and the offset in the value says which it is.
    """
    from datetime import datetime

    try:
        from zoneinfo import ZoneInfo

        moment = datetime.fromisoformat(read_at).astimezone(ZoneInfo(LOCAL_ZONE))
    except (ValueError, KeyError, ModuleNotFoundError):
        return read_at
    return moment.isoformat(timespec="seconds")


#: Fields never published, whatever else is. Anything whose name mentions a
#: serial: the whole point of the stand-in is that the real one does not leave
#: `.testdata/`, and a full sweep of the map would otherwise walk straight
#: into `sungrow_inverter_serial`.
NEVER_PUBLISH = ("serial",)


#: Attempts for a read whose loss changes the *filename*: the serial, the
#: device type code, the output type and the 6100 transport signal. A busy
#: inverter beat three attempts repeatedly on one measured machine, and each
#: time the published name quietly lost a part -- its hash, its phase word, or
#: worse, it gained a `winet` it had not earned. More attempts, spread wider,
#: because the collision is a moment and not a state.
IDENTITY_ATTEMPTS = 6


async def _async_read_retrying(
    read, address: int, count: int, attempts: int = 3
) -> list[int]:
    """Read one block, retrying a dropped link before giving up.

    A capability probe's answer is published, and "refused" reads as evidence
    that the inverter has no such register. It is not: on a device that
    accepts very few Modbus sessions, another client polling at the same
    moment produces exactly that. The reference SH10RT published MPPT3 as
    "refused" for precisely this reason, when the truth -- established on the
    same machine, twice -- is that it answers 0xFFFF.
    """
    ModbusError = _modbus_error()

    for attempt in range(1, max(1, attempts) + 1):
        try:
            return list(await read(address, count))
        except (ModbusError, TimeoutError, OSError):
            if attempt >= attempts:
                raise
            await asyncio.sleep(1.5)
    raise AssertionError("unreachable")


#: Address bands worth dumping raw, with why each is here. Protocol
#: addresses, so one below the register number in Sungrow's document.
#:
#: Bands rather than the whole space: a blind sweep of 0-40000 is some 300
#: reads, almost all of them "Reserved", and every one is a chance to drop the
#: link on a device that grants few sessions. These are the neighbourhoods the
#: specification and the YAML package actually use, plus the two that have
#: already paid for themselves -- 6100, which decides the transport, and
#: 33000-33200, where registers nothing documents were found reading 200 W and
#: 100 W.
DUMP_BANDS: tuple[tuple[str, int, int, str], ...] = (
    ("input", 2580, 80, "the 26xx firmware strings"),
    ("input", 4949, 210, "identity, firmware, AC and DC basics"),
    ("input", 5600, 160, "meter and battery"),
    ("input", 6099, 100, "the block a WiNet-S does not forward"),
    ("input", 10740, 60, "an SBR's own registers, when it answers here"),
    ("input", 12999, 110, "the 13xxx measurements"),
    ("input", 13199, 160, "meter channel 2 and the firmware block"),
    ("holding", 4999, 60, "holding-side identity"),
    ("holding", 12999, 110, "the 13xxx settings"),
    ("holding", 31200, 60, "the active-power-limit block"),
    ("input", 33000, 200, "undocumented, and known to hold real values"),
    # The same band on the holding side, which is where the registers this
    # project actually uses there live: battery max charge and discharge power
    # at 33047-33048, and the charge/discharge start thresholds at
    # 33149-33150. The first dump asked for 33000 on the *input* side only and
    # missed all four -- and got 200 answers back from the input space
    # regardless, which is its own thing worth having on record.
    ("holding", 33000, 200, "battery power limits and start thresholds"),
)

#: Never published raw, whatever band covers it: the serial number's ten
#: registers. The document carries a stand-in precisely so the real one stays
#: out, and a raw dump would hand it over in words instead of characters.
DUMP_MASKED: tuple[tuple[str, int, int], ...] = (("input", 4989, 10),)

#: The wallbox's own registers, read at the unit that answered for it. Its
#: register space is the least documented thing this project touches -- Sungrow
#: publishes nothing for the AC wallboxes at all -- so a fingerprint that says
#: only "a wallbox answered" throws away the one chance to record what it
#: holds. What is known is in `doc/wallbox_registers.md`, which compares this
#: measurement against the two projects that made their own.
#:
#: The bands are **measured**, on an AC22E-01 through a WiNet-S on
#: 2026-09-08 -- register 21224 reads 0x3F80, and its 22080 W maximum agrees --
#: input 21201-21280 and 21297-21340 answer, 21281-21296 refuse,
#: and the holding space answers 21201-21248 and scattered addresses up to
#: 21328. Another model may differ; a band that reads nothing costs one
#: refused block and says so, which is the cheaper mistake.
WALLBOX_DUMP_BANDS: tuple[tuple[str, int, int, str], ...] = (
    ("input", 21200, 80, "identity, model, firmware, ratings"),
    ("input", 21296, 44, "the live measurements: state, power, energy"),
    ("holding", 21200, 50, "settings, as far as they answer"),
    ("holding", 21297, 32, "the scattered upper settings"),
)

#: The wallbox's serial, which is a serial like any other. `A25A123456` was
#: published in a fingerprint as the words `[16690, 13633]` before anybody
#: thought about the second device in the house.
WALLBOX_DUMP_MASKED: tuple[tuple[str, int, int], ...] = (("input", 21200, 6),)


#: What the wallbox's registers mean, so a fingerprint carries readings and
#: not only words. Sungrow documents none of this; every line was measured,
#: and `doc/wallbox_registers.md` says by whom -- the `held` field here is
#: that document's confidence mark, travelling with the value so a reader of
#: one file does not have to go and find the other.
#:
#: Addresses, not register numbers: one below what the tables say, as
#: everywhere else in this project. `kind` is how to read the words --
#: `u16`, `u32` (low word first, which is what these are), `ascii`, or an
#: enum named below.
WALLBOX_FIELDS: tuple[tuple, ...] = (
    # (name, space, address, count, kind, scale, unit, held)
    ("model_name", "input", 21215, 5, "ascii", 1, None, "two sources"),
    ("device_type_code", "input", 21223, 1, "hex", 1, None, "two sources"),
    ("phase_count", "input", 21224, 1, "u16", 1, None, "two sources"),
    ("version_string", "input", 21225, 10, "ascii", 1, None, "measured here"),
    ("nominal_voltage", "input", 21261, 1, "u16", 1, "V", "three sources"),
    ("rated_current", "input", 21262, 1, "u16", 0.1, "A", "measured here"),
    ("phase_mode", "input", 21269, 1, "phase_mode", 1, None, "three sources"),
    ("minimum_charging_power", "input", 21271, 1, "u16", 1, "W", "named elsewhere"),
    ("maximum_charging_power", "input", 21272, 1, "u16", 1, "W", "two sources"),
    ("lifetime_energy", "input", 21299, 2, "u32", 1, "Wh", "measured here"),
    ("phase_a_voltage", "input", 21301, 1, "u16", 0.1, "V", "three sources"),
    ("phase_a_current", "input", 21302, 1, "u16", 0.1, "A", "three sources"),
    ("phase_b_voltage", "input", 21303, 1, "u16", 0.1, "V", "three sources"),
    ("phase_b_current", "input", 21304, 1, "u16", 0.1, "A", "three sources"),
    ("phase_c_voltage", "input", 21305, 1, "u16", 0.1, "V", "three sources"),
    ("phase_c_current", "input", 21306, 1, "u16", 0.1, "A", "three sources"),
    ("charging_power", "input", 21307, 2, "u32", 1, "W", "three sources"),
    ("session_energy", "input", 21309, 2, "u32", 1, "Wh", "three sources"),
    ("control_pilot_voltage", "input", 21311, 1, "u16", 0.01, "V", "two sources"),
    # Named for its register precisely because nobody can name it: three
    # independent measurements of this wallbox family, and none of them knows
    # what this is. An entity must not be invented for it.
    ("unnamed_register_21313", "input", 21312, 1, "u16", 1, None, "open"),
    ("start_mode", "input", 21313, 1, "start_mode", 1, None, "two sources"),
    ("power_request", "input", 21314, 1, "u16", 1, None, "named elsewhere"),
    ("power_control_allowed", "input", 21315, 1, "u16", 1, None, "named elsewhere"),
    ("charging_status", "input", 21316, 1, "status", 1, None, "three sources"),
    ("charging_started", "input", 21317, 2, "local_epoch", 1, None, "named elsewhere"),
    ("charging_ended", "input", 21319, 2, "local_epoch", 1, None, "named elsewhere"),
    ("available_current", "input", 21321, 1, "u16", 0.1, "A", "measured here"),
    ("output_current_setting", "holding", 21202, 1, "u16", 0.1, "A", "two sources"),
    (
        "phase_mode_setpoint",
        "holding",
        21203,
        1,
        "phase_mode",
        1,
        None,
        "three sources",
    ),
    ("charger_enabled", "holding", 21210, 1, "enabled", 1, None, "two sources"),
    ("start_stop", "holding", 21211, 1, "start_stop", 1, None, "two sources"),
    ("mileage_per_kwh", "holding", 21231, 1, "u16", 0.1, "km/kWh", "named elsewhere"),
)

#: The enums, kept out of the table above so they can be read as a list. The
#: charging status is the one that cannot be measured: watching a session end
#: shows the register settle on 6, and only a source with the whole table says
#: 6 is *Completed* rather than idle -- a distinction every finished charge
#: depends on.
WALLBOX_ENUMS: dict[str, dict[int, str]] = {
    "status": {
        1: "idle",
        2: "standby",
        3: "charging",
        4: "suspended by the charge point",
        5: "suspended by the vehicle",
        6: "completed",
        7: "reserved",
        8: "disabled",
        9: "fault",
    },
    "phase_mode": {0: "three phase", 1: "single phase"},
    "start_mode": {0: "stopped", 1: "start with EMS", 2: "start by swiping"},
    "enabled": {0: "disabled", 1: "enabled"},
    "start_stop": {0: "start", 1: "stop"},
}


def _wallbox_readings(dump: dict) -> dict:
    """Decode a wallbox dump into named readings, from the dump already read.

    No extra Modbus traffic: the survey reads 206 addresses once and this
    reads them again out of the result. So a fingerprint carries both -- the
    words, for whoever disagrees with an interpretation here, and the
    interpretation, for whoever does not want to decode a JSON object of
    integers by hand.

    Every value keeps the register it came from and the confidence
    `doc/wallbox_registers.md` records. A reading nobody can name is
    published under its register number rather than dropped, because the next
    person to see one may recognise it.
    """
    readings: dict[str, dict] = {}
    for name, space, address, count, kind, scale, unit, held in WALLBOX_FIELDS:
        words = [(dump.get(space) or {}).get(str(address + i)) for i in range(count)]
        if any(word is None for word in words):
            continue
        entry: dict[str, object] = {
            "register": address + 1,
            "held": held,
        }
        if kind == "ascii":
            raw = b"".join(int(word).to_bytes(2, "big") for word in words)
            text = raw.decode("ascii", "replace").strip("\x00").strip()
            if not text:
                continue
            entry["value"] = text
        elif kind == "hex":
            entry["value"] = f"0x{int(words[0]):04X}"
            model = WALLBOX_MODELS.get(int(words[0]))
            if model:
                entry["model"] = model
        elif kind == "u32":
            # Low word first, which is what these are -- read the other way
            # round, a 280 kWh lifetime counter reads as 1.2 GWh.
            value = (int(words[1]) << 16) | int(words[0])
            entry["value"] = round(value * scale, 2) if scale != 1 else value
        elif kind == "local_epoch":
            value = (int(words[1]) << 16) | int(words[0])
            entry["value"] = value
            entry["local_time"] = _wallbox_time(value)
            entry["note"] = "epoch, but the value is the wallbox's local clock"
        elif kind in WALLBOX_ENUMS:
            entry["value"] = int(words[0])
            entry["means"] = WALLBOX_ENUMS[kind].get(int(words[0]), "unknown code")
        else:
            value = int(words[0]) * scale
            entry["value"] = round(value, 2) if scale != 1 else int(value)
        if unit:
            entry["unit"] = unit
        readings[name] = entry
    return readings


def _wallbox_time(value: int) -> str | None:
    """Render a wallbox timestamp, which is local time wearing an epoch's shape.

    Decoded as UTC it reads two hours off in Berlin, and matched the wall
    clock exactly -- so the number is the device's own local time, the same
    quirk the inverter's clock registers have. Rendered without a zone
    suffix, because attaching one would be a claim this cannot support.
    """
    if not value:
        return None
    try:
        return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%dT%H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return None


#: Which wallbox a device type code names. `0x3F80` was read here; the other
#: two come from the projects in `doc/wallbox_registers.md`.
WALLBOX_MODELS: dict[int, str] = {
    0x3F80: "AC22E-01",
    0x20DA: "AC011E-01",
    0x20ED: "AC007-00",
}


class _Progress:
    """A line that rewrites itself while something slow happens.

    Written to **stderr**, so redirecting the report to a file still shows
    progress on the terminal and the file stays clean.

    Two modes, because both matter here. On a terminal it redraws one line.
    Piped -- into a log, or a CI job -- redrawing produces a file full of
    carriage returns, so it prints a line at most every `every` seconds
    instead. Either way the total is known up front: "47 of 48" tells somebody
    whether to wait, and a spinner does not.

    No dependency. `tqdm` would do this better and this script is one users
    run against their own hardware from a checkout, where a pip install is a
    reason not to bother.
    """

    WIDTH = 24

    def __init__(self, label: str, total: int, *, every: float = 3.0) -> None:
        """Start a bar, and draw it once so something appears immediately."""
        self.label = label
        self.total = max(total, 1)
        self.every = every
        self.done = 0
        self.live = sys.stderr.isatty()
        self.last = 0.0
        self._draw("")

    def step(self, note: str = "") -> None:
        """Count one unit of work, and redraw if it is time to."""
        self.done += 1
        now = time.monotonic()
        if self.live or now - self.last >= self.every:
            self.last = now
            self._draw(note)

    def redraw(self, note: str = "") -> None:
        """Re-draw at the same count, to show that slow work is still moving.

        `step` advances the count, which is wrong for work that is *inside*
        one unit -- the dump's fallback to single reads can spend a minute
        below one block, and counting each read would push the bar past its
        own total. This keeps the count honest and the note moving, which is
        the only thing distinguishing slow from stuck.
        """
        now = time.monotonic()
        if self.live or now - self.last >= self.every:
            self.last = now
            self._draw(note)

    def finish(self, note: str = "") -> None:
        """Clear the line, so the report that follows starts clean."""
        if self.live:
            sys.stderr.write("\r" + " " * 78 + "\r")
            sys.stderr.flush()
        elif note:
            print(f"  {self.label}: {note}", file=sys.stderr)

    def _draw(self, note: str) -> None:
        filled = round(self.WIDTH * self.done / self.total)
        bar = "#" * filled + "-" * (self.WIDTH - filled)
        line = f"  {self.label} [{bar}] {self.done}/{self.total}"
        if note:
            line += f"  {note}"
        if self.live:
            sys.stderr.write(f"\r{line[:78]:<78}")
            sys.stderr.flush()
        else:
            print(line, file=sys.stderr)


async def _async_dump_bands(
    unit,
    ModbusError,
    block: int = 32,
    # 600, not 240, now that the budget is enforced per block and can
    # therefore actually stop a run. Measured: the reference SH10RT's dump
    # takes about 300 seconds -- it stops answering rather than refusing, so
    # every unmapped address waits out a timeout -- and it reads 1461 of 1510
    # addresses in that time. At 240 the newly-effective budget would have
    # truncated a dump that completes, which is the opposite of the point.
    budget: float = 600.0,
    bands: tuple = DUMP_BANDS,
    what: str = "register dump",
) -> dict:
    """Read every band raw, one small block at a time.

    Small blocks and per-block tolerance, because the point is coverage: a
    band that fails as a whole tells nobody anything, where a band with eight
    addresses missing from the middle is a map of what this firmware answers.

    **A refused address is not retried.** Refusal is the expected answer over
    most of these bands -- they are mostly "Reserved" -- and the first version
    retried each one with a 1.5 second pause between attempts, which turned a
    few hundred reserved addresses into a run so long it was killed. A dropped
    *block* is still retried, because that is the case where the address might
    have answered.

    Bounded by `budget` seconds. A dump is a nice-to-have appended to a report
    that is already complete, so it gives up rather than holding the whole run
    hostage, and says which bands it never reached.
    """
    dump: dict[str, dict[str, int | None]] = {}
    skipped: list[str] = []
    started = time.perf_counter()
    print(f"  {'':<38}reading these ranges, as register numbers:")
    for space, start, count, why in bands:
        print(f"  {'':<38}  {space:<8}{start + 1}-{start + count:<7} {why}")
    print(f"  {'':<38}Most of these addresses are 'Reserved' and answer nothing.")
    print(f"  {'':<38}A block that fails is retried one register at a time, and")
    print(f"  {'':<38}an address that does not answer costs a whole timeout -- so")
    print(f"  {'':<38}the bar can sit on one block for a minute. It says which")
    print(f"  {'':<38}register it is waiting on and for how long.")
    # Counted in blocks, which is what the loop below actually does. A
    # refused block falls back to reading its addresses one at a time, so the
    # bar can slow down without stalling -- and the note says which band, so a
    # long pause is attributable rather than mysterious.
    blocks = sum(len(range(0, count, block)) for _space, _start, count, _why in bands)
    bar = _Progress(what, blocks)
    for space, start, count, why in bands:
        if time.perf_counter() - started > budget:
            skipped.append(f"{space} {start}+{count} ({why})")
            for _ in range(0, count, block):
                bar.step("skipped, out of budget")
            continue
        read = (
            unit.read_input_registers
            if space == "input"
            else unit.read_holding_registers
        )
        into = dump.setdefault(space, {})
        for offset in range(0, count, block):
            # Checked per **block**, not only per band. Per band alone, the
            # budget cannot interrupt the band it is already inside -- and on
            # the reference SH10RT the first band spent minutes on a single
            # 80-address range, because that inverter stops answering rather
            # than refusing and every read waits out its own timeout. The
            # budget then cut the remaining eleven bands and the one that had
            # already overrun was untouched, which is the opposite of what a
            # budget is for. Worse, the save comes after the dump: a run that
            # overruns its outer timeout here loses a complete reading that
            # had already succeeded.
            if time.perf_counter() - started > budget:
                if f"{space} {start}+{count} ({why})" not in skipped:
                    skipped.append(f"{space} {start}+{count} ({why}), part read")
                for _ in range(offset, count, block):
                    bar.step("out of budget")
                break
            size = min(block, count - offset)
            address = start + offset
            # Stepped here rather than after the read, because the read has
            # two exits: a block that answers, and one that falls back to
            # reading its addresses singly and then `continue`s. Counting
            # attempts keeps the bar honest on both, and the slow path shows
            # as a pause on a step that is already drawn.
            bar.step(why)
            try:
                words = await _async_read_retrying(read, address, size, 2)
            except (ModbusError, TimeoutError, OSError):
                # Down to single reads, one attempt each: one refused address
                # in a block of 32 would otherwise hide the 31 that answer.
                #
                # The bar is re-drawn *inside* this loop, and it is worth a
                # line of code: the fallback can take 32 timeouts on an
                # inverter that stops answering rather than refusing, and the
                # bar used to sit unchanged for minutes on end. It read as a
                # hung tool -- convincingly enough that I killed a run that
                # had in fact already finished. Whoever runs this on their
                # own house gets no transcript to check afterwards, so a
                # progress bar that lies about being stuck is worse than none.
                fell_back = time.perf_counter()
                for number, single in enumerate(range(address, address + size), 1):
                    # Registers, not addresses, and the elapsed seconds. The
                    # first version said "1/18" and nothing else, and somebody
                    # watching it reasonably asked what the numbers meant and
                    # whether it had hung. An address that does not answer
                    # costs a whole timeout, so the honest thing is to say
                    # which register is being waited on and for how long.
                    waited = time.perf_counter() - fell_back
                    bar.redraw(
                        f"{why} -- reg {single + 1} alone, {number} of {size}, "
                        f"{waited:.0f}s in this block"
                    )
                    try:
                        value = await _async_read_retrying(read, single, 1, 1)
                    except (ModbusError, TimeoutError, OSError):
                        into[str(single)] = None
                    else:
                        into[str(single)] = value[0]
                continue
            for index, word in enumerate(words):
                into[str(address + index)] = word
    bar.finish()
    if skipped:
        dump["bands_not_reached"] = skipped  # type: ignore[assignment]
    return dump


def _masked_dump(dump: dict, mask: tuple = DUMP_MASKED) -> dict:
    """Return the dump with the serial's registers removed.

    The mask is a parameter because there is more than one serial in a house:
    the inverter's at input 4990, and the wallbox's at input 21201 on its own
    unit. The second one was published as raw words before anybody thought
    about the device attached to the inverter, so the masking is now applied
    by whoever writes a dump rather than assumed to be the inverter's.
    """
    masked = {
        space: (dict(values) if isinstance(values, dict) else values)
        for space, values in dump.items()
    }
    for space, start, count in mask:
        for address in range(start, start + count):
            if str(address) in masked.get(space, {}):
                masked[space][str(address)] = None
    return masked


async def _async_field_by_field(
    unit, component_class, ModbusError, sweeps: int = 3
) -> tuple[dict[str, object], list[str]]:
    """Read a component's fields one at a time, tolerating the ones that fail.

    The fallback for a component that will not update as a whole. A
    `Component` either updates or raises, and the library pools neighbouring
    registers, so **one** unanswerable register empties every field beside it:
    a measured SH8.0RT-V112 refused five scattered addresses inside the
    13002-13046 energy block and lost all 33 of `slowest_input`'s fields for
    it, on a machine whose WiNet-S served every one of them.

    Reducing `max_gap` does not help, because the all-or-nothing is in the
    component and not in the block plan. So each field is given a component
    of its own -- built here from the same descriptor object, so the address,
    scale, word order and sentinel are exactly the declared ones -- and read
    alone. What comes back is a component minus only the registers the device
    genuinely will not answer.

    Expensive by design: one read per field instead of a pooled handful, so it
    runs only after the whole-component attempts have failed.
    """
    from modbus_connection.model import Component

    from sungrow_modbus.model import present

    values: dict[str, object] = {}
    pending = dict(component_class.declared_fields)
    # Swept repeatedly, and the reason is a mistake this made on its first
    # run: a single failed read is not a refusal. One sweep of ~90 individual
    # reads on a contended port reported `phase_a_voltage`, `mppt2_voltage`
    # and `inverter_rated_output` as refused, when the curated probes had read
    # all three minutes earlier. Only a field that misses every separated
    # sweep is evidence about the device rather than about the traffic.
    for sweep in range(1, max(1, sweeps) + 1):
        missed_this_sweep: dict[str, object] = {}
        for name, descriptor in pending.items():
            solo_class = type(
                f"Solo_{name}",
                (Component,),
                {"register_space": component_class.register_space, name: descriptor},
            )
            try:
                solo = solo_class(unit)
                await solo.async_update()
            except (ModbusError, TimeoutError, OSError):
                missed_this_sweep[name] = descriptor
            else:
                # `present`, because `Device.field` applies it and these
                # values sit beside its in one report. Without it the same
                # unavailable firmware string reads as None when its block
                # answered and as "" when it was salvaged -- a difference
                # that says nothing about the device and would be compared
                # against other documents as though it did.
                values[name] = present(getattr(solo, name))
        if not missed_this_sweep:
            return values, []
        pending = missed_this_sweep
        if sweep < max(1, sweeps):
            await asyncio.sleep(2.0)
    return values, sorted(pending)


def _plan_battery_units() -> list[int]:
    """Return the unit ids an SBR pack may answer on, from the committed plan.

    200 over the inverter's own LAN port, 2 through a WiNet-S -- measured at
    three houses, and it moves with the transport rather than with the pack.
    Read from `scan_plan.json` because this file runs from a zip where
    `sungrow_modbus.battery` does not exist.
    """
    from portable import load_plan

    try:
        units = load_plan().get("battery_pack_units")
    except Exception:
        units = None
    return [int(unit) for unit in units] if units else [200, 2]


async def _async_battery_readings(connection, unit_id: int) -> dict[str, object]:
    """Read the SBR's own two blocks, on the unit that answered for it.

    The gap this closes: the survey probed unit 200 and unit 2 with a
    two-register read to see *whether* a pack answered, recorded "present",
    and stopped. So no fingerprint anywhere carried a single SBR reading, and
    the question of whether a WiNet-S withholds the per-module cell data
    stayed open for two days on one path's evidence -- while a nine-register
    read would have answered it.

    Forty-two registers in three reads, against an inverter dump of 1510. The
    wallbox had the same gap and was given its own dump for the same reason:
    a rare device whose registers nobody else has measured is exactly the one
    worth carrying.

    The two blocks are read **separately and reported separately**, because
    they fail separately -- measured on one SBR096 read both ways within
    seconds, the cell block refuses through a dongle while the pack block
    answers. Pooled into one read, a document would say the pack was
    unreadable when it was not.
    """
    unit = connection.for_unit(unit_id)
    if not have_library():
        from portable import load_plan, read_fields

        # `role="battery"` selects the two components the plan marks as not
        # being on the inverter's unit. Without it this would read the
        # inverter's own map at unit 200.
        return await read_fields(load_plan(), unit, passes=2, role="battery")

    from modbus_connection import ModbusError

    from sungrow_modbus.battery_registers import (
        SbrBatteryCells,
        SbrBatteryModules,
        SbrBatteryPack,
    )
    from sungrow_modbus.model import present

    values: dict[str, object] = {}
    missed: list[str] = []
    for name, klass in (
        ("sbr_battery_pack", SbrBatteryPack),
        ("sbr_battery_cells", SbrBatteryCells),
        # Twenty-five more registers, and a third component because it fails
        # a third way: a module that is not fitted answers 0 whatever the
        # transport, so an SBR096 reports five empty slots on a perfectly
        # good link.
        ("sbr_battery_modules", SbrBatteryModules),
    ):
        component = klass(unit)
        try:
            await component.async_update()
        except (ModbusError, TimeoutError, OSError) as err:
            missed.append(f"{name} ({type(err).__name__})")
            continue
        for field_name in component.resolved_fields:
            values[field_name] = present(getattr(component, field_name))
        # The unpacked halves too, which are the point of carrying this at
        # all: 780 is not a cell anybody can look up. See
        # `SbrBatteryCells` for the encoding and what it rests on.
        if klass is SbrBatteryCells:
            for field_name in (
                "max_cell_module",
                "max_cell_number",
                "min_cell_module",
                "min_cell_number",
                "max_module_temperature_module",
                "max_module_temperature_sensor",
                "min_module_temperature_module",
                "min_module_temperature_sensor",
            ):
                values[field_name] = getattr(component, field_name)
    return {
        "values": values,
        "components_that_did_not_answer": missed,
    }


async def _async_decoded_readings(unit, passes: int = 8) -> dict[str, object]:
    """Return every register the integration reads, decoded.

    A fingerprint used to carry 22 curated probes, chosen to answer capability
    questions. That is the right set for *capabilities* and the wrong set for
    everything else -- both of the day's findings came from registers outside
    it: a Pylontech reporting capacity 0 where a Sungrow pack reports its
    size, and registers 33149/33150 reading 200 W and 100 W when the
    specification does not document them at all.

    So it now carries all of them. The cost is bounded and small because the
    library pools neighbouring registers: 105 fields in **23 reads**. A blind
    sweep of the whole address span, by contrast, is 30,569 addresses in 245
    reads, mostly "Reserved" per the specification and each one a chance to
    drop the link -- which is why the wider net is cast over the *map* and not
    over the address space.

    Decoded rather than raw, deliberately. A raw word says the read worked; a
    decoded value says the scale and word order are right, which is the
    mistake worth catching.

    Without the library this hands the same job to `portable.read_fields`,
    which drives the committed plan and decodes from it. The report is the
    same report -- same keys, same values, same omissions --
    `tests/test_portable_readings.py` requires it of both scenarios, blocks
    and salvage. The one thing only this branch reports is
    `identity_did_not_read`, because only this branch has capability gating
    to be working blind.
    """
    if not have_library():
        from portable import load_plan, read_fields

        return await read_fields(load_plan(), unit, passes)

    from modbus_connection import ModbusError

    from sungrow_modbus import COMPONENTS, SungrowInverter

    inverter = SungrowInverter(unit)
    # Retried and then tolerated. This one call was the only un-guarded read
    # in the function, so a single drop here raised past all the per-component
    # tolerance below and published a document with **no decoded readings at
    # all** -- an empty block that no reader would notice, when catching a
    # wrong scale or word order is the whole reason the block exists.
    identity_failed: str | None = None
    for attempt in (1, 2, 3):
        try:
            await inverter.async_update_identity()
        except (ModbusError, TimeoutError, OSError) as err:
            identity_failed = type(err).__name__
            if attempt < 3:
                await asyncio.sleep(1.5)
        else:
            identity_failed = None
            break

    # One component at a time, and then round again for whatever is still
    # missing, until everything has answered once or the budget runs out.
    #
    # This is what makes a report usable on an inverter somebody is already
    # polling, which is nearly all of them. Three attempts per component,
    # taken back to back, competed with the other client at exactly the wrong
    # moment and left 10 of 104 fields on a busy machine. Spreading the
    # attempts out and only re-reading what is still missing gets the lot,
    # because the collision is a moment rather than a state.
    #
    # The cost is that fields come from different moments, so arithmetic
    # *between* them can be inconsistent -- mppt1 + mppt2 need not equal a
    # total_dc_power read forty seconds later. That is already true of this
    # block ("not stable between reads") and is the right trade for a
    # capability report, where the questions are whether a register answers
    # and whether its scale is right.
    pending = list(COMPONENTS)
    bar = _Progress("reading registers", len(pending))
    for this_pass in range(1, max(1, passes) + 1):
        still_missing: list[str] = []
        for attribute in pending:
            try:
                await inverter.component(attribute).async_update()
            except (ModbusError, TimeoutError, OSError):
                still_missing.append(attribute)
            if this_pass == 1:
                # Only the first pass advances the bar. Later passes re-read
                # what is still missing, and counting those would push it past
                # its own total -- a bar that reads 31/23 is worse than none.
                bar.step(attribute)
        # `pending` is assigned *before* the emptiness test, not after. The
        # other way round -- `if not still_missing: break` and then
        # `pending = still_missing` -- leaves `pending` holding whatever the
        # pass began with, so a device that answered everything on pass 1 was
        # reported as **13 components missed** and then had all 104 of its
        # fields re-read one at a time. It produced a plausible document with
        # plausible values, which is why it survived: gerd's direct-LAN
        # fingerprint claims no component answered as a whole, while the
        # run's own transcript shows every one of them answering on the first
        # pass. Guarded by
        # `test_a_device_that_answers_everything_reports_nothing_missed`.
        pending = still_missing
        if not pending:
            if this_pass > 1:
                print(f"  {'':<38}all components answered by pass {this_pass}")
            break
        if this_pass < max(1, passes):
            print(f"  {'':<38}pass {this_pass}: still waiting on {', '.join(pending)}")
            await asyncio.sleep(2.0)
    bar.finish(f"{len(COMPONENTS) - len(pending)} of {len(COMPONENTS)} components")
    missed = pending

    # Whatever is still missing, read field by field so that only the
    # registers the device truly refuses are absent from the report.
    salvaged: dict[str, object] = {}
    unreadable: list[str] = []
    for attribute in missed:
        print(
            f"  {'':<38}{attribute}: reading its fields one at a time",
            flush=True,
        )
        recovered, refused = await _async_field_by_field(
            unit, type(inverter.component(attribute)), ModbusError
        )
        salvaged.update(recovered)
        unreadable.extend(refused)
        print(
            f"  {'':<38}{attribute}: {len(recovered)} recovered, "
            f"{len(refused)} still missing",
            flush=True,
        )

    readings: dict[str, object] = {}
    for name in sorted(inverter._fields):
        if any(word in name for word in NEVER_PUBLISH):
            continue
        try:
            readings[name] = inverter.field(name)
        except (AttributeError, KeyError):
            continue
    # The field-by-field values live in their own throwaway components, so
    # they are not in the inverter's stores; overlay them, and only where the
    # component read left nothing.
    for name, value in salvaged.items():
        if any(word in name for word in NEVER_PUBLISH):
            continue
        if readings.get(name) is None:
            readings[name] = value
    report: dict[str, object] = {
        "values": readings,
        # Sorted, so two readings of one machine differ only where the
        # machine did. It is also what makes a document from the portable
        # path comparable with one from the library path, which is the
        # property `tests/test_portable_readings.py` rests on.
        "components_that_did_not_answer": sorted(missed),
    }
    # `NEVER_PUBLISH` applies to these two lists as well, and did not: the
    # *values* were dropped but `sungrow_inverter_serial` was still named
    # here, in a file whose whole premise is that it carries no serial. A
    # field name is not a serial, but the rule is worth keeping absolute.
    # Filtered before the emptiness test, so a list that is empty only after
    # filtering is omitted rather than published bare.
    named = sorted(
        name for name in salvaged if not any(w in name for w in NEVER_PUBLISH)
    )
    if named:
        # Named, because these came from a different moment than their
        # neighbours and from a read of their own -- which is also why they
        # are the best evidence in the file about what this device refuses.
        report["fields_read_individually"] = named
    silent = sorted(
        name for name in unreadable if not any(w in name for w in NEVER_PUBLISH)
    )
    if silent:
        # Not "refused": that is a claim about the device, and this is only
        # what did not read after several separated attempts of its own. On a
        # quiet inverter it is good evidence; on a busy one, read it with the
        # block read test in `blocks.py` before believing it.
        report["fields_that_did_not_read"] = silent
    if identity_failed:
        # Named rather than hidden: without the identity block the capability
        # gating is working from nothing, so every field below is suspect.
        report["identity_did_not_read"] = identity_failed
    return report


def transport_verdict(*, answered_6100: bool, module_named: bool) -> str:
    """Read the two transport signals, one measured row at a time.

    Separated from the reading so the truth table can be asserted without a
    device. Every row below happened on somebody's house; see
    `_async_connection` for which.
    """
    if answered_6100 and module_named:
        # Worth saying out loud rather than leaving in the two raw signals.
        # This installation has both routes, and the one it is not using
        # forwards fewer measuring points and answers zero where the inverter
        # answers "unavailable" -- which fabricates capabilities. Somebody
        # reading their own fingerprint should be able to see that they are
        # already on the better path, or that they have a choice.
        return (
            "direct to the inverter's LAN port, with a communication module "
            "fitted as well but not in the path"
        )
    if answered_6100:
        return "direct to the inverter's LAN port"
    if module_named:
        return "through a communication module (WiNet-S, WiNet-S2 or Logger)"
    return (
        "through a communication module (WiNet-S, WiNet-S2 or Logger), "
        "which did not name itself"
    )


async def _async_connection(unit, host: str, firmware: dict, ModbusError) -> dict:
    """Work out how we got in, from evidence rather than from asking.

    Two signals, both from the specification rather than inferred:

    * **Registers 6100-6195** are documented "WiNet-S/S2 and Logger is not
      supported". If they answer, we are not behind one of those.
    * **Register 13265**, Communication Module Firmware Information, names the
      module if there is one. A direct-LAN inverter has no module and returns
      the specification's UTF-8 unavailable, which decodes to an empty string.

    The first decides. The second was written as its equal, on the reasoning
    that anything behind a WiNet-S names itself -- and two measured dongles
    return an empty string for it, which is exactly what an inverter with no
    module returns. So its silence is no evidence either way, and only its
    presence adds anything.

    What neither signal can reach is the **medium**: a WiNet-S answers the
    same wired as it does over WiFi. Nothing in the protocol reports it and
    latency is only a hint, so `--transport` is how a contributor supplies
    what only they can know. Both signals stay in the document regardless.

    Both are recorded, not just the conclusion, because the conclusion is a
    reading of them and somebody may later read them differently.

    **WiFi versus Ethernet on a WiNet-S is not determinable over Modbus, and
    latency does not help.** Settled on 2026-09-08 against the controlled
    case: bar12's SH10RT-20, one dongle, read wired and then over WiFi. The
    structural diff is *nil* -- identical capability probe states, identical
    failed components, identical fields filled, identical firmware strings.
    Nothing in the register space moves.

    Latency was the standing hypothesis and it does not survive either. Across
    four installations the direct-LAN medians span 2.0 to 61.5 ms and the
    WiNet medians 24.3 to 48.3, so they overlap -- and gerd's direct link is
    *slower* than his own dongle, because he reaches it over a VPN. Jitter
    fails too: the same dongle spread 1.6 ms wired and 4.9 over WiFi, while
    another house's wired WiNet spread 8.6. It measures the path between the
    client and the device.

    So the samples stay in the document as evidence, `--transport` carries
    what only the owner knows, and no code guesses.
    """
    import statistics
    import time

    signals: dict[str, object] = {}
    try:
        # Retried: this single read decides the transport verdict, and losing
        # it to a moment's contention says "a module is in the way" -- which
        # put `winet` in the filename of a reading taken on an inverter's own
        # LAN port, while the curated probe of the same register, two seconds
        # later and retried, answered.
        await _async_read_retrying(
            unit.read_input_registers, 6099, 2, IDENTITY_ATTEMPTS
        )
        signals["winet_restricted_block_6100"] = "answered"
    except (ModbusError, TimeoutError, OSError):
        signals["winet_restricted_block_6100"] = "refused"
    signals["communication_module_firmware"] = firmware.get("communication_module", "")

    samples: list[float] = []
    for _ in range(7):
        started = time.perf_counter()
        try:
            await unit.read_input_registers(4999, 1)
        except (ModbusError, TimeoutError, OSError):
            break
        samples.append(round((time.perf_counter() - started) * 1000, 1))
    if samples:
        signals["latency_ms"] = {
            "median": statistics.median(samples),
            "min": min(samples),
            "max": max(samples),
        }

    # Register 6100 decides; 13265 only ever corroborates. The truth table
    # below is measured on three installations, not reasoned:
    #
    #   6100 answered, no module named    fwitten, direct   -> direct
    #   6100 refused,  no module named    fwitten, dongle   -> dongle
    #   6100 refused,  module named       bar12, dongle     -> dongle
    #   6100 answered, module named       gerd, LAN port    -> direct
    #
    # Sungrow documents 6100-6195 as not forwarded by a WiNet-S or Logger, so
    # answering it means nothing is in the way -- and that holds whatever
    # 13265 says. The last row is the one that settles the module string's
    # role: gerd's inverter has a WiNet-S fitted and answers on its own LAN
    # port too, so 13265 names the dongle on a reading that never went
    # through it. It reports what is **attached**, not the route taken.
    #
    # Which leaves 13265 unable to conclude anything in either direction:
    # fwitten's dongles return it **empty**, exactly as an inverter with no
    # module does. It is recorded, and it decides nothing.
    verdict = transport_verdict(
        answered_6100=signals["winet_restricted_block_6100"] == "answered",
        module_named=bool(signals["communication_module_firmware"]),
    )

    return {
        "verdict": verdict,
        "wifi_or_ethernet": (
            "not determinable over Modbus. Nothing in the protocol reports it, "
            "and latency cannot stand in: measured across four installations, "
            "direct-LAN medians run from 2.0 to 61.5 ms and WiNet medians from "
            "24.3 to 48.3, so the ranges overlap -- one house's direct link is "
            "slower than its own dongle. Jitter does not separate them either: "
            "a WiNet-S measured 1.6 ms of spread wired and 4.9 over WiFi on the "
            "same dongle, while another house's wired WiNet spread 8.6. Latency "
            "describes the network between the client and the device, not how "
            "the device is attached. Use the reported_by_hand field."
        ),
        **signals,
    }


#: Hex characters of the serial hash appended to a filename. Six is 24 bits.
#: Ten *bits*, which was the first suggestion, is 1024 buckets -- two setups of
#: the same shape collide 18 % of the time by the twentieth fingerprint and
#: essentially always by the hundredth. 24 bits is 0.7 % at five hundred, and
#: still short enough to read.
LABEL_HASH_CHARS = 6


def _all_zero(raw: dict, names: tuple[str, ...]) -> bool:
    """Say whether every one of these registers answered, and answered zero.

    Sungrow's specification defines an "unavailable" sentinel per field, and
    `_classify` reads anything else as a value -- correctly, for a register
    that reports a measurement. Some absent hardware does not use the
    sentinel: it fills the block with 0x0000, which decodes to a perfectly
    plausible zero and sails through as a reading.

    Every name must be present and zero. One zero among values is a
    measurement; all of them together is the block not being filled in.
    """
    registers = raw.get("registers", {})
    values = [registers.get(name) for name in names]
    if any(value is None for value in values):
        return False
    return all(all(word == 0 for word in value) for value in values)


#: What `--transport` may say: a key, the sentence a person is asked to agree
#: with, and the verdict it becomes. The verdicts are phrased like the measured
#: ones so that everything reading a verdict keeps working.
#:
#: `winet_lan` and `winet_wlan` are worth separating even though Modbus cannot
#: tell them apart -- that is exactly why. The protocol reports nothing about
#: the medium and latency is only a hint, so if a fingerprint is ever to say
#: whether a reading came over WiFi, a person has to be the one to say it.
REPORTED_TRANSPORTS: dict[str, tuple[str, str, str, str]] = {
    "direct_lan": (
        "the inverter's own LAN port",
        "direct to the inverter's LAN port (reported by the contributor)",
        "direct LAN port",
        "",
    ),
    "winet_lan": (
        "a WiNet-S dongle, wired",
        "through a WiNet-S, wired (reported by the contributor)",
        "WiNet-S, wired",
        "winet-lan",
    ),
    "winet_wlan": (
        "a WiNet-S dongle, over WiFi",
        "through a WiNet-S, over WiFi (reported by the contributor)",
        "WiNet-S, WiFi",
        "winet-wlan",
    ),
    "winet": (
        "a WiNet-S dongle, medium unknown",
        "through a WiNet-S (reported by the contributor)",
        "WiNet-S",
        "winet",
    ),
    "logger": (
        "a Logger1000/3000",
        "through a Logger (reported by the contributor)",
        "Logger",
        "logger",
    ),
    "unsure": ("not sure", "", "", ""),
}


def _claim_of(verdict: str) -> str | None:
    """Return what a verdict actually claims, or None where it claims nothing.

    Verdicts are sentences so that a reader gets the reasoning, which makes
    them the wrong thing to compare. This reduces one to `direct`, `module`,
    or None for the "not determinable" cases -- so that agreement is judged
    on the claim rather than on the wording.
    """
    if verdict.startswith("direct"):
        return "direct"
    if verdict.startswith(("through a communication module", "through a WiNet-S")):
        return "module"
    if verdict.startswith("through a Logger"):
        return "module"
    return None


def _effective_verdict(connection: dict) -> str:
    """Return the transport to act on: what somebody said, else what was read.

    Testimony outranks the measurement here, which is the opposite of the rule
    everywhere else in this project. It has to be, because the measurement
    cannot reach the question at all in one case that matters: **a WiNet-S
    answers the same wired as it does over WiFi.**

    One dongle read on both of its addresses produced *identical* documents --
    all 22 capability probes, all 104 decoded fields, and the same TLS
    certificate on port 443 down to the second it was issued. Only round-trip
    latency differed, and over a VPN even that is swamped. So the medium is
    knowable only to the person who plugged the cable in, and `unsure`
    overrides nothing.
    """
    reported = str(connection.get("reported_by_hand") or "")
    verdict = REPORTED_TRANSPORTS.get(reported, ("", ""))[1]
    # "unsure" maps to an empty verdict on purpose: somebody saying they do
    # not know must not outrank a measurement that does know.
    return verdict or str(connection.get("verdict", ""))


def _battery_token(fingerprint: dict, connection: dict, raw: dict) -> str:
    """Return what can honestly be said about the battery, in one word.

    Every state is prefixed `battery-` so the words sort together and read as
    one field rather than as unrelated tokens.

    The states, and the awkward one is load-bearing:

    * **`battery-sbr096`, `battery-sbh200`, …** — unit 200 answered, so it is
      a Sungrow pack, and the capacity it reports matches a model in the
      datasheet table within `CAPACITY_TOLERANCE_KWH`. The **model**, size
      included.

      This used to be the family alone, on the grounds that a size in a
      filename claims a module count the capacity does not support. Measuring
      an SBR096 settled it: the per-module arrays at 10765-10788 each hold
      **eight slots** -- eight being SBR256, the largest SBR -- and exactly
      three were filled, for three 3.2 kWh modules, agreeing with the 9.6 kWh
      at register 5639. A capacity that lands within tolerance of one model
      and no other is therefore reported as that model.

      Register 5639 is the one that decides, and deliberately: it is the
      documented capacity, where the arrays are only reachable on a direct
      connection -- a WiNet-S forwards 10740-10751 and refuses the rest.
    * **`battery-sungrow`** — unit 200 answered but the capacity did not, or
      did not match anything. Still certainly Sungrow.
    * **`battery-thirdparty`** — battery registers answered, unit 200 did
      not, **and the connection is direct**. The specification puts the
      per-module block at unit 200 only on a direct path, so on this route a
      silence there is evidence.
    * **`battery-unknown`** — the same silence **behind a dongle**, where it
      is no evidence at all: "the battery communication address will be the
      WiNet internal forwarding address", and Logger is not supported. The two
      cases look identical over the wire and are not the same fact, so
      reporting third-party here would be inventing one.
    * **`battery-none`** — the registers reported the unavailable sentinel,
      **or every one of them answered zero**. The second case is what a slave
      inverter in a master/slave cluster does: the battery belongs to the
      master, and the slave fills its own battery block with 0x0000 rather
      than with the sentinel. Read as a value that is third-party evidence,
      which is why it is tested first.
      It earns a word where a missing meter does not: a hybrid inverter is
      *sold* to have a battery, so its absence is information, and it is a
      common state because people fit the inverter first.
    * **`battery-unreadable`** — the reads were refused, which is worth
      recording rather than smoothing over.
    """
    registers = fingerprint.get("registers", {})
    # Either address is proof of a Sungrow pack. At unit 2 the module block
    # alone is not enough, because a slave inverter lives there too on a
    # direct connection -- but a slave answers the device type code and a
    # battery does not, so the pair of readings separates them.
    module_block = registers.get("unit 200 SBR battery module block")
    forwarded = registers.get("unit 2 SBR battery module block") == "present" and (
        registers.get("unit 2 inverter device type code") != "present"
    )
    states = [registers.get(name) for name in ("battery voltage", "battery level")]

    if module_block == "present" or forwarded:
        values = raw.get("registers", {}).get("battery capacity (5639)")
        if values:
            model = _battery_model_for_capacity(values[0] * 0.01)
            if model is not None:
                return f"battery-{model.name.lower()}"
        return "battery-sungrow"
    if _all_zero(raw, ("battery voltage", "battery level")):
        # Zeros rather than the sentinel, which is how a cluster slave says it
        # has no battery of its own. Checked before the "present" branch,
        # because a zero decodes as a value and would otherwise be read as
        # evidence of a third-party pack.
        return "battery-none"
    if any(state == "present" for state in states):
        direct = _effective_verdict(connection).startswith("direct")
        return "battery-thirdparty" if direct else "battery-unknown"
    if any(state == "unavailable" for state in states):
        return "battery-none"
    return "battery-unreadable"


def _slug(text: str) -> str:
    """Return text safe to put in a filename, or "anonymous" if nothing is left.

    Contributor names arrive as free text and land in a filename that goes
    into a public repository, so anything outside a-z, 0-9 and a dash becomes
    a dash. Lowercase, because the rest of the label is.
    """
    kept = "".join(c if c.isalnum() else "-" for c in text.strip().lower())
    return "-".join(part for part in kept.split("-") if part) or "anonymous"


def _firmware_token(raw: dict) -> str:
    """Return the inverter firmware as a filename word, or "" if it did not read.

    `SAPPHIRE-H_B001.V000.P022` becomes `b001v000p022`. The family prefix goes
    because the model word already says `sh80rt`, and the punctuation goes
    because a filename reads better without it -- the document keeps the
    string exactly as the device gave it.

    Omitted rather than filled in when the read failed, the way the other
    optional words are: a name that says nothing about firmware is honest,
    where `fw-unknown` would sort as though it were a version.
    """
    value = str((raw.get("firmware") or {}).get("inverter") or "")
    if not value:
        return ""
    # Everything after the first underscore is the version; a string with no
    # underscore is taken whole rather than dropped.
    version = value.split("_", 1)[-1]
    return _slug(version).replace("-", "")


def _derive_label(
    fingerprint: dict,
    connection: dict,
    stand_in_serial: str,
    raw: dict,
    reporter: str = "anonymous",
) -> str:
    """Return a filename from what the device said, not from what it is called.

    The default used to be the serial number, falling back to the host — both
    of which are the two things the publishable document exists to *not*
    carry, and putting either in the filename hands it over anyway.

    So it is derived from capability facts, with a short hash of the serial to
    keep two setups of the same shape apart. A `winet` word says the reading
    came through a communication module rather than the inverter's own port,
    which is what separates two otherwise identical filenames for one machine.

    Order is `model-firmware-phases-contributor-standin`, then everything
    attached. The identity word used to
    come last, which sorted a directory by what was *wired up* and split one
    machine's documents apart -- an inverter read directly and through its
    dongle differ in the words after the battery, so the pair ended up at
    opposite ends. With the hash third, every document from one machine shares
    a prefix and they group.

    The identity word is the document's own `serial_anonymized_hashed`, so a
    name can be checked against the file it belongs to by reading both. It
    was `sha256(real serial)[:6]` until somebody asked why
    `anon-00267885816` in a document and `aa2678` in its name shared four
    characters and no more -- two derivations of one serial, overlapping by
    chance, and only one of them recomputable from what is published.
    """
    registers = fingerprint.get("registers", {})

    def answered(*names: str) -> bool:
        return any(registers.get(name) == "present" for name in names)

    code = str(fingerprint.get("device_type_code", ""))
    model = "unknown"
    if code.startswith("0x"):
        model = (_model_for(int(code, 16)) or "unknown").lower().replace(".", "")

    parts = [model]

    # Firmware directly after the model, because it qualifies the model and
    # nothing else: which registers a device answers moves between versions,
    # so `sh80rt-v112` alone does not say what to expect and
    # `sh80rt-v112-b001v000p022` does. Sorting a directory then groups a
    # model with its firmwares, which is the comparison a reader makes.
    #
    # The *inverter* firmware of the five recorded, chosen for granularity: it
    # carries a build and a patch number, so two machines on one ARM version
    # can still be told apart.
    firmware = _firmware_token(raw)
    if firmware:
        parts.append(firmware)

    # Only the *unusual* wiring is named, because only the unusual wiring
    # changes what a reading means.
    #
    # 3P4L is three phases and a neutral -- an ordinary domestic supply -- and
    # spelling it out lengthened every filename to say "normal". 3P3L has no
    # neutral, and the specification is explicit that registers 5019-5021 then
    # report **line** voltages rather than phase voltages: "A-B line
    # voltage/phase A voltage ... 0: phase voltage; 1: phase voltage; 2: line
    # voltage". So the same register means A-B instead of A-N, a reading about
    # 1.73x higher, and a fingerprint that did not say so would look like a
    # scaling bug.
    #
    # `w` for wire rather than the specification's `L` for Line: they mean the
    # same thing -- its own worked example glosses 3P4L as "three-phase
    # four-wire" -- but a lowercase L beside a digit reads as a one.
    #
    # The document always carries the exact value in `output_type`.
    phases = str(fingerprint.get("output_type", ""))
    if "3P3L" in phases:
        parts.append("3p3w")
    elif "3P4L" in phases:
        parts.append("3p")
    elif "single" in phases:
        parts.append("1p")

    # Who sent it, before the hash. One contributor usually sends several --
    # a master and its slave, or one inverter through two paths -- and this
    # groups their files together, where sorting by model scattered them
    # among everybody else's. "anonymous" is a group like any other.
    parts.append(_slug(reporter))

    # The hash sits here, between what the device *is* and what is attached to
    # it, so that every document from one machine shares a prefix and they
    # group when sorted. One installation produces several: read the same
    # inverter directly and through its dongle and the words after the hash
    # differ -- `battery-sbr096-meter` against `battery-unknown-winet` -- which
    # with the hash last scattered the pair to opposite ends of the directory.
    # Hashed from the **real** serial, not from the stand-in. Both are
    # one-way and 24 bits either way, and the difference is that the real
    # serial never changes: hashing the stand-in coupled every filename to
    # how the stand-in happened to be formatted, so prefixing it with `anon-`
    # renamed nine contributors' files for a reason that had nothing to do
    # with their hardware. It is the raw file that carries the real serial, so
    # it is read from there and hashed, never published.
    # The document's own stand-in serial, verbatim. It used to be
    # `sha256(real serial)[:6]`, which nobody holding the published file
    # could recompute -- and since the stand-in is *also* derived from the
    # serial, a document and its name carried two different derivations of
    # one thing. On the first machine to have both they shared four
    # characters by chance, `anon-00267885816` against `aa2678`, which reads
    # as one value gone wrong rather than two values unrelated.
    #
    # The old objection to using the stand-in was that the filename then
    # depends on the stand-in's *format*, and adding the `anon-` prefix did
    # once rename nine files. That is a settled format now, and the trade is
    # worth it: a reader can check a name against the file it belongs to
    # without holding the serial that neither of them carries.
    # Only ever a value that says it is a stand-in. Putting the caller's
    # string into the name unchecked is how a real serial would reach a
    # filename -- `_slug("A123456789")` is `a2311227462`, which also slides
    # past a case-sensitive test for the serial. `anon-` cannot occur in a
    # Sungrow serial, which is why schema 10 put it there, so requiring it
    # makes the mistake unrepresentable rather than merely unlikely.
    if stand_in_serial.startswith(STAND_IN_PREFIX):
        parts.append(_slug(stand_in_serial))

    parts.append(_battery_token(fingerprint, connection, raw))
    if answered("meter phase A voltage (5741)"):
        parts.append("meter")
    if answered("unit 3 wallbox serial", "unit 248 wallbox serial (direct)"):
        parts.append("wallbox")

    # The way in, when it is not the inverter's own port. Transport belongs in
    # the label because it decides which registers answer at all: read
    # directly, the reference master/slave pair reports a wired meter, answers
    # 6100 and hangs up on the firmware block at 13250; read through the
    # WiNet-S dongles in front of the same two inverters, the meter block and
    # 6100 are refused and 13250 answers 0.
    #
    # It is here for a blunter reason too: without it those two documents
    # collide. Same serial, same phases, same battery, so the same filename,
    # and the second **silently overwrote** the first.
    # The medium is in the filename only because leaving it out lost a file.
    # One dongle read wired and over WiFi is two legitimate readings that are
    # otherwise indistinguishable, so both derived the same name and the
    # second silently overwrote the first. What a reader should take from
    # `winet-lan` against `winet-wlan` is which cable, not any expectation
    # that different registers answer -- they do not.
    reported = str(connection.get("reported_by_hand") or "")
    word = REPORTED_TRANSPORTS.get(reported, ("", "", "", ""))[3]
    if not word and _claim_of(_effective_verdict(connection)) == "module":
        # Falling back to the measurement, which cannot see the medium. This
        # is also the "not sure" path: saying so must not veto a reading, and
        # `_effective_verdict` already resolves that precedence.
        word = "winet"
    if word:
        parts.append(word)

    return "-".join(parts)


#: Whether the document may carry the tail of the address, as its owner
#: decides. Withholding is the default: consent that was never asked for is
#: not consent, and `xxx.xxx` is a truthful answer where `178.105` would be a
#: guess about what somebody is willing to publish.
ADDRESS_HIDDEN = "xxx.xxx"

ADDRESS_ANSWERS: tuple[str, str] = ("two_octets", "hidden")


def _last_two_octets(host: str) -> str | None:
    """Return the last two octets of an IPv4 address, each zero-filled.

    Strings rather than numbers, because JSON cannot write a leading zero.
    Three digits is the widest an octet gets, so every value is the same
    width: "178.029" beside "178.114" lines up in a table and sorts as text
    in the order an address sorts, where 4, 28 and 128 as numbers-in-text
    would not.

    Two octets rather than one because the third is what separates one
    contributor's network from another's -- three of the installations on
    record sit on 192.168.178 and two on 192.168.176, which one octet cannot
    show. It is also the more revealing half, which is why it is asked for
    rather than taken.

    A hostname has no octets, and neither does an IPv6 address; both are
    perfectly ordinary things to point this script at, so both give None
    rather than a guess at the last things after a dot.
    """
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return None
    if address.version != 4:
        return None
    third, fourth = str(address).split(".")[2:]
    return f"{int(third):03d}.{int(fourth):03d}"


def _ask_address(host: str) -> str:
    """Ask whether the document may carry the tail of this address.

    Shows the value itself rather than describing it. "The last two octets"
    is an abstraction somebody has to decode before they can consent to it;
    `178.105` is the thing that would be published, and a person can look at
    that and say yes or no.
    """
    octets = _last_two_octets(host)
    if octets is None:
        return "hidden"
    print(
        "\nThe report can carry the tail of this address, which is what lets"
        "\nseveral readings from one house be told apart -- a master, a slave"
        "\nand two dongles otherwise produce four files that look alike."
    )
    labels = {
        "two_octets": f"yes -- publish {octets}",
        "hidden": f"no -- publish {ADDRESS_HIDDEN}",
    }
    return _ask_menu(list(ADDRESS_ANSWERS), labels, "two_octets")


def _document(raw: dict, fingerprint: dict) -> dict:
    """Return the one publishable document for a setup.

    What makes the raw file private is the serial, the host and the exact
    time: a timestamped set of live power, battery and meter readings is a
    statement about when somebody was at home. Replace the serial, drop the
    host, round the time to the day, and what is left is evidence -- real
    values from real hardware, which is what proves a scale factor or a word
    order right in a way synthesised numbers cannot.
    """
    registers: dict[str, dict] = {}
    for label, state in fingerprint.get("registers", {}).items():
        entry: dict[str, object] = {"state": state}
        values = raw.get("registers", {}).get(label)
        # `NEVER_PUBLISH` applies here too, and did not. Two of these probes
        # are named "wallbox serial", and their raw words were published: on
        # gerd's document `[16690, 13633]` decodes to `A25A`, the first four
        # characters of the wallbox's real serial. The inverter's own serial
        # was masked in the register dump and nowhere else, so the *one*
        # device whose identity nobody thought about was the one attached to
        # the inverter. What matters for a capability is that the register
        # answered; the value never did.
        if values is not None and not any(word in label for word in NEVER_PUBLISH):
            entry["values"] = values
        registers[label] = entry

    claimed = raw.get("connection", {})
    # A copy, because `raw` keeps the whole connection block: the filename is
    # derived from it, and the raw file is the record of what was actually
    # collected.
    measured_connection = {
        key: value
        for key, value in claimed.items()
        if key not in CLAIMED_CONNECTION_KEYS
    }

    return {
        "schema": SCHEMA,
        # The invocation that reproduces this reading, with the host replaced
        # by a placeholder -- the document is built around not carrying the
        # address, and `ip_address_last_octet` stays the one exception.
        #
        # Rebuilt from the parsed arguments, so a run collected by answering
        # prompts publishes a runnable command too. That is most of them.
        "command_line": raw.get("command_line", f"{SCRIPT} capabilities <host>"),
        "read_on": str(raw["read_at"])[:10],
        # The date alone could not order two readings taken minutes apart,
        # which is precisely the interesting pair: one machine on its LAN port
        # and then through its dongle, or a master and its slave. So the local
        # time is here too, with its offset, because a contributor reasoning
        # about their own files thinks in the clock on their wall and not in
        # UTC. `read_on` stays the **UTC** date, so late-evening readings show
        # a local date one day later -- the offset in this value is what
        # reconciles them.
        #
        # It does loosen what `read_on` was rounding away: a set of live power,
        # battery and meter readings stamped to the second says when somebody
        # was at home. That is a deliberate trade rather than an oversight --
        # the readings are contributed knowingly, the address is already gone,
        # and a fingerprint whose captures cannot be ordered is harder to
        # reason about than one whose owner can be told was up at ten.
        "read_at_local": _local_time(str(raw["read_at"])),
        # Everything a person typed, in one place and first.
        #
        # These are the only values in the file that were not read off a wire,
        # and mixing them in with the ones that were is how a claim gets
        # quoted back as a measurement. Four keys used to carry that
        # distinction in their own names -- `battery_reported_by_hand`,
        # `reported_by_hand` -- scattered across three sections, which asks a
        # reader to know the convention before they can trust anything. The
        # section is the convention now.
        #
        # Every one of them exists because Modbus cannot answer the question.
        # No register reports a battery's make. Nothing distinguishes a
        # master from a slave, because the difference is that the master has
        # the meter and the battery, which reads exactly like a lone inverter
        # that has neither. And a WiNet-S answers the same wired as over
        # WiFi -- one dongle read both ways produced identical documents down
        # to the TLS certificate.
        #
        # They are still worth having. A fingerprint that says "SBR096" is
        # more useful than one that says a Sungrow pack of 9.6 kWh, provided
        # nobody mistakes the first for something the inverter said.
        "user_inputs": {
            # Who to credit, and who to ask when a row raises a question.
            # Defaults to anonymous, because a fingerprint is worth having
            # either way and nobody should have to attach their name to
            # contribute one.
            "reporter": raw.get("reporter", "anonymous"),
            "comment": raw.get("comment", ""),
            "battery": raw.get("battery", ""),
            "transport": claimed.get("reported_by_hand", ""),
            # Whether anything is multiplexing the connection. Empty means
            # the question was not put -- documents written before schema 7
            # -- which is a different statement from `unknown`, where it was
            # put and the answer was that they did not know.
            #
            # It belongs here and it matters more than its one line suggests:
            # a proxy holds one connection to the inverter and lends it out,
            # so a reading taken through one describes the proxy as much as
            # the device. Blocks that never drop say the proxy serialises
            # well, and a proxy rebuilds every frame -- which can normalise a
            # quirk away or introduce one, and frame quirks are why
            # `layout.py` exists.
            "modbus_proxy": raw.get("proxy", ""),
        },
        # The tail of the address, and only ever with permission. Observed
        # rather than claimed -- this is the address that answered -- so it
        # stays out of `user_inputs`; what belongs to the contributor is the
        # *permission*, and without it this reads `xxx.xxx`.
        #
        # What it buys is that a contributor sending several files can tell
        # which box each came from: an installation with a master, a slave and
        # two dongles produces four documents whose readings look alike, and
        # "178.114" against "178.105" is the difference between a set that can
        # be reasoned about and four files in a heap.
        #
        # Two octets rather than one because the third is what separates one
        # contributor's network from another's -- on the record so far, three
        # installations sit on 192.168.178 and two on 192.168.176. That is
        # also the more revealing half, which is exactly why it is asked for.
        "ip_address_last_two_octets": _address_tail(raw),
        "device": {
            "device_type_code": fingerprint.get("device_type_code"),
            "output_type": fingerprint.get("output_type"),
            # One key, whose *name* is the explanation: three fields saying
            # "this is not the real serial" in three different ways was two
            # fields too many, and the note repeated what the README says
            # properly. `_fake_serial` keeps the shape and derives it by hash,
            # so one device always maps to one value and files stay diffable.
            "serial_anonymized_hashed": _fake_serial(str(raw.get("serial", ""))),
        },
        "firmware": raw.get("firmware", {}),
        "connection": measured_connection,
        # Every register the integration reads, decoded. Not stable between
        # reads -- these are live values -- but it is what catches a scale or
        # a word order that is wrong.
        "readings": raw.get("readings", {}),
        # Raw words for the bands worth keeping, with the serial's registers
        # blanked. Absent unless --dump asked for it, because it costs reads.
        **(
            {"register_dump": _masked_dump(raw["register_dump"])}
            if raw.get("register_dump")
            else {}
        ),
        # The wallbox's own registers, when one answered, with its serial
        # masked by its own mask rather than the inverter's -- the two live at
        # different addresses, and using the wrong one publishes a serial
        # while looking careful.
        **(
            {
                "wallbox": {
                    "unit": raw["wallbox"]["unit"],
                    # Decoded from the masked dump, not from the raw one, so
                    # a reading can never come from a register the document
                    # is refusing to publish -- the serial included.
                    "readings": _wallbox_readings(
                        _masked_dump(
                            raw["wallbox"]["register_dump"], WALLBOX_DUMP_MASKED
                        )
                    ),
                    "register_dump": _masked_dump(
                        raw["wallbox"]["register_dump"], WALLBOX_DUMP_MASKED
                    ),
                }
            }
            if raw.get("wallbox", {}).get("register_dump")
            else {}
        ),
        # What the block read test measured, when one ran.
        #
        # Absent for a whole schema before this, which was a real gap: the
        # measurement `scripts/layout.py` is only ever changed from lived in
        # the transcript, and the transcript is the file a contributor is
        # told to **keep** because it holds their real address. So a
        # submitted document carried none of it, and a maintainer reading one
        # could not see which blocks the integration would actually fail on.
        #
        # Rendered by the caller, because `blocks.py` owns the vocabulary and
        # `layout.py` quotes its wording.
        **(
            {"block_read_test": raw["block_read_test"]}
            if raw.get("block_read_test")
            else {}
        ),
        # The battery's own readings, when a pack answered. No masking:
        # nothing in these seventeen registers is a serial or an address,
        # and `NEVER_PUBLISH` is asserted over the whole document anyway.
        #
        # `battery_pack`, not `battery`: that key is already taken by what
        # the *owner* typed about their battery, and the first version of
        # this overwrote their testimony with a measurement.
        # `test_a_supplied_value_lands_only_in_user_inputs` caught it, which
        # is precisely the split that test exists to defend.
        **(
            {"battery_pack": raw["battery_pack"]}
            if (raw.get("battery_pack", {}).get("readings", {}).get("values"))
            else {}
        ),
        # The curated probes: which registers answered, which is what the
        # capability model and the compatibility table are built from, and
        # which is stable between reads.
        #
        # Last, because it is four lines per register and somebody opening
        # one of these wants to know *which setup it is* first. The order
        # below is the order the file is written in -- see `_ordered`.
        "capability_probes": registers,
    }


def _sorted_deep(value: object) -> object:
    """Return the value with every mapping key-sorted, recursively."""
    if isinstance(value, dict):
        return {key: _sorted_deep(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sorted_deep(item) for item in value]
    return value


def _ordered(document: dict) -> dict:
    """Return the document with its top-level order kept and the rest sorted.

    `sort_keys=True` was doing both jobs and only one of them well. Sorting
    matters *inside* the document, where the keys are register labels and
    field names: a stable order is what makes two fingerprints diffable and
    keeps a re-read from churning the whole file. At the top level it is
    actively wrong, because those keys are not a list of anything -- they are
    a document with a beginning, and alphabetical order opened every file with
    22 register probes and buried what setup it was underneath them.
    """
    return {key: _sorted_deep(value) for key, value in document.items()}


#: The raw reading never goes anywhere else, whatever --save is pointed at.
#: An earlier version wrote all three files to the chosen directory, so
#: `--save doc/device-fingerprints` — which is what the documentation told people to
#: run — put the real serial number into a directory that gets committed to a
#: public repository. The destination is no longer a choice.
RAW_DIR = Path(".testdata/fingerprints")

#: Where it goes when there is no `.testdata/` to hide it in. Still not a
#: parameter -- a caller cannot redirect the real serial anywhere, which is
#: the rule -- but the name has to work outside the checkout too. Unpacked
#: from the zip, `.testdata` is a *hidden* directory holding somebody's
#: serial and address, created inside the very folder they were told to send
#: back; a visible name that says what it is beats that in the one situation
#: where nobody has read this comment.
PRIVATE_DIR = Path("sungrow-scan-private")


def _checkout_root(start: Path | None = None) -> Path | None:
    """Return the repository this is running inside, or None.

    Walks **up**, which the first version did not: it asked whether the
    *current directory* held a `.git`, so running the survey from inside
    `scripts/sungrow_scan/` -- the obvious place to run it from, and where the
    zip's README says to -- concluded "not a checkout" and wrote a document
    into the source tree. The private file and the transcript were covered by
    `.gitignore`; the document was not, and sat there staged for the next
    `git add`.
    """
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        if (directory / ".git").exists() and (directory / "scripts").is_dir():
            return directory
    return None


def _raw_dir() -> Path:
    """Return the directory the un-redacted reading goes to.

    A checkout has `.testdata/`, which `.gitignore` covers. Anywhere else the
    file needs a name a stranger will recognise as private.
    """
    root = _checkout_root()
    return root / RAW_DIR if root else PRIVATE_DIR


def _destination(directory: Path, label: str, raw: dict, document: dict) -> Path:
    """Return where to write, and never over another device's document.

    Two readings of one machine can derive the same name: same serial, same
    battery, same capabilities, and the only thing between them is the path
    they came through -- which the label spells out only when somebody *said*
    which path it was. Answer "not sure" twice, as a first-time contributor
    reasonably does, and the second reading lands on the first one's filename.
    That has already cost a file in this project, and it happened again in the
    run that prompted this: one inverter, two dongle addresses, "not sure"
    both times.

    Same device re-read still overwrites, because that is a correction and a
    directory of `-2`, `-3` copies of one machine is worse than none. The two
    cases are told apart by the **host**, which the raw file beside each
    document carries -- and has to be, because a contributor who declines to
    publish the address leaves both documents saying `xxx.xxx`, so the
    document alone cannot distinguish them.
    """
    host = str(raw.get("host", ""))
    tail = str(document.get("ip_address_last_two_octets") or "")

    def is_this_device(stem: str) -> bool:
        """Whether the document called `stem` was read from this same host."""
        beside = _raw_dir() / f"{stem}.raw.json"
        if not beside.exists():
            # No raw file to ask -- which happens when the two live in
            # different places, or somebody moved one. Fall back to the tail,
            # and where that is withheld, treat it as a different device: a
            # spurious second file costs a filename, and being wrong the other
            # way costs a reading.
            existing = directory / f"{stem}.json"
            try:
                theirs = json.loads(existing.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return False
            return bool(tail) and theirs.get("ip_address_last_two_octets") == tail
        try:
            return str(json.loads(beside.read_text(encoding="utf-8")).get("host")) == (
                host
            )
        except (OSError, ValueError):
            return False

    candidates = [label]
    if tail and tail != ADDRESS_HIDDEN:
        # The address tail, which is in the document precisely so that several
        # readings from one house can be told apart.
        candidates.append(f"{label}-{tail.replace('.', '-')}")
    candidates += [f"{label}-{number}" for number in range(2, 20)]

    for stem in candidates:
        path = directory / f"{stem}.json"
        if not path.exists() or is_this_device(stem):
            if stem != label:
                print(
                    f"\n  {label}.json is already here from another address, so"
                    f"\n  this reading is written as {path.name} rather than"
                    "\n  over the top of it."
                )
            return path
    # Twenty readings of one label without a matching host is not a case worth
    # coding for; overwriting the first is still wrong, so the timestamp goes
    # in the name.
    return directory / f"{label}-{str(raw.get('read_at', '')).replace(':', '')}.json"


def _save(directory: Path, label: str, raw: dict, fingerprint: dict) -> list[Path]:
    """Write one publishable document, and the raw one out of harm's way.

    It used to be two publishable files -- a `capabilities` one saying *which*
    registers answered and a `readings` one with the values -- and they carried
    the same register labels twice. One document says both per register, which
    is what anybody reading it wants and one fewer thing to keep in step.

    The raw file still lands in the gitignored `.testdata/`, because it carries
    the real serial, the host and the exact time. The publishable document
    carries a stand-in serial, no host, and the day rather than the moment.
    """
    written = []
    directory.mkdir(parents=True, exist_ok=True)
    document = _ordered(_document(raw, fingerprint))
    path = directory / f"{label}.json"

    path = _destination(directory, label, raw, document)
    path.write_text(json.dumps(document, indent=2) + "\n")
    written.append(path)
    label = path.stem

    raw_dir = _raw_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{label}.raw.json"
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")
    written.append(raw_path)
    return written


async def capabilities(args: argparse.Namespace) -> Reading:
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
        "reporter": args.reporter,
        "battery": args.battery,
        "comment": args.comment,
        "proxy": args.proxy,
        "address_detail": args.address,
        # Reconstructed here rather than stored as the Namespace it came
        # from: `raw` is written out as JSON, and an argparse Namespace is not
        # serialisable -- which would have failed at the last line of a run
        # that had already spent a minute reading the device.
        "command_line": _invocation(args),
        # What the block read test found, when the caller ran one and handed
        # it over. `collect.py` does; the bare `capabilities` subcommand does
        # not, and a document without it says so by its absence rather than
        # by an empty section.
        "block_read_test": getattr(args, "block_read_test", None),
        "registers": {},
    }
    fingerprint: dict[str, object] = {
        "read_at": raw["read_at"],
        "registers": {},
    }
    print(f"{args.host}:{args.port} unit {args.unit}")
    try:
        try:
            serial = await _async_read_retrying(
                unit.read_input_registers, 4989, 10, IDENTITY_ATTEMPTS
            )
            text = b"".join(int(v).to_bytes(2, "big") for v in serial)
            decoded = text.decode("ascii", "replace").strip("\x00")
            raw["serial"] = decoded
            # Both, so that somebody about to send the file can see exactly
            # what leaves the building in place of their serial.
            print(f"  {'serial':<38}{decoded}  (anonymized to {_fake_serial(decoded)})")
        except (ModbusError, TimeoutError, OSError) as err:
            print(f"  {'serial':<38}unreadable ({type(err).__name__})")

        # Firmware first, because it is what makes two fingerprints
        # comparable: which registers a device answers moves between versions.
        firmware: dict[str, str] = {}
        for name, space, address, count in FIRMWARE:
            read = (
                unit.read_input_registers
                if space == "input"
                else unit.read_holding_registers
            )
            try:
                words = await _async_read_retrying(read, address, count)
            except (ModbusError, TimeoutError, OSError):
                continue
            text = b"".join(int(v).to_bytes(2, "big") for v in words)
            # Sungrow fills a UTF-8 field it has nothing for with 0x00, so an
            # empty result means "no such firmware here" rather than "a
            # firmware whose name is the empty string" -- null, the way the
            # decoded readings report it, not "".
            decoded = text.decode("ascii", "replace").strip("\x00").strip()
            firmware[name] = decoded or None
            print(f"  {'firmware ' + name:<38}{firmware[name]!r}")
        raw["firmware"] = firmware

        # Every register the integration reads, decoded. 23 block reads for
        # 105 fields, so the wider net costs almost nothing.
        try:
            raw["readings"] = await _async_decoded_readings(unit, args.passes)
            values = raw["readings"]["values"]
            answered = sum(1 for value in values.values() if value is not None)
            missed = raw["readings"]["components_that_did_not_answer"]
            note = f", {len(missed)} component(s) missed" if missed else ""
            print(f"  {'decoded readings':<38}{answered} of {len(values)} fields{note}")
        except (ModbusError, TimeoutError, OSError) as err:
            # Nothing, not "incomplete". The distinction matters: an empty
            # readings block is the one part of the document a reader cannot
            # tell is missing by looking at it.
            print(f"  {'decoded readings':<38}NONE READ ({type(err).__name__})")

        if args.dump:
            print(f"  {'register dump':<38}reading {len(DUMP_BANDS)} bands...")
            # Guarded, like the readings above it. `_async_dump_bands`
            # tolerates a band and even a single address failing, so what
            # escapes here is the link itself going away -- and the one
            # `try` around this whole function has no `except`, only a
            # `finally`, so an escape would sail past the save step and
            # discard a minute of reading that had already succeeded. The
            # dump is the optional extra; it must not cost the document.
            try:
                raw["register_dump"] = await _async_dump_bands(unit, ModbusError)
            except (ModbusError, TimeoutError, OSError) as err:
                print(
                    f"  {'register dump':<38}stopped early "
                    f"({type(err).__name__}); the document is written without it"
                )
            bands = [
                values
                for values in (raw.get("register_dump") or {}).values()
                if isinstance(values, dict)
            ]
            answered = sum(
                1 for values in bands for value in values.values() if value is not None
            )
            total = sum(len(values) for values in bands)
            if total:
                print(f"  {'register dump':<38}{answered} of {total} addresses")

        # The connection type, from the two signals the specification gives
        # rather than from asking the user -- who mostly does not know, and
        # reasonably confuses a WiNet-S with the inverter's own LAN port.
        raw["connection"] = await _async_connection(
            unit, args.host, firmware, ModbusError
        )
        if args.transport:
            raw["connection"]["reported_by_hand"] = args.transport
            # A disagreement between what the contributor reports and what the
            # signals measured is worth surfacing: it is evidence about the
            # *signals* rather than about this house, and both have been
            # caught out. But it was a stored field, and a stored comparison
            # of two values in the same file is the thing the `user_inputs`
            # split exists to stop -- it is neither what a person typed nor
            # what a wire said, it goes stale if the verdict logic changes,
            # and a reader can recompute it in a second.
            #
            # So it is said here, at the moment it can be acted on. Somebody
            # who has just typed the wrong cable can retype it; somebody whose
            # hardware really contradicts the specification has found the
            # interesting case and can say so in --comment.
            #
            # A measurement that concluded nothing does not disagree.
            measured = _claim_of(str(raw["connection"].get("verdict", "")))
            reported = _claim_of(REPORTED_TRANSPORTS[args.transport][1])
            if measured is not None and reported is not None and measured != reported:
                print(
                    f"\n  WARNING: you reported {args.transport!r}, but the "
                    f"registers say {measured!r}.\n"
                    "  Register 6100 has agreed with the reported transport on "
                    "every reading so far,\n"
                    "  so this is worth a second look -- and worth a --comment "
                    "if the hardware really\n"
                    "  does contradict it.\n"
                )
        verdict = _effective_verdict(raw["connection"])
        print(f"  {'connection':<38}{verdict}")

        for label, space, address, count, _axis in FINGERPRINT:
            read = (
                unit.read_input_registers
                if space == "input"
                else unit.read_holding_registers
            )
            try:
                # The identity registers decide the filename, so they get the
                # longer budget; the rest are evidence and a miss costs only
                # itself.
                # "battery capacity" is in here because it decides the
                # battery *model* in the filename: lose it and an SBR096
                # publishes as `battery-sungrow`, which is a weaker claim
                # than the machine actually supports.
                attempts = (
                    IDENTITY_ATTEMPTS
                    if label.startswith(
                        ("device type", "output type", "battery capacity")
                    )
                    else 3
                )
                values = await _async_read_retrying(read, address, count, attempts)
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
            # A WiNet-S forwards the pack here instead of at 200 -- measured
            # on three dongles. Unit 2 is also where a slave inverter lives,
            # so the device type code is read alongside: a slave answers it
            # and a battery does not, which is what tells the two apart.
            ("SBR battery module block", 2, 10740),
            ("inverter device type code", 2, 4999),
            ("wallbox serial", 3, 21200),
            ("wallbox serial (direct)", 248, 21200),
        ):
            try:
                # Retried, like every other read here. Single-shot, this
                # reported "no answer" for an SBR that the `units` command had
                # found at 200 a minute earlier -- and a missing pack is not a
                # cosmetic error: it put `battery-unknown` in the filename of
                # a machine with a perfectly ordinary SBR096.
                # The longer budget: whether unit 200 or unit 2 answers is
                # what separates `battery-sbr096` from `battery-unknown`, so
                # a miss here is a published claim about somebody's hardware.
                values = await _async_read_retrying(
                    conn.for_unit(other_unit).read_input_registers,
                    address,
                    2,
                    IDENTITY_ATTEMPTS,
                )
            except (ModbusError, TimeoutError, OSError):
                fingerprint["registers"][f"unit {other_unit} {label}"] = "no answer"
                print(f"  unit {other_unit:<4} {label:<32} no answer")
                continue
            raw["registers"][f"unit {other_unit} {label}"] = values
            fingerprint["registers"][f"unit {other_unit} {label}"] = "present"
            # A device type code is a hex code in Sungrow's document, in the
            # model table, and in `device.device_type_code` -- so [3598] was
            # the one place it had to be converted by hand to be looked up.
            shown = list(values)
            if "device type code" in label:
                note = " -> " + ", ".join(f"0x{value:04X}" for value in values)
            else:
                note = ""
            print(f"  unit {other_unit:<4} {label:<32} {shown}{note}")

        # The battery's own registers, on whichever unit answered for it.
        # Seventeen registers, so it is not behind the dump question either.
        # From the plan, not from the library: this file has to run from a
        # zip, and `generate_scan_plan.py` copies `battery.PACK_UNITS` into
        # it for exactly that reason. Falls back to the pair every measured
        # house has used, so a plan that predates the key still works.
        for pack_unit in _plan_battery_units():
            if (
                fingerprint["registers"].get(
                    f"unit {pack_unit} SBR battery module block"
                )
                != "present"
            ):
                continue
            # Unit 2 is also where a slave inverter lives on a direct
            # connection, and a slave answers this address with 0xFFFF. The
            # device type code separates them: a slave answers it, a battery
            # does not -- the same discriminator `_battery_token` uses, and
            # without it a slave inverter would be read as its own battery.
            if (
                pack_unit != 200
                and fingerprint["registers"].get(
                    f"unit {pack_unit} inverter device type code"
                )
                == "present"
            ):
                print(
                    f"  {'battery readings':<38}unit {pack_unit} is an inverter, "
                    "not a pack"
                )
                continue
            print(f"  {'battery readings':<38}unit {pack_unit}, 17 registers...")
            try:
                readings = await _async_battery_readings(conn, pack_unit)
            except (ModbusError, TimeoutError, OSError) as err:
                print(f"  {'battery readings':<38}failed ({type(err).__name__})")
            else:
                raw["battery_pack"] = {"unit": pack_unit, "readings": readings}
                got = len(readings.get("values") or {})
                missed = readings.get("components_that_did_not_answer") or []
                print(
                    f"  {'battery readings':<38}{got} values"
                    + (f", missed {', '.join(missed)}" if missed else "")
                )
            break

        # The wallbox's own register space, whenever one answered. Read
        # unconditionally rather than behind the dump question, because that
        # question is about the inverter's 1510 addresses and this is 206:
        # a wallbox is rare, its registers have no public document at all,
        # and a fingerprint that recorded only "a wallbox answered" was
        # throwing away the whole reason to have found it.
        for wallbox_unit in (3, 248):
            if fingerprint["registers"].get(f"unit {wallbox_unit} wallbox serial") != (
                "present"
            ) and fingerprint["registers"].get(
                f"unit {wallbox_unit} wallbox serial (direct)"
            ) != ("present"):
                continue
            print(f"  {'wallbox dump':<38}unit {wallbox_unit}, 206 addresses...")
            try:
                raw["wallbox"] = {
                    "unit": wallbox_unit,
                    "register_dump": await _async_dump_bands(
                        conn.for_unit(wallbox_unit),
                        ModbusError,
                        bands=WALLBOX_DUMP_BANDS,
                        what="wallbox dump",
                    ),
                }
            except (ModbusError, TimeoutError, OSError) as err:
                print(f"  {'wallbox dump':<38}stopped early ({type(err).__name__})")
            else:
                answered = sum(
                    1
                    for values in raw["wallbox"]["register_dump"].values()
                    if isinstance(values, dict)
                    for value in values.values()
                    if value is not None
                )
                print(f"  {'wallbox dump':<38}{answered} addresses answered")
            break
    finally:
        await conn.close()

    # The filename is built from the identity registers, so a read that
    # dropped changes what gets published: a transient refusal of 5002 cost
    # one document its `3p` word, which is invisible unless you know every
    # good filename has one. Cheap to re-run, expensive to notice.
    #
    # Computed whether or not anything is saved, because a caller wanting to
    # summarise the run needs to know the reading was thin.
    missing = [
        name
        for name, value in (
            ("device type code (5000)", fingerprint.get("device_type_code")),
            ("output type (5002)", fingerprint.get("output_type")),
            # Losing this one costs the filename its hash, which is the
            # only thing keeping two setups of the same shape apart.
            ("serial number (4990)", raw.get("serial")),
            (
                "the decoded readings",
                (raw.get("readings") or {}).get("values"),
            ),
        )
        if not value
    ]
    if missing and args.save:
        print(
            f"\n  WARNING: {', '.join(missing)} did not read, so the "
            f"filename below is missing what it would have said.\n"
            f"  Both answer on a quiet inverter -- worth re-running.",
        )
    document = _document(raw, fingerprint)
    written: list[Path] = []
    if args.save:
        label = args.label or _derive_label(
            fingerprint,
            # `raw`, not the document: the published connection block no
            # longer carries what the contributor reported, and the filename
            # is one of the places that reporting is for.
            raw.get("connection", {}),
            str(document["device"]["serial_anonymized_hashed"]),
            raw,
            str(raw.get("reporter", "anonymous")),
        )
        written = list(_save(Path(args.save), label, raw, fingerprint))
        for path in written:
            print(f"  wrote {path}")
    return Reading(raw, fingerprint, document, written, missing)


async def cmd_capabilities(args: argparse.Namespace) -> int:
    """Fingerprint one device, as the `capabilities` subcommand."""
    await capabilities(args)
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


def _ask(question: str, default: str = "") -> str:
    """Ask one question, offering a default that Enter accepts."""
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{question}{suffix}: ").strip()
    except EOFError:
        # Piped input that ran out. Taking the default beats a traceback.
        print()
        return default
    return answer or default


def _ask_yes(question: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    answer = _ask(f"{question} (y/n)", "y" if default else "n").lower()
    return answer.startswith("y")


def _ask_menu(keys: list[str], labels: dict[str, str], default: str) -> str:
    """Offer a numbered menu and return the chosen key.

    **Numbered, not lettered.** Letters were worse than they looked: `a-h`
    with six options means half the alphabet is invalid, `l` and `1` are hard
    to tell apart in some terminal fonts, and a contributor reading the answer
    back has to count on their fingers to check it. A number is the position.

    The key itself is still accepted, so a copy-paste of `winet_wlan` from the
    documentation works, and so does re-running a command someone was told.
    """
    for number, key in enumerate(keys, start=1):
        marker = " (default)" if key == default else ""
        print(f"  {number}) {labels[key]}{marker}")
    while True:
        choice = _ask("Choose", str(keys.index(default) + 1)).strip().lower()
        if choice in keys:
            return choice
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            return keys[int(choice) - 1]
        print(f"  Not one of the options. Pick a number from 1 to {len(keys)}.")


def _ask_transport() -> str:
    """Ask how the reading reaches the device, because Modbus cannot tell.

    Offered as a menu rather than a free-text field: the whole value of this
    answer is that it can be compared between fingerprints, and "WiNet" typed
    six different ways cannot be. "Not sure" is a first-class answer -- most
    people genuinely do not know, and a guess recorded as fact is worse than
    an honest gap.
    """
    keys = list(REPORTED_TRANSPORTS)
    print("\nHow is the inverter connected? Modbus cannot tell, so this is")
    print("the one thing only you can supply.")
    # "not sure" is the default, and deliberately so. A WiNet-S is the
    # commonest fitting, which is what made it tempting -- but a default is
    # what somebody gets for pressing Enter, and the value of this field is
    # that it is testimony. Pre-filling the likeliest answer turns a guess
    # into a record, and this is the one field no measurement can correct.
    return _ask_menu(keys, {k: v[0] for k, v in REPORTED_TRANSPORTS.items()}, "unsure")


#: What a complete dump costs, by link. Measured on 2026-09-08 against the
#: reference SH10RT, with the extra latency injected by a local proxy so the
#: numbers are measurements and not arithmetic: +24 ms reproduces a WiNet-S
#: over WiFi (25.7 ms median, bar12's) and +46 ms the slowest WiNet reading on
#: record (48.3 ms median, gerd's).
#:
#: 1510 addresses either way. The dump is 48 block reads plus a single read
#: for each address in a block that refused, so the cost is per-read latency
#: multiplied by roughly a hundred -- which is why a link 12 times slower
#: takes four times as long rather than 12.
DUMP_SECONDS: dict[str, int] = {
    "direct_lan": 7,
    "winet_lan": 30,
    "winet_wlan": 30,
    "winet": 30,
    "logger": 40,
    "unsure": 30,
}


def _ask_dump(transport: str) -> bool:
    """Offer the complete register dump, with what it will cost on this link.

    Worth offering rather than assuming either way. It is where the inverter's
    own clock at holding 5000-5005 was found, and the 45 holding registers
    nothing reads that answer real values -- neither of which any curated
    probe would have reached. And it is the one part of a run that a WiNet-S
    can feel: about 7 seconds on a direct LAN against about 30 through a
    dongle, which is also the link least able to spare them.
    """
    seconds = DUMP_SECONDS.get(transport, 30)
    print(
        f"\nA complete dump reads 1510 documented addresses raw -- about "
        f"{seconds}s on\nthe link you described. It is where the inverter's "
        "clock and 45 undocumented\nholding registers were found."
    )
    return _ask_yes("Include the complete dump?", default=True)


def _ask_proxy() -> str:
    """Ask whether anything is multiplexing the connection.

    This changes how nearly every other line in the document should be read,
    which is why it is asked rather than assumed absent.

    A Modbus proxy -- `modbus-proxy`, the evcc one, a Home Assistant add-on --
    exists because a Sungrow accepts very few sessions at once, and it works
    by holding one connection to the inverter and lending it out. So a
    fingerprint taken through one is a reading of *the proxy and* the inverter
    together:

    * a component that never drops says the proxy is serialising well, not
      that this inverter is generous with connections;
    * latency includes a hop, and the samples here have already been shown to
      say more about the network than about the device;
    * a proxy rebuilds every request and response, so a frame quirk can be
      normalised away -- or introduced. The padded frames at registers 2613
      and 2629 are exactly that class of finding, and they are the reason
      `layout.py` exists.

    Three answers, and the third is the honest one for most people: somebody
    who does not know what a Modbus proxy is almost certainly does not have
    one, but "probably not" is not a measurement and is not recorded as one.
    """
    print("\nIs anything between you and the inverter multiplexing Modbus")
    print("-- modbus-proxy, evcc's proxy, a Home Assistant add-on?")
    return _ask_menu(list(PROXY_ANSWERS), PROXY_ANSWERS, "unknown")


class Identity(NamedTuple):
    """Who answered at one address, as evidence rather than as a sentence.

    `_identify` returned its findings already formatted, which is all a menu
    needs and not enough for `collect.py`: the same serial on two addresses
    means **one inverter reached two ways**, and that changes the answer to
    every question that follows. It is also the condition that produced two
    withdrawn documents. So the serial comes back as a value, and the
    sentence is rendered from it.
    """

    serial: str | None
    device_type_code: int | None
    model: str | None
    #: Why nothing was learned, when nothing was.
    error: str | None = None
    #: Which unit id answered. `None` when nothing did.
    #:
    #: Here because a caller has to *ask* on the unit that answered, and
    #: because 1 is not always it: a cluster slave reached at its own LAN
    #: port answers on **2** and nothing at all on 1.
    unit: int | None = None


#: The unit ids `identify` tries for an inverter, in order, and why each.
#:
#: Only inverter-shaped units: a battery at 200 and a wallbox at 3 are found
#: later by `cmd_capabilities`, which probes for them behind an endpoint that
#: has already answered. This list is for the question "is there an inverter
#: here at all", and getting it wrong means a contributor is told their
#: inverter is absent.
#:
#: 1 first, because it is what Sungrow's app and manual assume and what all
#: but one measured machine uses. Then 2, measured on fwitten's second
#: inverter on 2026-09-09: at its own LAN port unit 1 times out and unit 2
#: answers, because a cluster slave's own device address is 2. Then 3 to 5,
#: which the specification allows for further slaves and which nothing has
#: yet been measured on.
IDENTIFY_UNITS: tuple[int, ...] = (1, 2, 3, 4, 5)


async def identify(host: str, port: int) -> Identity:
    """Ask whoever is at this address who they are, on whichever unit answers.

    Tries `IDENTIFY_UNITS` in order and returns the first that names itself.
    It used to ask unit 1 and give up, which cost nothing until the first
    cluster slave: fwitten's second inverter answers on unit 2 at its own LAN
    port and times out on 1, so the survey reported "no serial at unit 1" and
    then offered a unit prompt defaulting to 1. That scan only succeeded
    because the operator already knew the answer. A contributor would have
    been told their inverter is not there -- and `CANDIDATE_UNITS` had listed
    unit 2 as "inverter slave" the whole time.

    The cost is paid only where the first attempt fails: an address with an
    inverter on unit 1 makes exactly the two reads it always did.
    """
    ModbusError, ModbusTcpParams, ModbusConnection = _require_library()
    connection = ModbusConnection(ModbusTcpParams(host=host, port=port), timeout=5)
    try:
        first_error: str | None = None
        for unit_id in IDENTIFY_UNITS:
            unit = connection.for_unit(unit_id)
            try:
                values = await unit.read_input_registers(4989, 10)
            except (ModbusError, TimeoutError, OSError) as err:
                if first_error is None:
                    first_error = type(err).__name__
                continue
            text = b"".join(int(v).to_bytes(2, "big") for v in values)
            serial = text.decode("ascii", "replace").strip("\x00").strip()
            if not serial:
                # Answered, but named nothing. Not a reason to keep looking:
                # something is there and talking, and a later unit answering
                # would make the report say the wrong thing about which
                # device this address is.
                return Identity(
                    None, None, None, "answered, but reported no serial", unit_id
                )
            try:
                code = await unit.read_input_registers(4999, 1)
            except (ModbusError, TimeoutError, OSError):
                return Identity(serial, None, None, None, unit_id)
            return Identity(
                serial, int(code[0]), _model_for(int(code[0])), None, unit_id
            )
        tried = ", ".join(str(unit_id) for unit_id in IDENTIFY_UNITS)
        return Identity(None, None, None, f"no serial at unit {tried} ({first_error})")
    finally:
        await connection.close()


def described(who: Identity) -> str:
    """Return the one-line description a menu shows.

    The serial is printed with its stand-in beside it, because that is the
    name the published file will carry; the wording matches the document's own
    `serial_anonymized_hashed`.
    """
    if who.error is not None:
        return who.error
    described = f"serial {who.serial}, anonymized to {_fake_serial(who.serial)}"
    if who.device_type_code is not None:
        model = who.model or f"0x{who.device_type_code:04X}"
        described = f"{model}, {described}"
    # Said only when it is not the obvious one, because on every other
    # address this line is already dense and unit 1 carries no information.
    if who.unit is not None and who.unit != 1:
        described += f" -- on unit {who.unit}, not 1"
    return described


async def _sweep_addresses(network: str, port: int) -> tuple[list[str], float]:
    """Return the addresses with that port open, and how long the sweep took.

    The duration is reported because it is the one number that says whether
    to trust a negative result. A /24 back in a second was swept at LAN
    speed; the same /24 taking half a minute went through a tunnel, and a
    tunnelled sweep that finds nothing is worth repeating before believing.
    """
    if have_library():
        from sungrow_modbus import hosts_in
    else:
        from portable import hosts_in

    try:
        hosts = hosts_in(network)
    except Exception as error:
        print(f"  {network} is not a network this can sweep: {error}")
        return [], 0.0
    # Deliberately gentler than the `sweep` command's defaults: this path is
    # for somebody who does not know the answers yet, quite possibly over a
    # VPN, and a false negative here sends them looking in the wrong place.
    semaphore = asyncio.Semaphore(32)
    # The bar matters most on exactly this path. Every address with nothing
    # listening costs the full timeout, so a quiet network is the slowest
    # case and the one where somebody wonders whether it has hung -- and this
    # sweep is deliberately gentle, 32 at a time with a 4 second timeout.
    bar = _Progress(f"sweeping {network}", len(hosts))
    settled = 0
    hits = 0

    async def check(host: str) -> str | None:
        nonlocal settled, hits
        async with semaphore:
            found_here = await _tcp_open(host, port, 4.0)
        settled += 1
        if found_here:
            hits += 1
        bar.step(f"{hits} found" if hits else "")
        return host if found_here else None

    started = time.perf_counter()
    found = [h for h in await asyncio.gather(*(check(h) for h in hosts)) if h]
    bar.finish(f"{len(found)} of {len(hosts)} answered")
    return found, time.perf_counter() - started


def _default_network() -> str:
    """Guess a network worth offering, and never offer the Docker bridge.

    In the devcontainer the only local address is on 172.17.0.0/16, which is
    the bridge and never where an inverter is. Offering it would be worse
    than offering nothing, so a private-looking address that is not the
    bridge is used and otherwise a common home range is suggested.
    """
    if have_library():
        from sungrow_modbus import network_of
    else:
        from portable import network_of

    try:
        import socket

        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("192.168.1.1", 1))
        address = probe.getsockname()[0]
        probe.close()
        if not address.startswith("172.17."):
            return network_of(address)
    except Exception:
        pass
    return "192.168.178.0/24"


#: How to stop Home Assistant polling a Sungrow for a couple of minutes.
#: Printed rather than linked because the person who needs it is at a
#: terminal being asked to send a fingerprint, not reading the docs.
PAUSE_ADVICE = """  A Sungrow accepts very few Modbus sessions at once, so
  anything already polling it competes with this script for them. It still
  works -- reads are retried and spread out -- but a quiet inverter gives a
  fuller report.

  To pause the YAML package: comment it out in Home Assistant's
  configuration.yaml -- put a # in front of the line that includes
  modbus_sungrow.yaml -- and then restart Home Assistant:

    Developer Tools  >  YAML  >  "Restart Home Assistant"  >  Restart

  As soon as Home Assistant is back up, carry on with this script.

  AFTERWARDS: take the # out again and restart the same way. Left
  commented, the YAML package stays switched off and those entities
  stop recording.

  For the new integration, or any other config entry: Settings > Devices &
  Services > the entry's menu > Disable, then Enable afterwards.

  Either way the entities go quiet for the duration, which leaves a short
  gap in the recorder and nothing worse."""


def _ask_about_pollers() -> None:
    """Mention the other pollers, and say how to quiet them.

    Asked rather than assumed, because the answer changes what a thin report
    means: on a busy inverter a missing component is probably contention and
    worth re-running, and on a quiet one it is probably the firmware and
    worth reporting. This does not gate anything -- a report from a busy
    inverter is still worth having, and refusing to take one would just mean
    no fingerprint at all.
    """
    print()
    if _ask_yes(
        "Is Home Assistant -- or anything else -- polling this inverter right now?",
        default=True,
    ):
        print(f"\n{PAUSE_ADVICE}\n")
        if not _ask_yes("Carry on anyway?", default=True):
            print("Nothing read. Quiet the pollers and run this again.")
            raise SystemExit(1)
    else:
        print("  Good -- a quiet inverter gives the fullest report.")


async def _ask_battery(host: str, port: int, unit_id: int) -> str:
    """Ask what the battery is, but only for the part no register reports.

    Most of it is readable. A Sungrow pack reports its capacity at register
    5639 and answers a block of its own at unit 200 or, behind a WiNet-S, at
    unit 2; between them that gives the exact model -- SBR096, not merely "a
    Sungrow" -- so asking would be asking for a fact the file already
    derives.

    Even a third-party pack is mostly readable: on the measured Pylontech the
    capacity register reads 0, but max charge and discharge power at
    33047-33048 read true, and so does state of health. What survives all
    that is the **brand**, which no register anywhere reports -- an inverter
    with a Pylontech attached looks exactly like one with an unbranded pack of
    the same size. So that is the only thing asked, and only when there is a
    battery whose module block did not answer.
    """
    ModbusError, ModbusTcpParams, ModbusConnection = _require_library()

    connection = ModbusConnection(ModbusTcpParams(host=host, port=port), timeout=6)
    capacity: float | None = None
    sungrow_pack = False
    has_battery = False
    extras: dict[str, float] = {}
    try:
        unit = connection.for_unit(unit_id)
        try:
            words = await _async_read_retrying(unit.read_input_registers, 5638, 1, 2)
        except (ModbusError, TimeoutError, OSError):
            pass
        else:
            if words[0] not in (0, 0xFFFF):
                capacity = words[0] * 0.01
        try:
            level = await _async_read_retrying(unit.read_input_registers, 13019, 1, 2)
        except (ModbusError, TimeoutError, OSError):
            pass
        else:
            has_battery = level[0] not in (0, 0xFFFF)
        # Read even where capacity is not, because a third-party pack answers
        # these: showing them keeps the question down to the unreadable fact.
        for name, address, scale, space in (
            ("charge_power", 33046, 10, "holding"),
            ("discharge_power", 33047, 10, "holding"),
            ("health", 13023, 0.1, "input"),
        ):
            read = (
                unit.read_input_registers
                if space == "input"
                else unit.read_holding_registers
            )
            try:
                got = await _async_read_retrying(read, address, 1, 2)
            except (ModbusError, TimeoutError, OSError):
                continue
            if got[0] not in (0, 0xFFFF):
                extras[name] = got[0] * scale
        for pack_unit in (200, 2):
            try:
                await _async_read_retrying(
                    connection.for_unit(pack_unit).read_input_registers, 10740, 2, 2
                )
            except (ModbusError, TimeoutError, OSError):
                continue
            sungrow_pack = True
            break
    finally:
        await connection.close()

    if sungrow_pack:
        model = _battery_model_for_capacity(capacity)
        if model is not None:
            print(
                f"\n  Battery: a Sungrow {model.name}, {model.capacity_kwh} kWh. "
                f"Read from register 5639\n  and its own module block, so not asking."
            )
            return ""
        print(
            "\n  Battery: a Sungrow pack -- its module block answers -- though the\n"
            "  capacity matched no model, which the file records as it found it."
        )
        return ""
    if not has_battery:
        print("\n  Battery: none attached, as far as the registers show. Not asking.")
        return ""

    print(
        "\n  Battery: attached, but its own module block does not answer, so it\n"
        "  is not a Sungrow pack. What the registers already say:"
    )
    for label, value, unit_name in (
        ("capacity (5639)", capacity, "kWh"),
        ("max charge power (33047)", extras.get("charge_power"), "W"),
        ("max discharge power (33048)", extras.get("discharge_power"), "W"),
        ("state of health (13024)", extras.get("health"), "%"),
    ):
        shown = f"{value:g} {unit_name}" if value else "not reported"
        print(f"    {label:<30}{shown}")
    print(
        "\n  Only the brand is left. No register anywhere reports it, and on the\n"
        "  measured Pylontech the capacity register reads 0 while the power\n"
        "  registers read true."
    )
    return _ask("Brand of the battery, with its size if you know it (blank to skip)")


def main() -> int:
    """Parse arguments and run the requested probe."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=False)

    p_mdns = sub.add_parser("mdns", help="see what the LAN advertises over mDNS")
    p_mdns.add_argument("--seconds", type=float, default=8.0)
    p_mdns.set_defaults(func=cmd_mdns)

    p_sweep = sub.add_parser(
        "sweep",
        help="find hosts with a Modbus port open",
        # The example goes in the **metavar**, so it appears in the usage line
        # argparse prints when the argument is missing -- which is the moment
        # somebody needs it. `help=` is only shown by `--help`, which is not
        # what you are looking at when you have just been told an argument is
        # required.
        epilog=(
            "examples:\n"
            "  probe.py sweep 192.168.1.0/24            a home network\n"
            "  probe.py sweep 192.168.1.0/24 --port 503 a Logger, or an\n"
            "                                           iHomeManager at unit 247\n"
            "  probe.py sweep 192.168.1.0/24 --port 516 an iHomeManager's own\n"
            "                                           port. TLS-wrapped, so\n"
            "                                           this finds it and\n"
            "                                           cannot read it\n"
            "  probe.py sweep 10.0.0.0/24 --concurrency 32 --timeout 3\n"
            "                                           through a VPN: fewer at\n"
            "                                           once, and more patience\n\n"
            "Or run collect.py, which asks for the network and offers yours as\n"
            "the default."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_sweep.add_argument(
        "subnet",
        metavar="192.168.1.0/24",
        help="the network to sweep, in CIDR form",
    )
    p_sweep.add_argument("--port", type=int, default=502)
    p_sweep.add_argument("--timeout", type=float, default=1.0)
    p_sweep.add_argument("--concurrency", type=int, default=512)
    p_sweep.add_argument("--max-hosts", type=int, default=4096)
    p_sweep.set_defaults(func=cmd_sweep)

    p_units = sub.add_parser("units", help="find Modbus units behind one host")
    p_units.add_argument("host")
    p_units.add_argument("--port", type=int, default=502)
    p_units.add_argument("--timeout", type=float, default=3.0)
    p_units.add_argument(
        "--retries",
        type=int,
        default=3,
        help="attempts per read (default 3). A Sungrow accepts very few "
        "Modbus sessions, so one timeout is not evidence of absence",
    )
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
        help="write <label>.json here, and <label>.raw.json to .testdata/ "
        "(default .testdata/fingerprints, which is gitignored)",
    )
    p_caps.add_argument(
        "--label",
        help="name the file this. The default is derived from what the device "
        "said -- model, phases, what is attached -- and never from the serial "
        "or the host, which are the two things the publishable file exists not "
        "to carry",
    )
    p_caps.add_argument(
        "--reporter",
        default="anonymous",
        help="who to credit, and who to ask when a row raises a question. "
        "Defaults to anonymous: a fingerprint is worth having either way",
    )
    p_caps.add_argument(
        "--dump",
        action="store_true",
        help="also read every documented address band raw and keep it in the "
        "report, so a register nobody has mapped yet can still be studied "
        "later. Costs a few dozen extra reads; the serial's registers are "
        "blanked in the published copy",
    )
    p_caps.add_argument(
        "--passes",
        type=int,
        default=8,
        help="how many times to go round re-reading whatever has not "
        "answered yet (default 8). Raise it on an inverter that something "
        "else is polling hard; 1 disables the persistence entirely",
    )
    p_caps.add_argument(
        "--transport",
        choices=tuple(REPORTED_TRANSPORTS),
        help="how this reading reached the device, when you know. A WiNet-S "
        "answers identically wired and over WiFi, so no register can tell "
        "those apart -- this outranks the measurement, and both are kept in "
        "the document",
    )
    p_caps.add_argument(
        "--address",
        default="hidden",
        choices=ADDRESS_ANSWERS,
        help="whether the report may carry the last two octets of the "
        "address, e.g. 178.105. It is what lets several readings from one "
        "house be told apart -- a master, a slave and two dongles otherwise "
        "produce four files that look alike -- and the third octet is what "
        "separates one contributor's network from another's, so it is the "
        "owner's to give. Withheld as xxx.xxx by default",
    )
    p_caps.add_argument(
        "--proxy",
        default="",
        choices=("", *PROXY_ANSWERS),
        help="whether a Modbus proxy is in the path -- modbus-proxy, evcc's, "
        "a Home Assistant add-on. It changes how the rest of the document "
        "should be read: a proxy holds one connection and lends it out, so "
        "blocks that never drop describe the proxy, and it rebuilds every "
        "frame, which can hide or create the length quirks layout.py exists "
        "for. 'unknown' is a real answer",
    )
    p_caps.add_argument(
        "--comment",
        default="",
        help="anything about this setup that no register reports, e.g. "
        "'master with battery' or 'slave, no battery'. Free text, and "
        "**published in the document**, so keep serials, addresses and names "
        "out of it",
    )
    p_caps.add_argument(
        "--battery",
        default="",
        help="the battery's **brand**, e.g. 'Pylontech Force H1, 14.4 kWh'. "
        "Only the brand needs saying: no register anywhere reports it. A "
        "Sungrow pack's model comes from register 5639 and its own module "
        "block, and even a third-party pack reports its charge and discharge "
        "power at 33047-33048",
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
    if args.command is None:
        # No subcommand: point at `collect.py`, rather than printing usage at
        # somebody who was told "run this and send me the file". This used to
        # run the wizard itself; `collect.py` is that wizard plus the phases
        # a survey needs -- identifying every device before asking anything,
        # the block read test, the transcript and a summary -- so having two
        # ways in would mean two answers to "how is this collected".
        print("For a full survey, run the one entry point:\n")
        print(f"    {_run_command('collect.py')}\n")
        print("It finds the devices, asks what it cannot measure, and writes")
        print("the report. This script's subcommands are the pieces it uses:")
        print("  mdns, sweep, units, capabilities, dump -- see --help.")
        return 1
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
