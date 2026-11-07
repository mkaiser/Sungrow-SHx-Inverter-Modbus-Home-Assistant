"""The run's state, its progress and budget, and its reads and writes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
import math
from typing import Any

from modbus_connection import ModbusError, ModbusExceptionError

from ..addresses import DIRECT_ONLY_PROBE
from ..hybrid_inverter import export_scale
from ..hybrid_inverter.capabilities import Capability
from ..hybrid_inverter.device import SungrowInverter
from ..model import SETTLES_NOTHING
from .procedure import (
    DROPPED,
    EFFECT_BUDGET,
    IMPORT_LIMIT_BUDGET,
    PREFLIGHT_BUDGET,
    PV_CUT_BUDGET,
    READBACK_BUDGET,
    REFUSED,
    RESTART_BUDGET,
    RUN_BUDGET,
    SAMPLE_COMPONENTS,
    SEVERITY,
    VERIFY_BUDGET,
    WAIT_TICK,
    WINDOW_BUDGET,
    Clock,
    Options,
    Probe,
    Progress,
    RealClock,
    Sample,
    Snapshot,
)

_LOGGER = logging.getLogger(__name__)


class ControlTestBase:
    """What every phase of a run shares: its state, clock, reads and writes."""

    def __init__(
        self,
        inverter: SungrowInverter,
        *,
        options: Options | None = None,
        on_progress: Progress | None = None,
        clock: Clock | None = None,
        on_snapshot: Callable[[Snapshot], Awaitable[None]] | None = None,
        on_wait: Callable[[], None] | None = None,
        sungrow_pack: bool = False,
    ) -> None:
        """Prepare a run. Nothing is read and nothing is written until `async_run`.

        `sungrow_pack` says a Sungrow pack answered on its own unit, which the
        inverter alone cannot see; with an SBR's capacity it grants
        `Capability.SUNGROW_BATTERY`, as the integration's setup does.

        `on_wait` is called every `WAIT_TICK` seconds while the run waits for
        the inverter to stop, start or generate -- a heartbeat, carrying no
        progress, for a waiting time measured in minutes.
        """
        self.inverter = inverter
        self.options = options or Options()
        self.clock = clock or RealClock()
        self._progress = on_progress
        self._on_wait = on_wait
        self._last_tick = 0.0
        self._on_snapshot = on_snapshot
        self._sungrow_pack = sungrow_pack
        self.snapshot = Snapshot(taken_at=0.0)
        self.capabilities: frozenset[Capability] = frozenset()
        self.plan: tuple[Probe, ...] = ()
        self.conditions: dict[str, Any] = {}
        self.direct: bool | None = True
        """Whether this endpoint is the inverter's own port rather than a
        dongle, or `None` where the link would not say. Decides whether the
        readback legs can be believed: a WiNet-S forwards a write and then
        answers the old value when it is read back, so through one "write it
        and read it back" settles nothing. `None` is not `False` -- it means
        the question could not be put, and the report says so rather than
        discarding legs A and B on a guess."""
        self._transport_checked = False
        """Whether `direct` was measured. A restore run on its own -- the CLI's
        `--restore`, Home Assistant's repair -- has had no preflight, and must
        not take the default for a cable."""
        self.unestablished: list[str] = []
        self._written: dict[str, float] = {}
        self._last_refused: str | None = None
        self.refusals: dict[str, str] = {}
        """Field name to the exception a write came back with, verbatim.

        Kept because "refused" is not a finding on its own: the device saying a
        value is out of range and the device saying it is busy are different
        facts, and only one of them is about the register.
        """
        self._taken: list[float] = []
        """Every value this run has written anywhere, so no two controls get the
        same one. Held on the run rather than in the readback walk, because the
        behavioural phase picks a value too -- and a forced charge at the value
        the charge limit already holds is exactly the collision that makes a
        write to the wrong address invisible."""
        self.export_write_scale: int | None = None
        """How this firmware writes 13074, as `export_scale` measured it, or
        `None` before it is asked or where it could not answer. `None` writes
        through the field, which divides by ten: what the integration falls
        back to as well."""
        self.accepted_forced_w: float | None = None
        """What the pack actually took for the last forced command.

        Not the same as what was asked for: a BMS clamps to its own live limit,
        which moves with charge and temperature. The effect checks compare
        measured power against what was *accepted*, because comparing against a
        figure the device already declined would report the clamp as a finding.
        """
        self._deadlines: dict[str, float] = {}
        self._done = 0
        self._total = 1
        self._codes: set[int] = {0}

    # -- progress and budget -------------------------------------------------

    def _step(self, label: str) -> None:
        """Advance the progress bar by one counted unit."""
        self._done += 1
        if self._progress is not None:
            self._progress(min(self._done / self._total, 1.0), label)

    def _tick(self, *, start: bool = False) -> None:
        """Call `on_wait` once per `WAIT_TICK` of a wait; `start` begins one."""
        now = self.clock.monotonic()
        if start:
            self._last_tick = now
        elif now - self._last_tick >= WAIT_TICK:
            self._last_tick = now
            if self._on_wait is not None:
                self._on_wait()

    def _plan_budget(self) -> None:
        """Fix every phase deadline now, against one origin.

        Absolute rather than cumulative, and that is the point: a preflight that
        overruns spends its own slack and leaves the readback's deadline exactly
        where it was. Cumulative budgets let the first slow phase eat the phase
        that would have found something.
        """
        start = self.clock.monotonic()
        share = self.options.run_budget / RUN_BUDGET
        running = start
        effect = EFFECT_BUDGET + (PV_CUT_BUDGET if self.options.cut_pv else 0.0)
        effect += WINDOW_BUDGET * (
            self.options.charge_window + self.options.discharge_window
        )
        effect += IMPORT_LIMIT_BUDGET if self.options.import_limit else 0.0
        for name, budget in (
            ("preflight", PREFLIGHT_BUDGET),
            ("readback", READBACK_BUDGET),
            ("effect", effect),
            ("verify", VERIFY_BUDGET),
        ):
            running += budget * share
            self._deadlines[name] = running
        self._deadlines["restart"] = running + RESTART_BUDGET

    def _expired(self, phase: str) -> bool:
        """Whether this phase is out of time. Never consulted by the restore."""
        return self.clock.monotonic() >= self._deadlines.get(phase, math.inf)

    def _note(self, sentence: str) -> None:
        """Record something this run could not establish."""
        if sentence not in self.unestablished:
            self.unestablished.append(sentence)

    def _worst(self, code: int) -> None:
        """Remember a code, so the run ends in the most serious one seen."""
        self._codes.add(code)

    @property
    def code(self) -> int:
        """The most serious outcome this run reached."""
        return max(self._codes, key=SEVERITY.index)

    # -- reading -------------------------------------------------------------

    async def _refresh(self, *names: str) -> None:
        """Re-read some components, tolerating a component that will not answer.

        Tolerated rather than raised: a poll losing one block is normal on this
        hardware, and a run that aborts on the first missing optional component
        would never complete on an inverter without a battery.
        """
        for name in names:
            try:
                await self.inverter.component(name).async_update()
            except (ModbusError, TimeoutError, OSError) as err:
                _LOGGER.debug("control test: %s did not answer: %s", name, err)

    def _value(self, name: str) -> Any:
        """Return a decoded field, or None where the device has no such field."""
        try:
            return self.inverter.field(name)
        except AttributeError:
            return None

    async def _raw(self, probe: Probe) -> int | None:
        """Read the register's own word, which is leg B's whole evidence.

        Deliberately not routed through the component: the component would
        decode it with the very factor under test, and a value that has been
        through that factor cannot be used to check it.
        """
        component = self.inverter.component(probe.component)
        resolved = component.resolved_fields.get(probe.field)
        if resolved is None:
            return None
        if resolved.count != 1:
            # Every control in `PROBES` is one U16, which a test asserts. A
            # wider one would need its word order applied here, and applying
            # the map's word order would put the map back into leg B.
            return None
        try:
            words = await self.inverter.async_read_words("holding", resolved.address, 1)
        except (ModbusError, TimeoutError, OSError) as err:
            _LOGGER.debug("control test: raw read of %s failed: %s", probe.field, err)
            return None
        return words[0]

    async def _sample(self) -> Sample:
        """Read one moment of the house."""
        await self._refresh(*SAMPLE_COMPONENTS)
        return Sample(
            at=self.clock.monotonic(),
            pv=self._value("total_dc_power"),
            battery=self._value("battery_power"),
            export=self._value("export_power_raw"),
            load=self._value("load_power"),
            soc=self._value("battery_level"),
        )

    # -- writing -------------------------------------------------------------

    WRITE_SETTLE = 1.5
    """Seconds between a write and the read that checks it. The YAML package
    used one second for its switch verification and a tenth for its selects,
    and both worked; this is the larger of the two with room for a dongle."""

    #: What tells a cable from a dongle: see `addresses.DIRECT_ONLY_PROBE`.
    #: `survey_document.PROBES` reads the same register for the survey.
    DIRECT_ONLY = DIRECT_ONLY_PROBE

    #: Three attempts, a second apart, for the same reason `SNAPSHOT_PAUSE`
    #: has them: on a link somebody else is polling, one read can simply miss.
    TRANSPORT_ATTEMPTS = 3
    TRANSPORT_PAUSE = 1.0

    async def _detect_transport(self) -> bool | None:
        """Whether this endpoint is the inverter's own port rather than a dongle.

        Worth its own read, because it decides what the run may claim. A WiNet-S
        forwards a write and then answers a **stale** value when the register is
        read back -- measured at gerd, where cable and dongle disagreed about
        33047 before anything was written, and a write sent over the dongle
        arrived while the dongle went on reporting the old figure.

        So through a dongle, "write it and read it back" is not evidence: it
        cannot tell a dropped write from a cache, in either direction. Leg C is
        untouched, since watching real power change needs no readback at all.

        **And waiting does not fix it**, which is the measurement that decides
        this rather than a guess. Polled every 5 s for two minutes, the same
        dongle never once reported a value the cable had confirmed -- and the
        figure it kept returning was hours old, not seconds. So there is no
        settling time the tool could sit out to earn legs A and B back on a
        dongle, and offering one would only make a stale answer look ripe.

        **Three answers, not two**, and the third is the point. Treating *any*
        failure as a dongle is wrong in the one direction that costs
        something: a lost read is not a refusal. On a cable with Home Assistant
        polling alongside, a lost read would stamp the readback table "not
        evidence" while the survey half of the same document said "direct to
        the inverter's LAN port" -- and over a VPN, where 10-second timeouts
        are measured, that would be the common case rather than the unlucky
        one.

        So a *refusal* -- the device answering with an exception code -- is
        evidence and means a dongle, while a connection lost, a timeout or a
        desync is the link failing to carry the question and is evidence of
        nothing. `model.SETTLES_NOTHING` sits with the latter: it means ask
        me later, not there is no such register. Undetermined returns `None`,
        which the report renders as an unknown rather than as a dongle,
        because asserting a dongle discards legs A and B.
        """
        for attempt in range(self.TRANSPORT_ATTEMPTS):
            try:
                await self.inverter.async_read(self.DIRECT_ONLY)
            except SETTLES_NOTHING:
                pass
            except ModbusExceptionError:
                return False
            except (ModbusError, TimeoutError, OSError):
                pass
            else:
                return True
            if attempt < self.TRANSPORT_ATTEMPTS - 1:
                await self.clock.sleep(self.TRANSPORT_PAUSE)
        return None

    async def _touch(self, field: str) -> None:
        """Record that this run is about to write `field`, and flush it first.

        Before the write, for the snapshot's reason: a write that lands and a
        process that dies before saying so would leave a register changed that
        the snapshot does not know was touched. See `Snapshot.touched`.
        """
        touched = self.snapshot.touched
        if touched is None or field in touched:
            return
        touched.append(field)
        if self._on_snapshot is not None:
            await self._on_snapshot(self.snapshot)

    async def _write(self, probe: Probe, value: float) -> str | None:
        """Write one control. Returns a verdict word on failure, None on success.

        The refusal is recorded with **which exception came back**, in
        `self.refusals`, because "refused" on its own is not a finding. An
        exception 0x04 is the device saying the value is out of range, which is
        a fact about the register; 0x06 is the device saying it is busy, which
        on a link something else is polling is a fact about the afternoon. A
        refusal without its exception type cannot be explained afterwards, nor
        told apart from one that fails to reproduce.
        """
        if self.options.dry_run:
            return None
        await self._touch(probe.field)
        if probe.raw_only:
            # A value, like every other write: the register's own counts are
            # `spec_units_per_count`, which is 1 for the discharge windows and
            # 0.01 kW for the import limit. A restore's fallback writes the
            # snapshot's value through here, so a value taken as a word would
            # put 20.00 kW back as 0.20.
            word = round(value / probe.spec_units_per_count)
            failure = await self._write_word(probe, word)
            if failure is not None:
                self.refusals[probe.field] = f"the raw write {failure}"
                self._last_refused = probe.field
                return failure
            self._written[probe.field] = value
            return None
        try:
            if (
                probe.field == "export_power_limit"
                and self.export_write_scale is not None
            ):
                await self.inverter.async_write_word(
                    export_scale.LIMIT.address,
                    export_scale.word_for(value, self.export_write_scale),
                )
            else:
                await self.inverter.component(probe.component).write(probe.field, value)
        except ModbusError as err:
            _LOGGER.debug("control test: %s refused %s: %s", probe.field, value, err)
            self.refusals[probe.field] = f"{type(err).__name__}: {err}"
            self._last_refused = probe.field
            return REFUSED
        except (TimeoutError, OSError) as err:
            _LOGGER.debug("control test: %s dropped on %s: %s", probe.field, value, err)
            self.refusals[probe.field] = f"{type(err).__name__}: {err}"
            self._last_refused = probe.field
            return DROPPED
        self._written[probe.field] = value
        return None

    async def _write_word(self, probe: Probe, word: int) -> str | None:
        """Write one raw word to a control's register. None on success.

        Refusals are deliberately **not** recorded in `self.refusals`: on a
        multiplying firmware this write is expected to be refused, and that
        table is what the report quotes for the probe's own write.
        """
        if self.options.dry_run:
            return None
        await self._touch(probe.field)
        component = self.inverter.component(probe.component)
        resolved = component.resolved_fields.get(probe.field)
        if resolved is None or resolved.count != 1:
            return REFUSED
        try:
            await self.inverter.async_write_word(resolved.address, word)
        except ModbusError as err:
            _LOGGER.debug(
                "control test: %s refused word %s: %s", probe.field, word, err
            )
            return REFUSED
        except (TimeoutError, OSError) as err:
            _LOGGER.debug(
                "control test: %s dropped word %s: %s", probe.field, word, err
            )
            return DROPPED
        return None
