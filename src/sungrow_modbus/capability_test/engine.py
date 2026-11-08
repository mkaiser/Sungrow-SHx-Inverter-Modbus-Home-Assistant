"""The capability test, put together from its phases, and its document."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import logging
from typing import Any

from modbus_connection import ModbusError

from .effects import EffectSteps
from .procedure import (
    BLOCK_SCHEMA,
    CODES,
    DRY_RUN_MEANS,
    PROBES,
    USER_DECLINED,
    EffectResult,
    Guard,
    Options,
    Outcome,
    ProbeResult,
    RestartResult,
    RestoreResult,
)

_LOGGER = logging.getLogger(__name__)


class CapabilityTest(EffectSteps):
    """One run: preflight, readback, effect, restore, and maybe a restart.

    Construct it with a connected `SungrowInverter` whose tiers have been read
    at least once, call `async_run`, and read the `Outcome`. The object holds
    the snapshot for the whole run, which is what makes `async_restore` callable
    on its own after something went wrong.
    """

    # -- the run -------------------------------------------------------------

    def _count_steps(self) -> int:
        """Count this run's progress units. See `planned_steps`."""
        return planned_steps(self.options)

    async def _shielded(self, coro: Awaitable[Any]) -> Any:
        """Await something that must finish even if this run is being cancelled.

        Home Assistant cancels a background task when the entry unloads or the
        instance shuts down, and a restore interrupted halfway is the one
        outcome this module exists to prevent. The inner work runs as its own
        task so a cancellation delivered here does not reach it; this end
        absorbs a bounded number of cancellations while it finishes.
        """
        task = asyncio.ensure_future(coro)
        for _attempt in range(3):
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.done():
                    raise
                _LOGGER.warning("capability test: cancelled, but the restore continues")
        return await task

    async def async_run(self) -> Outcome:
        """Run the whole procedure and put everything back, whatever happens."""
        self._plan_budget()
        self._total = self._count_steps()
        probes: list[ProbeResult] = []
        effects: list[EffectResult] = []
        restores: list[RestoreResult] = []
        restart: RestartResult | None = None

        try:
            await self._preflight()
            if self.options.forced_startup:
                effects = await self._forced_startup_effect()
            elif not self.options.restart_only:
                probes = await self._readback()
                effects = await self._effects()
        except Guard as guard:
            self._worst(guard.code)
            self.conditions["refused"] = str(guard)
            _LOGGER.warning("capability test refused to run: %s", guard)
        except (ModbusError, TimeoutError, OSError) as err:
            self._worst(1)
            self.conditions["failed"] = f"{type(err).__name__}: {err}"
            _LOGGER.warning("capability test stopped: %s", err)
        finally:
            if self.snapshot.values:
                restores = await self._shielded(self.async_restore())

        if self.options.forced_startup:
            # Its own mode: the inverter was asleep, and a restart would
            # measure nothing the check did not.
            pass
        elif (
            self.options.restart
            and self.options.dry_run
            and "refused" not in self.conditions
        ):
            # A dry run sends no stop, so a restart would wait out the whole
            # stop deadline for a state that never comes and then report it.
            self._note("no restart: a dry run sends no stop command")
        elif (
            self.options.restart
            and self.snapshot.values
            and "refused" not in self.conditions
        ):
            restart = await self._restart()
        elif not self.options.restart and "refused" not in self.conditions:
            # Said out loud rather than left as a blank section. "What this run
            # could not establish" is generated from every skip, and a restart
            # that nobody asked for is a skip like any other -- a reader
            # otherwise cannot tell it from one the tool decided against.
            self._note(
                f"no restart: {USER_DECLINED}, so the recovery time on this "
                "model is not in this report"
            )

        if self.snapshot.unreadable:
            self._note(
                "not every control could be read before the run, so "
                f"{len(self.snapshot.unreadable)} of them were never written"
            )
        if self.options.restart_only:
            self._note(
                "only the restart was measured: nothing was written to any control, "
                "so this run establishes nothing about their scales"
            )
        if self.options.simulated:
            self._note(
                "this run was made against a simulator, which stores raw words with "
                "no scale of its own -- no measurement in it is evidence about hardware"
            )
        self.conditions["simulated"] = self.options.simulated
        self.conditions["dry_run"] = self.options.dry_run
        return Outcome(
            code=self.code,
            probes=tuple(probes),
            effects=tuple(effects),
            restores=tuple(restores),
            restart=restart,
            conditions=dict(self.conditions),
            unestablished=tuple(self.unestablished),
        )


def planned_steps(options: Options) -> int:
    """Count the progress units a run will report, before any are spent.

    Counted up front because a bar whose total grows halfway through is worse
    than no bar at all.

    Part of it is necessarily an estimate: how many controls a device turns out
    to have is not known until the preflight has read it. So the count is
    deliberately generous and `_step` clamps the fraction at one, which makes a
    bar that may finish early and never one that overflows.

    A caller sharing one bar between this and something else needs the number
    without building a runner, which is why it is a function.
    """
    # Two opening steps, one per probe, one more for each probe that gets a
    # second point a decade away, and one per behavioural check: forced charge,
    # forced discharge, the charge ceiling and the export limit.
    steps = 2 + len(PROBES) + len(CapabilityTest.TWO_POINT) + 4
    if options.restart:
        steps += 2
    # One more for each timed window the run was given leave to write.
    steps += options.charge_window + options.discharge_window
    # And one for the import limit check.
    steps += options.import_limit
    if options.forced_startup:
        # The mode alone: reading, the snapshot, the check and its two waits.
        return 5
    return steps


def document(outcome: Outcome) -> dict[str, Any]:
    """Return the publishable block, which carries no serial and no host.

    Anonymous by construction rather than by redaction, which is the shape
    `sungrow_diagnosis._block_document` established: what goes in is register numbers,
    the values this run chose, the words that came back and the words that were
    expected. None of that identifies an installation, so there is nothing here
    for a filter to miss.

    The conditions are the exception worth naming: they carry a state of charge
    and a PV reading, which is a household's afternoon. They are already what a
    diagnosis publishes in its readings block, knowingly and with the address
    already gone, and a behavioural verdict cannot be read without them.
    """
    return {
        "schema": BLOCK_SCHEMA,
        "outcome": outcome.code,
        "outcome_means": (
            DRY_RUN_MEANS
            if outcome.conditions.get("dry_run") and outcome.code == 0
            else CODES[outcome.code]
        ),
        "conditions": outcome.conditions,
        "readback": [row._asdict() for row in outcome.probes],
        "effects": [row._asdict() for row in outcome.effects],
        "restored": [row._asdict() for row in outcome.restores],
        "restart": outcome.restart._asdict() if outcome.restart else None,
        "not_established": list(outcome.unestablished),
    }
