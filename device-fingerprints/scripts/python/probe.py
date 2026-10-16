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
    python device-fingerprints/scripts/python/probe.py mdns
    python device-fingerprints/scripts/python/probe.py sweep 192.168.1.0/24 [--port 502]
    python device-fingerprints/scripts/python/probe.py units <host> [--port 502]
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from datetime import UTC, datetime
import ipaddress
import json
from pathlib import Path
import shlex
import socket
import sys
import time
from typing import NamedTuple

from modbus_connection import (
    ModbusError,
    ModbusExceptionError,  # noqa: F401
    ModbusTcpParams,
)
from modbus_connection.tmodbus import ModbusConnection

from sungrow_modbus import (
    COMPONENTS,
    async_decoded_readings,
    async_probe_fields,
    async_probe_siblings,
    async_read_6100,
    async_read_firmware,
    async_read_retrying,
    battery_pack_unit,
    battery_readings,
    connection_block,
    dump as register_dump,
    hosts_in,
    label_for as package_label_for,
    local_time,
    model_for,
    model_for_capacity,
    network_of,
    publish_document,
    wallbox_unit,
    word_reader,
)
from sungrow_modbus.addresses import declared_field, field_address
from sungrow_modbus.battery import PACK_UNITS, PACK_VOLTAGE
from sungrow_modbus.battery_device import (
    COMPONENTS as BATTERY_COMPONENTS,
    PUBLISHED_NAMES as BATTERY_NAMES,
    SURVEY_COMPONENTS as BATTERY_SURVEY_COMPONENTS,
    SungrowBattery,
)
from sungrow_modbus.discovery import Identity, async_identify, async_mdns_services
from sungrow_modbus.dump import DUMP_BANDS, WALLBOX_BANDS
from sungrow_modbus.fingerprint import (
    NEVER_PUBLISH,  # noqa: F401
    OTHER_INVERTER_CLAIMS,
    OUTPUT_TYPES,
    REPORTED_TRANSPORTS as DOCUMENT_TRANSPORTS,
    TRANSPORT_CLAIMS,
    UNAVAILABLE,
    WIFI_OR_ETHERNET,  # noqa: F401
    State,  # noqa: F401
    address_tail,
    effective_verdict,
    last_two_octets,
    slave_inverter_at,
    stand_in,
    transport_contradiction,
    transport_verdict,  # noqa: F401
)
from sungrow_modbus.model import words_text

#: Where every file this folder's tools write goes: beside the scripts,
#: whichever directory they were started from. `.gitignore` covers the names
#: inside a checkout.
# Published documents are chosen explicitly; private run artifacts belong
# beside the launchers, not beside the Python implementation.
HERE = Path(__file__).resolve().parents[2]

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


async def _cmd_mdns_legacy(args: argparse.Namespace) -> int:
    """Browse every mDNS service type and report anything Sungrow-shaped.

    The one command in this file that needs a package the survey does not
    declare: `zeroconf` implements multicast DNS-SD, and a survey has no use
    for it. So a missing one gets a sentence naming the alternative, which is
    the sweep, rather than a traceback that reads as "the directory is
    broken".
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


async def cmd_mdns(args: argparse.Namespace) -> int:
    """Render the package's optional mDNS discovery result for a user."""
    try:
        found = await async_mdns_services(args.seconds)
    except RuntimeError:
        print(
            "mDNS discovery needs the optional sungrow-modbus discovery extra.\n\n"
            "  Install it: pip install sungrow-modbus[discovery]\n"
            "  Sweep the network instead: "
            f"python {_script_name()} sweep 192.168.1.0/24"
        )
        return 1
    if not found:
        print(
            "Nothing advertised. Either nothing is on this segment, or "
            "multicast is not reaching this host. Run a network sweep on "
            "the LAN itself."
        )
        return 1
    for name, entry in sorted(found.items()):
        interesting = "sungrow" in (name + str(entry)).lower()
        mark = "  <-- SUNGROW" if interesting else ""
        print(f"\n{name}{mark}")
        print(f"  type      {entry['type']}")
        addresses = ", ".join(str(address) for address in entry["addresses"])
        print(f"  addresses {addresses}:{entry['port']}")
        for key, value in entry["properties"].items():
            print(f"  {key:<12}{value}")
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


def _model_for_code(code: object) -> str | None:
    """Return the model name for a `0x….` device type code string, or None.

    Takes the published hex string rather than an int because that is what
    both producers hold at the point they need it, and because a code that is
    missing or malformed has to come back as None rather than raise: a
    document describing an unknown inverter is exactly the document this
    project most wants to receive.
    """
    text = str(code or "")
    if not text.startswith("0x"):
        return None
    try:
        return model_for(int(text, 16))
    except ValueError:
        return None


