"""A capability survey, from a running integration rather than a terminal.

The evidence this project reasons from lives in `device-fingerprints/`:
nine documents, four houses, **all of them the maintainer's or a friend's**.
That is not because nobody else would help. It is because contributing meant
cloning a repository and running Python on a machine that can reach the
inverter, and almost nobody who has a Sungrow has that.

Somebody who has set this integration up has the hard part already — a working,
identified connection to their inverter. This turns it into a document, in
exactly the format `device-fingerprints/scripts/python/sungrow_survey.py` writes,
so one generator keeps building `doc/compatibility.md` from both and a reading
from somebody who only ever clicked a button counts the same as one from a
terminal.

**It rides in the diagnostics download** rather than inventing a delivery
mechanism. Home Assistant already has a button that produces a JSON file a
user attaches to an issue, it works on an entry with no entities, and nothing
here has to write to disk or ask for a path.

Three honest limits, each recorded *in* the document rather than left for a
reader to discover:

* **It is taken under contention.** Home Assistant is polling this inverter;
  that is what it is for. This project discards documents taken while
  something else was polling, because contention and a register fault are
  hard to tell apart from the result — four documents were thrown away for
  exactly that. So the document says so in a `contention` section of its own,
  as a measurement rather than as testimony: the integration knows precisely
  what it was doing. Holding the coordinators off for the duration is the
  fix, and is not done here yet.
* **The block read test runs from the button, never from the download.**
  That measurement is what `src/sungrow_modbus/layout.py` is ever changed from, and it
  costs 27 block reads times three rounds, twice each, plus narrowing — fine
  for a background task with a progress bar, too long for a download somebody
  is waiting on. So a document from **Download diagnostics** carries none, and
  says so under `contention`.
* **Nothing is asked that the owner has not been asked.** The testimony no
  register can answer — which cable, whether a proxy is in the path, whether
  the address may be published — comes from the options flow and defaults to
  empty. Empty means *the question was not put*, which is a different
  statement from an answer of "unknown", and the format has always kept those
  apart.

The tables, the schema, the stand-in and the transport vocabulary all come
from `sungrow_modbus.fingerprint`, so this and the standalone survey cannot
drift apart on what a probe is called or what a serial becomes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from sungrow_modbus import (
    block_test,
    dump as register_dump,
    fingerprint as survey,
    survey as survey_api,
    wallbox as wallbox_reader,
)
from sungrow_modbus.battery_device import PUBLISHED_NAMES as BATTERY_NAMES
from sungrow_modbus.survey import summarise as _summarise

from .const import (
    CONF_PUBLISH_ADDRESS,
    CONF_REPORTER,
    CONF_SURVEY_BATTERY,
    CONF_SURVEY_COMMENT,
    CONF_SURVEY_DUMP,
    CONF_SURVEY_OTHER_INVERTER,
    CONF_SURVEY_OTHER_INVERTER_DETAIL,
    CONF_SURVEY_POLLERS,
    CONF_SURVEY_PROXY,
    CONF_SURVEY_TRANSPORT,
    CONF_WALLBOX_HOST,
    DEFAULT_SURVEY_DUMP,
)
from .coordinator import SungrowConfigEntry
from .survey import Progress


def summarise(document: dict[str, Any]) -> str:
    """Keep the integration import surface while using package logic."""
    return _summarise(document)


def planned_steps(
    dumping: bool,
    block_reads: int = 0,
    *,
    wallbox: bool = False,
    wallbox_direct: bool = False,
) -> int:
    """Count the reads a survey will report progress for, before it starts.

    Every probe, and one step for assembling what the
    coordinators already hold -- assembly is a single step because it does no
    reading and is the only part that cannot stall. `block_reads` is the block
    read test's countable share, from `block_test.planned_steps`; its
    narrowing is not counted, because how much there is depends on what
    fails.

    The dump's share is counted here rather than discovered as it goes, because
    a bar whose total grows halfway through is worse than no bar: with the dump
    on it is 52 of the 76 steps, so getting it wrong would not be a rounding
    error. A caller sharing one bar between this and the control test needs the
    number without starting a survey, which is why it is a function.
    """
    total = len(survey.PROBES) + 1 + block_reads
    if dumping:
        total += register_dump.block_count()
        if wallbox:
            total += register_dump.block_count(wallbox_bands(wallbox_direct))
    return total


def wallbox_bands(direct: bool) -> tuple[tuple[str, int, int, str], ...]:
    """Return the wallbox's dump bands for the path it is read on.

    Its own address over TLS answers a read only where a data point starts,
    so it gets bands cut to measured starts; a WiNet-S answers any start.
    """
    return register_dump.WALLBOX_TLS_BANDS if direct else register_dump.WALLBOX_BANDS


def wallbox_is_direct(coordinator: Any) -> bool:
    """Whether this wallbox is read at its own address rather than through a dongle."""
    return bool(coordinator.config_entry.options.get(CONF_WALLBOX_HOST))


def _testimony(options: Mapping[str, Any]) -> dict[str, str]:
    """Return everything a person typed, so a claim cannot be misread as a reading.

    Kept together and named for what it is: the document separates what was
    *measured* from what was *said*, and a reader who cannot tell the two apart
    will eventually quote one as the other.

    `other_inverter` is the case that proves the distinction is not pedantry. A
    non-Sungrow inverter on the same meter makes `load_power` low by exactly
    its own output, because the Sungrow computes house load from its own output
    plus grid import -- while every register answers normally. The inverter
    cannot see the thing that is confusing it, so only the owner can say, and
    an empty answer means the question was not put rather than that the answer
    was no.
    """
    return {
        "reporter": options.get(CONF_REPORTER) or "anonymous",
        "comment": options.get(CONF_SURVEY_COMMENT, ""),
        "battery": options.get(CONF_SURVEY_BATTERY, ""),
        "transport": options.get(CONF_SURVEY_TRANSPORT, ""),
        "modbus_proxy": options.get(CONF_SURVEY_PROXY, ""),
        # What the owner says about anything *else* polling. What this Home
        # Assistant does is not testimony and is measured separately.
        "other_pollers": options.get(CONF_SURVEY_POLLERS, ""),
        "other_inverter": options.get(CONF_SURVEY_OTHER_INVERTER, ""),
        "other_inverter_detail": options.get(CONF_SURVEY_OTHER_INVERTER_DETAIL, ""),
    }


async def async_build(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    options: dict[str, Any] | None = None,
    on_progress: Progress | None = None,
    *,
    allow_dump: bool = False,
    allow_block_test: bool = False,
    control_test: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one publishable survey document for this entry.

    `options` overrides the entry's own, which the options flow needs: it
    runs the survey to show the contributor what was found *before* it
    commits their answers, so the document has to be built from testimony
    that is not saved yet.

    `on_progress(fraction, step)` is called after each read that can be
    counted, so a device page can show how far along a survey is and what it
    is reading. Counted rather than timed: the same survey is under a second
    on a cable and a quarter of an hour over a VPN, and only the number of
    reads is known in advance. Optional, because diagnostics downloads build
    the same document with nobody watching.

    `allow_dump` is what makes the owner's `survey_register_dump` option
    count, and it is a separate argument rather than being read straight from
    the options for one reason: **the caller decides whether it can afford
    five minutes.** The survey button can -- it is a background task with a
    progress bar and a notification at the end. The diagnostics download
    cannot: it is a button somebody waits on, so it leaves this False and the
    option has no effect there, however the owner set it.

    `allow_block_test` is the same decision for the block read test, which is
    not an option at all: the survey button always runs it and the download
    never does. It runs **first**, before the probes, because it is the
    measurement that only means anything on an idle link -- the probes and the
    dump are themselves reads.

    `control_test` is part B's result, already measured, and it is passed in
    rather than run from here for the same reason `allow_dump` is a parameter:
    **the caller decides.** Only one caller may write to an inverter -- the
    control test button -- and the diagnostics download, which builds this same
    document from this same code, must never acquire that power by inheriting
    a default.
    """
    runtime = entry.runtime_data
    device = next(iter(runtime.coordinators.values())).device
    if options is None:
        options = dict(entry.options)

    # Asked for and affordable are two different things; see the docstring.
    dumping = allow_dump and bool(options.get(CONF_SURVEY_DUMP, DEFAULT_SURVEY_DUMP))

    # The denominator, so a fraction means something: every probe, one step
    # for assembling what the coordinators already
    # hold, and every block of the dump when there is one. Assembly is a
    # single step because it does no reading -- it is the only part that
    # cannot stall.
    #
    # The dump's share is counted here rather than discovered as it goes,
    # because a bar whose total grows halfway through is worse than no bar --
    # and with the dump on it is 52 of the 76 steps, so getting it wrong
    # would not be a rounding error.
    blocks = await block_test.inverter_blocks() if allow_block_test else []
    total = planned_steps(
        dumping,
        block_test.planned_steps(blocks) if blocks else 0,
        wallbox=runtime.wallbox is not None,
        wallbox_direct=runtime.wallbox is not None
        and wallbox_is_direct(runtime.wallbox),
    )
    done = 0

    def step(label: str, counted: bool = True) -> None:
        nonlocal done
        if counted:
            done += 1
        if on_progress is not None:
            on_progress(done / total, label)

    blocks_measured = (
        await block_test.measure(device.async_read_words, blocks, step=step)
        if blocks
        else None
    )
    probes = await _async_probes(device, step)
    raw = await _async_dump(device, step) if dumping else None
    wallbox = await _async_wallbox(runtime, dumping, step)
    step("assembling the document")

    answered_6100 = _state_of(probes, "PV power of today (6100, direct-only)")
    firmware = _firmware(device)
    module = firmware.get("communication_module")

    # Same keys and shapes as `sungrow_survey.py` writes, through the same
    # builder, so `doc/compatibility.md` and anybody reading a document need
    # not know which producer made it. The builder masks the dump and checks
    # part B's block for the serial; a caller cannot hand it either unshaped.
    return survey.assemble_document(
        command_line=f"{survey.COLLECTED_BY_INTEGRATION} diagnostics",
        read_at=dt_util.utcnow().isoformat(timespec="seconds").replace("+00:00", "Z"),
        user_inputs=_testimony(options),
        host=entry.data.get(CONF_HOST, ""),
        publish_address=bool(options.get(CONF_PUBLISH_ADDRESS, False)),
        device_type_code=device.device_type_code,
        output_type=device.output_type,
        serial=device.serial_number or "",
        firmware=firmware,
        connection=survey.connection_block(str(answered_6100), module),
        readings=_readings(runtime, device),
        capability_probes=probes,
        contention=_contention(runtime, block_test_run=blocks_measured is not None),
        register_dump=raw,
        wallbox=wallbox,
        block_read_test=(
            block_test.document(blocks_measured)
            if blocks_measured is not None
            else None
        ),
        battery_pack=await _async_battery_pack(runtime),
        # Part B, when a run did one. Absent from almost every document, and
        # its absence means "this run only read" rather than "this inverter
        # failed" -- which is why the schema number moved rather than the key
        # simply appearing.
        control_test=control_test,
    )


