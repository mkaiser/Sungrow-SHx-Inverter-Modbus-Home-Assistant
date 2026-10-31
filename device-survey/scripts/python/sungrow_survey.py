#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "sungrow-modbus==0.1.0a23",
#     "modbus-connection[tmodbus]>=4.10.0",
#     "tzdata",
# ]
# ///
"""Scan a Sungrow installation and write one report -- run this file.

    ./survey.sh            (Linux, macOS)
    survey.cmd             (Windows, or double-click it)

The launchers fetch what this needs -- a Python and the `sungrow-modbus`
library, pinned in the header above -- through `uv`. In a checkout with the
library installed, `python3 sungrow_survey.py` runs it directly.

Nothing else to remember: no flags, no order, no second command. It finds the
devices, asks the handful of things no register can answer, measures, and
prints what it found along with the path of the file to send back.

One entry point, because most of what a survey needs is *testimony* --
which cable, is there a proxy, may the address be published -- rather than
settings, and testimony typed as flags into several commands in the right
order is where a transport gets recorded wrong or a block test runs against
the wrong client.

**The survey reads, and writes only when it is told it may.** Its last
question asks whether the control test may run after the reading: a short
forced charge and discharge, feed-in limitation lifted for seconds, PV cut for
about a minute, a stop and start of the inverter -- each put back and read
back. Answered no, or not answered at all, nothing is written.
`./survey.sh control ...` hands everything after `control` to
`sungrow_control_test.py`, for its modes the survey never needs: a dry run, a
restore, a start.

The phases run in an order that each earns:

1. **Find and identify every device**, before any question. Two addresses
   with the same serial are one inverter reached two ways, which changes
   every answer that follows.
2. **Ask.** The questions Modbus cannot answer, and the consent questions.
3. **Check the transport**, so a claim that contradicts the measurement can
   be re-asked rather than warned about afterwards.
4. **The block read test**, before the long poll: it is the measurement that
   only works on an idle inverter, and the poll is itself a few dozen block
   reads of contention. Its result also explains the poll's misses.
5. **Read the registers and save**, which is `probe.py capabilities --save`.
6. **The control test**, only with leave given in step 2, folded into the
   document step 5 wrote -- after the reading, so a refusal or a restart
   cannot cost the reading.
7. **Say what was found**, rendered from the document that was written, so
   every claim in the summary is a value somebody can go and check.

One connection at a time throughout, and several devices strictly one after
another: a Sungrow grants very few Modbus sessions, and the surest way to
measure contention is to cause it.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from datetime import datetime
import ipaddress
import logging
from pathlib import Path
import shlex
import sys
import textwrap
import time
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blocks
import ihomemanager_direct
import probe
import sungrow_control_test
import wallbox_direct

from sungrow_modbus import block_test, dump as register_dump, model_for
from sungrow_modbus.block_test import ATTEMPTS, ROUNDS
from sungrow_modbus.control_test import FORCED_EFFECT_W
from sungrow_modbus.discovery import NetworkTooLarge, async_identify_unit_247, hosts_in
from sungrow_modbus.survey import async_read_6100, async_read_module, next_steps
from sungrow_modbus.survey_document import (
    address_tail,
    claim_of,
    collected_nothing,
    connection_block,
    transport_contradiction,
)

#: The ports a sweep looks at, what answering on each one means, and whether
#: this tool can then read it.
#:
#: 502 and 503 are Modbus TCP and get identified. **516 is swept and not
#: read**, and what it is was measured rather than taken from the web.
#:
#: It is Modbus TCP **inside TLS**, served by two different devices. A
#: **WiNet-S** has it beside its 502, and is not read here: it refuses the same
#: registers over TLS as on 502 -- inputs 2612 and 2628 with 0x02 -- so it is
#: not a way round what a dongle will not forward. A **wallbox with a network
#: connection of its own** has only this, answering as unit 248, and is read:
#: `wallbox_direct.py` finds it by its model name and surveys it into a
#: document of its own.
#:
#: 503 is the Logger's port, and one an iHomeManager may answer on at unit
#: 247. Sungrow's V1.0.2 document gives it 502, 503 and 504, **one TCP
#: connection each**, so a port somebody else holds looks closed; whatever
#: answers on 502 or 503 is asked for it, and `--port 504` reaches the third.
#: An iHomeManager is read (`ihomemanager_direct.py`) into a document of its
#: own. Neither it nor a Logger has answered on any network surveyed.
SWEEP_PORTS: tuple[tuple[int, str, bool], ...] = (
    (
        502,
        "an inverter, or the WiNet-S dongle in front of one."
        "\n          Sungrow's default, and where nearly everything answers",
        True,
    ),
    (503, "a Logger1000/3000, or an iHomeManager at unit 247", True),
    (
        516,
        "Modbus over TLS: a wallbox at its own address (read),"
        "\n          or a WiNet-S (reported only)",
        False,
    ),
)

#: Exit codes, and the sentence each one means. Printed as the last line,
#: because a pasted transcript loses `$?`.
CODES = {
    0: "the scan completed and every device produced a whole document",
    1: "nothing was collected",
    2: "this cannot run here",
    3: "collected, but something the filename claims did not read",
    4: "collected, but the reported transport contradicts the measurement",
    5: "the control test left something changed -- run the --restore line above",
}

#: Worst-first ordering for a run over several devices. `max()` on the codes
#: themselves gets this wrong -- 2 is not worse than 4 by arithmetic, it is
#: worse because nothing ran at all. 5 is worst of all: it is the one code
#: that means a house is left changed.
SEVERITY = (0, 3, 4, 1, 2, 5)

#: What the control-test question may be answered with.
CONTROL_TEST_ANSWERS: tuple[str, ...] = ("no", "yes")

#: The control-test question, asked last of the questions so the long part of
#: the run needs nobody at the keyboard. Every effect the test can have is
#: named, because leave given for less than it does is not leave.
CONTROL_TEST_QUESTION = f"""
  One last question, and the only one that lets this run write.

  After the reading, the control test can check that the integration writes
  each setting at the right scale: it writes a setting, reads it back, and
  watches what the inverter does. It asks the inverter for this:

    * a forced charge and a forced discharge of the battery at
      {FORCED_EFFECT_W:.0f} W, for less than a minute together;
    * feed-in limitation switched on for a few seconds where it is off,
      capping the export while it is;
    * PV generation cut for about half a minute, where the inverter has
      the register for it, and back within a minute more;
    * a stop and a start of the inverter. Stopped within seconds, running
      again after 3 to 4 minutes in daylight and over 6 at night. While it
      is stopped there is no PV production, the battery is idle, backup
      output drops, and Home Assistant and the app see it unavailable.

  Every setting it touches is saved first, and put back and read back at
  the end -- whatever happens. If anything cannot be put back the run says
  so, keeps the saved copy, and prints the one command that restores it.
"""


class Found(NamedTuple):
    """One device, and what was learned about it before anything was asked."""

    host: str
    port: int
    unit: int
    who: probe.Identity


class Transport(NamedTuple):
    """What the wire says about how we got in."""

    state_6100: str
    """`answered`, `refused` (an exception response) or `no answer` (the link)."""
    module_named: str | None
    verdict: str
    web_ui: bool


class Outcome(NamedTuple):
    """One device's survey, for the summary and for the exit code."""

    found: Found
    #: What was actually surveyed, which is the unit the *answers* named --
    #: not the default `Found` was built with.
    unit: int
    document: dict
    written: list[Path]
    transport: Transport | None
    reported_transport: str
    block_outcome: block_test.Outcome | None
    code: int
    #: The control test's own exit code, or None where it did not run.
    control_code: int | None = None