async def cmd_units(args: argparse.Namespace) -> int:
    """Ask each candidate unit id what it is, using the device library."""
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


#: The document format's history, by schema number; the number itself is
#: `sungrow_modbus.fingerprint.SCHEMA`. Bumped when the shape changes, so a
#: reader can tell a document written
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
#: answered only sometimes. That measurement is the one `src/sungrow_modbus/layout.py`
#: is ever changed from, and until now it existed only in the transcript -- the
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
#: measurement. 17 admits a **second producer**: the integration can write
#: one of these from Home Assistant's diagnostics download, so `command_line`
#: may name a tool rather than an invocation -- a download cannot be
#: reproduced by typing anything. The shape is otherwise identical, which is
#: the point: one generator keeps building `doc/compatibility.md` from both,
#: and a reading from somebody who only ever clicked a button counts the same
#: as one from a terminal. 18 asks whether the installation holds a **non-Sungrow
#: inverter**, in `user_inputs.other_inverter` and its free-text
#: `other_inverter_detail`. It is a schema bump rather than an addition
#: because the question changes how an existing field should be read: a
#: Sungrow computes house load from its own output plus grid import, so a
#: second inverter on the same meter makes every `load_power` figure low by
#: exactly that inverter's output while every register answers normally. A
#: document at 17 or below is silent on it, and silence there cannot be
#: distinguished from "no". 19 admits an
#: optional **`control_test`** block: what happened when each control was
#: written, read back and watched. Nothing in this directory produces it --
#: nothing here can write a register -- but the number is shared, so it moves
#: when the shape of the document does. `connection.latency_ms` was then
#: **removed without a bump**, on 2026-10-09: nothing ever read it, so its
#: absence tells a reader nothing, and it was stripped from every committed
#: document at the same time. 20 admits an optional **`export_scale`** block,
#: how the firmware writes register 13074; like `control_test` it is written by
#: `device-fingerprints/scripts/python/sungrow_control_test.py`, never from here.

#: Keys of the connection block that carry a claim rather than a measurement.
#: They are moved into `user_inputs`, so the published `connection` holds only
#: what was read off the wire.


#: Whether a Modbus proxy is in the path, as the contributor understands it.
#: `unknown` is a real answer and the default: somebody who does not know what
#: a Modbus proxy is almost certainly has not installed one, but "probably
#: not" is not a measurement and must not be recorded as one.
PROXY_ANSWERS: dict[str, str] = {
    "yes": "yes -- modbus-proxy, evcc's proxy, a Home Assistant add-on",
    "no": "no, this talks straight to the inverter",
    "unknown": "I do not know what that is",
}

#: The answers to "is there a non-Sungrow inverter here", as a menu.
#:
#: Two, where the proxy question has three. Somebody who does not know what a
#: Modbus proxy is has told us something useful by saying so; somebody who
#: does not know what is on their own roof is not a case worth a menu entry.
#:
#: Keyed by `sungrow_modbus.fingerprint.OTHER_INVERTER_CLAIMS`, which is what
#: the integration offers in its own dialog, so the two cannot disagree.
OTHER_INVERTER_ANSWERS: dict[str, str] = dict(
    zip(
        OTHER_INVERTER_CLAIMS,
        (
            "yes -- there is another inverter that is not a Sungrow",
            "no, the Sungrow is the only inverter here",
        ),
        strict=True,
    )
)

#: Where the contributors are. Used only to render a local time beside the UTC
#: one, so that two readings taken minutes apart can be told apart and ordered
#: without a reader doing timezone arithmetic in their head.
LOCAL_ZONE = "Europe/Berlin"


class Reading(NamedTuple):
    """Everything one pass over a device produced, for a caller to summarise.

    `cmd_capabilities` used to build all of this and then throw it away behind
    `return 0`, so anything wanting to report on a run had to read the
    registers again. The summary in `sungrow_survey.py` renders from `document`
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
SCRIPT = "python/probe.py"


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
    that is the repository path; in a downloaded copy of the folder there is
    no `scripts/` directory above it and the command is `python probe.py`. Printing the
    repository path there would be an instruction that fails.
    """
    here = Path(__file__).resolve()
    if here.parent.name == "python":
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
    ("--other-inverter", "other_inverter"),
    ("--other-inverter-detail", "other_inverter_detail"),
    ("--address-tail", "address_tail"),
)


