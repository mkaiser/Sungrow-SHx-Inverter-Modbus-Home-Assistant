"""The control test, checked without an inverter and without a sky.

Two kinds of test live here and they defend different things.

The **static** ones compare the procedure's hand-typed specification column
against the register map, and the procedure's plan against
`scripts/writes.py`. They need no hardware and no hardware is what makes them
valuable: they would have caught a factor-10 error in the map at the moment
somebody committed it, months before a hardware run could have found it.

The **behavioural** ones drive the engine against a stub that lies in a chosen
way -- a device that stores ten times what it was given, a library whose factor
has been tampered with -- and require the procedure to notice and to say which
side is at fault. A detector nobody has watched detect is not a detector.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
import sys
from typing import Any

from modbus_connection.mock import MockModbusUnit
import pytest

from sungrow_modbus import SungrowInverter
from sungrow_modbus.control_test import (
    CLAMPED,
    CONFIRMED,
    DECADE_OUT_OF_RANGE,
    DEVICE,
    EFFECT_FLOOR_W,
    EFFECT_SCALED,
    EMS_MODE,
    EXPORT_MODE,
    FORCE_DISCHARGE,
    FORCED_CMD,
    FORCED_EFFECT_W,
    INCONCLUSIVE,
    LIBRARY,
    MATCH,
    MIN_EXPORT_W,
    NO_EFFECT,
    NOT_PROBED,
    OFF_BY,
    ONE_SIDED_DOWN,
    PROBES,
    REFUSED,
    SCALED,
    SEVERITY,
    START_WORD_PROBE,
    TWO_SIDED,
    ControlTest,
    Options,
    Probe,
    Sample,
    Snapshot,
    _admissible,
    choose_probe,
    classify_ratio,
    mad,
    median,
    restore_order,
    soc_pair_order,
    visibility,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import writes

#: Protocol address of register 13087, the feed-in limitation switch.
EXPORT_MODE_ADDRESS = 13086

ALL_PROBES = (*PROBES, EMS_MODE, FORCED_CMD, EXPORT_MODE, START_WORD_PROBE)


# -- the static half ---------------------------------------------------------


@pytest.mark.parametrize("probe", ALL_PROBES, ids=lambda probe: probe.field)
def test_the_specification_column_agrees_with_the_register_map(
    probe: Probe, sungrow_unit: MockModbusUnit
) -> None:
    """Every hand-typed scale equals the map's, and every address lines up.

    This is the regression guard the whole module is built around, and the only
    one that does not need an inverter. `spec_units_per_count` is typed from
    V1.1.11 and is deliberately never read from `field.scale`; here is where the
    two are made to meet. A factor-10 error introduced into `registers.py` fails
    this test on the commit that introduces it.

    Addresses are protocol addresses, one below the register number printed in
    Sungrow's document, which is the other arithmetic slip this catches.
    """
    inverter = SungrowInverter(sungrow_unit)
    resolved = inverter.component(probe.component).resolved_fields[probe.field]
    assert resolved.address == probe.spec_register - 1
    assert float(resolved.field.scale) == float(probe.spec_units_per_count)
    assert resolved.field.writable is True


@pytest.mark.parametrize("probe", ALL_PROBES, ids=lambda probe: probe.field)
def test_every_probe_is_one_register(
    probe: Probe, sungrow_unit: MockModbusUnit
) -> None:
    """Leg B reads a single word, so nothing here may span two.

    A wider field would need its word order applied to reassemble it, and
    applying the map's word order would put the map back inside the leg that
    exists to be independent of it.
    """
    inverter = SungrowInverter(sungrow_unit)
    assert inverter.component(probe.component).resolved_fields[probe.field].count == 1


def test_every_writable_register_is_either_probed_or_excused() -> None:
    """A new control cannot quietly escape the procedure.

    `scripts/writes.py` is where writability is declared. Anything it names has
    to be either something this test writes or something this test has written
    down a reason for not writing -- and adding a control to the integration
    fails this suite until somebody decides which of the two it is.
    """
    probed = {probe.field for probe in PROBES}
    assert probed | set(NOT_PROBED) >= writes.WRITABLE_FIELDS
    assert probed <= writes.WRITABLE_FIELDS
    assert not probed & set(NOT_PROBED)
    for field, reason in NOT_PROBED.items():
        assert field in writes.WRITABLE_FIELDS
        assert len(reason) > 20, f"{field} needs a reason, not a label"


def test_the_start_stop_register_is_not_in_the_writable_table() -> None:
    """It is hand-written in `components.py`, and stays outside the walk.

    The readback phase must never touch it: a procedure that included the one
    register that turns the inverter off among the settings it writes and
    restores would stop an inverter as a side effect of checking a scale.
    """
    assert START_WORD_PROBE.field not in writes.WRITABLE_FIELDS
    assert START_WORD_PROBE not in PROBES


@pytest.mark.parametrize("probe", PROBES, ids=lambda probe: probe.field)
def test_the_bounds_are_the_ones_the_entities_use(probe: Probe) -> None:
    """The plan's bounds equal `scripts/writes.py`'s, field by field.

    The duplication is deliberate -- the library cannot import a file from
    `scripts/` -- and this is the assertion that makes it safe, the same trade
    already made for `IDENTIFY_UNITS` and `fingerprint.PROBES`.
    """
    row = next(entry for entry in writes.NUMBERS if entry["field"] == probe.field)
    assert probe.minimum == row.get("minimum", 0)
    assert probe.step == row.get("step", 1)
    assert probe.minimum_field == row.get("minimum_field")
    assert probe.maximum_field == row.get("maximum_field")
    assert probe.maximum_from_battery == row.get("maximum_from_battery", False)
    if not (probe.maximum_from_battery or probe.maximum_field):
        assert probe.maximum == row.get("maximum", 0)


@pytest.mark.parametrize("probe", PROBES, ids=lambda probe: probe.field)
def test_the_capability_matches_the_write_table(probe: Probe) -> None:
    """The procedure gates a control exactly as the entity for it is gated.

    Two tables again, kept equal by a test, for the reason the library cannot
    import `scripts/writes.py`. The direction that matters is this one: if the
    entity for a register is not created on some hardware because a capability
    is absent, the control test must not go writing to that register there
    either.

    This is also the assertion that would have caught the 2026-09-18 bug from
    the other side -- `writes.py` said `BATTERY` for the start-power pair while
    this table said `BATTERY_START_POWER`, and nothing compared them.
    """
    row = next(entry for entry in writes.NUMBERS if entry["field"] == probe.field)
    declared = row.get("requires")
    assert (probe.requires.name if probe.requires else None) == declared


def test_the_enumerations_only_offer_values_the_write_table_knows() -> None:
    """Never write an enum the integration would refuse.

    EMS mode skips 1, so the codes are not a range and nothing may treat them
    as one. A value outside the select's own option map is a value nobody has
    evidence about.
    """
    by_key = {select["key"]: select for select in writes.SELECTS}
    ems = {option["value"] for option in by_key["ems_mode"]["options"]}
    forced = {
        option["value"]
        for option in by_key["battery_forced_charge_discharge"]["options"]
    }
    assert set(EMS_MODE.exact) == ems
    assert 1 not in EMS_MODE.exact
    assert set(FORCED_CMD.exact) == forced


def test_the_severity_order_ranks_a_finding_below_a_run_that_never_happened() -> None:
    """A decade error is a successful run; an unrestored register is not.

    The ordering is the one piece of this module a reader is most likely to
    assume, and assuming it backwards would make the worst outcome look like
    the mildest.
    """
    assert SEVERITY.index(4) < SEVERITY.index(1)
    assert SEVERITY.index(5) == len(SEVERITY) - 1


# -- picking a value that can carry evidence ---------------------------------


def test_zero_is_never_a_probe_value() -> None:
    """Ten times zero is zero, and so is a tenth of it.

    The one value on which a decade error is perfectly invisible, which makes
    it the worst possible thing to write to a register you are testing.
    """
    assert not _admissible(0, 0, 100, 1, 1, None)


def test_a_value_the_register_already_holds_proves_nothing() -> None:
    """A device that ignored the write would read back correct."""
    assert not _admissible(30, 0, 100, 1, 1, current=30)
    assert _admissible(30, 0, 100, 1, 1, current=40)


def test_a_probe_off_the_step_would_look_like_a_finding() -> None:
    """On a scale-10 field, an odd value comes back rounded.

    `encode` rounds half to even, so 205 W lands at 200 and 215 W at 220. Either
    would read as a raw word one away from the expected one -- which is exactly
    what a real off-by-one finding looks like, and is not one.
    """
    assert not _admissible(205, 0, 5000, 100, 10, None)
    assert _admissible(700, 0, 5000, 100, 10, None)


def test_the_banker_rounding_edge_is_real_and_is_why(
    sungrow_unit: MockModbusUnit,
) -> None:
    """Assert the rounding rather than spending an inverter minute on it."""
    inverter = SungrowInverter(sungrow_unit)
    field = (
        inverter.component("fast_holding")
        .resolved_fields["battery_max_charge_power"]
        .field
    )
    assert field.encode(705) == [70]
    assert field.encode(715) == [72]
    assert field.encode(700) == [70]


def test_a_probe_is_chosen_where_a_decade_error_either_way_would_show() -> None:
    """The window is where the evidence is.

    Inside `[10*lo, hi/10]` both a ten-times-too-large and a ten-times-too-small
    value stay within what the device accepts, so a scale error comes back as a
    *wrong number* rather than as an exception -- and exception 0x04 cannot be
    read as evidence about scale, because it is also what a legitimately
    out-of-range value returns.
    """
    probe = next(row for row in PROBES if row.field == "battery_max_charge_power")
    value, seen = choose_probe(probe, 10, 5000, None)
    assert value is not None
    assert seen == TWO_SIDED
    assert 10 * value <= 5000
    assert value / 10 >= 10


def test_a_range_with_no_room_for_a_decade_says_so() -> None:
    """The maximum state of charge cannot show a decade error at all.

    Its range is 50 to 100, so ten times any admissible value is above the
    ceiling and a tenth of it is below the floor. Reported rather than passed
    over, because "matched" on that row means less than it does on the others.
    """
    probe = next(row for row in PROBES if row.field == "battery_max_soc")
    _value, seen = choose_probe(probe, 50, 100, None)
    assert seen == DECADE_OUT_OF_RANGE
    assert visibility(95, 50, 100) == DECADE_OUT_OF_RANGE
    assert visibility(6, 0, 50) == ONE_SIDED_DOWN


def test_no_two_controls_get_the_same_probe_value() -> None:
    """So that writing to the wrong address is visible as itself.

    Reading 800 back out of the export register when 600 was written there names
    the mix-up. Give two registers the same probe and the same mix-up reports as
    two unrelated failures.
    """
    taken: list[float] = []
    for probe in PROBES:
        value, _seen = choose_probe(probe, 10, 5000, None, taken)
        if value is not None:
            assert value not in taken
            taken.append(value)


# -- telling a decade from a rounding ----------------------------------------


@pytest.mark.parametrize(
    ("observed", "expected", "verdict", "ratio"),
    [
        (70, 7, SCALED, 10.0),
        (1, 7, SCALED, 0.1),
        (7, 70, SCALED, 0.1),
        (80, 800, SCALED, 0.1),
        (8000, 800, SCALED, 10.0),
        (600, 600, MATCH, 1.0),
        (601, 600, OFF_BY, None),
        (9, 7, OFF_BY, None),
    ],
)
def test_classify_ratio(
    observed: int, expected: int, verdict: str, ratio: float | None
) -> None:
    """Quantised decades first, because these registers hold small integers.

    A decade below an expected 7 is **1**, not 0.7: the register cannot hold a
    fraction, so the device rounded. A purely multiplicative test sees 0.143 and
    a logarithm sees -0.845, neither anywhere near a decade, and the clearest
    finding in the set gets reported as "off by something else".
    """
    got_verdict, got_ratio = classify_ratio(observed, expected)
    assert got_verdict == verdict
    if ratio is not None:
        assert got_ratio == pytest.approx(ratio)


# -- statistics over a sky that will not sit still ---------------------------


def test_the_median_survives_what_a_mean_does_not() -> None:
    """And assert the mean would have differed, so the choice is documented.

    One maximum-power-point spike in a window of ten is normal. The median moves
    by nothing; the mean moves by four hundred watts and reports it as an
    effect.
    """
    quiet = [1000.0] * 9 + [5000.0]
    assert median(quiet) == 1000.0
    assert sum(quiet) / len(quiet) == pytest.approx(1400.0)
    assert mad([1000.0] * 10) == 0.0
    assert mad([900.0, 1000.0, 1100.0]) == 100.0


# -- restore ordering --------------------------------------------------------


def test_the_forced_command_is_always_put_back_first() -> None:
    """It is the only register in the set that makes the inverter act.

    Restoring a power while the inverter is still forcing a charge at the old
    one is a worse intermediate state than any the reversal would otherwise
    produce.
    """
    order = restore_order(
        ["battery_min_soc", FORCED_CMD.field, EMS_MODE.field, EXPORT_MODE.field]
    )
    assert order[0] == FORCED_CMD.field
    assert order[1] == EMS_MODE.field
    assert order[-1] == EXPORT_MODE.field


async def test_a_register_already_holding_its_value_is_restored_without_writing(
    full_unit: MockModbusUnit,
) -> None:
    """Read first: a restore is a statement about where the register *is*.

    The first hardware run reported the export power limit as **not restored**
    -- the one verdict that means a house is left changed -- while the register
    held its original value throughout. The inverter had silently ignored the
    probe write, so there was nothing to undo, and then refused the write of the
    original, so the restore called itself failed.
    """
    from modbus_connection import ModbusError

    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = ControlTest(inverter, clock=FakeClock())
    await run._preflight()
    # Refuses every write, and does not need to take one.
    full_unit.fail_write(13073, ModbusError("this register is not writable now"))

    restores = await run.async_restore()

    row = next(row for row in restores if row.field == "export_power_limit")
    assert row.restored
    assert row.attempts == 0
    assert run.code != 5


@pytest.mark.parametrize(
    ("current_min", "target_min", "expected_first"),
    [(5.0, 20.0, "battery_max_soc"), (20.0, 5.0, "battery_min_soc")],
)
def test_the_soc_pair_never_crosses(
    current_min: float, target_min: float, expected_first: str
) -> None:
    """The interlock has to hold at every intermediate step, not just at the end.

    The inverter enforces `min < max`. Raise the floor before the ceiling has
    moved and one of the two writes is refused, leaving the house carrying
    exactly one of this run's values.
    """
    order = soc_pair_order(current_min, 80.0, target_min, 95.0)
    assert order[0] == expected_first


# -- does the detector detect ------------------------------------------------


class FakeClock:
    """A clock that agrees to anything, so a ten-minute budget costs no time."""

    def __init__(self) -> None:
        """Start at an arbitrary origin."""
        self.now = 0.0

    def monotonic(self) -> float:
        """Return the current fake time."""
        return self.now

    async def sleep(self, seconds: float) -> None:
        """Advance instead of waiting."""
        self.now += seconds


CHARGE_POWER = "battery_max_charge_power"
CHARGE_ADDRESS = 33046


def _runner(unit: MockModbusUnit, **options: Any) -> ControlTest:
    """Build a runner with a snapshot already in place for the charge power."""
    inverter = SungrowInverter(unit)
    run = ControlTest(inverter, options=Options(**options), clock=FakeClock())
    run.snapshot = Snapshot(
        taken_at=0.0,
        values={CHARGE_POWER: 5000.0},
        raw={CHARGE_POWER: 500},
        bounds={CHARGE_POWER: [10.0, 10000.0]},
    )
    return run


def _probe() -> Probe:
    return next(row for row in PROBES if row.field == CHARGE_POWER)


async def test_a_device_that_stores_ten_times_is_caught_and_blamed(
    sungrow_unit: MockModbusUnit,
) -> None:
    """The firmware-side decade error, which leg B is the only way to see.

    Here the library encodes correctly -- 700 W at 10 W per count is 70 -- and
    the device stores 700. The readback through the library would report 7000 W,
    but the point is that the *register* holds ten times what the specification
    says it should, and that the run says the device is the one doing it.
    """

    def exaggerate(event: Any) -> None:
        if event.address == CHARGE_ADDRESS:
            sungrow_unit.holding[event.address] = event.values[0] * 10

    sungrow_unit.on_write(exaggerate)
    run = _runner(sungrow_unit)

    result = await run._probe_once(_probe(), 700.0, (10.0, 10000.0))

    assert result.verdict == SCALED
    assert result.ratio == pytest.approx(10.0)
    assert result.expected_raw == 70
    assert result.raw_word == 700
    assert result.implicates == DEVICE
    assert run.code == 4


async def test_a_library_whose_factor_is_wrong_is_caught_and_blamed(
    sungrow_unit: MockModbusUnit, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The map-side decade error, which a readback through the map cannot see.

    `encode` and `decode` share the factor, so with the factor tampered with the
    library still reads back exactly what it wrote -- 700 W in, 700 W out, and
    every existing test still passes. Only the raw word betrays it, and only
    because the specification column refused to be derived from the map.
    """
    inverter = SungrowInverter(sungrow_unit)
    field = inverter.component("fast_holding").resolved_fields[CHARGE_POWER].field
    monkeypatch.setattr(field, "scale", 1.0)
    run = _runner(sungrow_unit)

    result = await run._probe_once(_probe(), 700.0, (10.0, 10000.0))

    assert result.verdict == SCALED
    assert result.ratio == pytest.approx(10.0)
    assert result.raw_word == 700
    assert result.expected_raw == 70
    assert result.implicates == LIBRARY
    assert result.library_read == 700  # and this is why one leg is not enough