class Tee:
    """Write to the terminal and to the transcript at once.

    A transcript rather than a shell redirect, for one reason: whoever runs
    this is usually being walked through it, and "run this and send me both
    files" fails at the step where they have to remember `| tee`. Line
    buffered, so the file is complete even if the run is interrupted --
    which, on an inverter that hangs up, it sometimes is.
    """

    def __init__(self, stream, path: Path):
        """Open the transcript beside the stream it mirrors."""
        self._stream = stream
        self._file = path.open("a", encoding="utf-8", buffering=1)

    def write(self, text: str) -> int:
        """Write to both, and never let the transcript break the run."""
        with contextlib.suppress(Exception):
            self._file.write(text)
        return self._stream.write(text)

    def flush(self) -> None:
        """Flush both."""
        with contextlib.suppress(Exception):
            self._file.flush()
        self._stream.flush()

    def isatty(self) -> bool:
        """Answer for the terminal, so the progress bars still redraw."""
        return self._stream.isatty()

    def close(self) -> None:
        """Close the transcript, leaving the terminal alone."""
        with contextlib.suppress(Exception):
            self._file.close()


def _workspace() -> tuple[Path, Path]:
    """Return where the document and the transcript go: `device-survey/`.

    Anchored on the script, not the working directory, so the launcher, `make
    scan` and a plain `python` from anywhere all land in the same place --
    the folder above the launcher a person double-clicked, under visible
    names, with the summary saying which file is which. Inside a checkout
    `.gitignore` covers both names, which matters because the transcript
    carries the real serial.
    """
    return probe.HERE, probe.HERE


def _library() -> str:
    """Say which `sungrow-modbus` this runs on, and whether it is a release.

    The version alone cannot tell: a source tree carries the version of the
    release it is heading for, and the tree and PyPI can both say 0.1.0a14
    while only one of them has the code being tested. What can tell is
    `direct_url.json`, which an installer writes for a library installed from
    a path -- `SUNGROW_MODBUS_LIBRARY`, `make scan-local`, an editable install
    -- and never for one fetched from an index.
    """
    from importlib.metadata import PackageNotFoundError, distribution
    import json

    try:
        dist = distribution("sungrow-modbus")
    except PackageNotFoundError:
        return "(version unknown)"
    try:
        origin = json.loads(dist.read_text("direct_url.json") or "null")
    except ValueError:
        origin = None
    if not isinstance(origin, dict):
        return f"{dist.version}, the PyPI package"
    where = str(origin.get("url", "")).removeprefix("file://")
    kind = "source" if "dir_info" in origin else "wheel"
    return f"{dist.version} from the {kind} {where} -- NOT a release"


def _preamble(echo, transcript: Path) -> None:
    """Say what this is, what it will do, and what it will not do."""
    echo("=" * 72)
    echo("Sungrow device survey")
    echo("=" * 72)
    echo("")
    echo("  This reads registers. It writes to your inverter only if you say")
    echo("  yes to the control test at the end of the questions, and then only")
    echo("  after the reading is done.")
    echo("")
    echo("  What it does, in order:")
    echo("    1  find the devices on your network and ask each one who it is")
    echo("    2  ask you the few things no register can answer")
    echo("    3  work out how the reading reaches the device")
    echo("    4  test the block reads the integration makes")
    echo("    5  read every register in the map, sweep the raw register bands,")
    echo("       and write the report")
    echo("    6  the control test, only if you allowed it")
    echo("    7  print what it found")
    echo("")
    echo(f"  Library         sungrow-modbus {_library()}")
    echo("                  (the package the Home Assistant integration uses)")
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    echo(f"  Started         {started}")
    echo(f"  Transcript      {transcript}")
    echo("")


#: Addresses that answered a port this tool cannot read, as (host, port).
#:
#: Module level rather than returned, because it is a finding about the
#: *network* and not about any one device -- and `_find` already returns the
#: list of devices to survey. A list nobody consumes would be worse than a
#: global here: the summary is the only reader, and this is what it reads.
_UNREADABLE: list[tuple[str, int]] = []

#: Wallboxes answering at their own address, found by `_find`, surveyed by
#: `run` after the inverters. Module state like `_UNREADABLE`, for the same
#: reason: `_find` returns the inverters, which is what every caller expects.
_WALLBOXES: list[wallbox_direct.Found] = []

#: iHomeManagers found by `_find`, surveyed by `run` after the wallboxes.
_MANAGERS: list[ihomemanager_direct.Found] = []


async def _find(args, echo) -> list[Found]:
    """Find every device worth surveying, and ask each who it is.

    Identity first, for every address, because it is what tells one inverter
    on two paths from two inverters -- and the answer changes what every
    later question means.
    """
    unreadable = _UNREADABLE
    unreadable.clear()
    wallboxes = _WALLBOXES
    wallboxes.clear()
    managers = _MANAGERS
    managers.clear()
    echo("-" * 72)
    echo("1  Finding devices")
    echo("-" * 72)

    if args.host:
        addresses = []
        for host in args.host:
            # A wallbox at its own address has no 502, so asking it as an
            # inverter would only produce a document of nothing.
            if found_wallbox := await wallbox_direct.async_identify(host):
                wallboxes.append(found_wallbox)
                echo(f"  {host}:{wallbox_direct.PORT}  a {found_wallbox.model} wallbox")
                if not await probe._tcp_open(host, args.port, 2.0):
                    continue
            addresses.append((host, args.port))
    else:
        echo("")
        echo("  Which addresses to look at. The default below is this")
        echo("  machine's own network, worked out from its address -- on a")
        echo("  home network that is almost always the right answer, so press")
        echo("  Enter to accept it. Type a different one only if your inverter")
        echo("  is on another network, in the form 192.168.1.0/24.")
        echo("")
        echo("  Three ports get looked at, and they mean different devices:")
        for port, means, readable in SWEEP_PORTS:
            echo(f"    {port}   {means}")
            if not readable:
                echo("          reported only -- this tool cannot read it")
        echo("")
        echo("  A quiet address costs the full 4 seconds, so a network of 254")
        echo("  addresses takes about a minute per port. Nothing is written to")
        echo("  anything: this only opens a connection and closes it.")
        echo("")
        network = _ask_network(echo)
        addresses = []
        for port, _means, readable in SWEEP_PORTS:
            echo(f"\n  sweeping {network} on port {port}")
            hosts, elapsed = await probe._sweep_addresses(network, port)
            echo(f"  {len(hosts)} answered in {elapsed:.1f}s")
            if readable:
                addresses += [(host, port) for host in hosts]
                continue
            # A wallbox at its own address is read; anything else here is
            # found and not read. Saying so is the whole value: a user whose
            # dongle answers here would otherwise conclude it has no Modbus
            # at all, when it has Modbus this tool does not read.
            for host in hosts:
                if found_wallbox := await wallbox_direct.async_identify(host):
                    wallboxes.append(found_wallbox)
                    echo(f"    {host}:{port} a {found_wallbox.model} wallbox")
                    continue
                unreadable.append((host, port))
                echo(f"    {host}:{port} answered, and cannot be read -- see below")
        if not addresses:
            echo("")
            echo("  Nothing answered. An inverter reached over a VPN often needs")
            echo("  a longer timeout than a sweep uses, and one on another")
            echo("  subnet will not be found at all -- pass the address:")
            echo(f"    python {Path(__file__).name} 192.168.1.50")
            typed = _ask_host(echo)
            if not typed:
                return []
            addresses = [(typed, args.port)]

    found = []
    unknown_247 = []
    echo("")
    for host, port in addresses:
        who = await probe.identify(host, port)
        echo(f"  {host}:{port}  {probe.described(who)}")
        if who.kind == "ihomemanager":
            # Read by its own map, not the inverter's: every inverter block
            # refuses at unit 247. One device answering on 502 and 503 is
            # read once, on the first port it answered.
            if not any(manager.host == host for manager in managers):
                managers.append(
                    ihomemanager_direct.Found(host, port, who.model or "iHomeManager")
                )
            continue
        if who.kind == "logger":
            # A Logger with no inverter on units 1-5 of its endpoint. Read
            # like an iHomeManager, by its own package.
            if not any(manager.host == host for manager in managers):
                managers.append(
                    ihomemanager_direct.Found(host, port, who.model, "logger")
                )
            continue
        if who.kind == "unit247":
            # Something at unit 247 that is neither: its type code is the
            # finding, and nothing here knows how to read it.
            unknown_247.append(who.device_type_code)
            continue
        # The unit that answered, not the flag's default. Where `--unit` was
        # given explicitly it still wins, because somebody passing it knows
        # something the probe does not.
        found.append(Found(host, port, args.unit or who.unit or 1, who))

    for code in sorted(set(unknown_247)):
        echo("")
        echo(f"  A device answered at unit 247 with type code 0x{code:04X}, which is")
        echo("  neither an iHomeManager's (0x072A) nor a known Logger's. This")
        echo("  survey cannot read it; its type code is worth reporting on the")
        echo("  tracker as it is.")
    if managers:
        echo("")
        echo("  An iHomeManager or Logger answered. Neither has been read at any")
        echo("  house before, so its reading is the first: it is read after")
        echo("  the inverters, into a document of its own.")
        if not found and any(manager.kind == "logger" for manager in managers):
            echo("")
            echo("  No inverter answered on units 1-5. A Logger gives the inverters")
            echo("  behind it unit ids of its own, listed on its web page, and this")
            echo("  survey only looks at 1-5. Say on the tracker which unit ids your")
            echo("  Logger lists, beside this document.")
        elif not found:
            echo("")
            echo("  No inverter was found at these addresses. An iHomeManager")
            echo("  does not forward its inverters: Sungrow's own note says it")
            echo("  carries only system energy dispatch data, not the devices")
            echo("  behind it. So the inverter is a separate address -- sweep")
            echo("  for it, or pass it as well:")
            echo(f"    python {Path(__file__).name} 192.168.1.50")

    _report_shared_serials(found, echo)
    # Addresses given on the command line are all surveyed: they are the
    # choice, and asking again would stop a replay from running unattended.
    if len(found) > 1 and not args.host:
        echo("")
        keys = [f"{entry.host}:{entry.port}" for entry in found] + ["all"]
        labels = {key: key for key in keys}
        labels["all"] = f"all {len(found)} of them, one after another"
        chosen = probe._ask_menu(keys, labels, "all")
        if chosen != "all":
            found = [entry for entry in found if f"{entry.host}:{entry.port}" == chosen]
    return found


