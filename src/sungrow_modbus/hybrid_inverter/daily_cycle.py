"""When the inverter's day began, seen in its own daily counters.

A value computed from several daily counters wobbles by a few tenths of a kWh,
so its falling proves nothing, and the inverter's clock need not be Home
Assistant's, so midnight proves nothing either. A counter that falls does:
these only ever rise within a day.

Plain arithmetic over (time, counters), like `smoothing` next door: no Home
Assistant and no clock of its own.
"""

from __future__ import annotations

from collections.abc import Sequence

#: A fall of less than this is no fall; the counters step by 0.1 kWh.
_STEP = 0.05
#: A counter that held less than this, in kWh, may stand where it was after
#: the reset, so none is waited for.
_WORTH_WAITING_FOR = 0.5
#: How long, in seconds, the counters have to fall together.
HOLD = 600.0


class DailyCycle:
    """Tell the one update in which a set of daily counters began again.

    The first counter to fall starts a wait for the others, at most `HOLD`
    seconds, in which a value computed from them is neither day's
    (`holding`). One that comes back to what it was had not been reset: a
    misread, and the wait is called off. A fall seen after a gap longer than
    the hold -- a restart of Home Assistant, a night offline -- is a reset at
    once, since a counter may by then have passed where it was.
    """

    def __init__(self, counters: Sequence[float] | None = None) -> None:
        """Initialize, with the counters of an earlier run where there are any."""
        self._known = tuple(counters) if counters is not None else None
        self._seen_at: float | None = None
        self._since: float | None = None

    @property
    def counters(self) -> tuple[float, ...] | None:
        """The counters to compare with: those before the fall, while holding."""
        return self._known

    @property
    def holding(self) -> bool:
        """Whether some counters have fallen and others are waited for."""
        return self._since is not None

    def update(self, now: float, counters: Sequence[float]) -> bool:
        """Feed the counters read at `now`; return whether the day began."""
        current = tuple(counters)
        known, seen_at = self._known, self._seen_at
        self._seen_at = now
        if known is None or len(known) != len(current):
            self._known, self._since = current, None
            return False
        fell = [new < old - _STEP for old, new in zip(known, current, strict=True)]
        if not any(fell):
            self._known, self._since = current, None
            return False
        if self._since is None:
            self._since = now
        after_a_gap = seen_at is None or now - seen_at > HOLD
        waiting = any(
            old > _WORTH_WAITING_FOR and not down
            for old, down in zip(known, fell, strict=True)
        )
        if waiting and not after_a_gap and now - self._since < HOLD:
            return False
        self._known, self._since = current, None
        return True