async def test_a_clamped_register_is_not_reported_as_a_match(
    sungrow_unit: MockModbusUnit,
) -> None:
    """Two points, because one cannot tell a right scale from a clamp.

    A device that answers the same word whatever it is given reads back
    correctly on any single probe that happens to land on the clamp. The slope
    between two points is zero, which no scale error can imitate.
    """

    def clamp(event: Any) -> None:
        if event.address == CHARGE_ADDRESS:
            sungrow_unit.holding[event.address] = 70

    sungrow_unit.on_write(clamp)
    run = _runner(sungrow_unit)
    probe = _probe()

    first = await run._probe_once(probe, 700.0, (10.0, 10000.0))
    assert first.verdict == MATCH  # a single point is fooled

    withslope = await run._slope(probe, first, (10.0, 10000.0), [700.0])
    assert withslope.verdict == CLAMPED
    assert withslope.slope == pytest.approx(0.0)


async def test_a_correct_device_matches_on_both_legs(
    sungrow_unit: MockModbusUnit,
) -> None:
    """The case the others are measured against."""
    run = _runner(sungrow_unit)
    probe = _probe()

    result = await run._probe_once(probe, 700.0, (10.0, 10000.0))

    assert result.verdict == MATCH
    assert result.raw_word == result.expected_raw == 70
    assert result.library_read == 700
    withslope = await run._slope(probe, result, (10.0, 10000.0), [700.0])
    assert withslope.verdict == MATCH
    assert withslope.slope == pytest.approx(0.1)
    assert run.code == 0