def _report_shared_serials(found: list[Found], echo) -> None:
    """Say out loud when one inverter answers at two addresses.

    An inverter with a cable in its own LAN port *and* a WiNet-S dongle
    answers at both addresses with the same serial, and every reading differs
    between them -- which measuring
    points are forwarded, which unit ids exist, whether 0xFFFF arrives as 0.
    Two documents from one machine are useful, and only if the file says so.
    """
    serials: dict[str, list[Found]] = {}
    for entry in found:
        if entry.who.serial:
            serials.setdefault(entry.who.serial, []).append(entry)
    for serial, entries in serials.items():
        if len(entries) < 2:
            continue
        where = ", ".join(f"{entry.host}:{entry.port}" for entry in entries)
        echo("")
        echo(f"  Note: {where} report the same serial.")
        echo("  That is one inverter reached two ways -- typically a cable in")
        echo("  the inverter and a dongle beside it. Both are worth scanning,")
        echo("  and each answer below applies to the path being scanned, not")
        echo("  to the machine.")
        del serial


def _ask_network(echo) -> str:
    """Ask which network to sweep, until the answer is one that can be swept.

    Checked here rather than left to the sweep, because the sweep refuses
    once per port and is then followed by "Nothing answered", which reads as
    a fact about the network rather than about the typing -- `192.168.3`
    typed for `192.168.178.3/24`, say.
    """
    default = probe._default_network()
    while True:
        network = probe._ask(
            "Network to scan -- Enter to accept, or type another range", default
        )
        try:
            hosts_in(network)
        except NetworkTooLarge as error:
            echo(f"  {error}")
        except ValueError:
            echo(f"  {network!r} is not a network. Type it as an address and a")
            echo("  prefix, e.g. 192.168.178.0/24 -- or one address on its own.")
        else:
            return network


def _ask_host(echo) -> str:
    """Ask for one address, refusing an IP address with a part missing.

    A hostname is allowed, so not everything must parse as an address -- but
    something made only of digits and dots is meant as one, and must be
    whole. The resolver would otherwise accept `192.168.3` as 192.168.0.3, an
    inet_aton shorthand nobody types on purpose, and connect somewhere else.
    """
    while True:
        typed = probe._ask("Or type an address now (blank to give up)")
        if not typed or not all(c.isdigit() or c == "." for c in typed):
            return typed
        try:
            ipaddress.ip_address(typed)
        except ValueError:
            echo(f"  {typed!r} is not a whole address -- it needs four parts,")
            echo("  e.g. 192.168.178.3.")
        else:
            return typed


#: What `--pollers` may say. `probe._ask_about_pollers` returns the same.
POLLER_ANSWERS: tuple[str, ...] = ("no", "yes")

#: The flags that answer a question, in the order the questions come. Each is
#: written even when its value is empty -- `--comment ''` -- because an absent
#: flag means "ask", and the point of the line is that nothing is asked.
REPLAY_FLAGS: tuple[tuple[str, str], ...] = (
    ("--unit", "unit"),
    ("--pollers", "pollers"),
    ("--transport", "transport"),
    ("--proxy", "proxy"),
    ("--other-inverter", "other_inverter"),
    ("--other-inverter-detail", "other_inverter_detail"),
    ("--address", "address"),
    ("--reporter", "reporter"),
    ("--comment", "comment"),
    ("--battery", "battery"),
    ("--control-test", "control_test"),
)


def _script_name() -> str:
    """Return this script the way the person running it would type it.

    The repository path inside a checkout, the bare name in a downloaded copy
    of the folder, where there is no `scripts/` above it. The launchers pass
    every argument through, so `survey.sh` takes the same line.
    """
    here = Path(__file__).resolve()
    if here.parent.name == "python":
        return f"python/{here.name}"
    return here.name


def replay_command(answers: argparse.Namespace, host: str = "<host>") -> str:
    """Return the survey command that repeats a run without asking anything.

    **The host is a placeholder** unless the caller hands the real one, which
    only the screen does: the document is built around not carrying the
    address. Values are shell-quoted, so a comment with an apostrophe pastes
    back intact. `--port`, `--timeout` and `--passes` appear only where they
    differ from the defaults, since they shape the reading but answer nothing.
    """
    # The placeholder bare, as every published line has it; a real host quoted.
    parts = [_script_name(), host if host == "<host>" else shlex.quote(host)]
    for flag, attribute, default in (
        ("--port", "port", 502),
        ("--timeout", "timeout", 10.0),
        ("--passes", "passes", 8),
    ):
        value = getattr(answers, attribute, default)
        if value != default:
            parts += [flag, f"{value:g}" if isinstance(value, float) else str(value)]
    address_tail = getattr(answers, "address_tail", None)
    if address_tail:
        parts += ["--address-tail", shlex.quote(str(address_tail))]
    for flag, attribute in REPLAY_FLAGS:
        value = getattr(answers, attribute, None)
        if value is None:
            continue
        if attribute == "other_inverter_detail" and not value:
            continue
        parts += [flag, shlex.quote(str(value))]
    return " ".join(parts)