def attach_control_test(
    document: dict[str, Any], block: dict[str, Any], device: Any
) -> None:
    """Put part B's result into a document part A already built.

    The survey runs part B *after* part A, so the block does not exist yet
    when `async_build` is called. The package's door checks it for the
    serial on the way in, exactly as `assemble_document` does.
    """
    survey.attach_control_test(document, block, serial=device.serial_number or "")


async def _async_dump(device: Any, step: Progress) -> dict[str, Any]:
    """Sweep the raw address bands, reporting each block as a step.

    The band's reason -- "the block a WiNet-S does not forward" -- is what the
    step sensor shows, rather than an address. Somebody watching a five-minute
    bar wants to know what is being looked for, and an address tells them
    nothing they can check.
    """

    def on_block(done: int, total: int, why: str) -> None:
        step(f"reading raw registers: {why} ({done} of {total})")

    return await register_dump.async_dump(device.async_read_words, on_progress=on_block)


async def _async_probes(
    device: Any, step: Callable[[str], None] | None = None
) -> dict[str, dict[str, Any]]:
    """Read every curated probe once, in the package's published shape.

    One attempt each, unlike the terminal survey's three: this connection is
    shared with the coordinators, and a probe that retries holds every one of
    them off for as long as it waits.
    """
    raw, states = await survey_api.async_probe_words(
        device.async_read_words, attempts=lambda _label: 1, on_probe=step
    )
    return survey.capability_registers(states, raw)