def _invocation(args: object | None) -> str:
    """Return the command that would reproduce this reading.

    Rebuilt from the parsed arguments rather than copied from `sys.argv`, for
    a reason that matters more than tidiness: most of these documents are
    collected by answering prompts, where there is no command line at all.
    Reconstructing it means an interactive session still publishes something
    somebody can run -- their own reading, repeated, or a contributor's setup
    reproduced on request.

    **The host is masked, not omitted.** The first two octets are replaced
    with `***.***`, while the published tail remains visible so a contributor
    can identify the route to reuse. Values are shell-quoted, so a comment
    with spaces or an apostrophe pastes back intact.
    """
    script = _script_name()
    if args is None:
        return f"{script} capabilities <host>"

    host = str(getattr(args, "host", ""))
    tail = last_two_octets(host)
    shown_host = f"***.***.{tail}" if tail else "<host>"
    parts = [script, "capabilities", shown_host]
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
    return address_tail(
        str(raw.get("host", "")), raw.get("address_detail") == "two_octets"
    )


def _local_time(read_at: str) -> str:
    """Render a UTC timestamp in the contributors' own timezone, with offset.

    Falls back to the UTC string unchanged if the zone database is missing,
    which it can be on a slim container -- a wrong local time would be worse
    than an honest UTC one, and the offset in the value says which it is.

    Windows ships no zone database at all, so `zoneinfo` there reads the
    `tzdata` package, which the survey's PEP 723 header declares for that
    reason. Without it every Windows reading published in UTC.
    """
    return local_time(read_at, LOCAL_ZONE)


#: Attempts for a read whose loss changes the *filename*: the serial, the
#: device type code, the output type and the 6100 transport signal. A busy
#: inverter beat three attempts repeatedly on one measured machine, and each
#: time the published name quietly lost a part -- its hash, its phase word, or
#: worse, it gained a `winet` it had not earned. More attempts, spread wider,
#: because the collision is a moment and not a state.
IDENTITY_ATTEMPTS = 6


#: How many words a presence probe reads -- "does anything answer at this unit"
#: -- whatever the register's own width. Enough to tell an answer from a
#: refusal, and the count every published document was read with.
PRESENCE_WORDS = 2


def _reader(unit, space: str):
    """Return the unit's read function for one register table."""
    if space == "holding":
        return unit.read_holding_registers
    return unit.read_input_registers


_async_read_retrying = async_read_retrying


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
    """Read every band raw through `sungrow_modbus.dump.async_dump`, with a bar.

    The library reads; this says what it is reading. The fallback to single
    reads can wait out a timeout per address, so the bar is redrawn for each
    one with the register and the seconds spent in the block: a bar that sat
    unchanged for minutes read as a hung tool, convincingly enough that a run
    which had in fact finished was killed. Whoever runs this on their own
    house gets no transcript to check afterwards.
    """
    print(f"  {'':<38}reading these ranges, as register numbers:")
    for space, start, count, why in bands:
        print(f"  {'':<38}  {space:<8}{start + 1}-{start + count:<7} {why}")
    print(f"  {'':<38}Most of these addresses are 'Reserved' and answer nothing.")
    print(f"  {'':<38}A block that fails is retried one register at a time, and")
    print(f"  {'':<38}an address that does not answer costs a whole timeout -- so")
    print(f"  {'':<38}the bar can sit on one block for a minute. It says which")
    print(f"  {'':<38}register it is waiting on and for how long.")
    bar = _Progress(what, register_dump.block_count(bands, block))
    current = {"why": "", "fell_back": 0.0}

    def on_block(_done: int, _total: int, why: str) -> None:
        current["why"] = why
        bar.step(why)

    def on_narrow(single: int, number: int, size: int) -> None:
        if number == 1:
            current["fell_back"] = time.perf_counter()
        waited = time.perf_counter() - current["fell_back"]
        bar.redraw(
            f"{current['why']} -- reg {single + 1} alone, {number} of {size}, "
            f"{waited:.0f}s in this block"
        )

    try:
        return await register_dump.async_dump(
            word_reader(unit),
            on_progress=on_block,
            on_narrow=on_narrow,
            budget=budget,
            block=block,
            bands=bands,
        )
    finally:
        bar.finish()


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
    battery = SungrowBattery(connection.for_unit(unit_id), unit_id)
    missed: list[str] = []
    failed: list[str] = []
    for attribute in (*BATTERY_COMPONENTS, *BATTERY_SURVEY_COMPONENTS):
        try:
            await battery.component(attribute).async_update()
        except (ModbusError, TimeoutError, OSError) as err:
            failed.append(attribute)
            missed.append(f"{BATTERY_NAMES[attribute]} ({type(err).__name__})")
    return battery_readings(
        battery, missed, unanswered_fields=battery.fields_of(failed)
    )