def _echo_replay(echo, line: str) -> None:
    """Print the replay line, and how to hand it to the launcher."""
    _script, _, rest = line.partition(" ")
    echo("  To repeat this survey without the questions:")
    echo(f"    {line}")
    echo("  or through the launcher, with the same arguments:")
    echo(f"    ./survey.sh {rest}")


async def _ask_all(entry: Found, args, echo) -> argparse.Namespace:
    """Ask the questions no register can answer, for one device.

    Every prompt goes to stderr while this runs, so the transcript and the
    summary carry the answers rather than six-line menus and half-typed
    lines. What was answered is printed afterwards, once, as a block.
    """
    echo("-" * 72)
    echo(f"2  Questions for {entry.host}:{entry.port}")
    echo("-" * 72)
    answers = argparse.Namespace(
        host=entry.host,
        port=entry.port,
        unit=entry.unit,
        timeout=args.timeout,
        passes=args.passes,
        save=None,
        label=None,
    )
    with contextlib.redirect_stdout(sys.stderr):
        answers.pollers = args.pollers or probe._ask_about_pollers()
        if args.unit is None:
            print()
            print("  Every Modbus device on an endpoint has a number, its unit id")
            print("  or 'device address'. A Sungrow inverter is 1 unless somebody")
            print("  changed it, and 1 is what its app and its manual assume. A")
            print("  battery, a wallbox and a second inverter have their own, and")
            print("  this scan finds those by itself -- so unless you have been")
            print("  told otherwise, press Enter.")
            if entry.unit != 1:
                # Say why the default is not the number the paragraph above
                # just called usual, or it reads as a mistake.
                print()
                print(f"  This device answered on unit {entry.unit}, so that is the")
                print("  default below. A second inverter in a master/slave cluster")
                print("  has its own device address, and 2 is what one measured.")
            answers.unit = int(
                probe._ask("Modbus unit id (device address)", str(entry.unit))
            )
        answers.transport_given = args.transport is not None
        answers.transport = args.transport or probe._ask_transport()
        answers.proxy = args.proxy or probe._ask_proxy()
        if args.other_inverter:
            answers.other_inverter = args.other_inverter
            answers.other_inverter_detail = (
                (args.other_inverter_detail or "")
                if args.other_inverter == "yes"
                else ""
            )
        else:
            answers.other_inverter, answers.other_inverter_detail = (
                probe._ask_other_inverter()
            )
        # Always, and not asked: the raw bands are where registers nothing
        # maps were found -- the inverter's clock, 45 holding registers that
        # answer real values -- and a survey is the only thing that reads them.
        answers.dump = True
        answers.address = args.address or probe._ask_address(entry.host)
        answers.reporter = (
            args.reporter
            if args.reporter is not None
            else probe._ask(
                "Who is reporting this, to credit and to ask (blank for anonymous)",
                "anonymous",
            )
        )
        answers.comment = (
            args.comment
            if args.comment is not None
            else probe._ask("Anything else worth recording (blank to skip)")
        )
        if args.battery is None:
            print()
            print("  One more, and the registers may settle it without asking:")
            print("  reading what this device says about its battery. A few")
            print("  seconds, or up to half a minute over a slow link.")
    answers.battery = (
        args.battery
        if args.battery is not None
        else await probe._ask_battery(entry.host, answers.port, answers.unit)
    )
    answers.address_tail = args.address_tail or (
        probe.last_two_octets(entry.host) if answers.address == "two_octets" else None
    )
    answers.control_test = _ask_control_test(args)
    # The command that repeats this survey without a single question: every
    # answer as a flag, the host a placeholder. Published as `command_line`;
    # a `probe.py capabilities` line would repeat the reading but skip the
    # block read test, so it would not be this run.
    answers.command_line = replay_command(answers)
    echo("")
    echo("  Answered:")
    for label, value in (
        ("unit id", answers.unit),
        # The first of the four, not the second: the second is the sentence a
        # *document* carries and is empty for "not sure", which read here as
        # though the question had not been asked.
        ("transport", probe.REPORTED_TRANSPORTS[answers.transport][0]),
        ("behind a proxy", answers.proxy),
        (
            "another inverter",
            answers.other_inverter_detail or answers.other_inverter,
        ),
        ("address in the file", answers.address),
        ("reporter", answers.reporter),
        ("comment", answers.comment or "(none)"),
        ("battery", answers.battery or "(read from the registers)"),
        ("control test", answers.control_test),
    ):
        echo(f"    {label:<22} {value}")
    echo("")
    # Printed **after** the last question so it carries every answer, and
    # before the reading rather than only into the file: the moment somebody
    # wants it is the moment they realise they would have to answer the
    # questions again, and a run that dies halfway leaves them nothing
    # otherwise. With the real host, since this screen is theirs.
    _echo_replay(echo, replay_command(answers, host=entry.host))
    echo("")
    echo("  Starting now, and this is the long part: two registers that say")
    echo("  how the reading reaches the device, then every block read the")
    echo("  integration makes, then the whole register map, then 2181 raw")
    echo("  addresses. Over a slow link that can take a quarter of an hour, and")
    echo("  it will look stuck more than once. Every step says what it is")
    echo("  waiting for.")
    echo("")
    return answers


def _ask_control_test(args) -> str:
    """Ask whether the control test may run, defaulting to no.

    Nobody at a terminal is a no: leave to write is never assumed, and a run
    piped from somewhere else has nobody to give it.
    """
    if args.control_test is not None:
        return args.control_test
    if not sys.stdin.isatty():
        return "no"
    with contextlib.redirect_stdout(sys.stderr):
        print(CONTROL_TEST_QUESTION)
        allowed = probe._ask_yes(
            "May the control test run after the reading, and restart the inverter?",
            False,
        )
    return "yes" if allowed else "no"


async def _check_transport(entry: Found, answers, echo) -> Transport:
    """Measure how we got in, and re-ask if the answer contradicts it.

    Two signals, both from the specification rather than inferred: registers
    6100-6195 are documented as unsupported through a WiNet-S or Logger, and
    register 13265 names the communication module if one is fitted. Read
    here, before the long poll, so a disagreement is a question rather than a
    warning printed after the fact.
    """
    echo("-" * 72)
    echo("3  How the reading reaches the device")
    echo("-" * 72)

    connection = probe.ModbusConnection(
        probe.ModbusTcpParams(host=entry.host, port=entry.port),
        timeout=answers.timeout,
    )
    try:
        unit = connection.for_unit(answers.unit)
        state_6100 = await async_read_6100(unit, attempts=probe.IDENTITY_ATTEMPTS)
        module = await async_read_module(unit)
    finally:
        await connection.close()

    # A WiNet-S serves a web interface; an inverter's own LAN port does not.
    # A third signal, and the only one that does not come from a register.
    web_ui = await probe._tcp_open(entry.host, 443, 1.0) or await probe._tcp_open(
        entry.host, 80, 1.0
    )
    verdict = str(connection_block(state_6100, module)["verdict"])
    echo(f"  register 6100        {state_6100}")
    echo(f"  register 13265       {module or 'no module named'}")
    echo(f"  port 80 or 443       {'open' if web_ui else 'refused'}")
    echo(f"  verdict              {verdict}")

    contradiction = transport_contradiction(verdict, answers.transport)
    if contradiction is not None:
        measured, reported = contradiction
        echo("")
        echo("  This contradicts the answer given above.")
        echo(f"    measured   {measured}")
        echo(f"    you said   {reported}")
        if getattr(answers, "transport_given", False):
            # Given as a flag, so kept: a replay must not stop to ask, and
            # the document records the answer beside the measurement anyway.
            echo("  kept as given by --transport; the document records both")
            return Transport(state_6100, module, verdict, web_ui)
        with contextlib.redirect_stdout(sys.stderr):
            print("\n  The measurement is usually right: it is two registers and")
            print("  a port, and the same house can have both routes.")
            if probe._ask_yes("Change the answer to match the measurement?", True):
                answers.transport = (
                    "direct_lan" if measured.startswith("direct") else "winet"
                )
                echo(f"  answer changed to    {answers.transport}")
    return Transport(state_6100, module, verdict, web_ui)