# -- the behavioural leg, over a sky that will not sit still -----------------


def _scripted(run: ControlTest, *windows: list[float]) -> None:
    """Make `_sample` return a fixed series, so no sky and no inverter is needed."""
    values = [value for window in windows for value in window]
    ordered = iter(values)

    async def sample() -> Any:
        from sungrow_modbus.control_test import Sample

        value = next(ordered, values[-1])
        return Sample(
            at=run.clock.monotonic(),
            pv=3000.0,
            battery=value,
            export=value,
            load=0.0,
            soc=50.0,
        )

    run._sample = sample  # type: ignore[method-assign]


async def _bracket(run: ControlTest, commanded: float | None, *, setpoint: bool) -> Any:
    async def apply() -> None:
        return None

    async def undo() -> None:
        return None

    return await run._bracket(
        "check",
        lambda sample: sample.battery,
        "battery power",
        commanded,
        apply,
        undo,
        setpoint=setpoint,
    )


async def test_a_clean_step_is_confirmed(sungrow_unit: MockModbusUnit) -> None:
    """The case everything else is measured against."""
    run = _runner(sungrow_unit)
    _scripted(run, [200.0] * 10, [800.0] * 10, [200.0] * 10)

    result = await _bracket(run, 800.0, setpoint=True)

    assert result.verdict == CONFIRMED
    assert result.before == 200.0
    assert result.during == 800.0


async def test_a_drifting_sky_is_inconclusive_and_never_a_failure(
    sungrow_unit: MockModbusUnit,
) -> None:
    """The whole answer to a fluctuating input, in one assertion.

    Before and after are two estimates of the same undisturbed house. When they
    disagree the run has no opinion: a cloud that arrived mid-measurement is a
    reason to claim nothing, and blaming the inverter for it would put a
    weather report into a bug tracker.
    """
    run = _runner(sungrow_unit)
    _scripted(run, [200.0] * 10, [800.0] * 10, [2000.0] * 10)

    result = await _bracket(run, 800.0, setpoint=True)

    assert result.verdict == INCONCLUSIVE
    assert result.drift == pytest.approx(1800.0)
    assert "drift" in (result.detail or "")
    assert run.code == 3


async def test_an_input_already_unstable_is_rejected_before_the_write(
    sungrow_unit: MockModbusUnit,
) -> None:
    """Rejecting cheaply beats rejecting after the write.

    A window this noisy cannot carry a verdict however carefully the rest is
    measured, and finding that out first costs one window and no change to
    anybody's house.
    """
    run = _runner(sungrow_unit)
    _scripted(run, [200.0, 4000.0] * 5, [800.0] * 10, [200.0] * 10)

    result = await _bracket(run, 800.0, setpoint=True)

    assert result.verdict == INCONCLUSIVE
    assert result.detail == "the input was already unstable"
    assert result.during is None  # nothing was written


