#!/usr/bin/env python3
"""Scan a Sungrow installation and write one report -- run this file.

    python collect.py

Nothing else to remember: no flags, no order, no second command. It finds the
devices, asks the handful of things no register can answer, measures, and
prints what it found along with the path of the file to send back.

This exists because collecting one contributor's data took four commands in a
particular order with a dozen flags between them, most of which are
*testimony* -- which cable, is there a proxy, may the address be published --
rather than settings. That cost real mistakes in two days: a transport
recorded from a comment later withdrawn, a block test that reported "ok" for
reads the integration could not make, and nine documents deleted because
their transport could not be trusted.

**Everything here only reads.** No Modbus write function code is implemented
in any file of this directory.

The phases run in an order that each earns:

1. **Find and identify every device**, before any question. Two addresses
   with the same serial are one inverter reached two ways, which changes
   every answer that follows -- and is exactly what produced the withdrawn
   documents.
2. **Ask.** The questions Modbus cannot answer, and the consent questions.
3. **Check the transport**, so a claim that contradicts the measurement can
   be re-asked rather than warned about afterwards.
4. **The block read test**, before the long poll: it is the measurement that
   only works on an idle inverter, and the poll is itself 27 block reads of
   contention. Its result also explains the poll's misses.
5. **Read the registers and save**, which is `probe.py capabilities --save`.
6. **Say what was found**, rendered from the document that was written, so
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
from pathlib import Path
import sys
import textwrap
import time
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: Checked before anything else imports, because the alternative is a
#: traceback about `datetime.UTC` at a stranger who was told this needs
#: nothing installed. 3.11 is the floor for `datetime.UTC` and
#: `asyncio.Runner`, both of which are conveniences rather than
#: requirements -- so this says the version rather than blaming the user.
# ruff reads this against the *repository's* requires-python, which is 3.14
# because Home Assistant needs it. This file does not run here -- it runs on
# a contributor's own machine, where 3.11 is a real possibility and 3.14 is
# not. Hence the exemption rather than a raised bound.
if sys.version_info < (3, 11):  # noqa: UP036
    have = ".".join(str(part) for part in sys.version_info[:3])
    raise SystemExit(
        f"This needs Python 3.11 or newer, and this is Python {have}.\n\n"
        "  Try `python3` if you ran `python`.\n\n"
        "If 3.11 is genuinely not available to you, say so in the issue: the\n"
        "floor is two conveniences deep, not a real requirement, and it can\n"
        "be lowered."
    )

import blocks
import portable
import probe

#: How the block read test is driven, and why it is not one round.
#:
#: `--rounds` and `--attempts` measure different things, and the survey used
#: to use only the weaker one. Attempts are back-to-back reads of one block;
#: rounds go round the whole plan and come back. Contention correlates in
#: time, so three attempts at one block can all land inside the same busy
#: moment and be filed as a deterministic fault -- which is exactly what
#: happened. Home Assistant's fastest tier polls every five seconds
#: indefinitely, so a competing client is not a moment but a *state*, and
#: three rounds with twenty-six other blocks in between is what tells the two
#: apart.
#:
#: Three rounds of two attempts rather than one round of three: six reads per
#: block either way, spread out instead of bunched. The cost is that the
#: tally phase now takes three passes over the plan, which on a fast link is
#: seconds and on a slow one is minutes -- against a wrong `layout.py` entry,
#: which is permanent.
ROUNDS = 3
ATTEMPTS = 2

#: The ports a sweep looks at, what answering on each one means, and whether
#: this tool can then read it.
#:
#: 502 and 503 are Modbus TCP and get identified. **516 is swept and not
#: read**, and what it is was measured rather than taken from the web.
#:
#: It is a **WiNet-S** port serving Modbus over TLS. Found open on both
#: dongles of a house with no iHomeManager anywhere on it, and refused on
#: both inverters' own LAN ports -- so the report that called it an
#: iHomeManager port was wrong about whose it is. TLS 1.2 with a Sungrow
#: self-signed certificate, and a request through the tunnel returns real
#: registers.
#:
#: Not read here because this survey has no TLS client: a plain socket gets
#: the connection accepted and then closed, which is why the port looks dead
#: without one. Worth sweeping anyway -- it is a real Modbus interface, and a
#: user told their dongle has nothing on 516 would be told something false.
#:
#: And it is **not** a way round what a dongle will not forward: inputs 2612
#: and 2628 refuse with exception 0x02 over TLS exactly as on 502.
#:
#: 503 is the port an iHomeManager is *documented* on, at unit 247, and it is
#: also the Logger's. Neither has ever answered on any network surveyed.
SWEEP_PORTS: tuple[tuple[int, str, bool], ...] = (
    (
        502,
        "an inverter, or the WiNet-S dongle in front of one."
        "\n          Sungrow's default, and where nearly everything answers",
        True,
    ),
    (503, "a Logger1000/3000, or an iHomeManager at unit 247", True),
    (516, "a WiNet-S serving Modbus over TLS, which this cannot speak", False),
)

#: Exit codes, and the sentence each one means. Printed as the last line,
#: because a pasted transcript loses `$?`.
CODES = {
    0: "the scan completed and every device produced a whole document",
    1: "nothing was collected",
    2: "this cannot run here",
    3: "collected, but something the filename claims did not read",
    4: "collected, but the reported transport contradicts the measurement",
}

#: Worst-first ordering for a run over several devices. `max()` on the codes
#: themselves gets this wrong -- 2 is not worse than 4 by arithmetic, it is
#: worse because nothing ran at all.
SEVERITY = (0, 3, 4, 1, 2)


class Found(NamedTuple):
    """One device, and what was learned about it before anything was asked."""

    host: str
    port: int
    unit: int
    who: probe.Identity


class Transport(NamedTuple):
    """What the wire says about how we got in."""

    answered_6100: bool
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
    block_outcome: blocks.BlockOutcome | None
    code: int


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


def _workspace() -> tuple[Path, Path, bool]:
    """Return where the document, the transcript and the private file go.

    Two situations, and the difference matters more than it looks. Inside the
    checkout, `.testdata/` is gitignored and is where anything carrying a real
    serial belongs. Unpacked from a zip there is no `.testdata/`, and creating
    a *hidden* directory holding somebody's serial and address inside the
    folder they were told to send back is how a private file gets published by
    accident. So outside a checkout everything lands in the working directory
    under a visible name, and the summary says which file is which.
    """
    # `probe` owns the walk, so the document, the private reading and the
    # transcript cannot end up in different houses -- which is exactly what
    # happened when this asked about the current directory and `_raw_dir`
    # asked about it separately.
    root = probe._checkout_root()
    if root:
        return root / ".testdata" / "fingerprints", root / ".testdata", True
    here = Path.cwd()
    return here, here, False


def _preamble(echo, transcript: Path, client_label: str) -> None:
    """Say what this is, what it will do, and what it will not do."""
    echo("=" * 72)
    echo("Sungrow device scan")
    echo("=" * 72)
    echo("")
    echo("  This reads registers. It cannot write to your inverter: no Modbus")
    echo("  write function is implemented in any file here.")
    echo("")
    echo("  What it does, in order:")
    echo("    1  find the devices on your network and ask each one who it is")
    echo("    2  ask you the few things no register can answer")
    echo("    3  work out how the reading reaches the device")
    echo("    4  test the block reads the integration makes")
    echo("    5  read every register in the map and write the report")
    echo("    6  print what it found")
    echo("")
    echo(f"  Modbus client   {client_label}")
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    echo(f"  Started         {started}")
    echo(f"  Transcript      {transcript}")
    echo("")


#: Which Modbus client the block read test used, for the document to record.
#:
#: Module level for the same reason `_UNREADABLE` is: it is a fact about the
#: run rather than about a device, `_block_test` is where it is known, and
#: `BlockOutcome` has no business carrying it -- `blocks.py` is a tool in its
#: own right and its return type should not grow a field for one caller's
#: document.
_CLIENT_LABEL: list[str] = []

#: Addresses that answered a port this tool cannot read, as (host, port).
#:
#: Module level rather than returned, because it is a finding about the
#: *network* and not about any one device -- and `_find` already returns the
#: list of devices to survey. A list nobody consumes would be worse than a
#: global here: the summary is the only reader, and this is what it reads.
_UNREADABLE: list[tuple[str, int]] = []


async def _find(args, echo) -> list[Found]:
    """Find every device worth surveying, and ask each who it is.

    Identity first, for every address, because it is what tells one inverter
    on two paths from two inverters -- and the answer changes what every
    later question means.
    """
    unreadable = _UNREADABLE
    unreadable.clear()
    echo("-" * 72)
    echo("1  Finding devices")
    echo("-" * 72)

    if args.host:
        addresses = [(host, args.port) for host in args.host]
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
        network = probe._ask(
            "Network to scan -- Enter to accept, or type another range",
            probe._default_network(),
        )
        addresses = []
        for port, _means, readable in SWEEP_PORTS:
            echo(f"\n  sweeping {network} on port {port}")
            hosts, elapsed = await probe._sweep_addresses(network, port)
            echo(f"  {len(hosts)} answered in {elapsed:.1f}s")
            if readable:
                addresses += [(host, port) for host in hosts]
                continue
            # Found and not read. Saying so is the whole value: a user whose
            # iHomeManager answers here would otherwise conclude it has no
            # Modbus at all, when it has Modbus this tool cannot speak.
            for host in hosts:
                unreadable.append((host, port))
                echo(f"    {host}:{port} answered, and cannot be read -- see below")
        if not addresses:
            echo("")
            echo("  Nothing answered. An inverter reached over a VPN often needs")
            echo("  a longer timeout than a sweep uses, and one on another")
            echo("  subnet will not be found at all -- pass the address:")
            echo(f"    python {Path(__file__).name} 192.168.1.50")
            typed = probe._ask("Or type an address now (blank to give up)")
            if not typed:
                return []
            addresses = [(typed, args.port)]

    found = []
    echo("")
    for host, port in addresses:
        who = await probe.identify(host, port)
        echo(f"  {host}:{port}  {probe.described(who)}")
        # The unit that answered, not the flag's default. Where `--unit` was
        # given explicitly it still wins, because somebody passing it knows
        # something the probe does not.
        found.append(Found(host, port, who.unit or args.unit, who))

    _report_shared_serials(found, echo)
    if len(found) > 1:
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

    The condition that invalidated two documents: an inverter with a cable in
    its own LAN port *and* a WiNet-S dongle answers at both addresses with
    the same serial, and every reading differs between them -- which measuring
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
        probe._ask_about_pollers()
        print()
        print("  Every Modbus device on an endpoint has a number, its unit id")
        print("  or 'device address'. A Sungrow inverter is 1 unless somebody")
        print("  changed it, and 1 is what its app and its manual assume. A")
        print("  battery, a wallbox and a second inverter have their own, and")
        print("  this scan finds those by itself -- so unless you have been")
        print("  told otherwise, press Enter.")
        if entry.unit != 1:
            # Say why the default is not the number the paragraph above just
            # called usual, or it reads as a mistake.
            print()
            print(f"  This device answered on unit {entry.unit}, so that is the")
            print("  default below. A second inverter in a master/slave cluster")
            print("  has its own device address, and 2 is what one measured.")
        answers.unit = int(
            probe._ask("Modbus unit id (device address)", str(entry.unit))
        )
        answers.transport = probe._ask_transport()
        answers.proxy = probe._ask_proxy()
        answers.dump = probe._ask_dump(answers.transport)
        answers.address = probe._ask_address(entry.host)
        answers.reporter = probe._ask(
            "Who is reporting this, to credit and to ask (blank for anonymous)",
            "anonymous",
        )
        answers.comment = probe._ask("Anything else worth recording (blank to skip)")
        print()
        print("  One more, and the registers may settle it without asking:")
        print("  reading what this device says about its battery. A few")
        print("  seconds, or up to half a minute over a slow link.")
    answers.battery = await probe._ask_battery(entry.host, answers.port, answers.unit)
    echo("")
    echo("  Answered:")
    for label, value in (
        ("unit id", answers.unit),
        # The first of the four, not the second: the second is the sentence a
        # *document* carries and is empty for "not sure", which read here as
        # though the question had not been asked.
        ("transport", probe.REPORTED_TRANSPORTS[answers.transport][0]),
        ("behind a proxy", answers.proxy),
        ("register dump", "yes" if answers.dump else "no"),
        ("address in the file", answers.address),
        ("reporter", answers.reporter),
        ("comment", answers.comment or "(none)"),
        ("battery", answers.battery or "(read from the registers)"),
    ):
        echo(f"    {label:<22} {value}")
    echo("")
    # The command that repeats this run without asking anything, printed
    # **after** the last question so it carries every answer -- an earlier
    # version printed it before the battery question and left `--battery` out,
    # which is the one answer nobody can re-derive. Printed before the reading
    # rather than only into the file, because the moment somebody wants it is
    # the moment they realise they would have to answer eight questions again,
    # and because a run that dies halfway leaves them nothing otherwise.
    echo("  To repeat this reading without the questions:")
    echo(f"    python3 {probe.SCRIPT} capabilities {entry.host} \\")
    echo(
        f"      --unit {answers.unit} --transport {answers.transport} "
        f"--proxy {answers.proxy}{' --dump' if answers.dump else ''} \\"
    )
    line = f"      --address {answers.address} --reporter {answers.reporter!r}"
    if answers.battery:
        line += f" --battery {answers.battery!r}"
    echo(line + " \\")
    echo(f"      --save {_workspace()[0]}")
    echo("")
    echo("  Starting now, and this is the long part: two registers that say")
    echo("  how the reading reaches the device, then every block read the")
    echo("  integration makes, then the whole register map. Over a slow link")
    echo("  the whole thing is about six minutes and it will look stuck more")
    echo("  than once. Every step says what it is waiting for.")
    echo("")
    return answers


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

    ModbusError, params, connection_class = probe._require_library()
    connection = connection_class(
        params(host=entry.host, port=entry.port), timeout=answers.timeout
    )
    answered_6100 = False
    module: str | None = None
    try:
        unit = connection.for_unit(answers.unit)
        try:
            await unit.read_input_registers(6099, 2)
            answered_6100 = True
        except (ModbusError, TimeoutError, OSError):
            answered_6100 = False
        try:
            words = await unit.read_input_registers(13264, 15)
            module = portable.present(portable._decode_string(list(words))) or None
        except (ModbusError, TimeoutError, OSError):
            module = None
    finally:
        await connection.close()

    # A WiNet-S serves a web interface; an inverter's own LAN port does not.
    # A third signal, and the only one that does not come from a register.
    web_ui = await probe._tcp_open(entry.host, 443, 1.0) or await probe._tcp_open(
        entry.host, 80, 1.0
    )
    verdict = probe.transport_verdict(
        answered_6100=answered_6100, module_named=bool(module)
    )
    echo(f"  register 6100        {'answered' if answered_6100 else 'refused'}")
    echo(f"  register 13265       {module or 'no module named'}")
    echo(f"  port 80 or 443       {'open' if web_ui else 'refused'}")
    echo(f"  verdict              {verdict}")

    measured = probe._claim_of(verdict)
    reported = probe._claim_of(probe.REPORTED_TRANSPORTS[answers.transport][1])
    if measured is not None and reported is not None and measured != reported:
        echo("")
        echo("  This contradicts the answer given above.")
        echo(f"    measured   {measured}")
        echo(f"    you said   {reported}")
        with contextlib.redirect_stdout(sys.stderr):
            print("\n  The measurement is usually right: it is two registers and")
            print("  a port, and the same house can have both routes.")
            if probe._ask_yes("Change the answer to match the measurement?", True):
                answers.transport = (
                    "direct_lan" if measured.startswith("direct") else "winet"
                )
                echo(f"  answer changed to    {answers.transport}")
    return Transport(answered_6100, module, verdict, web_ui)


def _block_test(entry: Found, answers, echo) -> blocks.BlockOutcome | None:
    """Run the block read test as a phase, not as an afterthought.

    Every block the integration issues, read the way the integration reads
    it. This is where a register that takes a whole tier down shows up, and
    it has to run before the register poll: the poll is 27 block reads of
    contention, and this measurement only means anything on an idle link.

    Synchronous, and called through `asyncio.to_thread`. `blocks.py` is a
    blocking tool on purpose -- its clients own an `asyncio.Runner` so that
    the raw socket and the library client can be driven the same way -- and
    `Runner.run` raises inside a running loop. A thread of its own is what
    lets the tool stay as it is rather than being rewritten async for this
    caller's convenience.
    """
    echo("-" * 72)
    echo("4  Block read test")
    echo("-" * 72)
    plan = portable.load_plan()
    to_read = blocks._blocks_of(plan, None)
    verified = "verified against the library" if plan["verified"] else "not verified"
    echo(
        f"  plan    {portable.PLAN_FILE.name} -- "
        f"{len(plan['components'])} components, {verified}"
    )
    client = blocks.client_for(
        entry.host, answers.port, answers.unit, answers.timeout, 0.05
    )
    echo(f"  client  {client.label}")
    _CLIENT_LABEL[:] = [client.label]
    echo(f"  {len(to_read)} blocks, {ROUNDS} rounds, {ATTEMPTS} attempts each")
    # Said out loud because this is the phase that has to be bounded, and
    # somebody watching a run that has gone quiet needs to know it will end.
    echo(
        f"  whatever never answers is then narrowed, {blocks.NARROW_BUDGET:.0f}s "
        "in total\n"
    )
    try:
        outcome = blocks.measure(
            client, to_read, attempts=ATTEMPTS, rounds=ROUNDS, echo=echo
        )
    except (OSError, SystemExit) as error:
        echo(f"  the block read test could not run: {error}")
        return None
    finally:
        client.close()
    blocks.report(outcome, plan, echo=echo)
    echo("")
    return outcome


async def _survey(entry: Found, args, echo) -> Outcome:
    """Take one device through every phase and return what it produced."""
    answers = await _ask_all(entry, args, echo)
    transport = await _check_transport(entry, answers, echo)
    outcome = await asyncio.to_thread(_block_test, entry, answers, echo)

    echo("-" * 72)
    echo("5  Reading the registers")
    echo("-" * 72)
    documents, _private, _in_checkout = _workspace()
    answers.save = str(documents)
    # Handed over before the document is written, so the block evidence is
    # published rather than left in a transcript the contributor keeps.
    answers.block_read_test = _block_document(outcome)
    reading = await probe.capabilities(answers)
    echo("")

    return Outcome(
        found=entry,
        unit=answers.unit,
        document=reading.document,
        written=reading.written,
        transport=transport,
        reported_transport=answers.transport,
        block_outcome=outcome,
        code=_code_for(reading, transport, answers),
    )


def _block_document(outcome: blocks.BlockOutcome | None) -> dict | None:
    """Render a block read test for the published document, or None.

    The measurement `scripts/layout.py` is ever changed from, and it used to
    exist only in the transcript -- the file a contributor is told to *keep*,
    because it carries their real address. So a submitted document had no
    block evidence in it at all, and a maintainer reading one could not see
    which of the integration's reads that device would fail.

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
    """
    if outcome is None:
        return None

    def where(key: tuple[str, str, int, int]) -> dict:
        name, space, address, count = key
        return {
            "component": name,
            "space": space,
            "register": address + 1,
            "count": count,
        }

    return {
        "rounds": ROUNDS,
        "attempts": ATTEMPTS,
        # Said in the document because it changes what the rest of it means:
        # the library client fails wherever the integration fails, and the
        # raw one is deliberately more forgiving -- a lenient client reports
        # a padded frame as a clean read, which is how the first diagnosis of
        # 2612 was wrong for a day.
        "client": _CLIENT_LABEL[0] if _CLIENT_LABEL else None,
        "answered": [
            where(key)
            for key in outcome.tally
            if key not in outcome.failing and key not in outcome.intermittent
        ],
        "never_answered": [
            {**where(key), "outcomes": sorted(outcome.tally[key])}
            for key in outcome.failing
        ],
        "intermittent": [
            {**where(key), "outcomes": sorted(outcome.tally[key])}
            for key in outcome.intermittent
        ],
        # The narrowed ranges, which are what a fix is written from.
        "narrowed": [
            {
                "component": name,
                "space": space,
                "register": address + 1,
                "count": count,
                "outcome": kind,
                "detail": detail,
            }
            for name, space, address, count, kind, detail in outcome.culprits
        ],
        "reconnects": outcome.reconnects,
    }


def _code_for(reading: probe.Reading, transport: Transport, answers) -> int:
    """Return the exit code for one device.

    The code describes the *scan*, not the inverter. A run that finds three
    refusing registers is the most useful kind there is and exits 0; a run
    whose filename under-claims because the device type did not read exits 3,
    because nobody reading the file afterwards can see that.
    """
    # `capabilities` computes this for exactly this purpose: the fields whose
    # absence the *filename* hides. A document carries no model name -- only
    # the device type code, because naming it is the reader's job -- so
    # checking for one here reported every healthy scan as degraded, which is
    # how this function's first version rated the simulator run a 3.
    if reading.missing:
        return 3
    measured = probe._claim_of(transport.verdict) if transport else None
    reported = probe._claim_of(probe.REPORTED_TRANSPORTS[answers.transport][1])
    if measured is not None and reported is not None and measured != reported:
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
    # Read here rather than in `_summary_actions` so a failure to load it
    # cannot take the whole summary down: by this point the documents are
    # already written and the summary is the last thing owed to whoever ran
    # it. Without the plan the advice loses only its "already isolated" half.
    try:
        plan = portable.load_plan()
    except Exception:
        plan = None
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
        named = probe._model_for(int(code, 16)) if code else None
        echo(f"  read  model            {named or 'not in the model table'} ({code})")
        echo(f"  read  output           {device.get('output_type') or 'not read'}")
        stand_in = device.get("serial_anonymized_hashed", "not read")
        echo(f"  read  serial           {stand_in} (stand-in)")
        echo("")
        echo("  The way in")
        if result.transport is not None:
            echo(f"  read  verdict          {result.transport.verdict}")
            echo(
                "  read  register 6100    "
                f"{'answered' if result.transport.answered_6100 else 'refused'}"
            )
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
        _summary_actions(result, echo, plan)
        echo("  Told to this run, not measured")
        for key in sorted(inputs):
            # An empty answer is not silence. The battery question is only
            # *asked* when the registers cannot settle it -- a Sungrow pack
            # answers its own module block, so the run reads the model and
            # says nothing -- and "(not answered)" read as though somebody
            # had shrugged at it, on a document whose own filename carried
            # `battery-sbr096`.
            echo(f"  said  {key:<16} {inputs[key] or '(not asked -- read instead)'}")
        echo("")
        _summary_unreadable(echo)
        echo("  Wrote")
        # Named by what to do with them, not by their extension: the first is
        # the file to send, the second holds the real serial and address and
        # stays put. A `.raw.json` inside a hidden directory is a private file
        # a stranger will not know they are about to forward.
        for number, path in enumerate(result.written):
            role = "send this" if number == 0 else "keep this -- real serial"
            echo(f"        {path}")
            echo(f"          {role}")
        echo(f"        {transcript}")
        echo("          keep this -- the whole session, real addresses")
        echo("=" * 72)
        echo("")


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
    for key in outcome.failing:
        name, space, address, count = key
        echo(f"        {space} {address} x{count} in {name}   <-- never answered")
    for key in outcome.intermittent:
        name, space, address, count = key
        echo(
            f"        {space} {address} x{count} in {name}   <-- intermittent, so "
            "contention rather than a fault"
        )
    echo("")


def _ranges(numbers: list[int]) -> str:
    """Return "13200-13207" for eight consecutive registers, "5242" for one.

    Runs rather than a list, because consecutive addresses are the usual
    shape -- one absent measuring point is a block of them -- and eight
    numbers separated by commas hide whether they are contiguous, which is
    the first thing a reader wants to know.
    """
    runs: list[tuple[int, int]] = []
    for number in numbers:
        if runs and number == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], number)
        else:
            runs.append((number, number))
    return ", ".join(
        str(start) if start == end else f"{start}-{end}" for start, end in runs
    )


#: How a read has to have failed for `layout.py` to accept it as evidence.
#:
#: Every entry in `ISOLATE` today is one of these three: an exception code,
#: a deterministic hangup, or a padded frame. A bare timeout is deliberately
#: not among them -- from this end a silent inverter and an answer lost in a
#: tunnel are the same event, and the same four blocks at one house closed
#: the connection on a LAN two days before they timed out over a VPN. Same
#: registers, same machines, different sentence: so the sentence is the
#: link's and only the refusal is the device's.
REFUSED_OUTRIGHT = ("exception", "padded", "answered a different length")


def _refused_outright(detail: str) -> bool:
    """Whether a failure detail is the kind `layout.py` may be changed on."""
    lowered = detail.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return False
    return any(word in lowered for word in REFUSED_OUTRIGHT)


def _summary_unreadable(echo) -> None:
    """Say what answered a port this tool cannot speak, or say nothing.

    One case today: a **WiNet-S serving Modbus over TLS on 516**. Measured on
    two dongles -- TLS 1.2, a Sungrow self-signed certificate, and real
    registers through the tunnel -- and refused on the inverters' own LAN
    ports, so it is the dongle's port and not, as reported elsewhere, an
    iHomeManager's.

    Sweeping finds it; reading it needs a TLS client this survey does not
    have, which is why a plain socket sees the connection accepted and then
    closed. Printed as a finding rather than a warning, because a user told
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
    echo("        Modbus over TLS, which this survey does not speak. On a")
    echo("        WiNet-S this is normal and not a fault: the port works and")
    echo("        serves the same registers as 502, refusing the same ones.")
    echo("        Worth mentioning in an issue only if 502 found nothing --")
    echo("        then this is where your device is.")
    echo("")


