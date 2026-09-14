"""A capability survey, from a running integration rather than a terminal.

The evidence this project reasons from lives in `doc/device-fingerprints/`:
nine documents, four houses, **all of them the maintainer's or a friend's**.
That is not because nobody else would help. It is because contributing meant
cloning a repository and running Python on a machine that can reach the
inverter, and almost nobody who has a Sungrow has that.

Somebody who has set this integration up has the hard part already — a
working, identified connection to their inverter. This turns it into a
document, in exactly the format `scripts/sungrow_scan/collect.py` writes, so
one generator keeps building `doc/compatibility.md` from both and a reading
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
* **There is no block read test.** That measurement is what
  `scripts/layout.py` is ever changed from, and it costs 26 block reads times
  three rounds plus binary-tree narrowing — a background task with a progress
  notification, not something a diagnostics download can wait for.
  `test_a_collect_run_at_schema_16_carries_its_block_read_test` is keyed on
  the tool for this reason, so a document from here is not expected to carry
  one.
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

from collections.abc import Callable
import statistics
import time
from typing import Any

from modbus_connection import (
    ModbusConnectionError,
    ModbusError,
    ModbusExceptionError,
    ModbusTimeoutError,
)

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from sungrow_modbus import dump as register_dump, fingerprint as survey
from sungrow_modbus.const import model_for
from sungrow_modbus.fingerprint import State

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
)
from .coordinator import SungrowConfigEntry
from .survey import Progress

#: Which register fields carry each published firmware string.
#:
#: Sourced from the ordinary readings rather than re-read: the library polls
#: all five as part of its slowest tier, so a survey that read them again
#: would spend five requests on an inverter that grants very few sessions and
#: could disagree with the entities on the same page.
FIRMWARE_FIELDS = {
    "arm": "sungrow_arm_software",
    "dsp": "sungrow_dsp_software",
    "inverter": "inverter_firmware_version",
    "communication_module": "communication_module_firmware_version",
    "battery": "battery_firmware_version",
}

#: How many times to read one address when timing the link.
#:
#: The samples are published because latency is evidence about the *network*
#: and worth having; they are explicitly not evidence about the transport,
#: which the sentence in `wifi_or_ethernet` explains at length.
LATENCY_SAMPLES = 5


async def async_build(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    options: dict[str, Any] | None = None,
    on_progress: Progress | None = None,
    *,
    allow_dump: bool = False,
) -> dict[str, Any]:
    """Return one publishable survey document for this entry.

    `options` overrides the entry's own, which the options flow needs: it
    runs the survey to show the contributor what was found *before* it
    commits their answers, so the document has to be built from testimony
    that is not saved yet.

    Read order matters slightly: the probes come first and the latency
    samples after, so a link that is about to fail fails on the measurement
    that is worth something rather than on the timing.

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
    """
    runtime = entry.runtime_data
    device = next(iter(runtime.coordinators.values())).device
    if options is None:
        options = dict(entry.options)

    # Asked for and affordable are two different things; see the docstring.
    dumping = allow_dump and bool(options.get(CONF_SURVEY_DUMP, False))

    # The denominator, so a fraction means something: every probe, every
    # timing sample, one step for assembling what the coordinators already
    # hold, and every block of the dump when there is one. Assembly is a
    # single step because it does no reading -- it is the only part that
    # cannot stall.
    #
    # The dump's share is counted here rather than discovered as it goes,
    # because a bar whose total grows halfway through is worse than no bar --
    # and with the dump on it is 52 of the 76 steps, so getting it wrong
    # would not be a rounding error.
    total = len(survey.PROBES) + LATENCY_SAMPLES + 1
    if dumping:
        total += register_dump.block_count()
    done = 0

    def step(label: str) -> None:
        nonlocal done
        done += 1
        if on_progress is not None:
            on_progress(done / total, label)

    probes = await _async_probes(device, step)
    latency = await _async_latency(device, step)
    raw = await _async_dump(device, step) if dumping else None
    step("assembling the document")

    answered_6100 = _state_of(probes, "PV power of today (6100, direct-only)")
    firmware = _firmware(device)
    module = firmware.get("communication_module")

    document: dict[str, Any] = {
        "schema": survey.SCHEMA,
        # Not an invocation, because no command produced this and printing one
        # would invite somebody to run it and wonder why the output differs.
        "command_line": f"{survey.COLLECTED_BY_INTEGRATION} diagnostics",
        "read_on": dt_util.utcnow().isoformat()[:10],
        "read_at_local": dt_util.now().isoformat(timespec="seconds"),
        # Everything a person typed, first and in one place, so a claim can
        # never be quoted back as a measurement.
        "user_inputs": {
            "reporter": options.get(CONF_REPORTER) or "anonymous",
            "comment": options.get(CONF_SURVEY_COMMENT, ""),
            "battery": options.get(CONF_SURVEY_BATTERY, ""),
            "transport": options.get(CONF_SURVEY_TRANSPORT, ""),
            "modbus_proxy": options.get(CONF_SURVEY_PROXY, ""),
            # What the owner says about anything *else* polling. What this
            # Home Assistant does is not testimony and is recorded below.
            "other_pollers": options.get(CONF_SURVEY_POLLERS, ""),
            # Whether a **non-Sungrow** inverter shares the installation, and
            # what the owner says it is. Empty means the question was not put,
            # which the format has always kept distinct from an answer.
            #
            # The reason this is testimony and can never be a measurement:
            # the inverter computes house load from its own output plus grid
            # import, so a second inverter on the same meter makes
            # `load_power` low by exactly that inverter's output, while every
            # register answers normally. The Sungrow cannot see the thing
            # that is confusing it, so only the owner can say.
            "other_inverter": options.get(CONF_SURVEY_OTHER_INVERTER, ""),
            "other_inverter_detail": options.get(CONF_SURVEY_OTHER_INVERTER_DETAIL, ""),
        },
        "ip_address_last_two_octets": survey.address_tail(
            entry.data.get(CONF_HOST, ""),
            bool(options.get(CONF_PUBLISH_ADDRESS, False)),
        ),
        "device": {
            "device_type_code": _hex(device.device_type_code),
            # The model the code means, spelled out beside it. `0x0E03` is
            # not something a person reads, and a document is mostly read by
            # people -- in an issue, usually, where nobody has the lookup
            # table to hand. The code stays the authority because it is what
            # the inverter actually said; this is null for a code the project
            # has never seen, which is itself the most interesting document
            # to receive.
            "device_type": model_for(device.device_type_code),
            "output_type": survey.OUTPUT_TYPES.get(
                device.output_type, device.output_type
            ),
            "serial_anonymized_hashed": survey.stand_in(device.serial_number or ""),
        },
        "firmware": firmware,
        "connection": {
            "communication_module_firmware": module,
            "latency_ms": latency,
            "verdict": survey.transport_verdict(
                answered_6100=answered_6100 == survey.State.PRESENT,
                module_named=bool(module),
            ),
            "wifi_or_ethernet": survey.WIFI_OR_ETHERNET,
            "winet_restricted_block_6100": str(answered_6100),
        },
        # Not a claim, and not optional: a document produced by a running
        # Home Assistant was taken while something was polling the inverter,
        # and this project *discards* readings taken under contention because
        # contention and a register fault are hard to tell apart. Four
        # documents were thrown away for it. So the condition is stated as a
        # measurement -- the integration knows exactly what it was doing --
        # and a maintainer reading one knows what it is worth without having
        # to infer it from the tool name.
        "contention": _contention(runtime),
        "readings": _readings(runtime, device),
        "capability_probes": probes,
    }

    # Same key and same shape as a standalone survey writes, so one
    # generator keeps reading both and a document from a button is not a
    # second format. Masked before it goes in, never after: the serial's ten
    # registers sit inside the identity band and would otherwise be published
    # as words.
    if raw is not None:
        document["register_dump"] = register_dump.masked(raw)

    pack = _battery_pack(runtime)
    if pack is not None:
        document["battery_pack"] = pack

    wallbox = _wallbox(runtime)
    if wallbox is not None:
        document["wallbox"] = wallbox

    return document


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
    """Read every curated probe, recording what each answer establishes.

    A refusal and a timeout are recorded differently and deliberately: an
    exception 0x02 is the device saying the register is not there, while
    nothing coming back says only that nothing came back. Only the first
    belongs in an argument about a register.

    Values are published beside the state, because a state alone cannot
    settle a scale factor -- except where the label mentions a serial, which
    is how `[16690, 13633]` once reached a document and decoded to `A25A`.
    """
    probes: dict[str, dict[str, Any]] = {}
    for label, space, address, count, _axis in survey.PROBES:
        # Announced before the read, not after: on the link where this
        # matters a single read can take ten seconds, and a step that
        # appears only once it has finished shows the wrong one throughout.
        if step is not None:
            step(label)
        entry: dict[str, Any] = {}
        try:
            words = await device.async_read_words(space, address, count)
        except ModbusExceptionError:
            entry["state"] = str(survey.State.REFUSED)
        except (ModbusTimeoutError, ModbusConnectionError, TimeoutError, OSError):
            entry["state"] = str(survey.State.NO_ANSWER)
        except ModbusError:
            # Anything else the stack rejected -- a desynchronised or padded
            # frame, which is a real answer this client cannot use. Not
            # "refused": that would be a claim about the register.
            entry["state"] = str(survey.State.NO_ANSWER)
        else:
            entry["state"] = str(survey.classify(words))
            if survey.publishable(label):
                entry["values"] = [int(word) for word in words]
        probes[label] = entry
    return probes


async def _async_latency(
    device: Any, step: Callable[[str], None] | None = None
) -> dict[str, float] | None:
    """Time a few reads of one address that every inverter answers.

    Register 5000, the device type code: it is the one address a Sungrow
    always has, so the samples describe the link rather than a capability.
    """
    samples: list[float] = []
    for sample in range(LATENCY_SAMPLES):
        if step is not None:
            step(f"timing the link ({sample + 1} of {LATENCY_SAMPLES})")
        started = time.monotonic()
        try:
            await device.async_read_words("input", 4999, 1)
        except (ModbusError, TimeoutError, OSError):
            continue
        samples.append((time.monotonic() - started) * 1000)
    if not samples:
        return None
    return {
        "min": round(min(samples), 1),
        "median": round(statistics.median(samples), 1),
        "max": round(max(samples), 1),
    }


def _state_of(probes: dict[str, dict[str, Any]], label: str) -> str:
    """Return one probe's recorded state."""
    return str((probes.get(label) or {}).get("state", survey.State.NO_ANSWER))