def _state_of(probes: dict[str, dict[str, Any]], label: str) -> str:
    """Return one probe's recorded state."""
    return str((probes.get(label) or {}).get("state", survey.State.NO_ANSWER))


def _firmware(device: Any) -> dict[str, str | None]:
    """Return the five published firmware strings, from what was polled.

    Not re-read: the library polls all five in its slowest tier, so reading
    them again would spend five requests on an inverter that grants very few
    sessions, and could disagree with the entities on the same page.
    """
    return survey.firmware_section(device)


def _contention(runtime: Any, *, block_test_run: bool = False) -> dict[str, Any]:
    """State what this Home Assistant was doing while the document was made.

    The standalone survey asks an owner to confirm nothing else was polling,
    and refuses to trust a reading taken otherwise. Here the answer is known
    and it is *yes*: the coordinators kept their intervals throughout. Saying
    which components and how often lets a reader judge a dropped block --
    a component on a five-second tier is a very different neighbour to one
    on ten minutes.
    """
    return {
        "polled_by": "this Home Assistant, throughout",
        "components": len(runtime.coordinators),
        "intervals_seconds": sorted(
            {
                interval
                for component in runtime.coordinators
                if (interval := runtime.interval_of(component)) is not None
            }
        ),
        # Truthful rather than constant. It was hardcoded False until
        # 2026-09-18 and that was honest -- every document from a device page
        # really was collected while this entry's own tiers kept polling the
        # same serialized connection. Now the survey holds them off and says
        # so, and an older document saying False means what it always said.
        "coordinators_paused": bool(getattr(runtime, "polling_paused", False)),
        "block_read_test": (
            "run, before the probes, with this entry's polling held off; see "
            "block_read_test"
            if block_test_run
            else "not run: it costs 27 block reads times three rounds plus "
            "narrowing, which the survey button affords and a diagnostics "
            "download does not"
        ),
    }


