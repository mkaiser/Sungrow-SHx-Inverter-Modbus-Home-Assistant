"""Putting everything back, and restarting an inverter the run stopped.

The restore is never budgeted, never deadlined and never skipped.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
import math

from modbus_connection import ModbusError

from .base import CapabilityTestBase
from .procedure import (
    CONFIRMED,
    DROPPED,
    ENUMERATIONS,
    INCONCLUSIVE,
    PROBES,
    RESTART_DWELL,
    RESTART_GENERATING_DEADLINE,
    RESTART_POLL,
    RESTART_RESEND_AFTER,
    RESTART_RUNNING_DEADLINE,
    RESTART_STOP_DEADLINE,
    RESTORE_ATTEMPTS,
    RESTORE_PAUSE,
    RUNNING_STATES_STOPPED,
    SKIPPED,
    START_WORD,
    START_WORD_PROBE,
    STOP_WORD,
    Probe,
    RestartResult,
    RestoreResult,
    Snapshot,
    is_running,
    is_starting,
    restore_order,
    soc_pair_order,
)

_LOGGER = logging.getLogger(__name__)


class RestoreSteps(CapabilityTestBase):
    """Restore the snapshot, and make sure the inverter is left running."""

    # -- restore: the part that is never budgeted ----------------------------

    def _probe_for(self, name: str) -> Probe | None:
        """Find a probe row by field name, enumerations included."""
        for probe in (*PROBES, *ENUMERATIONS):
            if probe.field == name:
                return probe
        return None

    async def async_restore(
        self, snapshot: Snapshot | None = None
    ) -> list[RestoreResult]:
        """Put every control back, and prove it went back.

        No deadline is consulted anywhere in here, and that is deliberate to the
        point of being the module's first rule. Every early exit -- an expired
        budget, a guard, a cancellation, an exception -- arrives here, and a
        restore that could be cut short by a clock would turn a run that ran out
        of time into a house left changed.

        A field that will not go back does not stop the others. A link can be
        lost *during* a restore; the answer is not to try harder on that field
        but to make sure its failure cannot take the rest with it.

        **Through a dongle, only what this run touched.** The snapshot there is
        the dongle's cache, and a register the run never wrote cannot have
        been changed by it; writing the cached word into it could only put an
        older figure in place of the real one. A restore with no preflight
        behind it measures the transport first, because it may be running
        through a dongle that the snapshot's run was not.
        """
        snapshot = snapshot or self.snapshot
        if not self._transport_checked:
            self.direct = await self._detect_transport()
            self._transport_checked = True
        names = [name for name in snapshot.values if self._probe_for(name) is not None]
        order = list(restore_order(names))
        if "battery_min_soc" in order and "battery_max_soc" in order:
            pair = soc_pair_order(
                self._value("battery_min_soc"),
                self._value("battery_max_soc"),
                snapshot.values.get("battery_min_soc"),
                snapshot.values.get("battery_max_soc"),
            )
            order = [name for name in order if name not in pair]
            order.extend(pair)

        results: list[RestoreResult] = []
        for name in order:
            probe = self._probe_for(name)
            original = snapshot.values.get(name)
            if probe is None or original is None:
                continue
            if (
                self.direct is not True
                and snapshot.touched is not None
                and name not in snapshot.touched
            ):
                results.append(
                    RestoreResult(
                        field=name,
                        original=float(original),
                        readback=self._value(name),
                        restored=True,
                        attempts=0,
                        detail=(
                            "never written by this run, so left alone: through "
                            "a WiNet-S the snapshot is the dongle's cache"
                        ),
                    )
                )
                continue
            results.append(
                await self._restore_one(probe, float(original), snapshot.raw.get(name))
            )
        if any(not row.restored for row in results):
            self._worst(5)
        return results

    async def _restore_one(
        self, probe: Probe, original: float, word: int | None = None
    ) -> RestoreResult:
        """Put one control back, and prove it: read first, write only if needed.

        Reading first is not an optimisation. An inverter can silently ignore
        the write of a probe value, leaving nothing to undo, and then refuse
        the write of the original -- so a restore judged by its write reports
        **not restored**, the run's most serious verdict, for a register that
        held its original value the whole time.

        A restore is a statement about where the register *is*, not about
        whether a write succeeded. Asking the register settles it, and it also
        means a control this run never managed to change cannot be reported as
        one it failed to change back.

        `word` is the snapshot's raw word, and where there is one it is the
        target: see `_write_back`.

        **Only on a confirmed cable.** Through a WiNet-S the read is the
        dongle's stale cache, which still shows the original after a write
        landed -- so "already holding" skipped the write and left the house
        changed while the report said otherwise (gerd, 2026-11-03: a
        forced-charging window start). Anywhere the transport is not known to
        be direct, the snapshot's word is always written.
        """
        await self._refresh(probe.component)
        if self.direct is True and await self._holds(probe, original, word):
            return RestoreResult(
                field=probe.field,
                original=original,
                readback=self._value(probe.field),
                restored=True,
                attempts=0,
                detail="already holding its original value",
            )

        detail: str | None = None
        for attempt in range(1, RESTORE_ATTEMPTS + 1):
            restored, detail = await self._write_back(probe, original, word)
            if restored:
                return RestoreResult(
                    field=probe.field,
                    original=original,
                    readback=self._value(probe.field),
                    restored=True,
                    attempts=attempt,
                    detail=detail,
                )
            if attempt < RESTORE_ATTEMPTS:
                await self.clock.sleep(RESTORE_PAUSE)
        if self.direct is not True:
            # Through a dongle nothing can be read back, and a refusal there is
            # not proof the register stayed put: a window write refused with
            # 0x04 through gerd's WiNet-S had landed. So this may be a register
            # that never changed (icefest, 2026-11-06: the cable later found
            # it holding its original) or one left changed. Say which read
            # settles it rather than leave "not restored" to be guessed at.
            detail = (
                f"{detail}; through a WiNet-S it cannot be read back, and a "
                "refused write has landed there before, so whether it changed is "
                "not known: read this register over the inverter's own port"
            )
        _LOGGER.warning(
            "capability test could not restore %s to %s: %s",
            probe.field,
            original,
            detail,
        )
        return RestoreResult(
            field=probe.field,
            original=original,
            readback=self._value(probe.field),
            restored=False,
            attempts=RESTORE_ATTEMPTS,
            detail=detail,
        )

    async def _holds(self, probe: Probe, original: float, word: int | None) -> bool:
        """Say whether the register is back where the snapshot found it.

        By its own word where the snapshot has one, because the decoded value
        goes through the scale this whole procedure exists to doubt. The
        decoded comparison is the fallback, for a snapshot saved without words.
        """
        if word is not None:
            raw = await self._raw(probe)
            if raw is not None:
                return raw == word
        current = self._value(probe.field)
        return current is not None and math.isclose(
            float(current), original, rel_tol=1e-6, abs_tol=1e-6
        )

    async def _write_back(
        self, probe: Probe, original: float, word: int | None
    ) -> tuple[bool, str | None]:
        """Write one control back, raw word first, and read it to check.

        The raw word, because writing the *value* back goes through the write
        scale, and a restore that depends on the scale is only as right as the
        scale. At fwitten's SH10RT-V112, 13074 stores the word it is handed
        where other houses multiply it by ten, so a scaled restore of 11880 W
        writes 1188 and leaves the inverter capped at 1.2 kW.

        The scaled write stays as the fallback, and the multiplying firmware is
        why: there the raw word is itself multiplied -- 10000 goes in as 100000
        and is refused with 0x04, or a small word lands ten times too high --
        and only the scaled write puts it back. Each attempt is checked against
        the snapshot's word, so whichever firmware this is, the register ends
        where it started and a wrong intermediate lasts one settle.

        Through a dongle the readback is a stale cache and proves nothing
        either way, so the write being taken is the evidence: the snapshot's
        word, accepted, is a restore. A refused word still falls through to
        the scaled write, and two refusals are a register not put back. With
        nothing read back, a raw word a multiplying firmware takes would land
        ten times off unseen, so 13074 goes out at its measured factor alone.
        Unmeasured through a dongle means feed-in limitation is off, and then
        13074 ignores every write.
        """
        detail: str | None = None
        writes: list[Callable[[], Awaitable[str | None]]] = []
        measured = (
            probe.field == "export_power_limit" and self.export_write_scale is not None
        )
        if word is not None and not (self.direct is False and measured):
            writes.append(lambda: self._write_word(probe, word))
        writes.append(lambda: self._write(probe, original))
        for write in writes:
            failure = await write()
            if failure is None and self.direct is False:
                return True, (
                    "written back through a WiNet-S, which took the write; "
                    "its readback is a stale cache, so it was not read"
                )
            if failure is None:
                await self.clock.sleep(self.WRITE_SETTLE)
                await self._refresh(probe.component)
                if await self._holds(probe, original, word):
                    return True, None
                detail = f"wrote it back but read {self._value(probe.field)!r}"
            else:
                detail = f"the write {failure}"
        return False, detail

    # -- restart -------------------------------------------------------------

    async def _running_word(self) -> int | None:
        """Read the running state, treating a dropped link as a reading of nothing.

        During a stop the inverter may drop the connection entirely, so a
        connection error here is not a failure of the poll -- it is one of the
        two ways "not running" looks from this end. The two are counted
        separately, because a model whose stopped code differs would otherwise
        be indistinguishable from a hang.
        """
        try:
            await self.inverter.component("realtime_input").async_update()
        except (ModbusError, TimeoutError, OSError):
            return None
        value = self._value("running_state_raw")
        return None if value is None else int(value)

    async def _await_state(
        self, deadline: float, wanted: Callable[[int], bool]
    ) -> tuple[float | None, int | None, int]:
        """Poll the running state until it satisfies `wanted`, or time runs out."""
        started = self.clock.monotonic()
        refused = 0
        self._tick(start=True)
        while self.clock.monotonic() - started < deadline:
            self._tick()
            word = await self._running_word()
            if word is None:
                refused += 1
            elif wanted(word):
                return self.clock.monotonic() - started, word, refused
            await self.clock.sleep(RESTART_POLL)
        return None, None, refused

    async def async_ensure_running(self) -> bool:
        """Start the inverter and keep trying. Safe to call from anywhere.

        The one method in this module a driver may call out of band, because it
        is what a shutdown hook and a repair flow both need: the inverter is
        never left stopped, whatever happened to the run that stopped it.

        **Waits on one deadline rather than re-sending on a short one.** An
        inverter takes minutes to boot -- about four for the reference SH10RT
        in daylight, over six in the dark -- and re-sending on a short cycle
        writes into a machine already doing what it was asked, then gives up
        while the state still reads `Starting`.

        So: send once, then watch. `Starting` is progress and resets nothing;
        only a state that is still *stopped* after `RESTART_RESEND_AFTER`
        earns another command, in case the first was lost rather than slow.
        """
        if await self._write(START_WORD_PROBE, START_WORD) is not None:
            _LOGGER.warning("capability test: the start command itself was refused")
        started = self.clock.monotonic()
        last_sent = started
        seen_starting = False
        self._tick(start=True)

        while self.clock.monotonic() - started < RESTART_RUNNING_DEADLINE:
            self._tick()
            word = await self._running_word()
            if is_running(word):
                self.snapshot.stopped_at = None
                return True
            if is_starting(word):
                # Taken and working on it. Never re-send into this.
                seen_starting = True
                last_sent = self.clock.monotonic()
            elif (
                word is not None
                and word in RUNNING_STATES_STOPPED
                and self.clock.monotonic() - last_sent > RESTART_RESEND_AFTER
            ):
                _LOGGER.warning(
                    "capability test: still stopped after %.0fs, sending start again",
                    RESTART_RESEND_AFTER,
                )
                await self._write(START_WORD_PROBE, START_WORD)
                last_sent = self.clock.monotonic()
            await self.clock.sleep(RESTART_POLL)

        _LOGGER.error(
            "capability test: the inverter has not reported a running state "
            "after %.0fs%s",
            RESTART_RUNNING_DEADLINE,
            " -- it was still starting, so it is most likely still booting"
            if seen_starting
            else "",
        )
        self._worst(5)
        return False

    async def _await_generation(self) -> tuple[float | None, int]:
        """Wait until the inverter is producing again, and time it.

        Its own loop rather than another `_await_state`, because the two read
        different components: the running state is in `realtime_input` and the
        DC power is in `fast_input`. Polling one while asking about the other
        reads whatever was last refreshed, which would have timed how long the
        stale value took to be believed.
        """
        started = self.clock.monotonic()
        refused = 0
        self._tick(start=True)
        while self.clock.monotonic() - started < RESTART_GENERATING_DEADLINE:
            self._tick()
            try:
                await self.inverter.component("fast_input").async_update()
            except (ModbusError, TimeoutError, OSError):
                refused += 1
            else:
                power = self._value("total_dc_power")
                if power:
                    return self.clock.monotonic() - started, refused
            await self.clock.sleep(RESTART_POLL)
        return None, refused

    async def _restart(self) -> RestartResult:
        """Stop the inverter, start it again, and time all three transitions.

        See `RestartResult` for why these timings are worth publishing.
        """
        before = dict(self.snapshot.values)
        self.snapshot.stopped_at = self.clock.monotonic()
        if self._on_snapshot is not None:
            await self._on_snapshot(self.snapshot)

        self._step("stopping the inverter; the restart may take some minutes")
        if (failure := await self._write(START_WORD_PROBE, STOP_WORD)) is not None:
            self.snapshot.stopped_at = None
            return RestartResult(
                None, None, None, None, 0, None, SKIPPED, f"the stop {failure}"
            )

        stopped, word, refused = await self._await_state(
            RESTART_STOP_DEADLINE, lambda value: value in RUNNING_STATES_STOPPED
        )
        await self.clock.sleep(RESTART_DWELL)

        self._step("starting the inverter; this may take some minutes")
        running_from = self.clock.monotonic()
        started = await self.async_ensure_running()
        running = self.clock.monotonic() - running_from if started else None
        if not started:
            return RestartResult(
                stopped,
                None,
                None,
                word,
                refused,
                None,
                DROPPED,
                "the inverter did not come back; run --start-only",
            )

        generating, more_refused = await self._await_generation()
        await self._refresh("fast_holding")
        # Compared explicitly against None rather than for truth. Half of these
        # registers legitimately hold zero, and `value or default` treats a
        # restored 0 % as a missing reading -- which reported a perfectly
        # preserved set of settings as lost.
        survived = True
        for name, value in before.items():
            now = self._value(name)
            if now is None:
                continue
            if not math.isclose(float(now), float(value), rel_tol=1e-6, abs_tol=1e-6):
                survived = False
                break
        return RestartResult(
            stopped_after=stopped,
            running_after=running,
            generating_after=generating,
            stop_word_seen=word,
            polls_refused_connection=refused + more_refused,
            settings_survived=survived,
            verdict=CONFIRMED if stopped is not None else INCONCLUSIVE,
            detail=None if stopped is not None else "it never reported a stopped state",
        )
