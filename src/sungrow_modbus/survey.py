"""Backend-neutral helpers for survey consumers.

This module deliberately returns data rather than printing, prompting, writing
files, or submitting reports. The terminal survey and Home Assistant render
the same recommendations differently, but they must reason from the same
published document.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from modbus_connection import ModbusError, ModbusExceptionError
from modbus_connection.model import Component

from . import survey_document
from .addresses import DIRECT_ONLY_PROBE, declared_field, field_address, read
from .inverter.device import SungrowInverter
from .inverter.registers import COMPONENTS
from .model import Silent, present, words_text
from .survey_document import OTHER_INVERTER_YES, State, classify


@dataclass(frozen=True)
class NextStep:
    """A follow-up action justified by evidence in a survey document."""

    key: str
    title: str
    detail: str


async def async_read_retrying(
    read: Callable[[int, int], Awaitable[list[int]]],
    address: int,
    count: int,
    attempts: int = 3,
    *,
    delay: float = 1.5,
) -> list[int]:
    """Read one block, retrying transient Modbus failures."""
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return list(await read(address, count))
        except (ModbusError, TimeoutError, OSError):
            if attempt >= attempts:
                raise
            await asyncio.sleep(delay)
    raise AssertionError("unreachable")


def failure_state(error: BaseException) -> str:
    """Classify a failed read without treating a lost link as a refusal."""
    if isinstance(error, ModbusExceptionError):
        return str(State.REFUSED)
    return str(State.NO_ANSWER)


async def async_probe_words(
    read_words: Callable[[str, int, int], Awaitable[list[int]]],
    probes: Iterable[tuple[str, str, int, int, str]] | None = None,
    *,
    attempts: Callable[[str], int] | None = None,
    on_probe: Callable[[str], None] | None = None,
) -> tuple[dict[str, list[int]], dict[str, str]]:
    """Read capability probes and return raw values plus their states.

    `read_words(space, address, count)` is whatever reads raw words on the
    caller's connection -- `SungrowInverter.async_read_words`, say. A refusal
    and a timeout are recorded differently and deliberately: exception 0x02 is
    the device saying the register is not there, while nothing coming back
    says only that nothing came back.

    `on_probe(label)` is called *before* each read, not after: on the link
    where progress matters a single read can take ten seconds, and a step
    announced only once it has finished shows the wrong one throughout.

    Raw values are returned for every probe that answered, serial labels
    included; `survey_document.capability_registers` drops those at publication.
    `probes` defaults to `survey_document.PROBES`, looked up at the call.
    """
    raw: dict[str, list[int]] = {}
    states: dict[str, str] = {}
    for label, space, address, count, _axis in (
        survey_document.PROBES if probes is None else probes
    ):
        if on_probe is not None:
            on_probe(label)

        async def read(start: int, size: int, space: str = space) -> list[int]:
            return await read_words(space, start, size)

        retry_count = attempts(label) if attempts else 3
        try:
            values = await async_read_retrying(read, address, count, retry_count)
        except (ModbusError, TimeoutError, OSError) as error:
            states[label] = failure_state(error)
        else:
            raw[label] = values
            states[label] = classify(values).value
    return raw, states


async def async_probe_fields(
    unit: Any,
    probes: Iterable[tuple[str, str, int, int, str]] | None = None,
    *,
    attempts: Callable[[str], int] | None = None,
) -> tuple[dict[str, list[int]], dict[str, str]]:
    """`async_probe_words` on a modbus-connection unit."""
    return await async_probe_words(word_reader(unit), probes, attempts=attempts)


async def async_read_6100(unit: Any, *, attempts: int = 6) -> str:
    """Ask whether the path forwards register 6100: the transport's question.

    Registers 6100-6195 are documented as unsupported through a WiNet-S or a
    Logger, so an answer means the inverter's own port. Three-valued and
    never collapsed: `answered`, `refused` (an exception response, which is
    the dongle saying so) or `no answer` (the link, which says nothing). A
    lost link read as `refused` would make the verdict a dongle, and offer
    the owner of a cable to change a correct answer to match it.

    Retried with the long budget, because one read lost to contention is not
    an answer and this one decides a word in the filename.
    """
    space, start, count = DIRECT_ONLY_PROBE

    async def read(address: int, size: int) -> list[int]:
        return await word_reader(unit)(space, address, size)

    try:
        await async_read_retrying(read, start, count, attempts)
    except (ModbusError, TimeoutError, OSError) as error:
        return failure_state(error)
    return survey_document.ANSWERED_6100


async def async_read_module(unit: Any) -> str | None:
    """Return the communication module register 13265 names, or None.

    It names the module that is *fitted*, not the one in the path -- gerd's
    inverter names its WiNet-S on a reading taken through its own LAN port --
    and a dongle can answer it empty. So it is reported beside 6100 and
    decides nothing; a failed read is None, as an empty one is.
    """
    name = "communication_module_firmware_version"
    try:
        words = await read(unit, field_address(name))
    except (ModbusError, TimeoutError, OSError):
        return None
    value = present(declared_field(name).decode(words))
    return str(value) if value else None


async def async_read_firmware(
    unit: Any,
    *,
    on_string: Callable[[str, str | None], None] | None = None,
) -> dict[str, str | None]:
    """Read the five published firmware strings raw, for a survey with no poll.

    A string that did not read is left out; one that read empty is None.
    Sungrow fills a field it has nothing for with 0x00, so empty means "no
    such firmware here", not "a firmware named the empty string" -- null, the
    way the decoded readings report it. `on_string(name, value)` follows each
    string that read.
    """
    read_words = word_reader(unit)
    firmware: dict[str, str | None] = {}
    for name, space, address, count in survey_document.FIRMWARE_STRINGS:

        async def read(start: int, size: int, space: str = space) -> list[int]:
            return await read_words(space, start, size)

        try:
            words = await async_read_retrying(read, address, count)
        except (ModbusError, TimeoutError, OSError):
            continue
        firmware[name] = words_text(words).strip() or None
        if on_string is not None:
            on_string(name, firmware[name])
    return firmware


async def async_probe_siblings(
    unit_for: Callable[[int], Any],
    *,
    attempts: int = 6,
    on_probe: Callable[[str, list[int] | None], None] | None = None,
) -> tuple[dict[str, list[int]], dict[str, str]]:
    """Ask each unit in `survey_document.SIBLING_PROBES` whether anything answers.

    `unit_for(unit_id)` returns a modbus-connection unit on the same link.
    Retried with the long budget, because whether unit 200 or unit 2 answers
    is what separates `battery-sbr096` from `battery-unknown` in a filename:
    a miss here is a published claim about somebody's hardware, and a single
    shot can miss an SBR that answered at 200 a minute earlier.

    `on_probe(label, words)` follows each read, with None for no answer.
    """
    raw: dict[str, list[int]] = {}
    states: dict[str, str] = {}
    for label, unit_id, address in survey_document.SIBLING_PROBES:
        try:
            values = await async_read_retrying(
                unit_for(unit_id).read_input_registers,
                address,
                survey_document.PRESENCE_WORDS,
                attempts,
            )
        except (ModbusError, TimeoutError, OSError):
            states[label] = str(State.NO_ANSWER)
            if on_probe is not None:
                on_probe(label, None)
            continue
        raw[label] = values
        states[label] = str(State.PRESENT)
        if on_probe is not None:
            on_probe(label, values)
    return raw, states


def word_reader(unit: Any) -> Callable[[str, int, int], Awaitable[list[int]]]:
    """Adapt a modbus-connection unit to `read_words(space, address, count)`.

    The seam `dump.async_dump`, `wallbox.async_mapped_words` and the probes
    read through, so one adapter serves every caller holding a bare unit.
    """

    async def read_words(space: str, address: int, count: int) -> list[int]:
        if space == "holding":
            return list(await unit.read_holding_registers(address, count))
        return list(await unit.read_input_registers(address, count))

    return read_words


def _span(space: str, descriptor: Any) -> tuple[str, int, int]:
    """Return the registers one declared field reads: space, address, count."""
    return space, int(descriptor.address), int(getattr(descriptor, "count", 1))


async def async_read_field_by_field(
    unit: Any,
    component_class: type[Component],
    *,
    sweeps: int = 3,
    pause: float = 2.0,
    silent: Silent | None = None,
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
    runs only after the whole-component attempts have failed. With `silent`, a
    field whose read timed out is not asked again, in a later sweep or by any
    later narrowing in the run: a refusal is quick to repeat, a quiet register
    costs the whole timeout each time.
    """
    values: dict[str, object] = {}
    pending: dict[str, object] = dict(component_class.declared_fields)
    # Swept repeatedly, because a single failed read is not a refusal: on a
    # contended port one sweep of individual reads misses fields the curated
    # probes read minutes earlier. Only a field that misses every separated
    # sweep is evidence about the device rather than about the traffic.
    for sweep in range(1, max(1, sweeps) + 1):
        missed_this_sweep: dict[str, object] = {}
        for name, descriptor in pending.items():
            span = _span(component_class.register_space, descriptor)
            if silent is not None and silent.covers(*span):
                missed_this_sweep[name] = descriptor
                continue
            solo_class = type(
                f"Solo_{name}",
                (Component,),
                {"register_space": component_class.register_space, name: descriptor},
            )
            try:
                solo = solo_class(unit)
                await solo.async_update()
            except TimeoutError:
                missed_this_sweep[name] = descriptor
                if silent is not None:
                    silent.note(*span)
            except (ModbusError, OSError):
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
        if silent is not None and all(
            silent.covers(*_span(component_class.register_space, descriptor))
            for descriptor in pending.values()
        ):
            # Everything left is known to go quiet: another sweep would only
            # skip it after the pause.
            break
        if sweep < max(1, sweeps):
            await asyncio.sleep(pause)
    return values, sorted(pending)