async def _block_test(
    entry: Found, answers, echo
) -> tuple[block_test.Outcome, str] | None:
    """Run the block read test as a phase, not as an afterthought.

    Every block the integration issues, read the way the integration reads
    it. This is where a register that takes a whole tier down shows up, and
    it has to run before the register poll: the poll is itself block reads,
    and this measurement only means anything on an idle link.
    """
    echo("-" * 72)
    echo("4  Block read test")
    echo("-" * 72)
    to_read = await block_test.inverter_blocks()
    echo("  plan    the library's own block reads, recorded from the poll")
    client = blocks.client_for(
        entry.host, answers.port, answers.unit, answers.timeout, 0.05
    )
    echo(f"  client  {client.label}")
    echo(f"  {len(to_read)} blocks, {ROUNDS} rounds, {ATTEMPTS} attempts each")
    # Said out loud because this is the phase that has to be bounded, and
    # somebody watching a run that has gone quiet needs to know it will end.
    echo(
        f"  whatever never answers is then narrowed, {block_test.NARROW_BUDGET:.0f}s "
        "in total\n"
    )
    try:
        outcome = await blocks.measure(
            client, to_read, attempts=ATTEMPTS, rounds=ROUNDS, echo=echo
        )
    except OSError as error:
        echo(f"  the block read test could not run: {error}")
        return None
    finally:
        await client.close()
    blocks.report(outcome, echo=echo)
    echo("")
    return outcome, client.label


async def _survey(entry: Found, args, echo) -> Outcome:
    """Take one device through every phase and return what it produced."""
    answers = await _ask_all(entry, args, echo)
    transport = await _check_transport(entry, answers, echo)
    # Again, because the transport check may have changed an answer.
    answers.command_line = replay_command(answers)
    tested = await _block_test(entry, answers, echo)
    outcome, client = tested or (None, None)

    echo("-" * 72)
    echo("5  Reading the registers")
    echo("-" * 72)
    documents, _private = _workspace()
    answers.save = str(documents)
    # Handed over before the document is written, so the block evidence is
    # published rather than left in a transcript the contributor keeps.
    answers.block_read_test = _block_document(outcome, client)
    reading = await probe.capabilities(answers)
    echo("")
    code = _code_for(reading, transport, answers)

    control_code = None
    if answers.control_test == "yes" and reading.written and code != 1:
        control_code = await _control_test(
            entry, answers, reading.written[0], args, echo
        )
        if control_code == 5:
            code = 5

    return Outcome(
        found=entry,
        unit=answers.unit,
        document=reading.document,
        written=reading.written,
        transport=transport,
        reported_transport=answers.transport,
        block_outcome=outcome,
        code=code,
        control_code=control_code,
    )


def control_arguments(
    entry: Found, answers, document: Path, *, simulated: bool = False
) -> list[str]:
    """Return the control test's command line for the leave given in step 2.

    One yes covers everything the question named, so the restart, the
    export-limit lift and the PV cut are all on. `--allow-dark` because the
    readback half finds a factor-ten error with or without the sun, and
    refusing a run for want of it would refuse the one the person agreed to.
    `--yes` because the leave was given among the questions, and the run must
    not stop to ask it again a quarter of an hour later.
    """
    line = [
        entry.host,
        "--port",
        str(answers.port),
        "--unit",
        str(answers.unit),
        "--timeout",
        f"{answers.timeout:g}",
        "--merge-into",
        str(document),
    ]
    if simulated:
        # A simulator has nothing to restart and no behaviour to watch.
        return [*line, "--simulated", "--no-restart"]
    return [
        *line,
        "--restart",
        "--enable-export-limit",
        "--cut-pv",
        "--allow-dark",
        "--yes",
    ]


async def _control_test(entry: Found, answers, document: Path, args, echo) -> int:
    """Run the control test against the device just read, into its document."""
    echo("-" * 72)
    echo("6  Control test")
    echo("-" * 72)
    echo("  Pausing 10s so the reading's session is closed before this one")
    echo("  opens; a Sungrow grants very few.")
    await asyncio.sleep(10)
    line = control_arguments(entry, answers, document, simulated=args.simulated)
    control = sungrow_control_test._parser().parse_args(line)
    code = await sungrow_control_test.async_main(control, _DROPS)
    echo("")
    return code


def _block_document(
    outcome: block_test.Outcome | None, client: str | None = None
) -> dict | None:
    """Render a block read test for the published document, or None.

    The measurement `src/sungrow_modbus/inverter/layout.py` is ever changed
    from. Published, not left in the transcript -- the file a contributor is
    told to *keep*, because it carries their real address -- so a maintainer
    reading a submitted document can see which of the integration's reads
    that device would fail.

    Three lists rather than one, because the distinction is the whole point of
    the tool and a reader must not have to reconstruct it:

    * `answered` -- read at least once. Nothing to do.
    * `never_answered` -- failed every round while its neighbours answered.
      The only shape that belongs in `layout.py`, and only then if it failed
      *outright*: a range marked `not narrowed` names no register, and a read
      that only timed out cannot tell a silent inverter from a lost answer.
    * `intermittent` -- answered sometimes. Contention, not a fault, and
      re-running on a quiet inverter is the fix.

    Carries no host and no serial: block numbers and outcome words only.
    `client` is the label of the client that measured, which decides what
    the rest means: the library rejects a padded frame, the strict raw socket
    names the count that would read it.
    """
    if outcome is None:
        return None
    return block_test.document(
        outcome,
        rounds=ROUNDS,
        attempts=ATTEMPTS,
        client=client,
        reconnects=outcome.reconnects,
    )


def _code_for(reading: probe.Reading, transport: Transport, answers) -> int:
    """Return the exit code for one device.

    The code describes the *scan*, not the inverter. A run that finds three
    refusing registers is the most useful kind there is and exits 0; a run
    whose filename under-claims because the device type did not read exits 3,
    because nobody reading the file afterwards can see that.
    """
    # Before anything else: a document of nothing is not a degraded document.
    # A link that went away before the first read leaves every field missing,
    # which is 1, not 3 -- "the filename under-claims" would announce an
    # empty file as the one to send.
    if collected_nothing(reading.document):
        return 1
    # `capabilities` computes this for exactly this purpose: the fields whose
    # absence the *filename* hides. A document carries no model name -- only
    # the device type code, because naming it is the reader's job -- so
    # checking for one here would report every healthy scan as degraded.
    if reading.missing:
        return 3
    if transport and transport_contradiction(transport.verdict, answers.transport):
        return 4
    return 0


