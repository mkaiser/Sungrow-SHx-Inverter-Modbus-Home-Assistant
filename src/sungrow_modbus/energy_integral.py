"""Energy from power: the running integral a tracker's energy sensor reports.

No Sungrow register counts energy per MPP tracker: the hybrid's protocol
(V1.1.11) and the SG's (V1.1.58) list each tracker's voltage and current
only. So a tracker's energy is integrated here from its power, voltage times
current, sampled at every poll.

Like `hybrid_inverter.smoothing`, this takes the clock as an argument and
reads none, so an hour of generation tests without waiting an hour.

What the sum is worth: it is the trapezoid between polls, so it is as good
as the polling. Ten seconds against a cloud's minute is close; a WiNet-S
answering with a stale value between real updates turns some of the
trapezoids into rectangles, which shifts energy between polls but adds
little error over a day. Compare the trackers' sum with *Total PV
generation* to see how far off a house is.
"""

from __future__ import annotations

#: Watt-seconds in a kilowatt-hour.
_WS_PER_KWH = 3_600_000.0


class EnergyIntegral:
    """A running total in kWh, fed (time, power) samples.

    **Across a gap nothing is added.** A sample that is None -- the tracker
    did not answer, or the entity was unavailable -- ends the current run,
    and so does a gap longer than `max_gap` seconds, because nobody knows
    what the power did meanwhile. The total resumes from the next two
    samples. Leaving energy out is the safe side for a `total_increasing`
    sensor: invented energy can never be taken back.

    Power below zero counts as zero: a tracker does not consume, and a
    total that fell would read as a meter reset.

    **`signed=True` integrates power below zero too**, for a power by
    energy balance (`Derived.inverter_self_consumption`), whose single
    readings swing either side of the true value. Counting the negatives as
    zero would bias the total upwards by every swing below; so the running
    sum is signed, and what is reported is its highest value so far. The
    report never falls, and it is above the signed sum only by the depth of
    the current dip, which the next minutes above the line make good -- an
    error bounded by one dip, where clamping adds up every one of them.
    """

    def __init__(
        self, total_kwh: float = 0.0, *, max_gap: float, signed: bool = False
    ) -> None:
        """Start from `total_kwh`, the value restored after a restart."""
        self._total = total_kwh
        self._peak = total_kwh
        self.max_gap = max_gap
        self.signed = signed
        self._last: tuple[float, float] | None = None

    @property
    def total_kwh(self) -> float:
        """Energy so far, in kWh: the signed sum's highest value, if signed."""
        return self._peak

    def update(self, now: float, power_w: float | None) -> float:
        """Feed the power read at `now`, in W, and return the total."""
        if power_w is None:
            self._last = None
            return self._peak
        power = power_w if self.signed else max(power_w, 0.0)
        if self._last is not None:
            then, before = self._last
            elapsed = now - then
            if elapsed <= 0:
                # The same moment twice: keep the newer reading, add nothing.
                self._last = (then, power)
                return self._peak
            if elapsed <= self.max_gap:
                self._total += (before + power) / 2 * elapsed / _WS_PER_KWH
                self._peak = max(self._peak, self._total)
        self._last = (now, power)
        return self._peak
