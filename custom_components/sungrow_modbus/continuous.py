"""Continuous capability testing: a run every half hour from the press of Start.

One run answers only the checks its moment allowed (`ledger` says why), so an
owner who wants every check answered would have to come back at noon, in the
evening and after dark. This does the coming back. The press of *Diagnosis:
start* opens the first half-hour slot, and every `INTERVAL` after it opens the
next. In each slot at most one run starts -- the ordinary run, part A then
part B, with its own snapshot and its own restore -- at the first minute
(`TICK`) the inverter is running and a check still missing needs what the
house is doing now. A slot in which that never happens passes without a run.

**The switch is the leave, and it ends at a restart.** Turning it on is a
person deciding, once, that runs may start without them at a terminal. It
lasts until they turn it off or Home Assistant restarts or reloads the entry,
and it is never restored on: a reboot never resumes writing by itself. What
each run may do is still the entry's options, exactly as for the button.

Every tick between runs also feeds the polled readings to the plausibility
checks (`sungrow_modbus.capability_test.plausibility`), which need days of
readings rather than a moment; auto repeat stays on while any of them is
still unsettled, and writes nothing for them.

Bounded so a forgotten switch cannot become a nuisance: one run per slot, never
one while the inverter is not running (low-SoC Standby at night would refuse
it anyway, after part A), at least `QUIET` after the last run ended, and it
switches itself off once nothing waiting can answer is left.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from sungrow_modbus.capability_test import is_running, ledger

if TYPE_CHECKING:
    from .coordinator import SungrowConfigEntry
    from .diagnosis import DiagnosisRunner

_LOGGER = logging.getLogger(__name__)

#: How often the house is looked at. The readings are the coordinators', so
#: this costs no Modbus read of its own.
TICK = timedelta(minutes=1)

#: The length of one slot, counted from the press of Start. A run pauses
#: polling and writes for minutes, so a shorter one would leave the house's
#: own readings stale for much of the time.
INTERVAL = timedelta(minutes=30)

#: The slot of a wallbox at its own address, with no inverter beside it. Its
#: runs need a car charging, and a session lasts an hour or two: half-hour slots
#: would leave most of it unused. Not shorter, because every run interrupts the
#: charge (stop and start, a pause under 6 A, a phase switch, 75 s unread), and
#: a car stopped every few minutes may stop resuming. Only checks still missing
#: run, each at most `ledger.MAX_ATTEMPTS` times, so it cannot run for ever.
WALLBOX_ALONE_INTERVAL = timedelta(minutes=15)

#: The least time from the end of one run to the start of the next, when a
#: late run in one slot ends near the next slot's start: the link's few
#: sessions need it (wiki: contention, 90 s to recover).
QUIET = timedelta(minutes=2)


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
        self.started_at: datetime | None = None
        self.last_start: datetime | None = None
        self._last_slot: int | None = None
        #: The wallbox's own slots: its runs and the inverter's are counted apart,
        #: so a run of one never uses up the other's half hour.
        self._last_wallbox_slot: int | None = None
        self.runs_started = 0
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
            "device and put everything back start on their own until it is "
            "switched off or Home Assistant restarts.",
            self.entry.title,
        )
        # Auto repeat always leaves out what is established; the switch says
        # so, and keeps saying it for the single runs after it.
        self.runner.skip_established = True
        now = dt_util.utcnow()
        self.started_at, self.last_start, self._last_slot = now, None, None
        self._last_wallbox_slot = None
        self.runs_started = 0
        self._cancel = async_track_time_interval(self.hass, self._async_tick, TICK)
        self._async_tick(now)
        self.runner.async_notify()

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

    def live(self) -> ledger.Live:
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

    def _inverter_running(self) -> bool | None:
        """Whether the last poll saw the inverter running; None if not polled."""
        device = self.entry.runtime_data.inverter_coordinator.device
        try:
            word = device.field("running_state_raw")
        except AttributeError:
            return None
        return None if word is None else is_running(int(word))

    def _slot(self, now: datetime) -> int:
        """Return the number of the slot `now` falls in, 0 from the press."""
        assert self.started_at is not None
        return max(0, int((now - self.started_at) / INTERVAL))

    def _wallbox_slot(self, now: datetime) -> int:
        """Return the number of the wallbox's slot `now` falls in."""
        assert self.started_at is not None
        return max(0, int((now - self.started_at) / self.runner.wallbox_interval))

    def _next_wallbox_start(self) -> datetime:
        """Return the start of the wallbox's next slot, after the one it ran in."""
        assert self.started_at is not None and self._last_wallbox_slot is not None
        return self.started_at + (
            (self._last_wallbox_slot + 1) * self.runner.wallbox_interval
        )

    @callback
    def _async_tick(self, now: datetime) -> None:
        """Start a run when one is allowed and something missing is due."""
        if self.runner.state.running:
            self._say("a run is in progress")
            return
        # The readings' checks are fed every tick between runs: they cost no
        # Modbus read and need days, not moments.
        self.runner.async_observe(now)
        folded = self.runner.state.capability_test
        # A wallbox at its own address has no inverter checks to wait for.
        inverter = self.runner.inverter_tests
        waiting = ledger.awaited(folded) if inverter else []
        wallbox_waiting = self.runner.wallbox_awaited()
        if not waiting and not wallbox_waiting:
            observing = [
                *(self.runner.plausibility.unsettled() if inverter else []),
                *(
                    self.runner.wallbox_plausibility.unsettled()
                    if self.runner.wallbox_present
                    else []
                ),
            ]
            if observing:
                self._say(
                    "watching the readings for "
                    + "; ".join(f"{name}: {need}" for name, need in observing)
                )
                return
            self.async_turn_off("nothing left that a run at another moment can answer")
            return
        started = False
        if waiting:
            started = self._inverter_tick(now, folded, waiting)
        if not started and wallbox_waiting:
            self._wallbox_tick(now, wallbox_waiting, said=bool(waiting))

    def _quiet(self, now: datetime) -> bool:
        """Whether the last run ended too recently for another to start."""
        finished = self.runner.state.finished
        return finished is not None and now - finished < QUIET

    def _inverter_tick(
        self,
        now: datetime,
        folded: dict[str, Any] | None,
        waiting: list[tuple[str, str]],
    ) -> bool:
        """Start an inverter run when one is allowed and due; say whether it did."""
        if self._last_slot is not None and self._slot(now) <= self._last_slot:
            ready_at = self.next_start(now)
            if ready_at is not None:
                self._say(f"the next run at {dt_util.as_local(ready_at):%H:%M}")
            return False
        if self._quiet(now):
            self._say("a moment of quiet after the last run")
            return False
        if self._inverter_running() is False:
            self._say("waiting for the inverter to run")
            return False
        due = ledger.due(folded, self.live())
        if not due:
            self._say(
                "waiting for " + "; ".join(f"{name}: {need}" for name, need in waiting)
            )
            return False
        if self.runner.async_start(capability_test=True):
            self.last_start = now
            self._last_slot = self._slot(now)
            self.runs_started += 1
            _LOGGER.info(
                "%s: continuous capability testing started run %d, for %s",
                self.entry.title,
                self.runs_started,
                ", ".join(due),
            )
            self._say("running for " + ", ".join(due))
            return True
        return False

    def _wallbox_tick(
        self, now: datetime, waiting: list[tuple[str, str]], *, said: bool
    ) -> None:
        """Start a wallbox run when its slot is free and a car is there to judge.

        `said` is whether the inverter's tick already told the entities what
        it waits for: the wallbox then speaks only when it starts, so the one
        line does not flip between the two every minute.
        """
        slot = self._wallbox_slot(now)
        if self._last_wallbox_slot is not None and slot <= self._last_wallbox_slot:
            if not said:
                ready = self._next_wallbox_start()
                self._say(f"the next wallbox run at {dt_util.as_local(ready):%H:%M}")
            return
        if self._quiet(now):
            if not said:
                self._say("a moment of quiet after the last run")
            return
        due = self.runner.wallbox_due()
        if not due:
            if not said:
                self._say(
                    "waiting for the wallbox: "
                    + "; ".join(f"{name}: {need}" for name, need in waiting)
                )
            return
        if self.runner.async_start_wallbox():
            self.last_start = now
            self._last_wallbox_slot = slot
            self.runs_started += 1
            _LOGGER.info(
                "%s: continuous capability testing started wallbox run %d, for %s",
                self.entry.title,
                self.runs_started,
                ", ".join(due),
            )
            self._say("running the wallbox for " + ", ".join(due))

    @callback
    def _say(self, waiting: str) -> None:
        """Remember what it is waiting for, and let the entities show it."""
        if waiting != self.waiting:
            self.waiting = waiting
            self.runner.async_notify()

    def next_start(self, now: datetime) -> datetime | None:
        """Return the earliest a run may start on its own, when time decides it.

        The start of the next slot once this slot has had its run, and None
        when it is off, a run is in flight, or what decides is the house
        rather than the clock.
        """
        if not self.active or self.runner.state.running or self.started_at is None:
            return None
        if not self.runner.inverter_tests:
            if (
                self._last_wallbox_slot is not None
                and self._wallbox_slot(now) <= self._last_wallbox_slot
            ):
                return self._next_wallbox_start()
            return None
        if self._last_slot is not None and self._slot(now) <= self._last_slot:
            return self.started_at + (self._last_slot + 1) * INTERVAL
        return None

    def attributes(self) -> dict[str, Any]:
        """Return what the status sensor shows about this scheduler."""
        return {
            "continuous": self.active,
            "continuous_waiting": self.waiting,
            "continuous_runs_started": self.runs_started,
            "continuous_last_start": (
                self.last_start.isoformat() if self.last_start else None
            ),
        }