def _summary(results: list[Outcome], transcript: Path, echo) -> None:
    """Say what was found, in the order the questions arrived.

    Three markers, in plain words so they survive being pasted anywhere:
    `read` came off the wire, `said` a person typed it, `n/a` nothing
    established it. That mirrors the document's own split between measurements
    and `user_inputs`, which exists precisely so a claim is never read as a
    reading.

    Everything quoted here comes from the document that was written, which is
    what makes it paste-safe: the document carries two octets of the address
    and a stand-in serial, so this cannot carry more.
    """
    for result in results:
        document = result.document
        device = document.get("device", {})
        readings = document.get("readings", {})
        inputs = document.get("user_inputs", {})
        label = result.written[0].stem if result.written else "(not written)"
        tail = document.get("ip_address_last_two_octets", "hidden")

        echo("=" * 72)
        echo("What this scan found")
        echo(f"{label}    tail {tail}, unit {result.unit}")
        echo("=" * 72)
        echo("")
        echo("  The machine")
        code = device.get("device_type_code")
        named = model_for(int(code, 16)) if code else None
        echo(f"  read  model            {named or 'not in the model table'} ({code})")
        echo(f"  read  output           {device.get('output_type') or 'not read'}")
        stand_in = device.get("serial_anonymized_hashed", "not read")
        echo(f"  read  serial           {stand_in} (stand-in)")
        echo("")
        echo("  The way in")
        if result.transport is not None:
            echo(f"  read  verdict          {result.transport.verdict}")
            echo(f"  read  register 6100    {result.transport.state_6100}")
            echo(
                "  read  register 13265   "
                f"{result.transport.module_named or 'no module named'}"
            )
            ports = (
                "open, consistent with a dongle"
                if result.transport.web_ui
                else "refused, consistent with an inverter's own LAN port"
            )
            echo(f"  read  ports 80, 443    {ports}")
        echo(f"  said  transport        {inputs.get('transport', 'not said')}")
        echo("  n/a   wired or WiFi    not determinable over Modbus")
        echo("")
        echo("  What answered")
        values = readings.get("values", {})
        answered = sum(1 for value in values.values() if value is not None)
        echo(f"  read  decoded fields   {answered} of {len(values)}")
        missed = readings.get("components_that_did_not_answer", [])
        if missed:
            echo(f"  read  components       {len(missed)} missed as a whole:")
            for name in missed:
                echo(f"        {name}")
        else:
            echo("  read  components       every one answered as a whole block")
        salvaged = readings.get("fields_read_individually", [])
        if salvaged:
            echo(
                f"  read  salvaged         {len(salvaged)} field(s) read one at "
                "a time, so from different moments than their neighbours"
            )
        dump = document.get("register_dump")
        if dump:
            echo(f"  read  register dump    {dump.get('summary', 'written')}")
        echo("")
        _summary_blocks(result, echo)
        _summary_actions(result, echo)
        echo("  Told to this run, not measured")
        for key in sorted(inputs):
            # An empty answer is not silence. The battery question is only
            # *asked* when the registers cannot settle it -- a Sungrow pack
            # answers its own module block, so the run reads the model and
            # says nothing -- and "(not answered)" would read as though
            # somebody had shrugged at it.
            echo(f"  said  {key:<16} {inputs[key] or '(not asked -- read instead)'}")
        echo("")
        _summary_unreadable(echo)
        echo("  Survey has been written to")
        for path in result.written:
            echo(f"        {path}")
            echo("")
            _summary_control(result, path, echo)
        echo("=" * 72)
        echo("")


def _summary_control(result: Outcome, path: Path, echo) -> None:
    """Say what the control test did, or how to run it later."""
    if result.control_code is not None:
        means = sungrow_control_test.CODES[result.control_code]
        echo(f"  The control test: {means} (exit {result.control_code}).")
        echo("  Its result is in the document above.")
        return
    echo("  The control test did not run. To run it later, into this document:")
    echo(
        "        "
        + shlex.join(
            [
                "./survey.sh",
                "control",
                result.found.host,
                "--port",
                str(result.found.port),
                "--unit",
                str(result.unit),
                "--merge-into",
                str(path),
            ]
        )
    )


def _summary_blocks(result: Outcome, echo) -> None:
    """Report the block read test, in the words `layout.py` quotes."""
    echo("  The block read test")
    outcome = result.block_outcome
    if outcome is None:
        echo("  n/a   did not run")
        echo("")
        return
    total = len(outcome.tally)
    ok = total - len(outcome.failing)
    echo(f"  read  blocks           {ok} of {total} answered")
    for block in outcome.failing:
        echo(
            f"        {block.space} {block.address} x{block.count} in "
            f"{block.component}   <-- never answered"
        )
    for block in outcome.intermittent:
        echo(
            f"        {block.space} {block.address} x{block.count} in "
            f"{block.component}   <-- intermittent, so contention rather than "
            "a fault"
        )
    echo("")


def _summary_unreadable(echo) -> None:
    """Say what answered a port this tool cannot speak, or say nothing.

    One case today: a **WiNet-S serving Modbus over TLS on 516**. Measured on
    two dongles -- TLS 1.2, a Sungrow-signed certificate, and real registers
    through the tunnel -- and refused on the inverters' own LAN ports, so it
    is the dongle's port and not, as reported elsewhere, an iHomeManager's.

    A wallbox on 516 is read (`wallbox_direct.py`) and never lands here; a
    dongle's TLS port is only reported, because it serves what its 502
    serves. Printed as a finding rather than a warning, because a user told
    there is nothing on 516 would be told something false -- there is a
    working Modbus interface there.

    It is **not** a way round the dongle's forwarding limits: 2612 and 2628
    refuse over TLS exactly as they do on 502.
    """
    if not _UNREADABLE:
        return
    echo("  Answered a port this tool cannot read")
    for host, port in _UNREADABLE:
        echo(f"  read  {host}:{port}")
    echo("        Modbus over TLS, which this survey reads only from a wallbox. On a")
    echo("        WiNet-S this is normal and not a fault: the port works and")
    echo("        serves the same registers as 502, refusing the same ones.")
    echo("        Worth mentioning in an issue only if 502 found nothing --")
    echo("        then this is where your device is.")
    echo("")


def _advice(finding: block_test.Finding) -> str:
    """Say what a block-test finding means to the person who ran the survey."""
    Advice = block_test.Advice
    if finding.advice is Advice.FORWARDING_LIMIT:
        return (
            "This reading came through a communication module, which forwards "
            "fewer measuring points than the inverter's own LAN port -- so this "
            "may be a forwarding limit rather than a register fault. Read the "
            "same registers directly before touching "
            "src/sungrow_modbus/inverter/layout.py; if they answer there, it "
            "belongs in transport capability gating instead."
        )
    if finding.advice is Advice.NOT_NARROWED:
        # layout.py takes an exact register; offering it a fifteen-register
        # range would be offering it a guess out of fifteen.
        return (
            "Narrowing ran out of its budget here, so this range is not yet an "
            "answer -- it names no single register. Aim a full run at just this "
            "block to finish it: blocks.py <host> -r "
            f"{finding.space}:{min(finding.addresses)}:{len(finding.addresses)} "
            "--narrow-budget 0"
        )
    if finding.advice is Advice.NOT_EVIDENCE:
        return (
            "This failed by timing out rather than by refusing. A timeout cannot "
            "tell a silent inverter from an answer lost on the way, so it is not "
            "evidence about the register -- do not add it to "
            "src/sungrow_modbus/inverter/layout.py. Re-read these registers from "
            "a link that fails fast."
        )
    if finding.advice is Advice.ALREADY_ISOLATED:
        # A refusal `layout.py` already isolates is the isolation working,
        # not a recommendation to add it again.
        return (
            "Read directly from the inverter and refused outright, so this is "
            "the device. It is **already isolated** in "
            "src/sungrow_modbus/inverter/layout.py, which is why it cost only "
            "its own field(s) rather than its whole tier -- nothing to do, and worth "
            "adding to doc/compatibility.md as another machine that refuses it."
        )
    return (
        "Read directly from the inverter and refused outright, so this is the "
        "device refusing. Add the field(s) these belong to to "
        "src/sungrow_modbus/inverter/layout.py and quote the block read test "
        "above -- that module is only ever added to from a measurement, and "
        "this is the measurement."
    )