async def async_decoded_readings(
    unit: Any,
    *,
    passes: int = 8,
    pause: float = 2.0,
    on_component: Callable[[str], None] | None = None,
    on_passes_done: Callable[[int, int], None] | None = None,
    on_note: Callable[[str], None] | None = None,
    silent: Silent | None = None,
) -> dict[str, object]:
    """Return every register the integration reads, decoded.

    The curated probes are the right set for *capabilities* and the wrong set
    for everything else: a Pylontech reporting capacity 0 where a Sungrow pack
    reports its size, and registers 33149/33150 reading 200 W and 100 W where
    the specification documents nothing, are both outside them.

    So a survey carries the whole map. The cost is bounded and small
    because the library pools neighbouring registers into a few dozen reads.
    A blind sweep of the whole address span is tens of thousands of
    addresses, mostly "Reserved" per the specification and each one a chance
    to drop the link -- which is why the wider net is cast over the *map* and
    not over the address space.

    Decoded rather than raw, deliberately. A raw word says the read worked; a
    decoded value says the scale and word order are right, which is the
    mistake worth catching.

    Nothing is printed. `on_component(name)` follows each component's first
    attempt, `on_passes_done(answered, total)` the last pass, and
    `on_note(text)` carries a line worth showing a person; `pause` is the
    gap between passes, which is what lets a busy inverter's other client
    finish.
    """
    inverter = SungrowInverter(unit)
    # Retried and then tolerated. Unguarded, a single drop here would raise
    # past all the per-component tolerance below and lose every decoded
    # reading -- an empty block no reader would notice, when catching a wrong
    # scale or word order is the whole reason the block exists.
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
    # polling, which is nearly all of them. Attempts taken back to back
    # collide with the other client at exactly the wrong moment; spreading
    # them out and only re-reading what is still missing gets the lot,
    # because the collision is a moment rather than a state.
    #
    # The cost is that fields come from different moments, so arithmetic
    # *between* them can be inconsistent -- mppt1 + mppt2 need not equal a
    # total_dc_power read forty seconds later. That is already true of this
    # block ("not stable between reads") and is the right trade for a
    # capability report, where the questions are whether a register answers
    # and whether its scale is right.
    pending = list(COMPONENTS)
    for this_pass in range(1, max(1, passes) + 1):
        still_missing: list[str] = []
        for attribute in pending:
            try:
                await inverter.component(attribute).async_update()
            except (ModbusError, TimeoutError, OSError):
                still_missing.append(attribute)
            # Only the first pass reports progress. Later passes re-read what
            # is still missing, and counting those would push a bar past its
            # own total -- a bar that reads 31/23 is worse than none.
            if this_pass == 1 and on_component is not None:
                on_component(attribute)
        # `pending` is assigned *before* the emptiness test, not after. The
        # other way round -- `if not still_missing: break` and then
        # `pending = still_missing` -- leaves `pending` holding whatever the
        # pass began with, so a device that answered everything on pass 1
        # would be reported as every component missed and have all its fields
        # re-read one at a time: a plausible document with plausible values.
        # Guarded by
        # `test_a_device_that_answers_everything_reports_nothing_missed`.
        pending = still_missing
        if not pending:
            if this_pass > 1 and on_note is not None:
                on_note(f"all components answered by pass {this_pass}")
            break
        if this_pass < max(1, passes):
            if on_note is not None:
                on_note(f"pass {this_pass}: still waiting on {', '.join(pending)}")
            await asyncio.sleep(pause)
    if on_passes_done is not None:
        on_passes_done(len(COMPONENTS) - len(pending), len(COMPONENTS))
    missed = pending

    # Whatever is still missing, read field by field so that only the
    # registers the device truly refuses are absent from the report.
    salvaged: dict[str, object] = {}
    unreadable: list[str] = []
    for attribute in missed:
        if on_note is not None:
            on_note(f"{attribute}: reading its fields one at a time")
        recovered, refused = await async_read_field_by_field(
            unit, type(inverter.component(attribute)), pause=pause, silent=silent
        )
        salvaged.update(recovered)
        unreadable.extend(refused)
        if on_note is not None:
            on_note(
                f"{attribute}: {len(recovered)} recovered, {len(refused)} still missing"
            )

    report = survey_document.readings_section(
        inverter, missed, salvaged=salvaged, unreadable=unreadable
    )
    if identity_failed:
        # Named rather than hidden: without the identity block the capability
        # gating is working from nothing, so every field below is suspect.
        report["identity_did_not_read"] = identity_failed
    return report


