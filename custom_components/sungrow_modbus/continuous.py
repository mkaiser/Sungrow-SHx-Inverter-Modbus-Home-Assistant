"""Continuous capability testing: a run whenever one can still settle something.

One run answers only the checks its moment allowed (`ledger` says why), so an
owner who wants every check answered would have to come back at noon, in the
evening and after dark. This does the coming back. Every minute (`TICK`) it
compares the polled readings with what the checks still missing need, and
starts the ordinary run -- part A then part B, with its own snapshot and its
own restore -- when the inverter is running and one of them is due.

**How long after a run the next may start is what that run was worth.** One
that settled a check is followed after `GAP_USEFUL`: the house is in a state
that answers. One that settled nothing would only repeat itself, so the same
checks wait `INTERVAL`, and `GAP_VAIN` once that happened twice running. A
check that became possible meanwhile, and has not been tried in vain since the
last useful run, does not wait for that: a battery passing through 200 to
800 W is there for minutes. Each check can shorten the wait once, so a house
whose readings flicker cannot start a run every few minutes.

**The switch is the leave, and it ends at a restart.** Turning it on is a
person deciding, once, that runs may start without them at a terminal. It
lasts until they turn it off or Home Assistant restarts or reloads the entry,
and it is never restored on: a reboot never resumes writing by itself. What
each run may do is still the entry's options, exactly as for the button.

Every tick between runs also feeds the polled readings to the plausibility
checks (`sungrow_modbus.capability_test.plausibility`), which need days of
readings rather than a moment; auto repeat stays on while any of them is
still unsettled, and writes nothing for them.

Bounded so a forgotten switch cannot become a nuisance: the gaps above, never
a run while the inverter is not running -- except the forced startup check,
which needs exactly that: in low-SoC Standby, while no kept run has
established it, that mode runs
alone (`_forced_startup_due`) -- at least `QUIET` after the last run ended, and it
switches itself off once nothing waiting can answer is left. And it waits
after the owner changed a control (`write_owner.OWNER_QUIET`), or a managed
wallbox's charging (`OWNER_QUIET_EV`): a run then would read the house still
answering the owner.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from sungrow_modbus.capability_test import is_running, ledger, low_soc_standby
from sungrow_modbus.hybrid_inverter.capabilities import Capability

from .write_owner import (
    EV_CHARGER,
    OWNER_QUIET,
    OWNER_QUIET_EV,
    cluster_busy,
    owner_quiet_until,
)

if TYPE_CHECKING:
    from .coordinator import SungrowConfigEntry
    from .diagnosis import DiagnosisRunner

_LOGGER = logging.getLogger(__name__)

#: How often the house is looked at. The readings are the coordinators', so
#: this costs no Modbus read of its own.
TICK = timedelta(minutes=1)

#: The wait after a run that settled a check: time for the house to be polled
#: again and settle, and no more.
GAP_USEFUL = timedelta(minutes=5)

#: The wait before checks a run tried in vain are tried again, and the length
#: of a wallbox's slot. A run pauses polling and writes for minutes, so a
#: shorter one would leave the house's own readings stale for much of the time.
INTERVAL = timedelta(minutes=30)

#: The same wait from the second vain run in a row on.
GAP_VAIN = timedelta(minutes=60)

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
        #: What was still missing when the last run started; None once it is judged.
        self._missing_before: frozenset[str] | None = None
        #: The checks that run was started for.
        self._attempted: frozenset[str] = frozenset()
        #: What has been tried in vain since the last run that settled something.
        self._tried: frozenset[str] = frozenset()
        self._vain = 0
        self._last_end: datetime | None = None
        #: When the next run may start, unless a check becomes possible before.
        self._ready_at: datetime | None = None
        #: The earlier start a check that became possible allows, while it is due.
        self._early_at: datetime | None = None
        #: The wallbox's own slots, counted from the press: its runs and the
        #: inverter's are counted apart, so neither uses up the other's time.
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
        self.started_at, self.last_start = now, None
        self._missing_before, self._ready_at, self._last_end = None, None, None
        self._early_at = None
        self._attempted = self._tried = frozenset()
        self._vain = 0
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

    @callback
    def async_run_ended(self) -> None:
        """Say what it waits for now, rather than at the next tick.

        Only ever after a run: the quiet that follows one (`QUIET`) keeps this
        tick from starting another.
        """
        self._async_tick(dt_util.utcnow())

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

    def _forced_startup_wanted(self, folded: dict[str, Any] | None) -> bool:
        """Whether auto repeat still has the forced startup check to run here.

        Its own mode, so `ledger.awaited` never lists it: the inverter must
        answer register 13017 and no kept run may have established it. No
        option of its own: a few minutes awake at night, from the grid, with the
        register put back to off, harms nothing the auto repeat switch has not
        already allowed.
        """
        runtime = self.entry.runtime_data
        if runtime.is_string_inverter:
            return False
        if Capability.FORCED_STARTUP not in runtime.capabilities:
            return False
        return ledger.forced_startup_awaited(folded)

    def _forced_startup_due(self) -> bool:
        """Whether the last poll saw the low-SoC standby the check needs."""
        device = self.entry.runtime_data.inverter_coordinator.device

        def value(name: str) -> float | None:
            try:
                found = device.field(name)
            except AttributeError:
                return None
            return None if found is None else float(found)

        word = value("running_state_raw")
        return low_soc_standby(
            None if word is None else int(word),
            value("battery_level"),
            value("battery_min_soc"),
            value("total_dc_power"),
        )

    def _missing(self, folded: dict[str, Any] | None) -> frozenset[str]:
        """Return the names a run could still settle, the forced startup's too."""
        names = {name for name, _need in ledger.awaited(folded)}
        if self._forced_startup_wanted(folded):
            names.add(ledger.FORCED_STARTUP_CHECK)
        return frozenset(names)

    def _judge_last_run(self, now: datetime, folded: dict[str, Any] | None) -> None:
        """Set how long the next run waits, by what the last one settled."""
        if self._missing_before is None:
            return
        settled = self._missing_before - self._missing(folded)
        self._missing_before = None
        self._last_end, self._early_at = now, None
        if settled:
            self._vain, self._tried = 0, frozenset()
            self._ready_at = now + GAP_USEFUL
            return
        self._vain += 1
        self._tried |= self._attempted
        self._ready_at = now + (INTERVAL if self._vain == 1 else GAP_VAIN)

    def _may_start(self, now: datetime, due: list[str]) -> bool:
        """Whether the wait is over, or a check not tried in vain is due.

        Remembers the earlier start such a check allows (`_early_at`), so that
        *Diagnosis: next attempt* names it rather than the end of the wait.
        """
        self._early_at = None
        if self._ready_at is None or now >= self._ready_at:
            return True
        if self._vain == 0 or self._last_end is None or not set(due) - self._tried:
            return False
        self._early_at = self._last_end + GAP_USEFUL
        return now >= self._early_at

    def _note_start(
        self, now: datetime, folded: dict[str, Any] | None, due: list[str]
    ) -> None:
        """Remember what a run was started for, to judge it by when it ends."""
        self.last_start = now
        self._missing_before = self._missing(folded)
        self._attempted = frozenset(due)
        self.runs_started += 1

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
        # The readings' checks are fed by the runner's own timer, at the same
        # cadence, whether or not auto repeat is on: they write nothing, so
        # they are not the leave's to give (`DiagnosisRunner.OBSERVE_EVERY`).
        folded = self.runner.state.capability_test
        self._judge_last_run(now, folded)
        # A wallbox at its own address has no inverter checks to wait for.
        inverter = self.runner.inverter_tests
        waiting = ledger.awaited(folded) if inverter else []
        forced = inverter and self._forced_startup_wanted(folded)
        wallbox_waiting = self.runner.wallbox_awaited()
        if not waiting and not forced and not wallbox_waiting:
            observing = [
                *(self.runner.plausibility.unsettled() if inverter else []),
                *(
                    self.runner.wallbox_unsettled()
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
        if waiting or forced:
            started = self._inverter_tick(now, folded, waiting, forced=forced)
        if not started and wallbox_waiting:
            self._wallbox_tick(now, wallbox_waiting, said=bool(waiting or forced))

    def _start_forced_startup(self, now: datetime) -> bool:
        """Run the forced startup mode; say whether it started."""
        folded = self.runner.state.capability_test
        if not self.runner.async_start(capability_test=True, forced_startup=True):
            return False
        self._note_start(now, folded, [ledger.FORCED_STARTUP_CHECK])
        _LOGGER.info(
            "%s: continuous capability testing started run %d, for %s",
            self.entry.title,
            self.runs_started,
            ledger.FORCED_STARTUP_CHECK,
        )
        self._say(f"running for {ledger.FORCED_STARTUP_CHECK}")
        return True

    def _quiet(self, now: datetime) -> bool:
        """Whether the last run ended too recently for another to start."""
        finished = self.runner.state.finished
        return finished is not None and now - finished < QUIET

    def _inverter_tick(
        self,
        now: datetime,
        folded: dict[str, Any] | None,
        waiting: list[tuple[str, str]],
        *,
        forced: bool = False,
    ) -> bool:
        """Start an inverter run when one is allowed and due; say whether it did.

        `forced` says the forced startup check is still wanted: in low-SoC
        standby that mode runs instead of waiting for the inverter.
        """
        if forced:
            waiting = [
                *waiting,
                (ledger.FORCED_STARTUP_CHECK, ledger.FORCED_STARTUP_NEEDS),
            ]
        asleep = self._inverter_running() is False
        if not asleep:
            due = ledger.due(folded, self.live())
        elif forced and self._forced_startup_due():
            due = [ledger.FORCED_STARTUP_CHECK]
        else:
            due = []
        if not self._may_start(now, due):
            assert self._ready_at is not None
            at = self._early_at or self._ready_at
            self._say(f"the next run at {dt_util.as_local(at):%H:%M}")
            return False
        if self._quiet(now):
            self._say("a moment of quiet after the last run")
            return False
        held = owner_quiet_until(self.entry.runtime_data, OWNER_QUIET, now=now)
        if held is not None:
            self._say(
                "the owner changed a control; the next run not before "
                f"{dt_util.as_local(held):%H:%M}"
            )
            return False
        if (other := cluster_busy(self.hass, self.entry)) is not None:
            self._say(f"waiting for {other.title}'s test: the same cluster")
            return False
        if asleep:
            if due:
                return self._start_forced_startup(now)
            self._say(
                "waiting for the inverter to run"
                if len(waiting) > int(forced)
                else "waiting for "
                + "; ".join(f"{name}: {need}" for name, need in waiting)
            )
            return False
        if not due:
            self._say(
                "waiting for " + "; ".join(f"{name}: {need}" for name, need in waiting)
            )
            return False
        if self.runner.async_start(capability_test=True):
            self._note_start(now, folded, due)
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
        held = self._owner_charging_until(now)
        if held is not None:
            if not said:
                self._say(
                    "the owner changed the wallbox's charging; the next wallbox "
                    f"run not before {dt_util.as_local(held):%H:%M}"
                )
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

    def _owner_charging_until(self, now: datetime) -> datetime | None:
        """Return when a wallbox run may start after the owner set its charging.

        The owner sets it at the inverter that manages the wallbox, on that
        inverter's entry: its EV charger controls.
        """
        from .wallbox_capability_test import managing_entry

        inverter = managing_entry(self.hass, self.entry)
        if inverter is None:
            return None
        return owner_quiet_until(
            inverter.runtime_data, OWNER_QUIET_EV, (EV_CHARGER,), now=now
        )

    @callback
    def _say(self, waiting: str) -> None:
        """Remember what it is waiting for, and let the entities show it."""
        if waiting != self.waiting:
            self.waiting = waiting
            self.runner.async_notify()

    def next_start(self, now: datetime) -> datetime | None:
        """Return the earliest a run may start on its own, when time decides it.

        The end of the wait the last run left, which a check that becomes
        possible shortens to the earlier start it allows while it is due; None
        when it is off, a run is in flight or not yet judged, or what decides
        is the house rather than the clock.
        """
        if (
            not self.active
            or self.runner.state.running
            or self.started_at is None
            or self._missing_before is not None
        ):
            return None
        if not self.runner.inverter_tests:
            if (
                self._last_wallbox_slot is not None
                and self._wallbox_slot(now) <= self._last_wallbox_slot
            ):
                return self._next_wallbox_start()
            return None
        if self._ready_at is not None and now < self._ready_at:
            if self._early_at is not None and now < self._early_at:
                return self._early_at
            return self._ready_at
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