def _summary_actions(result: Outcome, echo) -> None:
    """Say what to do about what was measured, with the evidence beside it."""
    shared_steps = next_steps(result.document)
    if shared_steps:
        echo("  Shared next steps")
        for number, step in enumerate(shared_steps, 1):
            echo(f"  {number}. {step.title}: {step.detail}")
        echo("")

    actions = []
    outcome = result.block_outcome
    through_module = result.transport is not None and claim_of(
        result.transport.verdict
    ) not in ("direct",)
    for finding in (
        block_test.findings(outcome, through_module=through_module)
        if outcome is not None
        else []
    ):
        actions.append(
            f"{finding.component}: {finding.space} register {finding.registers} "
            f"{finding.outcome} ({finding.detail}). " + _advice(finding)
        )
    if outcome is not None and outcome.intermittent and not outcome.failing:
        actions.append(
            "Some blocks answered only sometimes, which is contention rather "
            "than a fault. Re-run with nothing else polling the inverter "
            "before reading anything into it."
        )
    if result.code == 1:
        actions.append(
            "Nothing was read from this device: not one value, not one raw "
            "address. That is the link, not the inverter -- check that the "
            "address still answers and nothing else holds the connection, "
            "then run again. The file written for it is not worth sending."
        )
    if result.code == 3:
        actions.append(
            "Something the filename claims did not read, so the name "
            "under-claims what this device is. Worth a second run."
        )
    if result.code == 4:
        actions.append(
            "The reported transport still contradicts the measurement. A "
            "document is read by comparing it with others, so this one should "
            "not be published until that is settled."
        )
    if not actions:
        return
    echo("  What to do about it")
    for number, action in enumerate(actions, 1):
        # Wrapped, because this block is written to be pasted into an issue
        # or a commit message, and a 300-column line survives neither.
        lines = textwrap.wrap(action, width=68)
        echo(f"  {number}  {lines[0]}")
        for line in lines[1:]:
            echo(f"     {line}")
    echo("")


def _worst(codes: list[int]) -> int:
    """Return the worst code by the table's order, not by arithmetic."""
    return max(codes, key=SEVERITY.index) if codes else 1


async def _survey_wallbox(found: wallbox_direct.Found, args, echo) -> int:
    """Ask the three questions a wallbox needs, read it, and say what was written.

    Fewer than an inverter's: transport is measured (it is this address), and
    a wallbox has no battery, proxy or second inverter to ask about. The
    address and the reporter are consent, and asked as they are for an
    inverter -- unless `--address`, `--reporter` and `--comment` answer them.
    """
    echo("-" * 72)
    echo(f"Wallbox at {found.host}:{wallbox_direct.PORT}, a {found.model}")
    echo("-" * 72)
    with contextlib.redirect_stdout(sys.stderr):
        consent = args.address or probe._ask_address(found.host)
        reporter = (
            args.reporter
            if args.reporter is not None
            else probe._ask(
                "Who is reporting this, to credit and to ask (blank for anonymous)",
                "anonymous",
            )
        )
        comment = (
            args.comment
            if args.comment is not None
            else probe._ask("Anything else worth recording (blank to skip)")
        )
    tail = address_tail(found.host, consent == "two_octets")
    answers = argparse.Namespace(
        timeout=args.timeout, reporter=reporter, comment=comment
    )
    # A wallbox is asked three of the questions, so its line carries three.
    answers.command_line = replay_command(
        argparse.Namespace(address=consent, reporter=reporter, comment=comment)
    )
    _echo_replay(
        echo,
        replay_command(
            argparse.Namespace(address=consent, reporter=reporter, comment=comment),
            host=found.host,
        ),
    )
    directory, _private = _workspace()
    echo("  reading over TLS, unit 248, every read on a data point's start")
    try:
        reading = await wallbox_direct.async_survey(
            found,
            answers,
            directory,
            echo,
            address_tail=tail,
            local_time=probe._local_time,
        )
    except (OSError, RuntimeError, probe.ModbusError) as error:
        echo(f"  {found.host}:{wallbox_direct.PORT} failed: {error}")
        return 1
    section = reading.document["wallbox"]
    answered = register_dump.answered(section["register_dump"])
    echo("")
    echo(f"  read  readings         {len(section['readings'])}")
    echo(f"  read  raw addresses    {answered} answered")
    if reading.written is None:
        echo("  Nothing was read from the wallbox -- the link, not the device.")
    else:
        echo(f"  Wrote\n        {reading.written}\n          send this")
    echo("")
    return reading.code


async def _find_loggers_behind(results: list[Outcome], echo) -> None:
    """Ask unit 247 behind every inverter its owner said a Logger fronts.

    A Logger gives its inverters units of their own on its endpoint, so
    `identify` stops at the inverter and never sees it. One read each, and
    only where the owner answered `logger` for the transport.
    """
    for result in results:
        if result.reported_transport != "logger":
            continue
        host, port = result.found.host, result.found.port
        if any(manager.host == host for manager in _MANAGERS):
            continue
        who = await async_identify_unit_247(host, port)
        if who is None or who.kind != "logger":
            echo(f"  {host}:{port}  no Logger answered at unit 247")
            continue
        echo(f"  {host}:{port}  {probe.described(who)}, read after the inverter")
        _MANAGERS.append(ihomemanager_direct.Found(host, port, who.model, "logger"))


async def _survey_ihomemanager(found: ihomemanager_direct.Found, args, echo) -> int:
    """Ask a wallbox's three questions, read the iHomeManager or Logger.

    Address, reporter and comment, asked as for a wallbox -- or answered by
    `--address`, `--reporter` and `--comment`. It has no battery, proxy or
    second inverter of its own to ask about.
    """
    echo("-" * 72)
    title = "Logger" if found.kind == "logger" else "iHomeManager"
    echo(f"{title} at {found.host}:{found.port}, unit 247, {found.model}")
    echo("-" * 72)
    with contextlib.redirect_stdout(sys.stderr):
        consent = args.address or probe._ask_address(found.host)
        reporter = (
            args.reporter
            if args.reporter is not None
            else probe._ask(
                "Who is reporting this, to credit and to ask (blank for anonymous)",
                "anonymous",
            )
        )
        comment = (
            args.comment
            if args.comment is not None
            else probe._ask("Anything else worth recording (blank to skip)")
        )
    tail = address_tail(found.host, consent == "two_octets")
    # The port goes in: an iHomeManager answers on 502, 503 or 504, and a
    # replay on the default would ask the wrong one.
    asked = argparse.Namespace(
        port=found.port,
        timeout=args.timeout,
        address=consent,
        reporter=reporter,
        comment=comment,
    )
    answers = argparse.Namespace(
        timeout=args.timeout,
        reporter=reporter,
        comment=comment,
        command_line=replay_command(asked),
    )
    _echo_replay(echo, replay_command(asked, host=found.host))
    directory, _private = _workspace()
    if found.kind == "logger":
        echo("  reading its identity, then the rest of its 8000 block raw;")
    else:
        echo("  reading every documented register, then the gaps between them;")
    echo("  this port takes one connection, so nothing else can use it meanwhile")
    try:
        reading = await ihomemanager_direct.async_survey(
            found, answers, directory, echo, address_tail=tail
        )
    except (OSError, RuntimeError, probe.ModbusError) as error:
        echo(f"  {found.host}:{found.port} failed: {error}")
        return 1
    section = reading.document[ihomemanager_direct.PACKAGES[found.kind].DOCUMENT]
    echo("")
    echo(f"  read  readings         {len(section['readings'])}")
    answered = register_dump.answered(section["register_dump"])
    echo(f"  read  raw addresses    {answered} answered")
    if section["masked_text"]:
        echo(
            f"  masked {len(section['masked_text'])} run(s) of text outside the"
            " documented strings, published only as stand-ins"
        )
    if reading.written is None:
        echo(f"  Nothing was read from the {title} -- the link, not the device.")
    else:
        echo(f"  Wrote\n        {reading.written}\n          send this")
    echo("")
    return reading.code


