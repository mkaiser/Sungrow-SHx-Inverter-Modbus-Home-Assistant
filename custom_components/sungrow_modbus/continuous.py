"""Continuous capability testing: run again whenever the house allows a missing check.

One run answers only the checks its moment allowed (`ledger` says why), so an
owner who wants every check answered would have to come back at noon, in the
evening and after dark. This does the coming back. While it is on it looks at
the polled readings once a minute, and starts the ordinary run -- part A,
then part B, with its own snapshot and its own restore -- when a check still
missing needs what the house is doing now.

**The switch is the leave, and it ends at a restart.** Turning it on is a
person deciding, once, that runs may start without them at a terminal. It
lasts until they turn it off or Home Assistant restarts or reloads the entry,
and it is never restored on: a reboot never resumes writing by itself. What
each run may do is still the entry's options, exactly as for the button.

Bounded so a forgotten switch cannot become a nuisance: at least `MIN_GAP`
between starts, at most `MAX_RUNS_PER_DAY`, and it switches itself off once
nothing waiting can answer is left.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from sungrow_modbus.capability_test import ledger

if TYPE_CHECKING:
    from .coordinator import SungrowConfigEntry
    from .diagnosis import DiagnosisRunner

_LOGGER = logging.getLogger(__name__)

#: How often the house is looked at. The readings are the coordinators', so
#: this costs no Modbus read of its own.
TICK = timedelta(minutes=1)

#: The least time between two starts. A run pauses polling and writes for
#: minutes; the house, and the link's few sessions, need the quiet after it
#: (wiki: contention, 90 s to recover) and a moment that has actually changed.
MIN_GAP = timedelta(minutes=30)

#: The most runs started in one calendar day, local time.
MAX_RUNS_PER_DAY = 12


class ContinuousCapabilityTest:
    """One entry's scheduler. Off until a person turns it on."""

    def __init__(
        self, hass: HomeAssistant, entry: SungrowConfigEntry, runner: DiagnosisRunner
    ) -> None:
        """Prepare it, off."""
        self.hass = hass
        self.entry = entry
        self.runner = runner
        self._cancel: CALLBACK_TYPE | None = None
        self.last_start: datetime | None = None
        self._day: str | None = None
        self.runs_today = 0
        self.waiting: str = "off"

    @property
    def active(self) -> bool:
        """Whether runs may start on their own."""
        return self._cancel is not None

    @callback
    def async_turn_on(self) -> None:
        """Take the leave, and look at the house straight away."""
        if self._cancel is not None:
            return
        _LOGGER.warning(
            "%s: continuous capability testing is on. Runs that write to the "
            "inverter and put everything back start on their own until it is "
            "switched off or Home Assistant restarts.",
            self.entry.title,
        )
        self._cancel = async_track_time_interval(self.hass, self._async_tick, TICK)
        self._async_tick(dt_util.utcnow())

    @callback
    def async_turn_off(self, why: str = "off") -> None:
        """Give the leave back. A run already going finishes, restore included."""
        if self._cancel is not None:
            self._cancel()
            self._cancel = None
            _LOGGER.info(
                "%s: continuous capability testing stopped: %s", self.entry.title, why
            )
        self.waiting = why
        self.runner.async_notify()

    def _live(self) -> ledger.Live:
        """Return the house now, from what the coordinators last polled."""
        device = self.entry.runtime_data.inverter_coordinator.device

        def value(name: str) -> float | None:
            try:
                found = device.field(name)
            except AttributeError:
                return None
            return None if found is None else float(found)

        return ledger.Live(
            pv=value("total_dc_power"),
            battery=value("battery_power"),
            export=value("export_power_raw"),
            soc=value("battery_level"),
        )

    @callback
    def _async_tick(self, now: datetime) -> None:
        """Start a run when one is allowed and something missing is due."""
        if self.runner.state.running:
            self._say("a run is in progress")
            return
        folded = self.runner.state.capability_test
        waiting = ledger.awaited(folded)
        if not waiting:
            self.async_turn_off("nothing left that a run at another moment can answer")
            return
        day = dt_util.as_local(now).date().isoformat()
        if day != self._day:
            self._day, self.runs_today = day, 0
        if self.runs_today >= MAX_RUNS_PER_DAY:
            self._say(f"{MAX_RUNS_PER_DAY} runs today; again tomorrow")
            return
        if self.last_start is not None and now - self.last_start < MIN_GAP:
            ready_at = dt_util.as_local(self.last_start + MIN_GAP)
            self._say(f"the next run at {ready_at:%H:%M} at the earliest")
            return
        due = ledger.due(folded, self._live())
        if not due:
            self._say(
                "waiting for " + "; ".join(f"{name}: {need}" for name, need in waiting)
            )
            return
        if self.runner.async_start(capability_test=True):
            self.last_start = now
            self.runs_today += 1
            _LOGGER.info(
                "%s: continuous capability testing started run %d today, for %s",
                self.entry.title,
                self.runs_today,
                ", ".join(due),
            )
            self._say("running for " + ", ".join(due))

    @callback
    def _say(self, waiting: str) -> None:
        """Remember what it is waiting for, and let the entities show it."""
        if waiting != self.waiting:
            self.waiting = waiting
            self.runner.async_notify()

    def attributes(self) -> dict[str, Any]:
        """Return what the status sensor shows about this scheduler."""
        return {
            "continuous": self.active,
            "continuous_waiting": self.waiting,
            "continuous_runs_today": self.runs_today,
            "continuous_last_start": (
                self.last_start.isoformat() if self.last_start else None
            ),
        }
