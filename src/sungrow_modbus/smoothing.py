"""Values that depend on time as well as on the registers.

The YAML package smooths two things for the dashboard's benefit, and both are
entity_ids people have on dashboards today, so both have to survive the
migration:

* seven `(delay)` binary sensors, which repeat a power-flow bit only once it
  has been true for a minute, so a card does not flicker every time the house
  crosses from importing to exporting;
* one `(filtered)` energy sensor, a five-minute moving average of the daily
  consumption, for the same reason.

Both are plain arithmetic over (time, value) pairs, so they live here rather
than in the entity layer: no Home Assistant, no clock of their own -- the
caller passes the time in, which is also what makes them testable to the
second without waiting one.

`derived.py` next door is stateless, a pure function of the current registers.
These two are not: they remember. That is the whole difference, and the reason
they are a separate module.
"""

from __future__ import annotations

from collections import deque


class DelayOn:
    """Report true only once the input has been true for long enough.

    Mirrors a template binary sensor's `delay_on`: going true is delayed,
    going false is immediate. An input of None -- the register did not answer
    -- reports None and **restarts** the delay, on the reading that "true for
    sixty seconds" means sixty seconds of knowing it was true.
    """

    def __init__(self, seconds: float) -> None:
        """Initialize with the delay in seconds."""
        self.seconds = seconds
        self._true_since: float | None = None

    @property
    def true_since(self) -> float | None:
        """When the input last became true, or None if it is not true."""
        return self._true_since

    def remaining(self, now: float) -> float | None:
        """Seconds until this starts reporting true, or None if never/already.

        What a caller needs to schedule a wake-up with: None means there is
        nothing to wait for, either because the input is not true or because
        the delay has already run out.
        """
        if self._true_since is None:
            return None
        left = self._true_since + self.seconds - now
        return left if left > 0 else None

    def update(self, now: float, value: bool | None) -> bool | None:
        """Feed a reading taken at `now` and return what to report."""
        if value is None:
            self._true_since = None
            return None
        if not value:
            self._true_since = None
            return False
        if self._true_since is None:
            self._true_since = now
        return self.elapsed(now)

    def elapsed(self, now: float) -> bool:
        """Whether the delay has run out, without feeding a new reading.

        The caller re-asks this when the delay expires rather than at the next
        poll. A minute-long delay reported up to one poll interval late is
        close enough for a dashboard and not close enough for an automation.
        """
        if self._true_since is None:
            return False
        return now - self._true_since >= self.seconds


class TimeWeightedAverage:
    """A moving average over a time window, weighted by how long each value held.

    This is Home Assistant's own `time_simple_moving_average`, which is what
    the YAML package asks for and is **not** the mean of the samples: each
    sample's value is held until the next one arrives and the average is of
    that step function, so an inverter that answers irregularly -- which one
    behind a WiNet-S does -- is not thereby given more weight for the samples
    that happened to arrive close together.

    Reproduced from core's `TimeSMAFilter` rather than from its name, down to
    integrating from `now - window` using the last value that fell out of the
    window, so a series that has not changed for ten minutes averages to its
    value and not to a fraction of it.
    """

    def __init__(self, window: float) -> None:
        """Initialize with the window length in seconds."""
        if window <= 0:
            raise ValueError("window must be positive")
        self.window = window
        self._samples: deque[tuple[float, float]] = deque()
        self._last_leak: tuple[float, float] | None = None

    def update(self, now: float, value: float | None) -> float | None:
        """Feed a reading taken at `now` and return the average.

        A reading of None is not a value of zero, so it is dropped rather than
        averaged in -- and the samples already collected are kept, because a
        block that missed one poll is ordinary on this hardware and is no
        reason to throw away four minutes of history.
        """
        if value is None:
            return self.value(now)

        self._leak(now)
        self._samples.append((now, float(value)))
        return self.value(now)

    def value(self, now: float) -> float | None:
        """Return the average as of `now`, without feeding a reading."""
        if not self._samples:
            return None

        total = 0.0
        start = now - self.window
        previous = self._last_leak or self._samples[0]
        for timestamp, sample in self._samples:
            total += (timestamp - start) * previous[1]
            start = timestamp
            previous = (timestamp, sample)
        # The stretch since the newest sample, which core never has to add:
        # it computes the average at the instant a new state arrives, so its
        # `now` *is* the newest timestamp and this term is always zero. Here
        # it is not -- a poll can be missed, and the entity is asked for its
        # value whenever Home Assistant feels like it -- and leaving it out
        # made a single reading of 10 average to 8 sixty seconds later, drifting
        # towards zero while the source sat perfectly still.
        total += (now - start) * previous[1]
        return total / self.window

    def _leak(self, boundary: float) -> None:
        """Drop the samples that have aged out, remembering the last of them."""
        while self._samples and self._samples[0][0] + self.window <= boundary:
            self._last_leak = self._samples.popleft()