async def run(args) -> int:
    """Run the whole scan, and return the exit code."""
    _documents, private = _workspace()
    private.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    transcript = private / f"sungrow-scan-{stamp}.log"

    out = Tee(sys.stdout, transcript)
    errors = Tee(sys.stderr, transcript)
    sys.stdout, sys.stderr = out, errors

    def echo(text: str = "") -> None:
        print(text, file=out, flush=True)

    try:
        _preamble(echo, transcript)
        echo("  A report is written to send. A private session log is also kept")
        echo("  beside it, and holds the real serial number and address.")
        echo("")

        try:
            found = await _find(args, echo)
        except ValueError as error:
            echo(f"  {error}")
            return _finish(2, echo)
        if not found and not _WALLBOXES and not _MANAGERS:
            echo("  Nothing to scan.")
            return _finish(1, echo)

        results = []
        for number, entry in enumerate(found, 1):
            if number > 1:
                echo("  Pausing 10s so the previous session is closed before the")
                echo("  next one opens; a Sungrow grants very few.")
                time.sleep(10)
            try:
                results.append(await _survey(entry, args, echo))
            except SystemExit:
                raise
            except (OSError, RuntimeError) as error:
                echo(f"  {entry.host}:{entry.port} failed: {error}")
        device_codes = []
        for found_wallbox in _WALLBOXES:
            if results or device_codes:
                echo("  Pausing 10s before the next device.")
                time.sleep(10)
            device_codes.append(await _survey_wallbox(found_wallbox, args, echo))
        await _find_loggers_behind(results, echo)
        for found_manager in _MANAGERS:
            if results or device_codes:
                echo("  Pausing 10s before the next device.")
                time.sleep(10)
            device_codes.append(await _survey_ihomemanager(found_manager, args, echo))
        if not results and not device_codes:
            return _finish(1, echo)

        if results:
            _summary(results, transcript, echo)
        return _finish(_worst([result.code for result in results] + device_codes), echo)
    finally:
        sys.stdout, sys.stderr = out._stream, errors._stream
        out.close()
        errors.close()


class _LinkDrops(logging.Handler):
    """Count the Modbus backend's reconnects instead of printing each one.

    `tmodbus` logs every connection the inverter drops, at ERROR, and re-opens
    it by itself -- so with no logging configured those lines reach the
    terminal through Python's last-resort handler, in the middle of a progress
    bar. The survey already tolerates and retries each drop. What they say
    together is worth one line: a Sungrow that keeps dropping the link has
    another client polling it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "connection lost" in message or "closed by remote host" in message:
            self.count += 1


#: Installed by `main`; `_finish` reports what it counted.
_DROPS = _LinkDrops()


def _quiet_backend() -> None:
    """Keep the backend's connection log off the terminal, and count drops."""
    backend = logging.getLogger("tmodbus")
    backend.addHandler(_DROPS)
    backend.propagate = False


def _finish(code: int, echo) -> int:
    """Print the code and the sentence it means, and return it."""
    if _DROPS.count:
        echo(
            f"The inverter dropped the connection {_DROPS.count} time(s); each "
            "was re-opened and the scan carried on."
        )
        echo(
            "Frequent drops mean something else is polling it -- stop Home "
            "Assistant for a fuller report."
        )
        echo("")
    echo(f"exit {code} -- {CODES[code]}.")
    return code


def _parser() -> argparse.ArgumentParser:
    """Return the command line: the addresses, and a flag for every answer."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "host",
        nargs="*",
        help="address(es) to scan. Omit to sweep the network and choose.",
    )
    parser.add_argument(
        "--address-tail",
        help="reuse a previous survey tail, combining it with this LAN prefix",
    )
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--passes", type=int, default=8)
    answers = parser.add_argument_group(
        "answers",
        "Each answers one question, which is then not asked. A document's "
        "command_line gives all of them, so it repeats a survey without "
        "asking anything. They apply to every device this run surveys.",
    )
    answers.add_argument(
        "--unit", type=int, help="the inverter's unit id (device address)"
    )
    answers.add_argument(
        "--pollers",
        choices=POLLER_ANSWERS,
        help="whether anything else is polling the inverter right now; "
        "'yes' carries on anyway",
    )
    answers.add_argument(
        "--transport",
        choices=tuple(probe.REPORTED_TRANSPORTS),
        help="how this reading reaches the device. Kept as given when the "
        "measurement disagrees; the document records both",
    )
    answers.add_argument("--proxy", choices=tuple(probe.PROXY_ANSWERS))
    answers.add_argument(
        "--other-inverter", choices=tuple(probe.OTHER_INVERTER_ANSWERS)
    )
    answers.add_argument(
        "--other-inverter-detail",
        help="make and size of that inverter; published, so no serials",
    )
    answers.add_argument(
        "--address",
        choices=probe.ADDRESS_ANSWERS,
        help="whether the document may carry the last two octets of the address",
    )
    answers.add_argument("--reporter", help="who to credit; published")
    answers.add_argument("--comment", help="free text; published, so no serials")
    answers.add_argument(
        "--battery",
        help="the battery's brand, where no register reports it ('' for none)",
    )
    answers.add_argument(
        "--control-test",
        choices=CONTROL_TEST_ANSWERS,
        help="whether the control test may run after the reading: a short forced "
        "charge and discharge, feed-in limitation for seconds, PV cut for about "
        "a minute, and a restart of the inverter, each put back afterwards",
    )
    parser.add_argument(
        "--simulated",
        action="store_true",
        help="the device is a simulator: the control test, if allowed, writes "
        "without a restart and stamps its result as evidence about nothing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and run.

    `control` first hands everything after it to the control test, so the one
    launcher reaches every mode of it -- the restore above all, which is the
    way out of exit 5 for somebody who has only this folder.
    """
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["control"]:
        return sungrow_control_test.main(argv[1:])
    args = _parser().parse_args(argv)
    if args.address_tail and args.host:
        # A host given outright wins: the tail is only a way to rebuild one,
        # from a prefix guessed off the local route -- which in a container is
        # the bridge's, not the LAN's. A tail that contradicts the host is a
        # pasted line meant for another device, so it is refused, not mixed in.
        tail = [part.lstrip("0") or "0" for part in args.address_tail.split(".")]
        wrong = [
            host
            for host in args.host
            if probe.last_two_octets(host)
            != probe.last_two_octets(f"0.0.{'.'.join(tail)}")
        ]
        if wrong:
            print(
                f"--address-tail {args.address_tail} does not match "
                f"{', '.join(wrong)}; drop one of them"
            )
            return 2
    elif args.address_tail:
        try:
            args.host = [probe.host_from_tail(args.address_tail)]
        except (OSError, ValueError) as error:
            print(f"cannot reconstruct address from --address-tail: {error}")
            return 2
        print(
            f"--address-tail {args.address_tail} on this machine's LAN prefix "
            f"is {args.host[0]}; if that is not the inverter, give its address"
        )
    _quiet_backend()
    try:
        return probe.run(run(args))
    except KeyboardInterrupt:
        if args.control_test == "yes":
            # Leave was given, so the run may have reached the control test,
            # which puts back whatever it wrote before it lets go.
            print(
                "\nStopped. If the control test had started, it put back what it "
                "wrote; a snapshot file beside the script means something was "
                "not, and `./survey.sh control <host> --restore <file>` restores it."
            )
            return 1
        print("\nStopped. Nothing was written to your inverter.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