async def test_a_device_acting_on_a_decade_is_the_finding_only_this_leg_can_make(
    sungrow_unit: MockModbusUnit,
) -> None:
    """Commanded 800 W, drew 80.

    Leg B cannot see this: the register holds exactly what the specification
    says it should. Only watching the inverter obey can tell that its idea of
    what the number means is a decade away from everyone else's.
    """
    run = _runner(sungrow_unit)
    _scripted(run, [4000.0] * 10, [80.0] * 10, [4000.0] * 10)

    result = await _bracket(run, 800.0, setpoint=True)

    assert result.verdict == EFFECT_SCALED
    assert result.ratio == pytest.approx(0.1)
    assert run.code == 4


async def test_the_right_magnitude_in_the_wrong_direction_is_named(
    sungrow_unit: MockModbusUnit,
) -> None:
    """A sign error reported as a sign error, not as a confusing failure."""
    run = _runner(sungrow_unit)
    _scripted(run, [0.0] * 10, [-800.0] * 10, [0.0] * 10)

    result = await _bracket(run, 800.0, setpoint=True)

    assert result.verdict == "right magnitude, wrong direction"
    assert run.code == 4


async def test_nothing_happening_is_reported_as_nothing_happening(
    sungrow_unit: MockModbusUnit,
) -> None:
    """Distinct from inconclusive: the house held still and did not react."""
    run = _runner(sungrow_unit)
    _scripted(run, [1000.0] * 10, [1000.0] * 10, [1000.0] * 10)

    result = await _bracket(run, None, setpoint=False)

    assert result.verdict == NO_EFFECT


async def test_one_spike_does_not_move_the_verdict(
    sungrow_unit: MockModbusUnit,
) -> None:
    """The median's whole job, asserted where a mean would have failed.

    The during window here averages 1120 W around a true 800 W. A mean-based
    check would call an obedient inverter disobedient, on one sample.
    """
    spiky = [800.0] * 9 + [4000.0]
    assert sum(spiky) / len(spiky) == pytest.approx(1120.0)
    run = _runner(sungrow_unit)
    _scripted(run, [200.0] * 10, spiky, [200.0] * 10)

    result = await _bracket(run, 800.0, setpoint=True)

    assert result.verdict == CONFIRMED


# -- a whole run -------------------------------------------------------------


def _same(after: dict[int, Any], before: dict[int, Any]) -> bool:
    """Whether every register holds what it held, unseeded ones included.

    The mock answers 0 for an address nothing has written, so a register the run
    restored to 0 gains a key without changing a value. Comparing the dicts
    would call that a difference; comparing what a read returns does not.
    """
    return all(
        after.get(address, 0) == before.get(address, 0)
        for address in set(after) | set(before)
    )


@pytest.fixture
def full_unit(sungrow_unit: MockModbusUnit) -> MockModbusUnit:
    """Return an inverter that states its own limits, so every bound resolves.

    The shared fixture leaves registers 5622, 5623 and 5628 unseeded, which is a
    faithful picture of a device that does not answer them -- and a run against
    it is worth having, because it exercises the path where the procedure
    declines to guess. This one is the other case.
    """
    sungrow_unit.input[5621] = 0  # export limit minimum, 10 W per count
    sungrow_unit.input[5622] = 1000  # export limit maximum: 10 kW
    sungrow_unit.input[5627] = 50  # BDC rated power, 100 W per count: 5 kW
    return sungrow_unit


async def test_a_whole_run_writes_checks_and_puts_everything_back(
    full_unit: MockModbusUnit,
) -> None:
    """The procedure end to end against a device that answers correctly.

    The assertion that matters is the last one: every control the run touched is
    holding exactly the word it held before, and the run says so itself rather
    than the test having to check the registers behind its back.
    """
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    before = dict(full_unit.holding)
    run = ControlTest(inverter, clock=FakeClock())

    outcome = await run.async_run()

    assert {row.field for row in outcome.probes} >= {
        probe.field for probe in PROBES[:7]
    }
    assert all(
        row.verdict == MATCH for row in outcome.probes if row.written is not None
    )
    assert not outcome.findings
    assert outcome.not_restored == ()
    assert _same(full_unit.holding, before)


async def test_the_forced_power_is_the_stated_constant(
    full_unit: MockModbusUnit,
) -> None:
    """What the behavioural checks command is now legible from one place.

    It used to be derived from the battery's own ceiling so that ten times the
    commanded power stayed inside the pack's rating. That property is given up
    deliberately -- 10 x 1250 W is more than a small pack is rated for, and the
    inverter refuses such a value rather than attempting it -- in exchange for a
    number that can be read here instead of reconstructed from three functions.

    The derivation is what produced a 5800 W forced charge against a 5883 W pack
    at a real house, because it borrowed `choose_probe`, which escapes the
    decade window once earlier probes have spent it.
    """
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = ControlTest(inverter, clock=FakeClock())
    await run._preflight()

    power = run._forced_power()

    assert power == FORCED_EFFECT_W
    assert run.snapshot.battery_ceiling == 5000


async def test_the_commanded_power_is_clamped_to_what_the_pack_can_take(
    full_unit: MockModbusUnit,
) -> None:
    """A constant must not become a value the register would refuse.

    The register's own bounds are read live, so a pack too small for 1250 W gets
    what it can take rather than an exception 0x04 -- which would be reported as
    a refusal and say nothing about anything.
    """
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = ControlTest(inverter, clock=FakeClock())
    await run._preflight()
    run.snapshot.bounds["battery_forced_charge_discharge_power"] = [0.0, 800.0]

    power = run._forced_power()

    assert power == 800.0, "clamped to the ceiling, not refused by it"


async def test_a_crowded_window_no_longer_changes_what_is_commanded(
    full_unit: MockModbusUnit,
) -> None:
    """The regression the constant closes, kept as the reason it is a constant.

    `_forced_power` borrowed `choose_probe`, which falls back from the decade
    window to the whole range once the window's values are taken. Correct for a
    readback, where the number is only written and read; wrong here, where it is
    commanded. By the time this runs, the readback phase has spent most of the
    window -- and at a house with a 5883 W ceiling that resolved a 5800 W forced
    charge, at night, which is 5.8 kW bought from the grid.

    A stated constant cannot depend on what earlier probes took, and this test
    is what says so.
    """
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = ControlTest(inverter, clock=FakeClock())
    await run._preflight()

    before = run._forced_power()
    run._taken.extend([400.0, 300.0, 200.0, 600.0, 60.0, 80.0, 100.0, 500.0])
    after = run._forced_power()

    assert before == after == FORCED_EFFECT_W


async def test_a_dry_run_writes_nothing_at_all(full_unit: MockModbusUnit) -> None:
    """The first thing anybody should run, and the reason it is safe to.

    It resolves every bound and picks every probe value, so the whole procedure
    can be reviewed before any of it is at risk.
    """
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    before = dict(full_unit.holding)
    run = ControlTest(inverter, options=Options(dry_run=True), clock=FakeClock())

    outcome = await run.async_run()

    assert _same(full_unit.holding, before)
    assert all(row.written is not None for row in outcome.probes)