def _hex(code: int | None) -> str | None:
    """Format a device type code the way a register document prints it."""
    return None if code is None else f"0x{code:04X}"


def _firmware(device: Any) -> dict[str, str | None]:
    """Return the five published firmware strings, from what was polled."""
    values: dict[str, str | None] = {}
    for name, field in FIRMWARE_FIELDS.items():
        try:
            value = device.field(field)
        except (AttributeError, KeyError):
            value = None
        values[name] = None if value is None else str(value)
    return values


def _contention(runtime: Any) -> dict[str, Any]:
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
        "coordinators_paused": False,
        "block_read_test": (
            "not run: it costs 26 block reads times three rounds plus "
            "narrowing, which belongs in a background task rather than a "
            "diagnostics download"
        ),
    }


def _readings(runtime: Any, device: Any) -> dict[str, Any]:
    """Every decoded value, and what did not read, in the survey's shape.

    Three lists rather than one, because they mean different things: a value
    that decoded, a field the device reported unavailable, and a component
    whose whole block failed its last poll. The middle one is the
    specification's 0xFFFF sentinel and the last is a Modbus failure, and
    treating them alike is most of what makes "my sensor is missing" hard to
    answer.
    """
    values: dict[str, Any] = {}
    unread: list[str] = []
    for name in sorted(device._fields):
        if not survey.publishable(name):
            continue
        try:
            value = device.field(name)
        except (AttributeError, KeyError):
            continue
        if value is None:
            unread.append(name)
        else:
            values[name] = value

    failed = sorted(
        component
        for component, coordinator in runtime.coordinators.items()
        if coordinator.data is not None and component in coordinator.data.failed
    )
    return {
        "values": values,
        "fields_that_did_not_read": unread,
        "components_that_did_not_answer": failed,
    }