class Step(StrEnum):
    """One step of a capability survey, in the order they are taken."""

    IDENTITY = "identity"
    READINGS = "readings"
    PROBES = "probes"
    CONNECTION = "connection"
    REGISTER_DUMP = "register dump"
    BATTERY = "battery"
    WALLBOX = "wallbox"


class SurveySource(Protocol):
    """How one producer collects each step; the order is not its to choose.

    The terminal survey reads everything raw, because it has no device yet.
    Home Assistant answers the identity and the readings from what its
    coordinators already polled, because reading them again would cost
    requests on a link a Sungrow grants very few sessions on. Either way a
    method returns the section in the shape `assemble_document` takes, and
    None for a step this run does not take -- a dump nobody asked for, a pack
    or a wallbox that is not there.
    """

    async def identity(self) -> tuple[str | None, dict[str, str | None]]:
        """Return the serial (or None where it did not read) and the firmware."""

    async def readings(self) -> dict[str, Any] | None:
        """Return every decoded value, in `readings_section`'s shape."""

    async def probes(self) -> tuple[dict[str, list[int]], dict[str, str]]:
        """Return the capability probes' raw words and their states."""

    async def connection(self, survey: CapabilitySurvey) -> dict[str, Any]:
        """Return the measured connection, from the probes already taken."""

    async def register_dump(self) -> dict[str, Any] | None:
        """Return the raw address bands, or None when this run takes none."""

    async def battery(self, survey: CapabilitySurvey) -> dict[str, Any] | None:
        """Return the pack's `{"unit", "readings"}`, or None without one."""

    async def wallbox(self, survey: CapabilitySurvey) -> dict[str, Any] | None:
        """Return the wallbox's section, or None without one."""