def _readings(runtime: Any, device: Any) -> dict[str, Any]:
    """Every decoded value, and what did not read, in the survey's shape."""
    return survey.readings_section(
        device,
        (
            component
            for component, coordinator in runtime.coordinators.items()
            if coordinator.data is not None and component in coordinator.data.failed
        ),
    )


async def _async_battery_pack(runtime: Any) -> dict[str, Any] | None:
    """Return the pack's own registers, when one answered on this endpoint.

    The poll leaves the per-module block unread, so the survey reads it here,
    once, and with the poll's own components reports what failed -- the
    terminal survey's section, whichever producer wrote it.
    """
    coordinator = runtime.battery
    if coordinator is None:
        return None
    device = coordinator.device
    report = await device.async_update(survey=True)
    failed = [
        f"{BATTERY_NAMES[attribute]} ({type(error).__name__})"
        for attribute, error in report.failed.items()
    ]
    return survey.battery_pack_section(
        device,
        device.unit_id,
        failed,
        unanswered_fields=device.fields_of(report.failed),
    )


async def _async_wallbox(
    runtime: Any, dumping: bool, step: Progress
) -> dict[str, Any] | None:
    """Return the wallbox's section, when one answered behind this endpoint.

    The survey's shape, from the library's decoder, so a document from the
    device page and one from `sungrow_survey.py` read the same: `unit` and
    per-field `readings`, plus the masked `register_dump` of its 206 addresses
    when the owner's dump option is on. Without it, one read per component
    -- the spans the poll already covers, which no serial is in.

    Masking and the stand-in are the package's, in `fingerprint.wallbox_section`
    and `wallbox_from_dump`, so they cannot drift from the terminal survey's.
    """
    coordinator = runtime.wallbox
    if coordinator is None:
        return None
    device = coordinator.device
    direct = wallbox_is_direct(coordinator)
    path = "tls" if direct else "dongle"
    if not dumping:
        found = wallbox_reader.readings(
            await wallbox_reader.async_mapped_words(device.async_read_words)
        )
        if not found:
            return None
        return survey.wallbox_section(
            device.unit_id,
            readings=found,
            serial_stand_in=await wallbox_reader.async_serial_stand_in(
                device.async_read_words
            ),
            path=path,
        )

    def on_block(done: int, total: int, why: str) -> None:
        step(f"reading the wallbox's raw registers: {why} ({done} of {total})")

    raw = await register_dump.async_dump(
        device.async_read_words,
        on_progress=on_block,
        bands=wallbox_bands(direct),
    )
    return survey.wallbox_from_dump(device.unit_id, raw, path=path)