def _summary_actions(result: Outcome, echo, plan: dict | None = None) -> None:
    """Say what to do about what was measured, with the evidence beside it."""
    actions = []
    outcome = result.block_outcome
    if outcome is not None and outcome.culprits:
        # Grouped by component and by how it failed, because the fix is per
        # component and the narrowing is per register: eight refused addresses
        # inside one meter block produced eight identical paragraphs, each
        # ending "add it to scripts/layout.py", which reads as eight problems
        # and is one.
        grouped: dict[tuple[str, str, str], list[int]] = {}
        details: dict[tuple[str, str, str], str] = {}
        for name, space, address, count, kind, detail in outcome.culprits:
            key = (name, space, kind)
            grouped.setdefault(key, []).extend(
                address + offset for offset in range(count)
            )
            details.setdefault(key, detail)
        # Whether this is a register fault at all depends on the path it was
        # measured over, so the advice does too. Measured on gerd's
        # SH8.0RT-V112: input 2612 and 2628 refuse with exception 0x02 three
        # times out of three through its WiNet-S, and read perfectly over the
        # inverter's own LAN port on the same machine four minutes later. They
        # are measuring points the dongle does not forward. Putting them in
        # `layout.ISOLATE` would make every direct-LAN user pay a per-field
        # read for a dongle's behaviour and would still not get a dongle user
        # the fields -- the answer there is capability gating by transport.
        through_module = result.transport is not None and probe._claim_of(
            result.transport.verdict
        ) not in ("direct",)
        isolated_components = {
            entry["component"]
            for entry in (plan or {}).get("components", [])
            if entry.get("isolated")
        }
        for (name, space, kind), addresses in grouped.items():
            isolated_already = name in isolated_components
            registers = _ranges(sorted(address + 1 for address in addresses))
            action = (
                f"{name}: {space} register {registers} {kind} "
                f"({details[(name, space, kind)]}). "
            )
            if through_module:
                action += (
                    "This reading came through a communication module, which "
                    "forwards fewer measuring points than the inverter's own "
                    "LAN port -- so this may be a forwarding limit rather "
                    "than a register fault. Read the same registers directly "
                    "before touching scripts/layout.py; if they answer there, "
                    "it belongs in transport capability gating instead."
                )
            elif kind == blocks.UNNARROWED:
                # The budget stopped, so the range is as small as the run got
                # and not as small as it goes. layout.py takes an exact
                # register; offering it a fifteen-register range would be
                # offering it a guess out of fifteen.
                action += (
                    "Narrowing ran out of its budget here, so this range is "
                    "not yet an answer -- it names no single register. Aim a "
                    "full run at just this block to finish it: "
                    f"blocks.py <host> -r {space}:{min(addresses)}:"
                    f"{len(addresses)} --narrow-budget 0"
                )
            elif not _refused_outright(details[(name, space, kind)]):
                # Every entry in layout.ISOLATE is an exception code, a
                # deterministic hangup or a padded frame. A bare timeout is
                # none of those: from this end a silent inverter and a lost
                # answer look identical, and the same four blocks at one
                # house closed the connection on a LAN two days before they
                # timed out over a VPN.
                action += (
                    "This failed by timing out rather than by refusing. A "
                    "timeout cannot tell a silent inverter from an answer "
                    "lost on the way, so it is not evidence about the "
                    "register -- do not add it to scripts/layout.py. Re-read "
                    "these registers from a link that fails fast."
                )
            elif isolated_already:
                # It printed nine recommendations to add what was already
                # there, at a house whose four failing blocks are the four
                # entries layout.py already has. The isolation was working:
                # each failure was costing one field instead of a tier.
                action += (
                    "Read directly from the inverter and refused outright, so "
                    "this is the device. It is **already isolated** in "
                    "scripts/layout.py, which is why it cost only its own "
                    "field(s) rather than its whole tier -- nothing to do, "
                    "and worth adding to doc/compatibility.md as another "
                    "machine that refuses it."
                )
            else:
                action += (
                    "Read directly from the inverter and refused outright, so "
                    "this is the device refusing. Add the field(s) these "
                    "belong to to scripts/layout.py and quote the block read "
                    "test above -- that module is only ever added to from a "
                    "measurement, and this is the measurement."
                )
            actions.append(action)
    if outcome is not None and outcome.intermittent and not outcome.failing:
        actions.append(
            "Some blocks answered only sometimes, which is contention rather "
            "than a fault. Re-run with nothing else polling the inverter "
            "before reading anything into it."
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


async def run(args) -> int:
    """Run the whole scan, and return the exit code."""
    _documents, private, in_checkout = _workspace()
    private.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    transcript = private / f"sungrow-scan-{stamp}.log"

    out = Tee(sys.stdout, transcript)
    errors = Tee(sys.stderr, transcript)
    sys.stdout, sys.stderr = out, errors

    def echo(text: str = "") -> None:
        print(text, file=out, flush=True)

    try:
        client_label = (
            "modbus-connection (the one the integration uses)"
            if probe.have_library()
            else "this directory's own client -- nothing installed"
        )
        _preamble(echo, transcript, client_label)
        if not in_checkout:
            echo("  Two files are written. Send the first; the second stays with")
            echo("  you -- it holds your real serial number and address.")
            echo("")

        try:
            found = await _find(args, echo)
        except ValueError as error:
            echo(f"  {error}")
            return _finish(2, echo)
        if not found:
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
        if not results:
            return _finish(1, echo)

        _summary(results, transcript, echo)
        return _finish(_worst([result.code for result in results]), echo)
    finally:
        sys.stdout, sys.stderr = out._stream, errors._stream
        out.close()
        errors.close()


def _finish(code: int, echo) -> int:
    """Print the code and the sentence it means, and return it."""
    echo(f"exit {code} -- {CODES[code]}.")
    return code


def main() -> int:
    """Parse the few optional arguments and run."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "host",
        nargs="*",
        help="address(es) to scan. Omit to sweep the network and choose.",
    )
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument(
        "--unit", type=int, default=1, help="default unit id offered when asked"
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--passes", type=int, default=8)
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nStopped. Nothing was written to your inverter, as nothing can be.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