@dataclass
class CapabilitySurvey:
    """What a capability survey collected, section by section.

    `failed` names each step the link lost, with the exception's type: the
    step's section is then absent, and the rest of the document is still
    worth publishing.
    """

    serial: str | None = None
    firmware: dict[str, str | None] = field(default_factory=dict)
    readings: dict[str, Any] | None = None
    probe_values: dict[str, list[int]] = field(default_factory=dict)
    probe_states: dict[str, str] = field(default_factory=dict)
    connection: dict[str, Any] = field(default_factory=dict)
    register_dump: dict[str, Any] | None = None
    battery_pack: dict[str, Any] | None = None
    wallbox: dict[str, Any] | None = None
    failed: dict[Step, str] = field(default_factory=dict)

    @property
    def capability_probes(self) -> dict[str, dict[str, Any]]:
        """The probes in the published shape, serial-bearing ones removed."""
        return survey_document.capability_registers(
            self.probe_states, self.probe_values
        )

    def thin(self) -> list[str]:
        """Name what a document's filename is built from and did not read.

        A transient miss of 5002 costs a document its `3p` word, which is
        invisible unless you know every good filename has one. Cheap to
        re-run, expensive to notice -- so the producer says so.
        """
        values = (self.readings or {}).get("values")
        return [
            name
            for name, value in (
                ("device type code (5000)", self._probed("device type code")),
                ("output type (5002)", self._probed("output type")),
                # The only thing keeping two setups of one shape apart.
                ("serial number (4990)", self.serial),
                ("the decoded readings", values),
            )
            if not value
        ]

    def _probed(self, prefix: str) -> list[int] | None:
        for label, words in self.probe_values.items():
            unavailable = all(word in survey_document.UNAVAILABLE for word in words)
            if label.startswith(prefix) and words and not unavailable:
                return words
        return None