def _battery_pack(runtime: Any) -> dict[str, Any] | None:
    """Return the pack's own registers, when one answered on this endpoint.

    `battery_pack` and never `battery`: that key holds what the owner *typed*
    about their battery, and the first version of this in the standalone
    survey overwrote their testimony with a measurement.
    """
    coordinator = runtime.battery
    if coordinator is None:
        return None
    device = coordinator.device
    values = {}
    for name in sorted(device._fields):
        if not survey.publishable(name):
            continue
        try:
            value = device.field(name)
        except (AttributeError, KeyError):
            continue
        if value is not None:
            values[name] = value
    if not values:
        # An empty section is worse than none: it would say the pack was read
        # and reported nothing.
        return None
    return {"unit": device.unit_id, "readings": {"values": values}}


def _wallbox(runtime: Any) -> dict[str, Any] | None:
    """Return the wallbox's readings, when one answered behind this endpoint.

    Nothing here reads its serial. It sits two registers below the model name
    the library probes instead, and it reached a published document once as
    the words `[16690, 13633]` -- so `publishable` is applied to these names
    as well, and the library never asks for the field at all.
    """
    coordinator = runtime.wallbox
    if coordinator is None:
        return None
    device = coordinator.device
    values = {}
    for name in sorted(device._fields):
        if not survey.publishable(name):
            continue
        try:
            value = device.field(name)
        except (AttributeError, KeyError):
            continue
        if value is not None:
            values[name] = value
    if not values:
        return None
    return {"unit": device.unit_id, "readings": {"values": values}}