async def test_a_stopped_inverter_is_refused_before_anything_is_written(
    full_unit: MockModbusUnit,
) -> None:
    """A guard is the only protection a button press has, so it runs first."""
    full_unit.input[12999] = 0x0008  # standby
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    before = dict(full_unit.holding)
    run = ControlTest(inverter, clock=FakeClock())

    outcome = await run.async_run()

    assert outcome.code == 2
    assert "Standby" in run.conditions["refused"]
    assert _same(full_unit.holding, before)


async def test_a_dark_inverter_is_refused_unless_the_run_was_told_to_expect_it(
    full_unit: MockModbusUnit,
) -> None:
    """Half the procedure is meaningless at night; the other half is not."""
    full_unit.input[5016] = [0, 0]
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = ControlTest(inverter, clock=FakeClock())

    assert (await run.async_run()).code == 2

    allowed = ControlTest(inverter, options=Options(allow_dark=True), clock=FakeClock())
    assert (await allowed.async_run()).code != 2


async def test_a_state_of_charge_probe_never_climbs_towards_the_battery(
    full_unit: MockModbusUnit,
) -> None:
    """The one guard with a bill attached.

    A minimum state of charge raised above where the battery actually sits is an
    instruction to charge, and a hybrid allowed to charge from the grid obeys it
    with somebody's money.
    """
    full_unit.input[13022] = 40  # 4.0 %, so 3 % is no longer a safe probe
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = ControlTest(inverter, clock=FakeClock())

    outcome = await run.async_run()

    minimum = next(row for row in outcome.probes if row.field == "battery_min_soc")
    assert minimum.written is None
    assert minimum.verdict == "not run"


# -- the restore is the part that is never optional --------------------------


async def test_the_restore_runs_even_when_the_budget_is_gone(
    full_unit: MockModbusUnit,
) -> None:
    """A run that ran out of time must not be a house left changed.

    Every deadline in the module is consulted by a phase; none is consulted by
    the restore. This is the assertion that keeps it that way -- and it also
    pins that running out of time is recorded as a skip rather than reported as
    a pass.
    """
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    before = dict(full_unit.holding)
    run = ControlTest(inverter, options=Options(run_budget=0.001), clock=FakeClock())

    outcome = await run.async_run()

    assert any(row.verdict == "not run" for row in outcome.probes)
    assert outcome.restores
    assert outcome.not_restored == ()
    assert _same(full_unit.holding, before)
    assert outcome.code == 3


async def test_one_register_that_will_not_go_back_does_not_take_the_rest_with_it(
    full_unit: MockModbusUnit,
) -> None:
    """The 2026-09-07 lesson, made into a test.

    That run lost its link during a restore and left one register at 210 W. The
    answer is not to try harder on the stubborn one: it is that its failure must
    not stop the others going back, and that the run must end in the code that
    means the house is still carrying something.
    """
    from modbus_connection import ModbusError

    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = ControlTest(inverter, clock=FakeClock())
    await run._preflight()
    # The register really is holding a probe value now, and really will not take
    # the write that would undo it. Both halves matter: a restore that finds the
    # original value already in place is finished without writing, so a test that
    # only failed the write would pass without exercising anything.
    full_unit.holding[13099] = 7
    full_unit.fail_write(13099, ModbusError("the link went away"))

    restores = await run.async_restore()

    stubborn = next(
        row for row in restores if row.field == "battery_reserved_soc_for_backup"
    )
    assert not stubborn.restored
    assert stubborn.attempts == 5
    assert full_unit.holding[13099] == 7  # still wrong, and the run says so
    assert all(row.restored for row in restores if row.field != stubborn.field)
    assert run.code == 5