async def async_capability_survey(
    source: SurveySource,
    *,
    on_failure: Callable[[Step, BaseException], None] | None = None,
) -> CapabilitySurvey:
    """Take every step of a capability survey, in one order for both producers.

    Identity first, because firmware is what makes two documents comparable;
    then the decoded readings; then the probes, and the connection from them;
    then the optional extras -- the raw bands, the pack, the wallbox -- which
    are the slow part and the part a link is most likely to drop.

    **A step the link loses costs its own section and nothing else.** A
    `ModbusError`, a timeout or a lost socket is caught here, recorded in
    `failed` and handed to `on_failure`; the next step still runs. A minute
    of reading that already succeeded is never discarded because the dump at
    the end of it stopped. Anything else is a bug and propagates.

    The block read test is not a step. It is the one measurement that means
    something only on an idle link, so a producer runs it *before* this, with
    whatever client it measures through.
    """
    survey = CapabilitySurvey()

    async def take(step: Step, collect: Callable[[], Awaitable[Any]]) -> Any:
        try:
            return await collect()
        except (ModbusError, TimeoutError, OSError) as error:
            survey.failed[step] = type(error).__name__
            if on_failure is not None:
                on_failure(step, error)
            return None

    identity = await take(Step.IDENTITY, source.identity)
    if identity is not None:
        survey.serial, survey.firmware = identity
    survey.readings = await take(Step.READINGS, source.readings)
    probes = await take(Step.PROBES, source.probes)
    if probes is not None:
        survey.probe_values, survey.probe_states = probes
    survey.connection = (
        await take(Step.CONNECTION, lambda: source.connection(survey)) or {}
    )
    survey.register_dump = await take(Step.REGISTER_DUMP, source.register_dump)
    survey.battery_pack = await take(Step.BATTERY, lambda: source.battery(survey))
    survey.wallbox = await take(Step.WALLBOX, lambda: source.wallbox(survey))
    return survey