def summarise(document: dict[str, Any]) -> str:
    """Describe what a document found, in a few lines a person can check.

    Rendered from the **document** rather than from the readings it was built
    from, deliberately: every claim here is then a value that was actually
    published, so a summary cannot promise something the file does not
    contain. The standalone survey's printed summary follows the same rule
    for the same reason.
    """
    device = document.get("device") or {}
    connection = document.get("connection") or {}
    probes = document.get("capability_probes") or {}
    firmware = document.get("firmware") or {}

    answered = sum(
        1 for entry in probes.values() if entry.get("state") == State.PRESENT
    )
    lines = [
        f"- **{len(probes)} registers probed**, {answered} answered with a value.",
        f"- Reached {connection.get('verdict', 'by an unknown route')}.",
        f"- Published as `{device.get('serial_anonymized_hashed', 'anon-…')}` —"
        " a stand-in, not your serial number.",
    ]
    version = firmware.get("inverter") or firmware.get("arm")
    if version:
        lines.append(f"- Firmware `{version}`.")
    else:
        lines.append(
            "- No firmware version: this machine refuses the block that "
            "reports it, which is itself worth knowing."
        )
    readings = (document.get("readings") or {}).get("values") or {}
    lines.append(f"- {len(readings)} register values decoded.")
    said = document.get("user_inputs") or {}
    if said.get("other_inverter") == survey.OTHER_INVERTER_YES:
        named = said.get("other_inverter_detail")
        lines.append(
            "- Another, non-Sungrow inverter shares this installation"
            f"{': ' + named if named else ''}. That is in the file, and it "
            "explains load figures that would otherwise read as a fault."
        )

    dump = document.get("register_dump") or {}
    bands = {
        space: values for space, values in dump.items() if isinstance(values, dict)
    }
    if bands:
        covered = sum(len(values) for values in bands.values())
        answered = sum(
            1
            for values in bands.values()
            for word in values.values()
            if word is not None
        )
        # The serial's ten masked registers count as unanswered here, as they
        # do in every document a standalone survey writes. Understating what
        # answered is the safe direction for a number a maintainer reads as
        # evidence about the device.
        lines.append(f"- Raw band sweep: {answered} of {covered} addresses answered.")
        missed = dump.get("bands_not_reached")
        if missed:
            lines.append(
                f"- The sweep ran out of time before {len(missed)} of its bands. "
                "Those addresses are absent from the file rather than refused."
            )
    if document.get("battery_pack"):
        lines.append("- A Sungrow battery answered, and its own registers are in.")
    if document.get("wallbox"):
        lines.append("- A wallbox answered, and its registers are in.")
    return "\n".join(lines)