async def _async_decoded_readings(unit, passes: int = 8) -> dict[str, object]:
    """Return every register the integration reads, decoded, with a bar.

    `sungrow_modbus.survey.async_decoded_readings` reads; this draws it.
    """
    bar = _Progress("reading registers", len(COMPONENTS))

    def note(text: str) -> None:
        print(f"  {'':<38}{text}", flush=True)

    return await async_decoded_readings(
        unit,
        passes=passes,
        on_component=bar.step,
        on_passes_done=lambda answered, total: bar.finish(
            f"{answered} of {total} components"
        ),
        on_note=note,
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
    same wired as it does over WiFi. Nothing in the protocol reports it, so
    `--transport` is how a contributor supplies what only they can know. Both
    signals stay in the document regardless.

    Both are recorded, not just the conclusion, because the conclusion is a
    reading of them and somebody may later read them differently.

    **WiFi versus Ethernet on a WiNet-S is not determinable over Modbus.**
    Settled on 2026-09-08 against the controlled
    case: bar12's SH10RT-20, one dongle, read wired and then over WiFi. The
    structural diff is *nil* -- identical capability probe states, identical
    failed components, identical fields filled, identical firmware strings.
    Nothing in the register space moves.

    Round-trip time was measured and published here until 2026-10-09, and
    removed: it describes the path from whoever reads to the inverter -- a VPN
    for most documents -- and the same dongle varied more between two nights
    than a cable and a dongle did within one. So `--transport` carries what only
    the owner knows, and no code guesses.
    """
    # Retried with the long budget: this single read decides the transport
    # verdict, and losing it to a moment's contention once put `winet` in the
    # filename of a reading taken on an inverter's own LAN port.
    state_6100 = await async_read_6100(unit, attempts=IDENTITY_ATTEMPTS)
    module = str(firmware.get("communication_module") or "")

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
    return connection_block(state_6100, module)


#: What `--transport` may say, as the menu line a person is asked to agree
#: with. The rest of each answer -- the verdict it becomes, its table label
#: and its filename word -- is the document's, in
#: `fingerprint.REPORTED_TRANSPORTS`.
TRANSPORT_MENU: dict[str, str] = {
    "direct_lan": "the inverter's own LAN port",
    "winet_lan": "a WiNet-S dongle, wired",
    "winet_wlan": "a WiNet-S dongle, over WiFi",
    "winet": "a WiNet-S dongle, medium unknown",
    "logger": "a Logger1000/3000",
    "unsure": "not sure",
}

#: Each answer whole: (menu line, verdict, table label, filename word).
REPORTED_TRANSPORTS: dict[str, tuple[str, str, str, str]] = {
    key: (TRANSPORT_MENU[key], *DOCUMENT_TRANSPORTS[key]) for key in TRANSPORT_CLAIMS
}


#: Whether the document may carry the tail of the address, as its owner
#: decides. Withholding is the default: consent that was never asked for is
#: not consent, and `xxx.xxx` is a truthful answer where `178.105` would be a
#: guess about what somebody is willing to publish.
ADDRESS_HIDDEN = "xxx.xxx"

ADDRESS_ANSWERS: tuple[str, str] = ("two_octets", "hidden")


def local_ipv4_for(host: str) -> str:
    """Return the local IPv4 address selected for reaching ``host``.

    The UDP socket is never sent; connect only asks the kernel which route and
    interface would carry traffic to the target.
    """
    target = socket.gethostbyname(host)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((target, 9))
        address = sock.getsockname()[0]
    finally:
        sock.close()
    if address.startswith("127."):
        raise OSError(f"no LAN route to {host}")
    return address


def host_from_tail(tail: str) -> str:
    """Combine a published tail with the local LAN interface prefix."""
    parts = tail.split(".")
    if len(parts) != 2 or any(not part.isdigit() for part in parts):
        raise ValueError("address tail must be two decimal IPv4 octets")
    if any(not 0 <= int(part) <= 255 for part in parts):
        raise ValueError("address tail contains an invalid IPv4 octet")
    local = local_ipv4_for("8.8.8.8").split(".")
    return ".".join(local[:2] + [str(int(part)) for part in parts])


def _ask_address(host: str) -> str:
    """Ask whether the document may carry the tail of this address.

    Shows the value itself rather than describing it. "The last two octets"
    is an abstraction somebody has to decode before they can consent to it;
    `178.105` is the thing that would be published, and a person can look at
    that and say yes or no.
    """
    octets = last_two_octets(host)
    if octets is None:
        return "hidden"
    try:
        local_prefix = ".".join(local_ipv4_for(host).split(".")[:2])
    except OSError:
        local_prefix = "the local LAN prefix"
    print(
        "\nThe report can carry the tail of this address, which is what lets"
        "\nseveral readings from one house be told apart -- a master, a slave"
        f"\nand two dongles otherwise produce four files that look alike."
        f"\nThe local route is {local_prefix}.x.x; only {octets} is published."
    )
    labels = {
        "two_octets": f"yes -- publish {octets}",
        "hidden": f"no -- publish {ADDRESS_HIDDEN}",
    }
    return _ask_menu(list(ADDRESS_ANSWERS), labels, "two_octets")


def _document(raw: dict, fingerprint: dict) -> dict:
    """Build the publishable document through the shared package API."""
    claimed = raw.get("connection", {})
    return publish_document(
        raw,
        fingerprint,
        command_line=raw.get("command_line", f"{SCRIPT} capabilities <host>"),
        host=str(raw.get("host", "")),
        publish_address=raw.get("address_detail") == "two_octets",
        user_inputs={
            "reporter": raw.get("reporter", "anonymous"),
            "comment": raw.get("comment", ""),
            "battery": raw.get("battery", ""),
            "transport": claimed.get("reported_by_hand", ""),
            "modbus_proxy": raw.get("proxy", ""),
            "other_inverter": raw.get("other_inverter", ""),
            "other_inverter_detail": raw.get("other_inverter_detail", ""),
        },
        serial=str(raw.get("serial", "")),
    )


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


def _destination(directory: Path, label: str, raw: dict, document: dict) -> Path:
    """Return where to write, and never over another device's document.

    Two readings of one machine can derive the same name: same serial, same
    battery, same capabilities, and the only thing between them is the path
    they came through -- which the label spells out only when somebody *said*
    which path it was. Answer "not sure" twice, as a first-time contributor
    reasonably does, and the second reading lands on the first one's filename.
    That has already cost a file in this project.

    Same device re-read still overwrites, because that is a correction and a
    directory of `-2`, `-3` copies of one machine is worse than none. The two
    cases are told apart by the **address tail** both documents carry. Where
    its owner withheld it, both say `xxx.xxx` and nothing published can tell
    them apart, so the reading is treated as another device: a spurious
    second file costs a filename, and being wrong the other way costs a
    reading.
    """
    tail = str(document.get("ip_address_last_two_octets") or "")
    known = bool(tail) and tail != ADDRESS_HIDDEN

    def is_this_device(stem: str) -> bool:
        """Whether the document called `stem` came from this same address."""
        if not known:
            return False
        try:
            theirs = json.loads(
                (directory / f"{stem}.json").read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return False
        return theirs.get("ip_address_last_two_octets") == tail

    candidates = [label]
    if known:
        # The address tail, which is in the document precisely so that several
        # readings from one house can be told apart.
        candidates.append(f"{label}-{tail.replace('.', '-')}")
    candidates += [f"{label}-{number}" for number in range(2, 20)]

    for stem in candidates:
        path = directory / f"{stem}.json"
        if not path.exists() or is_this_device(stem):
            if stem != label:
                print(
                    f"\n  {label}.json is already here from another reading, so"
                    f"\n  this one is written as {path.name} rather than"
                    "\n  over the top of it."
                )
            return path
    # Twenty readings of one label is not a case worth coding for; overwriting
    # the first is still wrong, so the timestamp goes in the name.
    return directory / f"{label}-{str(raw.get('read_at', '')).replace(':', '')}.json"


def _save(directory: Path, label: str, raw: dict, fingerprint: dict) -> list[Path]:
    """Write the one publishable document, and nothing else.

    The reading in memory carries the real serial and the full address; the
    document carries a stand-in serial and, with permission, two octets. No
    un-redacted copy is written: the transcript beside it already holds what
    the document leaves out, so a second private file would only be one more
    thing to forward by mistake.
    """
    directory.mkdir(parents=True, exist_ok=True)
    document = _ordered(_document(raw, fingerprint))
    path = _destination(directory, label, raw, document)
    path.write_text(json.dumps(document, indent=2) + "\n")
    return [path]


async def capabilities(args: argparse.Namespace) -> Reading:
    """Print one device's capability fingerprint, for comparing setups."""
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
        # `getattr`, because the bare `capabilities` subcommand's parser
        # supplies these and older callers holding a hand-built Namespace do
        # not. Absent reads the same as unasked, which is the honest default.
        "other_inverter": getattr(args, "other_inverter", ""),
        "other_inverter_detail": getattr(args, "other_inverter_detail", ""),
        "address_detail": args.address,
        # Reconstructed here rather than stored as the Namespace it came
        # from: `raw` is written out as JSON, and an argparse Namespace is not
        # serialisable -- which would have failed at the last line of a run
        # that had already spent a minute reading the device.
        #
        # `sungrow_survey.py` hands its own line, which repeats the whole
        # survey -- block read test included -- without a question.
        "command_line": getattr(args, "command_line", None) or _invocation(args),
        # What the block read test found, when the caller ran one and handed
        # it over. `sungrow_survey.py` does; the bare `capabilities` subcommand does
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
            space, start, count = field_address("serial_number")
            serial = await _async_read_retrying(
                _reader(unit, space), start, count, IDENTITY_ATTEMPTS
            )
            decoded = words_text(serial)
            raw["serial"] = decoded
            # Both, so that somebody about to send the file can see exactly
            # what leaves the building in place of their serial.
            print(f"  {'serial':<38}{decoded}  (anonymized to {stand_in(decoded)})")
        except (ModbusError, TimeoutError, OSError) as err:
            print(f"  {'serial':<38}unreadable ({type(err).__name__})")

        # Firmware first, because it is what makes two fingerprints
        # comparable: which registers a device answers moves between versions.
        firmware = await async_read_firmware(
            unit,
            on_string=lambda name, value: print(f"  {'firmware ' + name:<38}{value!r}"),
        )
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
                raw["register_dump"] = await _async_dump_bands(unit)
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
            contradiction = transport_contradiction(
                str(raw["connection"].get("verdict", "")), args.transport
            )
            if contradiction is not None:
                measured, _said = contradiction
                print(
                    f"\n  WARNING: you reported {args.transport!r}, but the "
                    f"registers say {measured!r}.\n"
                    "  Register 6100 has agreed with the reported transport on "
                    "every reading so far,\n"
                    "  so this is worth a second look -- and worth a --comment "
                    "if the hardware really\n"
                    "  does contradict it.\n"
                )
        verdict = effective_verdict(raw["connection"])
        print(f"  {'connection':<38}{verdict}")

        def probe_attempts(label: str) -> int:
            return (
                IDENTITY_ATTEMPTS
                if label.startswith(("device type", "output type", "battery capacity"))
                else 3
            )

        probe_values, probe_states = await async_probe_fields(
            unit, attempts=probe_attempts
        )
        for label, state in probe_states.items():
            values = probe_values.get(label)
            fingerprint["registers"][label] = state
            if values is None:
                print(f"  {label:<38}{state}")
                continue
            raw["registers"][label] = values
            if all(v in UNAVAILABLE for v in values):
                print(f"  {label:<38}unavailable (0x{values[0]:04X})")
                continue
            note = ""
            if label.startswith("device type"):
                note = f"  -> 0x{values[0]:04X}"
                # The model and phase are capability facts, not private ones.
                fingerprint["device_type_code"] = f"0x{values[0]:04X}"
            elif label.startswith("output type"):
                note = f"  -> {OUTPUT_TYPES.get(values[0], 'unknown')}"
                fingerprint["output_type"] = OUTPUT_TYPES.get(values[0], "unknown")
            print(f"  {label:<38}{values}{note}")

        # Devices that live on their own unit ids behind the same endpoint.
        def sibling(label: str, values: list[int] | None) -> None:
            unit_word, other_unit, name = label.split(" ", 2)
            if values is None:
                print(f"  {unit_word} {other_unit:<4} {name:<32} no answer")
                return
            # A device type code is a hex code in Sungrow's document, in the
            # model table, and in `device.device_type_code` -- so [3598] was
            # the one place it had to be converted by hand to be looked up.
            note = (
                " -> " + ", ".join(f"0x{value:04X}" for value in values)
                if "device type code" in name
                else ""
            )
            print(f"  {unit_word} {other_unit:<4} {name:<32} {list(values)}{note}")

        sibling_values, sibling_states = await async_probe_siblings(
            conn.for_unit, attempts=IDENTITY_ATTEMPTS, on_probe=sibling
        )
        raw["registers"].update(sibling_values)
        fingerprint["registers"].update(sibling_states)

        # The battery's own registers, on whichever unit answered for it.
        # Seventeen registers, so it is not behind the dump question either.
        pack_unit = battery_pack_unit(sibling_states)
        for unit_id in PACK_UNITS:
            if slave_inverter_at(sibling_states, unit_id) and (
                sibling_states.get(f"unit {unit_id} SBR battery module block")
                == "present"
            ):
                print(
                    f"  {'battery readings':<38}unit {unit_id} is an inverter, "
                    "not a pack"
                )
        if pack_unit is not None:
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

        # The wallbox's own register space, whenever one answered. Read
        # unconditionally rather than behind the dump question, because that
        # question is about the inverter's 1510 addresses and this is 206:
        # a wallbox is rare, its registers have no public document at all,
        # and a fingerprint that recorded only "a wallbox answered" was
        # throwing away the whole reason to have found it.
        wallbox_at = wallbox_unit(sibling_states)
        if wallbox_at is not None:
            print(f"  {'wallbox dump':<38}unit {wallbox_at}, 206 addresses...")
            try:
                raw["wallbox"] = {
                    "unit": wallbox_at,
                    "register_dump": await _async_dump_bands(
                        conn.for_unit(wallbox_at),
                        bands=WALLBOX_BANDS,
                        what="wallbox dump",
                    ),
                }
            except (ModbusError, TimeoutError, OSError) as err:
                print(f"  {'wallbox dump':<38}stopped early ({type(err).__name__})")
            else:
                answered = register_dump.answered(raw["wallbox"]["register_dump"])
                print(f"  {'wallbox dump':<38}{answered} addresses answered")
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
        label = args.label or package_label_for(document)
        written = list(_save(Path(args.save), label, raw, fingerprint))
        for path in written:
            print(f"  wrote {path}")
    return Reading(raw, fingerprint, document, written, missing)


async def cmd_capabilities(args: argparse.Namespace) -> int:
    """Fingerprint one device, as the `capabilities` subcommand."""
    if args.save is None:
        args.save = str(Path.cwd())
    reading = await capabilities(args)
    for path in reading.written:
        try:
            display_path = path.relative_to(Path.cwd())
        except ValueError:
            display_path = path
        merge = [
            "python/sungrow_control_test.py",
            args.host,
            "--port",
            str(args.port),
            "--unit",
            str(args.unit),
            "--merge-into",
            str(display_path),
        ]
        print(f"\nSurvey complete; fingerprint written to: {display_path}")
        print("To add the control-test result, run:")
        print("  " + shlex.join(merge))
    return 0


async def cmd_dump(args: argparse.Namespace) -> int:
    """Read a raw register range, block by block, and record what answered.

    The fingerprint checks registers we already know about. This is for the
    ones we do not: the documented gaps in the wallbox map at 21231-21261 and
    21267-21299, or any range a new model might answer. A block that fails is
    retried one register at a time, so one bad address does not hide the
    fifteen good ones beside it.
    """
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


def _ask_other_inverter() -> tuple[str, str]:
    """Ask whether a non-Sungrow inverter shares this installation.

    Returns the answer and, when it is yes, what they said it is.

    Worth a question because of what it does to a figure that otherwise looks
    like a fault. A Sungrow does not measure house load; it computes it, from
    its own output plus what the grid meter says is coming in. A second
    inverter feeding the same meter therefore makes `load_power` low by
    exactly that inverter's output -- continuously, while every register
    answers normally and every block reads clean.

    From the maintainer's end that is indistinguishable from a decoding bug,
    and no register can settle it: the inverter cannot see the thing that is
    confusing it. So it has to be asked, and the make and size are worth
    having because they say how large the error is.

    The detail is asked **only after a yes**, rather than as a box that sits
    there empty for the many people who have one inverter. A question nobody
    has to answer is cheaper than a field nobody has to fill in.
    """
    answer = _ask_menu(list(OTHER_INVERTER_ANSWERS), OTHER_INVERTER_ANSWERS, "no")
    if answer != "yes":
        return answer, ""
    print()
    print("  What is it? The make, and its size if you know it -- 'Fronius")
    print("  Symo 8.2' or '5 kW string inverter, south roof'. It explains a")
    print("  load figure that would otherwise read as a bug in this project.")
    return answer, _ask("The other inverter")


async def identify(host: str, port: int) -> Identity:
    """Identify an endpoint through the reusable package implementation."""
    return await async_identify(
        host,
        port,
        connection_factory=ModbusConnection,
    )


def described(who: Identity) -> str:
    """Return the one-line description a menu shows.

    The serial is printed with its stand-in beside it, because that is the
    name the published file will carry; the wording matches the document's own
    `serial_anonymized_hashed`.
    """
    if who.error is not None:
        return who.error
    if who.kind == "ihomemanager":
        # No serial line: the iHM's identity block has none, and nothing here
        # goes looking for one. The unit is always worth printing for this
        # device, because 247 is the whole reason it was found.
        model = who.model or "iHomeManager"
        return f"{model} -- on unit {who.unit}, port answered as an energy manager"
    described = f"serial {who.serial}, anonymized to {stand_in(who.serial)}"
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
    try:
        import socket

        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("192.168.1.1", 1))
        address = probe.getsockname()[0]
        probe.close()
        if not address.startswith("172.17."):
            # A /24, which is what a home router hands out. The prefix is not
            # knowable from a socket, and a wrong guess only changes the
            # default offered, which the person can type over.
            return network_of(address, 24)
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