def next_steps(document: dict[str, Any]) -> tuple[NextStep, ...]:
    """Return actionable follow-ups without inventing facts.

    Recommendations are derived only from data already published in the
    document. Consumers can render these as terminal text, a Home Assistant
    notification, or issue-template fields without duplicating the decision
    logic.
    """
    steps: list[NextStep] = []
    block_test = document.get("block_read_test") or {}
    never = block_test.get("never_answered") or []
    if never:
        names = ", ".join(
            f"{item.get('component', 'unknown')} at {item.get('register', '?')}"
            for item in never
        )
        steps.append(
            NextStep(
                "block-read-failure",
                "Investigate unanswered poll blocks",
                f"Read {names} directly and compare the transport before "
                "changing the register layout.",
            )
        )

    if block_test.get("intermittent"):
        steps.append(
            NextStep(
                "contention",
                "Repeat on an idle connection",
                "Intermittent block results indicate contention or an unstable "
                "link, not a confirmed register fault.",
            )
        )

    connection = document.get("connection") or {}
    if connection.get("verdict", "").startswith("through a communication module"):
        steps.append(
            NextStep(
                "direct-transport-check",
                "Compare the direct inverter path",
                "A communication module forwards fewer measuring points; repeat "
                "affected reads on the inverter's own LAN path before changing "
                "the map.",
            )
        )

    probes = document.get("capability_probes") or {}
    firmware = document.get("firmware") or {}
    if not firmware.get("inverter") and not firmware.get("arm"):
        steps.append(
            NextStep(
                "firmware-missing",
                "Check firmware access",
                "The firmware block did not provide a version; record whether the "
                "transport or device refuses that block.",
            )
        )

    if (document.get("user_inputs") or {}).get("other_inverter") == OTHER_INVERTER_YES:
        steps.append(
            NextStep(
                "external-inverter",
                "Account for the other inverter",
                "Use the named non-Sungrow inverter output when interpreting load "
                "power.",
            )
        )

    if not probes:
        steps.append(
            NextStep(
                "no-probes",
                "Repeat the survey",
                "No capability probes were published, so this document cannot "
                "establish compatibility.",
            )
        )
    return tuple(steps)


def summarise(document: dict[str, Any]) -> str:
    """Render a concise, document-derived summary for any consumer."""
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
        f"- Published as `{device.get('serial_anonymized_hashed', 'anon-…')}` — "
        "a stand-in, not your serial number.",
    ]
    version = firmware.get("inverter") or firmware.get("arm")
    lines.append(
        f"- Firmware `{version}`."
        if version
        else "- No firmware version: the firmware block did not provide one."
    )
    readings = (document.get("readings") or {}).get("values") or {}
    lines.append(f"- {len(readings)} register values decoded.")
    user_inputs = document.get("user_inputs") or {}
    if user_inputs.get("other_inverter") == OTHER_INVERTER_YES:
        detail = user_inputs.get("other_inverter_detail") or "not specified"
        lines.append(f"- A non-Sungrow inverter is also present: {detail}.")
    if document.get("register_dump"):
        lines.append("- Raw band sweep included in the document.")
    measured = document.get("block_read_test") or {}
    if measured:
        never = measured.get("never_answered") or []
        intermittent = measured.get("intermittent") or []
        total = len(measured.get("answered") or []) + len(never) + len(intermittent)
        if never:
            line = f"- Block read test: {len(never)} of {total} reads never answered"
        else:
            line = f"- Block read test: all {total} of the poll's reads answered"
        if intermittent:
            # Contention, not a fault -- but not "all answered" either.
            line += f", {len(intermittent)} only some of the time"
        lines.append(line + ".")
    if document.get("battery_pack"):
        lines.append("- A Sungrow battery answered, and its own registers are in.")
    if document.get("wallbox"):
        lines.append("- A wallbox answered, and its registers are in.")
    return "\n".join(lines)