async def test_a_cancelled_run_still_puts_everything_back(
    full_unit: MockModbusUnit, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Home Assistant cancels a background task on unload and on shutdown.

    A restore interrupted halfway is the one outcome this module exists to
    prevent, so the cancellation has to pass through the restore rather than
    around it.
    """
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    before = dict(full_unit.holding)
    run = ControlTest(inverter, clock=FakeClock())

    async def cancel_midway() -> list[Any]:
        raise asyncio.CancelledError

    monkeypatch.setattr(run, "_readback", cancel_midway)

    with pytest.raises(asyncio.CancelledError):
        await run.async_run()

    assert _same(full_unit.holding, before)


# -- the restart -------------------------------------------------------------


@pytest.fixture
def restartable(full_unit: MockModbusUnit) -> MockModbusUnit:
    """Return a device that stops and starts when register 13000 is written.

    The holding side of 13000 is Start/Stop and the input side of the same
    address is the running state -- two tables, two address spaces, one number.
    A mock that did not mirror one onto the other would let the restart phase
    pass without ever proving it can tell a stopped inverter from a hung link.
    """

    def obey(event: Any) -> None:
        if event.address != 12999:
            return
        word = event.values[0]
        full_unit.input[12999] = 0x0008 if word == 0xCE else 0x0000

    full_unit.on_write(obey)
    return full_unit


async def test_a_restart_is_measured_and_the_inverter_comes_back(
    restartable: MockModbusUnit,
) -> None:
    """Three timings this project has never had, and one guarantee it needs."""
    inverter = SungrowInverter(restartable)
    await inverter.async_update()
    run = ControlTest(inverter, options=Options(restart=True), clock=FakeClock())

    outcome = await run.async_run()

    assert outcome.restart is not None
    assert outcome.restart.stopped_after is not None
    assert outcome.restart.running_after is not None
    assert outcome.restart.settings_survived is True
    assert restartable.input[12999] == 0x0000
    assert run.snapshot.stopped_at is None


async def test_the_inverter_is_never_left_stopped(restartable: MockModbusUnit) -> None:
    """`async_ensure_running` is what a shutdown hook and a repair flow both call.

    It is deliberately callable out of band, because the run that stopped the
    inverter is exactly the thing that may not be around to start it again.
    """
    inverter = SungrowInverter(restartable)
    await inverter.async_update()
    run = ControlTest(inverter, clock=FakeClock())
    restartable.input[12999] = 0x0008
    run.snapshot.stopped_at = 1.0

    assert await run.async_ensure_running() is True
    assert restartable.input[12999] == 0x0000
    assert run.snapshot.stopped_at is None


async def test_a_run_without_consent_never_writes_the_stop_register(
    restartable: MockModbusUnit,
) -> None:
    """The one register that turns an inverter off stays out of the walk."""
    inverter = SungrowInverter(restartable)
    await inverter.async_update()
    run = ControlTest(inverter, clock=FakeClock())

    outcome = await run.async_run()

    assert outcome.restart is None
    assert restartable.holding.get(12999) is None


# -- the charge ceiling, which stops a charge rather than commanding one -----


async def test_lowering_the_ceiling_under_a_charging_battery_stops_it(
    full_unit: MockModbusUnit,
) -> None:
    """The only safe behavioural test of a state-of-charge limit.

    Safe because of its direction: it stops a charge. The mirror-image test on
    `battery_min_soc` would raise the floor above where the battery sits, which
    on a hybrid permitted to charge from the grid is an instruction to buy
    electricity -- so the guards refuse it and it is deliberately not written.
    """
    full_unit.input[13022] = 800  # 80.0 %, with room above the register's 50 % floor
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    await run._preflight()
    _scripted(run, [-2000.0] * 11, [0.0] * 10, [-2000.0] * 10)

    results = await run._soc_ceiling_effect()

    assert [row.verdict for row in results] == [CONFIRMED]
    assert results[0].commanded == pytest.approx(78.0)


async def test_a_battery_that_is_not_charging_has_nothing_to_stop(
    full_unit: MockModbusUnit,
) -> None:
    """Self-skips and says so, rather than reporting a confident nothing."""
    full_unit.input[13022] = 800
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    await run._preflight()
    _scripted(run, [0.0] * 40)

    assert await run._soc_ceiling_effect() == []
    assert any("was not charging" in note for note in run.unestablished)


async def test_the_ceiling_check_refuses_a_battery_too_low_to_test(
    full_unit: MockModbusUnit,
) -> None:
    """`battery_max_soc` cannot go below 50 %, so there has to be room.

    Without this the target would be clamped up to the bound and the check
    would set the ceiling *above* the state of charge -- measuring nothing
    while looking like it measured something.
    """
    full_unit.input[13022] = 520  # 52.0 %
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    await run._preflight()

    assert await run._soc_ceiling_effect() == []
    assert any("too low" in note for note in run.unestablished)


async def test_a_charge_that_carries_on_is_reported_as_no_effect(
    full_unit: MockModbusUnit,
) -> None:
    """The finding this check exists to be able to make."""
    full_unit.input[13022] = 800
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    await run._preflight()
    _scripted(run, [-2000.0] * 11, [-2000.0] * 10, [-2000.0] * 10)

    results = await run._soc_ceiling_effect()

    assert results[0].verdict == NO_EFFECT
    assert "carried on" in results[0].detail
    assert run.code == 3


async def test_a_refused_write_records_which_exception_came_back(
    full_unit: MockModbusUnit,
) -> None:
    """A refusal is not a finding until you know which exception it was.

    A `battery_min_soc` write was refused on 2026-09-15 and accepted on
    2026-09-19, and the first reading had been written up as a firmware limit.
    It could not be checked afterwards because the run recorded only that the
    write was refused -- not whether the device had said *out of range*, which
    is a fact about the register, or *busy*, which on a link the YAML package
    was also polling is a fact about the afternoon.
    """
    from modbus_connection import ModbusError

    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    full_unit.fail_write(CHARGE_ADDRESS, ModbusError("exception 0x04: out of range"))

    result = await run._probe_once(_probe(), 700.0, (10.0, 10000.0))

    assert result.verdict == REFUSED
    assert "0x04" in result.detail
    assert "out of range" in run.refusals[CHARGE_POWER]


def test_a_commanded_state_of_charge_is_not_reported_as_watts() -> None:
    """The charge ceiling commands a percentage; every other check commands power.

    Reported as "62.4 W" on the check's first hardware run -- a state of charge
    wearing the wrong unit, in a table otherwise full of real watts, so nothing
    about it looked wrong. The unit travels with the value now.
    """
    ceiling = next(
        row
        for row in inspect.getsource(ControlTest._soc_ceiling_effect).splitlines()
        if "commanded_unit" in row
    )
    assert '"%"' in ceiling

    # And every other bracket keeps the default.
    for source in (
        inspect.getsource(ControlTest._effects),
        inspect.getsource(ControlTest._export_effect),
    ):
        assert "commanded_unit" not in source


async def test_a_refused_behavioural_write_names_the_exception_too(
    full_unit: MockModbusUnit,
) -> None:
    """The same gap as the readback path had, one path over.

    The export limit's first refusal on hardware came back as "the write
    refused with an exception", which settles nothing: 0x04 would say the value
    is out of range and 0x06 would say the inverter is busy, and only the first
    is a fact about the register. Fixing the readback path and not this one
    left exactly the question the fix existed to answer.
    """
    from modbus_connection import ModbusError

    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    _scripted(run, [3000.0] * 12)
    full_unit.fail_write(CHARGE_ADDRESS, ModbusError("exception 0x04: out of range"))
    probe = _probe()

    async def apply() -> str | None:
        return await run._write(probe, 700.0)

    async def undo() -> None:
        return None

    result = await run._bracket(
        "capped",
        run._charging,
        "battery charge power",
        700.0,
        apply,
        undo,
        setpoint=False,
    )

    assert "0x04" in result.detail
    assert "out of range" in result.detail


async def test_the_reported_exception_is_the_one_from_the_failed_write(
    full_unit: MockModbusUnit,
) -> None:
    """Not the one from putting the old value back afterwards.

    `undo` writes too, and on a register that refuses writes it fails as
    readily as `apply` does. Reading the refusal after calling it reported the
    restore's exception while claiming to describe the attempt -- measured on
    hardware, where the export limit's refusal came back naming the *original*
    value rather than the cap under test.
    """
    from modbus_connection import ModbusError

    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    _scripted(run, [3000.0] * 12)
    probe = _probe()

    async def apply() -> str | None:
        full_unit.fail_write(CHARGE_ADDRESS, ModbusError("0x04 while setting the cap"))
        return await run._write(probe, 700.0)

    async def undo() -> None:
        full_unit.fail_write(CHARGE_ADDRESS, ModbusError("0x04 while putting it back"))
        await run._write(probe, 5000.0)

    result = await run._bracket(
        "capped",
        run._charging,
        "battery charge power",
        700.0,
        apply,
        undo,
        setpoint=False,
    )

    assert "setting the cap" in result.detail
    assert "putting it back" not in result.detail


async def test_restart_only_writes_no_control(full_unit: MockModbusUnit) -> None:
    """Timing a reboot does not need nine register writes first.

    A house lending its inverter for the one measurement this project still
    lacks should not have to accept the other twenty as the price -- and doing
    fewer writes before deliberately stopping somebody's inverter is the safer
    order regardless.
    """

    def obey(event: Any) -> None:
        if event.address == 12999:
            full_unit.input[12999] = 0x0008 if event.values[0] == 0xCE else 0x0000

    full_unit.on_write(obey)
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    before = dict(full_unit.holding)
    run = ControlTest(
        inverter,
        options=Options(restart=True, restart_only=True),
        clock=FakeClock(),
    )

    outcome = await run.async_run()

    assert outcome.probes == ()
    assert outcome.effects == ()
    assert outcome.restart is not None
    assert outcome.restart.running_after is not None
    # Every control untouched; only the start/stop register was written.
    assert _same(
        {a: v for a, v in full_unit.holding.items() if a != 12999},
        {a: v for a, v in before.items() if a != 12999},
    )
    assert any("only the restart" in note for note in outcome.unestablished)


async def test_a_slowly_booting_inverter_is_waited_for_not_shouted_at(
    full_unit: MockModbusUnit,
) -> None:
    """`Starting` is progress, and the first version could not see it.

    0x0020 contains neither "stop" nor "running", so it fell between both sets:
    the wait could not tell a booting inverter from a silent one. Measured on
    the reference SH10RT, which sat in it for minutes while the procedure
    re-sent the start command ten times, gave up inside 180 seconds, and told
    its owner to start the inverter by hand. It was already starting.
    """
    sends: list[int] = []

    def obey(event: Any) -> None:
        if event.address == 12999:
            sends.append(event.values[0])

    full_unit.on_write(obey)
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)

    # Starting for a long time -- far longer than the old per-attempt
    # allowance -- and then running, the way the reference inverter behaved.
    polls = iter([0x0020] * 90 + [0x0040])

    async def booting() -> int:
        return next(polls, 0x0040)

    run._running_word = booting  # type: ignore[method-assign]

    assert await run.async_ensure_running() is True

    # One start command, not ten: `Starting` must never provoke another.
    assert sends.count(0xCF) == 1


def test_the_running_deadline_outlasts_a_measured_boot() -> None:
    """Four minutes measured; 180 seconds was the guess that broke.

    The cost of waiting too long is a slow diagnostic. The cost of waiting too
    little is telling somebody their inverter is dead while it boots.
    """
    from sungrow_modbus.control_test import RESTART_RUNNING_DEADLINE

    assert RESTART_RUNNING_DEADLINE > 240


def test_starting_is_neither_running_nor_stopped() -> None:
    """The gap the state fell into, named so it cannot reopen."""
    from sungrow_modbus.control_test import (
        RUNNING_STATES_STOPPED,
        is_running,
        is_starting,
    )

    assert is_starting(0x0020)
    assert not is_running(0x0020)
    assert 0x0020 not in RUNNING_STATES_STOPPED
    # And the two real states stay unambiguous.
    assert is_running(0x0040) and not is_starting(0x0040)
    assert not is_running(0x0008) and not is_starting(0x0008)


# -- making the house export, rather than waiting for it --------------------


async def test_a_house_that_is_not_exporting_is_made_to(
    full_unit: MockModbusUnit,
) -> None:
    """The lever that turns a lucky-afternoon check into one that runs.

    A battery soaks up the surplus while the sun is up and there is none after
    dark, so most houses never export on their own -- which left a register
    carrying a real factor-10 error measurable only when the weather obliged.
    Discharging more than the house is using sends the difference to the grid
    by definition.
    """
    full_unit.input[13022] = 800  # 80 %, well clear of the floor
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    await run._preflight()
    sample = Sample(at=0.0, pv=0.0, battery=0.0, export=0.0, load=400.0, soc=80.0)

    commanded = await run._force_export(sample)

    assert commanded is not None
    # House load plus enough to clear the threshold a cap must bind against.
    assert commanded > 400 + MIN_EXPORT_W
    assert run.snapshot.values["battery_forced_charge_discharge_cmd_raw"] is not None


async def test_it_refuses_to_spend_a_battery_that_has_nothing_to_spend(
    full_unit: MockModbusUnit,
) -> None:
    """Discharging somebody's battery to make a test condition has a cost.

    Small, but not nothing -- so it is only reached when the house is not
    exporting anyway, and never below the floor its owner set.
    """
    full_unit.input[13022] = 120  # 12.0 % state of charge
    full_unit.holding[13058] = 100  # battery_min_soc = 10.0 %, the owner's floor
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    await run._preflight()
    sample = Sample(at=0.0, pv=0.0, battery=0.0, export=0.0, load=400.0, soc=12.0)

    assert await run._force_export(sample) is None
    assert any("nothing to spend" in note for note in run.unestablished)


async def test_it_refuses_a_discharge_the_battery_cannot_deliver(
    full_unit: MockModbusUnit,
) -> None:
    """A house using more than the pack is rated for cannot be made to export.

    The refusal is stated as the arithmetic rather than as "too big", because
    the interesting case is the near miss: a pack that could cover the house but
    not the house *plus* enough export for a cap to bind against. The note names
    all three figures so a reader can see which one was short.
    """
    full_unit.input[13022] = 800
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    await run._preflight()
    huge = Sample(at=0.0, pv=0.0, battery=0.0, export=0.0, load=99_000.0, soc=80.0)

    assert await run._force_export(huge) is None
    assert any("where a cap needs" in note for note in run.unestablished)


async def test_a_clamped_discharge_is_a_yes_and_a_decade_is_still_a_no(
    full_unit: MockModbusUnit,
) -> None:
    """The pack saying "not quite that much" must not abandon the check.

    Measured at bar12: 3158 W asked, 3150 W accepted, and the whole export
    limit check was dropped over 8 W. The ceiling is read once at preflight and
    the pack's real limit drifts under it -- the same house read 10000 W in the
    afternoon and 3200 W at 99.8 % that night -- so a clamp is the normal case
    near a full battery, not an anomaly.

    The second half is the part that matters: the tolerance must not be able to
    swallow the error the whole procedure exists to find. A decade short is
    about 90 % short, and is refused.
    """
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)
    await run._preflight()
    address = 13051  # register 13052

    def clamp_to(word: int) -> None:
        def hook(event: Any) -> None:
            if event.address == address:
                full_unit.holding[address] = word

        full_unit.on_write(hook)

    # A pack that gives 3150 of the 3158 asked for.
    clamp_to(3150)
    assert await run._forced(FORCE_DISCHARGE, 3158.0, allow_clamp=True) is None
    assert run.accepted_forced_w == 3150.0
    assert any("clamped" in note for note in run.unestablished)

    # A decade short is not a clamp, and is refused even when clamps are allowed.
    clamp_to(316)
    assert await run._forced(FORCE_DISCHARGE, 3158.0, allow_clamp=True) is not None


async def test_the_discharge_is_released_even_when_the_check_fails(
    full_unit: MockModbusUnit,
) -> None:
    """A forced discharge left running would be the worst thing here.

    It is held across all three windows on purpose -- released between them,
    the "after" reading would measure the discharge stopping rather than the
    limit lifting -- so the release has to be in a `finally`.
    """
    import inspect

    source = inspect.getsource(ControlTest._export_effect)
    assert "finally:" in source
    assert source.index("finally:") < source.index("return [result]")


@pytest.mark.parametrize("exporting", [2000.0, 2500.0, 5000.0, 8000.0, 11000.0])
def test_the_cap_is_stated_rather_than_derived(exporting: float) -> None:
    """The cap is `FORCED_EFFECT_W`, whatever the house is doing.

    It was a tenth of the room, which made this check an independent second
    detector of the decade error: a device applying ten times the value still
    curtailed, and the `during` window caught it. That reason has expired --
    `registers.AsymmetricNumberField` compensates the decade in the library now,
    confirmed on three houses -- and keeping it would curtail every honest house
    tenfold to catch something leg B already guards at commit time.
    """
    from sungrow_modbus.control_test import FORCED_EFFECT_W, export_cap

    cap = export_cap(exporting)

    assert cap == FORCED_EFFECT_W
    # It still has to bind, or the window measures nothing.
    assert cap < exporting
    assert cap + EFFECT_FLOOR_W <= exporting


def test_what_the_stated_cap_gives_up_is_named_precisely() -> None:
    """The one case leg C stops catching on 13074, stated so it stays a decision.

    Not "a device that decuples" -- that is the expected device and the library
    compensates for it. Nor a device that does *not* decuple: it gets 125 W
    where 1250 was asked, which binds harder and still reads as a decade.

    The lost case is a build whose compensation is broken or removed, against a
    firmware that decuples anyway. The cap then lands at 12500 W, binds on
    nothing, and reads `NO_EFFECT` -- the same answer an ignored write gives.
    Leg B sees it from the raw word and `tests/test_writes.py` fails on it at
    commit time, which is why this is affordable.
    """
    from sungrow_modbus.control_test import FORCED_EFFECT_W, export_cap

    exporting = 6000.0
    cap = export_cap(exporting)

    # Compensation working, firmware decuples: lands on the asked-for figure.
    assert cap == FORCED_EFFECT_W
    assert cap < exporting, "binds, so the window measures something"

    # Compensation working, firmware does NOT decuple: a tenth, binds harder,
    # and a tenth of the commanded figure is what `classify_ratio` calls a decade.
    assert cap / 10 < cap

    # Compensation broken, firmware decuples: this is the case given up.
    assert cap * 10 > exporting, "no longer binds, hence NO_EFFECT not EFFECT_SCALED"


def test_the_threshold_leaves_room_for_the_cap_to_bind() -> None:
    """The floor is what the cap needs under it, not what a decade needed."""
    from sungrow_modbus.control_test import FORCED_EFFECT_W, MIN_EXPORT_W, export_cap

    assert MIN_EXPORT_W > FORCED_EFFECT_W + EFFECT_FLOOR_W
    # At exactly the threshold the cap still bites by more than the floor.
    cap = export_cap(MIN_EXPORT_W)
    assert cap + EFFECT_FLOOR_W <= MIN_EXPORT_W


# -- what a dongle costs the readback legs ----------------------------------


async def test_a_dongle_endpoint_says_its_readbacks_cannot_be_believed(
    full_unit: MockModbusUnit,
) -> None:
    """Leg A is "write it, read it back", and a WiNet-S breaks the second half.

    It forwards the write and then answers the old value -- measured at gerd,
    where the cable and the dongle disagreed about 33047 before anything was
    written, and a write sent over the dongle arrived while the dongle kept
    reporting the previous figure. So through one, `UNCHANGED` cannot tell a
    dropped write from a cache and `MATCH` is only as good as that cache.

    Four registers at bar12 were written up as dropped writes on exactly this
    evidence, and that conclusion had to be withdrawn hours later.

    The refusal here is an `IllegalDataAddressError` rather than a bare
    `ModbusError`, and the difference is the whole point of the probe: a
    dongle **answers**, with exception 0x02. A bare transport failure is a
    different question with a different answer, in the test below.
    """
    from modbus_connection import IllegalDataAddressError

    # 6100 is the direct-only block; refusing it is what a dongle does.
    full_unit.fail_read(
        6099, IllegalDataAddressError("exception 0x02"), register_type="input"
    )
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)

    await run._preflight()

    assert run.direct is False
    assert run.conditions["direct_connection"] is False
    assert any("WiNet-S" in note for note in run.unestablished)


async def test_a_cable_endpoint_claims_nothing_extra(
    full_unit: MockModbusUnit,
) -> None:
    """Where 6100 answers, the readback legs mean what they say."""
    full_unit.input[6099] = 1234
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)

    await run._preflight()

    assert run.direct is True
    assert not any("WiNet-S" in note for note in run.unestablished)


async def test_a_lost_read_is_undetermined_rather_than_a_dongle(
    full_unit: MockModbusUnit,
) -> None:
    """A link that drops the question has not answered it.

    The regression this pins: `_detect_transport` used to read 6100 once and
    treat *any* failure as a dongle. Measured 2026-09-20 on the reference
    SH10RT -- a cable, no communication module fitted at all, 1.9 ms median --
    where a run made while Home Assistant was polling produced one document
    whose survey half said "direct to the inverter's LAN port" and whose
    control test said dongle, and which therefore stamped its own readback
    table "not evidence". That table carried the 13074 result the whole
    procedure exists to produce.

    Wrong in the expensive direction, and likelier the worse the link: this
    project has measured 10-second timeouts over a VPN against milliseconds
    elsewhere. So a transport failure gets `None`, and `None` must not read as
    `False` anywhere.
    """
    from modbus_connection import ModbusConnectionError

    full_unit.fail_read(
        6099,
        ModbusConnectionError("Connection lost before response was received"),
        register_type="input",
    )
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)

    await run._preflight()

    assert run.direct is None
    assert run.conditions["direct_connection"] is None
    # It must not claim a dongle, which is what discards legs A and B.
    assert not any("WiNet-S" in note for note in run.unestablished)
    assert any("could not be settled" in note for note in run.unestablished)


async def test_a_read_that_misses_once_is_retried_before_concluding(
    full_unit: MockModbusUnit,
) -> None:
    """One missed read is what contention looks like, not what a dongle is.

    `SNAPSHOT_PAUSE` already carries this lesson for the before-state reads --
    "on a link somebody else is polling the first one can simply miss" -- and
    the transport probe simply never had it.
    """
    from modbus_connection import ModbusConnectionError

    full_unit.input[6099] = 1234
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)

    attempts = 0
    original = run.inverter.async_read_words

    async def flaky(space: str, address: int, count: int) -> Any:
        nonlocal attempts
        if address == run.DIRECT_ONLY:
            attempts += 1
            if attempts == 1:
                raise ModbusConnectionError("lost")
        return await original(space, address, count)

    run.inverter.async_read_words = flaky  # type: ignore[method-assign]

    assert await run._detect_transport() is True
    assert attempts == 2


async def test_a_busy_device_is_retried_rather_than_called_a_dongle(
    full_unit: MockModbusUnit,
) -> None:
    """Exception 0x06 means ask me later, not there is no such register.

    It is the one exception *response* that is not evidence about the address,
    and a Sungrow with too many sessions open is exactly where it turns up.
    """
    from modbus_connection import ServerDeviceBusyError

    full_unit.input[6099] = 1234
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    run = _runner(full_unit)

    attempts = 0
    original = run.inverter.async_read_words

    async def busy_once(space: str, address: int, count: int) -> Any:
        nonlocal attempts
        if address == run.DIRECT_ONLY:
            attempts += 1
            if attempts == 1:
                raise ServerDeviceBusyError("exception 0x06")
        return await original(space, address, count)

    run.inverter.async_read_words = busy_once  # type: ignore[method-assign]

    assert await run._detect_transport() is True


async def test_the_export_probe_lifts_the_mode_only_when_it_is_allowed(
    full_unit: MockModbusUnit,
) -> None:
    """Leg B on 13074 needs feed-in limitation on, and most houses have it off.

    The register ignores writes entirely while 13087 is off -- no exception, no
    change -- so the probe reports `UNCHANGED` and the one leg that can catch a
    cap read a decade *too large* is simply not performed. Leg C cannot cover
    for it: a cap ten times too big leaves the export where it was, which is
    indistinguishable from the write doing nothing.

    So the register carrying the only firmware quirk this project has found was
    also the one whose readback was routinely unavailable. It is lifted only
    with the owner's leave, because switching it on curtails a real house.
    """
    inverter = SungrowInverter(full_unit)
    await inverter.async_update()
    probe = next(row for row in PROBES if row.field == "export_power_limit")

    refused = ControlTest(inverter, clock=FakeClock())
    await refused._preflight()
    assert await refused._lift_export_mode(probe) is False, "no leave, no lift"

    allowed = ControlTest(
        inverter, options=Options(enable_export_limit=True), clock=FakeClock()
    )
    await allowed._preflight()
    assert await allowed._lift_export_mode(probe) is True
    assert full_unit.holding[EXPORT_MODE_ADDRESS] == 0xAA

    # And never for a field that is not the export limit.
    other = next(row for row in PROBES if row.field == "battery_min_soc")
    assert await allowed._lift_export_mode(other) is False