def _ask_about_pollers() -> str:
    """Mention the other pollers, and say how to quiet them.

    Asked rather than assumed, because the answer changes what a thin report
    means: on a busy inverter a missing component is probably contention and
    worth re-running, and on a quiet one it is probably the firmware and
    worth reporting. This does not gate anything -- a report from a busy
    inverter is still worth having, and refusing to take one would just mean
    no fingerprint at all.

    Returns "yes" or "no", which `sungrow_survey.py --pollers` takes back.
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
        return "yes"
    print("  Good -- a quiet inverter gives the fullest report.")
    return "no"


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
    connection = ModbusConnection(ModbusTcpParams(host=host, port=port), timeout=6)
    capacity: float | None = None
    sungrow_pack = False
    has_battery = False
    extras: dict[str, float] = {}
    try:
        unit = connection.for_unit(unit_id)
        try:
            space, start, count = field_address("battery_capacity_high_precision")
            words = await _async_read_retrying(_reader(unit, space), start, count, 2)
        except (ModbusError, TimeoutError, OSError):
            pass
        else:
            if words[0] not in (0, 0xFFFF):
                capacity = declared_field("battery_capacity_high_precision").decode(
                    words
                )
        try:
            space, start, count = field_address("battery_voltage")
            voltage = await _async_read_retrying(_reader(unit, space), start, count, 2)
        except (ModbusError, TimeoutError, OSError):
            pass
        else:
            has_battery = voltage[0] not in (0, 0xFFFF)
        # Read even where capacity is not, because a third-party pack answers
        # these: showing them keeps the question down to the unreadable fact.
        for name, field in (
            ("charge_power", "battery_max_charge_power"),
            ("discharge_power", "battery_max_discharge_power"),
            ("health", "battery_state_of_health"),
        ):
            space, start, count = field_address(field)
            try:
                got = await _async_read_retrying(_reader(unit, space), start, count, 2)
            except (ModbusError, TimeoutError, OSError):
                continue
            if got[0] not in (0, 0xFFFF):
                extras[name] = declared_field(field).decode(got)
        space, start, _count = PACK_VOLTAGE
        for pack_unit in PACK_UNITS:
            try:
                await _async_read_retrying(
                    _reader(connection.for_unit(pack_unit), space),
                    start,
                    PRESENCE_WORDS,
                    2,
                )
            except (ModbusError, TimeoutError, OSError):
                continue
            sungrow_pack = True
            break
    finally:
        await connection.close()

    if sungrow_pack:
        model = model_for_capacity(capacity)
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
            "  probe.py sweep 192.168.1.0/24 --port 516 Modbus inside TLS: a\n"
            "                                           WiNet-S, or a wallbox at\n"
            "                                           its own address. Found\n"
            "                                           here; sungrow_survey.py\n"
            "                                           reads a wallbox\n"
            "  probe.py sweep 10.0.0.0/24 --concurrency 32 --timeout 3\n"
            "                                           through a VPN: fewer at\n"
            "                                           once, and more patience\n\n"
            "Or run sungrow_survey.py, which asks for the network and offers yours as\n"
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
        const=str(HERE),
        help="write <label>.json here, the publishable document "
        "(default: this script's folder)",
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
        "--other-inverter",
        default="",
        choices=("", *OTHER_INVERTER_ANSWERS),
        help="whether a non-Sungrow inverter shares this installation. It "
        "explains a reading that otherwise looks like a fault: the Sungrow "
        "computes house load from its own output plus grid import, so a "
        "second inverter on the same meter makes every load figure low by "
        "exactly that inverter's output while every register answers "
        "normally",
    )
    p_caps.add_argument(
        "--other-inverter-detail",
        default="",
        help="what that other inverter is -- make and size, e.g. 'Fronius "
        "Symo 8.2'. Free text and **published in the document**, so keep "
        "serials, addresses and names out of it",
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
    p_dump.add_argument(
        "--save",
        nargs="?",
        const=str(HERE),
        help="write <label>.dump.json here (default: this script's folder)",
    )
    p_dump.add_argument("--label")
    p_dump.set_defaults(func=cmd_dump)

    args = parser.parse_args()
    if args.command is None:
        # No subcommand: point at `sungrow_survey.py`, rather than printing usage at
        # somebody who was told "run this and send me the file". This used to
        # run the wizard itself; `sungrow_survey.py` is that wizard plus the phases
        # a survey needs -- identifying every device before asking anything,
        # the block read test, the transcript and a summary -- so having two
        # ways in would mean two answers to "how is this collected".
        print("For a full survey, run the one entry point:\n")
        print(f"    {_run_command('sungrow_survey.py')}\n")
        print("It finds the devices, asks what it cannot measure, and writes")
        print("the report. This script's subcommands are the pieces it uses:")
        print("  mdns, sweep, units, capabilities, dump -- see --help.")
        return 1
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
