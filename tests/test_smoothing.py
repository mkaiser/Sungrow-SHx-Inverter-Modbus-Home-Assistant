"""The two time-dependent values, checked against the clock they are given.

Both reproduce a Home Assistant behaviour the YAML package relies on, so the
tests are about matching *that*, not about being reasonable: a delay that goes
false immediately, and a moving average weighted by how long each value held
rather than by how many samples arrived.
"""

from __future__ import annotations

import pytest

from sungrow_modbus.smoothing import DelayOn, TimeWeightedAverage


def test_a_delay_reports_false_until_the_input_has_held() -> None:
    delay = DelayOn(60)

    assert delay.update(0.0, True) is False
    assert delay.update(30.0, True) is False
    assert delay.update(59.9, True) is False
    assert delay.update(60.0, True) is True
    assert delay.update(600.0, True) is True


def test_a_delay_goes_false_at_once() -> None:
    # Asymmetric on purpose: this is what `delay_on` means, and the seven
    # entities exist to stop a card flickering, not to hold it on.
    delay = DelayOn(60)
    delay.update(0.0, True)
    delay.update(100.0, True)

    assert delay.update(101.0, False) is False
    # And the count restarts rather than resuming: true from 102, so 162.
    assert delay.update(102.0, True) is False
    assert delay.update(161.9, True) is False
    assert delay.update(162.0, True) is True


def test_a_delay_restarts_when_the_reading_is_missing() -> None:
    delay = DelayOn(60)
    delay.update(0.0, True)

    assert delay.update(30.0, None) is None
    assert delay.update(31.0, True) is False
    assert delay.update(90.0, True) is False, "resumed instead of restarting"
    assert delay.update(91.0, True) is True


def test_a_delay_says_how_long_is_left() -> None:
    delay = DelayOn(60)

    assert delay.remaining(0.0) is None, "nothing to wait for yet"
    delay.update(10.0, True)
    assert delay.remaining(10.0) == 60
    assert delay.remaining(40.0) == 30
    # Already true, so there is nothing to schedule.
    assert delay.remaining(70.0) is None
    assert delay.remaining(1000.0) is None


def test_one_sample_averages_to_itself() -> None:
    average = TimeWeightedAverage(300)

    assert average.update(0.0, 4.0) == 4.0


def test_nothing_read_yet_is_not_zero() -> None:
    average = TimeWeightedAverage(300)

    assert average.update(0.0, None) is None
    assert average.value(0.0) is None


def test_a_missed_reading_keeps_the_samples_already_taken() -> None:
    # A block missing one poll is ordinary on this hardware and is no reason
    # to throw away four minutes of history.
    average = TimeWeightedAverage(300)
    average.update(0.0, 10.0)

    assert average.update(60.0, None) == pytest.approx(10.0)
    assert average.update(120.0, 10.0) == pytest.approx(10.0)


def test_the_average_is_weighted_by_time_not_by_sample_count() -> None:
    """Four samples of 0 in ten seconds must not outvote 290 seconds of 10.

    This is the difference between `time_simple_moving_average` and a plain
    mean, and getting it wrong would be invisible: the number would still look
    like an average.
    """
    average = TimeWeightedAverage(300)
    average.update(0.0, 10.0)
    for offset in (291.0, 294.0, 297.0, 300.0):
        result = average.update(offset, 0.0)

    # 10 held from 0 to 291, then 0 for the remaining 9 seconds.
    assert result == pytest.approx(291 * 10 / 300)
    # A plain mean of the five samples would be 2.0.
    assert result > 5.0


def test_a_value_that_has_not_changed_averages_to_itself() -> None:
    """The subtle half of core's algorithm.

    Integration starts at `now - window` from the last sample that fell *out*
    of the window, not from the oldest one still in it. Without that, a series
    nobody has updated for ten minutes averages to a fraction of its value and
    the sensor drifts towards zero while the source sits still.
    """
    average = TimeWeightedAverage(300)
    average.update(0.0, 7.0)

    assert average.update(600.0, 7.0) == pytest.approx(7.0)
    assert average.update(1200.0, 7.0) == pytest.approx(7.0)


def test_samples_older_than_the_window_stop_counting() -> None:
    average = TimeWeightedAverage(300)
    average.update(0.0, 100.0)
    # 100 holds until 300, then 0 for a full window.
    average.update(300.0, 0.0)

    assert average.update(600.0, 0.0) == pytest.approx(0.0)


def test_a_window_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        TimeWeightedAverage(0)


def test_the_average_agrees_with_home_assistants_own_filter() -> None:
    """The claim is that this *is* `time_simple_moving_average`.

    So it is checked against core's implementation rather than against a
    description of it, on a sequence built to hit the parts that are easy to
    get wrong: samples much closer together than the window, a gap longer than
    the window, a value that stops changing, and a leak.

    Core's filter is fed each sample at the moment it arrives, which is the
    only condition under which the two are required to agree -- it has no
    notion of being asked for a value later, which is the one behaviour added
    here.
    """
    from datetime import datetime, timedelta

    from homeassistant.components.filter.sensor import FilterState, TimeSMAFilter
    from homeassistant.core import State

    window = 300
    theirs = TimeSMAFilter(
        window_size=timedelta(seconds=window),
        entity="sensor.x",
        type="time_simple_moving_average",
    )
    mine = TimeWeightedAverage(window)

    epoch = datetime(2026, 9, 7, 12, 0, 0)
    offsets = [0, 5, 10, 11, 12, 200, 299, 300, 301, 700, 1000, 1000.5]
    values = [10.0, 10.0, 0.0, 0.0, 4.0, 4.0, 4.0, 9.0, 9.0, 9.0, 1.0, 1.0]

    for offset, value in zip(offsets, values, strict=True):
        state = State("sensor.x", str(value))
        state.last_updated = epoch + timedelta(seconds=offset)
        expected = theirs._filter_state(FilterState(state)).state

        assert mine.update(float(offset), value) == pytest.approx(expected), offset
