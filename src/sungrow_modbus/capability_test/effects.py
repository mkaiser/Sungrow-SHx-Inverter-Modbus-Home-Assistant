"""Leg C: what the inverter does with what was written."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
import logging
import math

from modbus_connection import ModbusError, ModbusExceptionError

from ..addresses import reg
from ..hybrid_inverter.capabilities import Capability
from .procedure import (
    CHARGE_ENABLE,
    CHARGE_WINDOW,
    CHARGE_WINDOW_AFTER,
    CHARGE_WINDOW_BEFORE,
    CHARGE_WINDOW_SOC_STEP,
    CLAMP_TOLERANCE,
    CONFIRMED,
    DECADES,
    DISCHARGE_WINDOW,
    DRIFT_ABS_W,
    DRIFT_FRACTION,
    DROPPED,
    EFFECT_FLOOR_W,
    EFFECT_SCALED,
    EMS_FORCED,
    EMS_MODE,
    EXPORT_MODE,
    FORCE_CHARGE,
    FORCE_DISCHARGE,
    FORCE_EXPORT_HEADROOM,
    FORCE_EXPORT_MARGIN,
    FORCE_STOP,
    FORCED_CMD,
    FORCED_EFFECT_W,
    FORCED_STARTUP,
    FORCED_STARTUP_OFF,
    FORCED_STARTUP_ON,
    FORCED_STARTUP_SLEEP,
    FORCED_STARTUP_WAKE,
    IMPORT_LIMIT,
    IMPORT_LIMIT_MIN_W,
    IMPORT_LIMIT_PROBE_WORDS,
    INCONCLUSIVE,
    MIN_EXPORT_W,
    MODE_ON,
    NO_EFFECT,
    PROBES,
    PV_CUT,
    PV_CUT_MIN_W,
    PV_CUT_ON,
    PV_CUT_SETTLE,
    PV_RECOVERY,
    RUNNING_STATES_STOPPED,
    SAMPLE_INTERVAL,
    SCALED,
    SETTLE,
    SIGN_INVERTED,
    SIGNIFICANCE,
    SKIPPED,
    SOC_CEILING_FLOOR,
    SOC_CEILING_MARGIN,
    SOC_CHARGE_CEILING,
    SOC_MARGIN,
    STABLE_MAD_W,
    STOP_BRACKET_W,
    STOPPED_W,
    WINDOW,
    WINDOW_RECOVERY,
    WINDOW_SETTLE,
    WINDOW_START_W,
    EffectResult,
    Probe,
    Sample,
    classify_ratio,
    export_cap,
    inverter_clock,
    is_running,
    is_starting,
    mad,
    median,
    window_around,
    window_away,
)
from .readback import ReadbackSteps

_LOGGER = logging.getLogger(__name__)


class EffectSteps(ReadbackSteps):
    """Watch the inverter's power answer a write, while the sun is up."""

    # -- effect: leg C -------------------------------------------------------

    EFFECT_TOLERANCE = 0.25
    """How far a measured power may sit from the value that commanded it and
    still count as obedience. Generous on purpose: the question this leg
    answers is which *decade* the inverter is working in, and a check tight
    enough to argue about 15 % would spend its verdicts on taper and ramp rate."""

    DECADE_TOLERANCE = 0.35
    """How loosely a measured power may sit around ten times, or a tenth of,
    what was commanded. A decade is a factor of ten; nothing needs precision
    here, and a tight window would turn a clear finding into `OFF_BY`."""

    async def _window(
        self, observable: Callable[[Sample], float | None]
    ) -> list[float]:
        """Collect one window of samples, discarding the ones that did not read."""
        values: list[float] = []
        deadline = self.clock.monotonic() + WINDOW
        while self.clock.monotonic() < deadline:
            sample = await self._sample()
            value = observable(sample)
            if value is not None:
                values.append(float(value))
            await self.clock.sleep(SAMPLE_INTERVAL)
        return values

    def _decade(self, observed: float, commanded: float) -> float | None:
        """Return the decade `observed` sits at relative to `commanded`, if any."""
        if commanded == 0:
            return None
        for decade in DECADES:
            if math.isclose(
                observed, commanded * decade, rel_tol=self.DECADE_TOLERANCE
            ):
                return decade
        return None

    async def _bracket(
        self,
        check: str,
        observable: Callable[[Sample], float | None],
        observable_label: str,
        commanded: float | None,
        apply: Callable[[], Awaitable[str | None]],
        undo: Callable[[], Awaitable[None]],
        *,
        setpoint: bool,
        expect_stop: bool = False,
        expect_start: bool = False,
        commanded_unit: str = "W",
        settle: float | None = None,
        recovery: float = SETTLE,
    ) -> EffectResult:
        """Measure one setting's effect, bracketed by two readings of the same state.

        The bracket is the whole answer to a fluctuating input. Before and after
        are two estimates of the *same* undisturbed house, so requiring them to
        agree is a test of whether the sky held still, asked of the sky rather
        than of a model of it. When they disagree the run says so and claims
        nothing -- a cloud that arrived during the measurement is a reason to
        have no opinion, never a reason to fail the inverter.
        """
        blank = EffectResult(
            check=check,
            observable=observable_label,
            commanded=commanded,
            commanded_unit=commanded_unit,
            before=None,
            during=None,
            after=None,
            before_mad=None,
            during_mad=None,
            after_mad=None,
            drift=None,
            delta=None,
            ratio=None,
            verdict=INCONCLUSIVE,
            detail=None,
        )
        if self.options.dry_run:
            return blank._replace(
                verdict=SKIPPED, detail="dry run: nothing was written"
            )

        before = await self._window(observable)
        if not before:
            return blank._replace(detail="nothing answered before the write")
        before_mid, before_mad = median(before), mad(before)

        # Rejected here, before the write is spent. A window this unstable
        # cannot carry a verdict however carefully the rest is measured, and
        # finding that out first costs nothing but the window itself.
        if before_mad > max(STABLE_MAD_W, 0.2 * abs(before_mid)):
            self._worst(3)
            self._note(
                f"{check}: not measured -- the house moved by {before_mad:.0f} W "
                "on its own before anything was written"
            )
            return blank._replace(
                before=before_mid,
                before_mad=before_mad,
                detail="the input was already unstable",
            )

        failure = await apply()
        if failure is not None:
            # Undone even though the change failed. `apply` is several writes,
            # and one of them failing means some of the others landed -- so the
            # only safe reading of a failure here is that something may have
            # been changed. The end-of-run restore would catch it anyway; this
            # keeps the window between them from existing.
            #
            # The refusal is read **before** the undo. `undo` writes too, and
            # fails as readily as `apply` does, so reading afterwards would
            # report the exception from putting the original back while
            # claiming to describe the write that failed.
            because = self.refusals.get(self._last_refused or "", "")
            await undo()
            self._worst(3)
            detail = f"the write {failure}"
            if because:
                detail = f"{detail}: {because}"
            return blank._replace(
                before=before_mid, before_mad=before_mad, detail=detail
            )
        try:
            await self.clock.sleep(SETTLE if settle is None else settle)
            during = await self._window(observable)
        finally:
            await undo()
        await self.clock.sleep(recovery)
        after = await self._window(observable)

        if not during or not after:
            self._worst(3)
            return blank._replace(
                before=before_mid,
                before_mad=before_mad,
                detail="a window did not read",
            )
        during_mid, during_mad_ = median(during), mad(during)
        after_mid, after_mad_ = median(after), mad(after)
        drift = abs(after_mid - before_mid)
        delta = during_mid - before_mid
        measured = blank._replace(
            before=before_mid,
            during=during_mid,
            after=after_mid,
            before_mad=before_mad,
            during_mad=during_mad_,
            after_mad=after_mad_,
            drift=drift,
            delta=delta,
        )
        return self._verdict(
            measured,
            check,
            observable_label,
            setpoint=setpoint,
            commanded=commanded,
            expect_stop=expect_stop,
            expect_start=expect_start,
        )

    def _verdict(
        self,
        measured: EffectResult,
        check: str,
        observable_label: str,
        *,
        setpoint: bool,
        commanded: float | None,
        expect_stop: bool,
        expect_start: bool = False,
    ) -> EffectResult:
        """Decide what three windows mean, given everything already measured.

        Separated from `_bracket` because it is the part with no `await` in it:
        `_bracket` opens windows, writes, waits and puts things back, and this
        reads the numbers that came out.

        The order of the questions is the design, not an accident:

        0. **A bracketed stop or start**, ahead of drift: zero between two
           windows of real power (`STOP_BRACKET_W`), or a window standing
           `WINDOW_START_W` above both its neighbours, is attributable whatever
           the sky did between them.
        1. **Then drift.** Before and after are two readings of the same
           undisturbed house, and when they disagree nothing else is worth
           asking -- the change cannot be attributed to the setting. The answer
           is `INCONCLUSIVE`, never a failure.
        2. **Then the decade**, for a setpoint, because a value off by a clean
           factor of ten is a finding and must not be reported as "close
           enough" by a tolerance wide enough to swallow it.
        3. **Then obedience**, and then the inverted sign, which is a named
           result rather than a confusing failure.
        4. **`expect_stop` is its own branch** because zero has no decades:
           there is no setpoint to be off by, only whether the thing went away.
           `expect_start` is its mirror, for a schedule that starts something
           at a rate the inverter chooses: only whether it began.

        `self._worst` and `self._note` are called here rather than returned,
        which is why this is a method: the exit code and the "could not
        establish" list are properties of the run, not of one measurement.
        """
        before_mid = measured.before
        during_mid = measured.during
        after_mid_ = measured.after
        before_mad = measured.before_mad
        after_mad_ = measured.after_mad
        drift = measured.drift
        delta = measured.delta
        assert before_mid is not None and during_mid is not None
        assert before_mad is not None and after_mad_ is not None
        assert drift is not None and delta is not None

        if (
            expect_stop
            and after_mid_ is not None
            and min(abs(before_mid), abs(after_mid_)) >= STOP_BRACKET_W
            and abs(during_mid) <= STOPPED_W
        ):
            return measured._replace(verdict=CONFIRMED)

        if (
            expect_start
            and after_mid_ is not None
            and during_mid - max(before_mid, after_mid_)
            > max(SIGNIFICANCE * max(before_mad, after_mad_), WINDOW_START_W)
        ):
            return measured._replace(verdict=CONFIRMED)

        if drift > max(DRIFT_ABS_W, DRIFT_FRACTION * abs(before_mid)):
            self._worst(3)
            self._note(
                f"{check}: not measured -- the house was {drift:.0f} W different "
                "afterwards, so the change cannot be attributed to the setting"
            )
            return measured._replace(detail="the input drifted across the measurement")

        if setpoint and commanded:
            decade = self._decade(during_mid, commanded)
            if decade is not None and decade != 1.0:
                self._worst(4)
                return measured._replace(
                    verdict=EFFECT_SCALED,
                    ratio=decade,
                    detail=f"commanded {commanded:.0f} W, measured {during_mid:.0f} W",
                )
            if math.isclose(during_mid, commanded, rel_tol=self.EFFECT_TOLERANCE):
                return measured._replace(
                    verdict=CONFIRMED, ratio=during_mid / commanded
                )
            if math.isclose(during_mid, -commanded, rel_tol=self.EFFECT_TOLERANCE):
                self._worst(4)
                return measured._replace(verdict=SIGN_INVERTED, ratio=-1.0)

        if expect_stop:
            # A check whose expected outcome is that something ceases, rather
            # than that it lands on a number. There is no setpoint to compare
            # against and no decade to be off by -- zero has no decades -- so
            # the question is only whether the quantity went away and came
            # back. `before` doubles as the significance floor: stopping a
            # charge that was never running establishes nothing.
            if abs(before_mid) < STOPPED_W:
                self._worst(3)
                self._note(
                    f"{check}: not measured -- {observable_label} was only "
                    f"{before_mid:.0f} W to begin with, so there was nothing to stop"
                )
                return measured._replace(detail="there was nothing to stop")
            if abs(during_mid) <= STOPPED_W:
                return measured._replace(verdict=CONFIRMED)
            self._worst(3)
            return measured._replace(
                verdict=NO_EFFECT,
                detail=f"{observable_label} carried on at {during_mid:.0f} W",
            )

        if expect_start:
            # A schedule names a time, not a power: the inverter picks the rate.
            # So the question is only whether the quantity rose clearly while
            # the setting was in place and fell back once it was put back --
            # the second half is what the drift check above has already asked.
            if delta > max(SIGNIFICANCE * max(before_mad, after_mad_), WINDOW_START_W):
                return measured._replace(verdict=CONFIRMED)
            self._worst(3)
            return measured._replace(
                verdict=NO_EFFECT,
                detail=f"{observable_label} did not start: {delta:+.0f} W",
            )

        significant = abs(delta) > max(
            SIGNIFICANCE * max(before_mad, after_mad_), EFFECT_FLOOR_W
        )
        if not significant:
            self._worst(3)
            return measured._replace(
                verdict=NO_EFFECT,
                detail="nothing moved by more than the house moves on its own",
            )
        if commanded and not setpoint:
            # A cap, not a setpoint. Obedience means the quantity came down to
            # about the cap; it cannot mean it came down *to* the cap exactly,
            # because what it was capped from is not under anybody's control.
            if math.isclose(during_mid, commanded, rel_tol=self.EFFECT_TOLERANCE):
                return measured._replace(
                    verdict=CONFIRMED, ratio=during_mid / commanded
                )
            decade = self._decade(during_mid, commanded)
            if decade is not None and decade != 1.0:
                self._worst(4)
                return measured._replace(verdict=EFFECT_SCALED, ratio=decade)
        self._worst(3)
        return measured._replace(
            detail="something changed, but not to the value that was commanded"
        )

    def _charging(self, sample: Sample) -> float | None:
        """Charge power, positive when charging.

        `battery_power` is negative while charging, which is the inverter's own
        convention and not a mistake to correct silently -- a check that flips
        the sign without saying so would report `SIGN_INVERTED` for a device
        behaving exactly as documented.
        """
        return None if sample.battery is None else -float(sample.battery)

    def _discharging(self, sample: Sample) -> float | None:
        """Discharge power, positive when discharging."""
        return None if sample.battery is None else float(sample.battery)

    def _exporting(self, sample: Sample) -> float | None:
        """Export power, positive when exporting."""
        return None if sample.export is None else float(sample.export)

    def _importing(self, sample: Sample) -> float | None:
        """Grid import power, positive when importing: 13010's export, negated."""
        return None if sample.export is None else -float(sample.export)

    async def _forced(
        self, direction: int, power: float, *, allow_clamp: bool = False
    ) -> str | None:
        """Command a forced charge or discharge, power first.

        The ordering is a rule, not a preference. The power register is written
        and its raw word checked **before** the command register is touched, so
        a mis-scaled power is caught while it is still only a number in a
        register -- rather than after the inverter has started acting on it.
        """
        probe = next(
            row
            for row in PROBES
            if row.field == "battery_forced_charge_discharge_power"
        )
        failure = await self._write(probe, power)
        if failure is not None:
            return failure
        raw = await self._raw(probe)
        expected = self._expected_raw(probe, power)
        if raw is None:
            return DROPPED
        self.accepted_forced_w = float(raw) * probe.spec_units_per_count
        if raw != expected:
            verdict, _ratio = classify_ratio(raw, expected)
            # A clamp is not a failure when the caller only needs *enough*
            # power rather than an exact figure. `_force_export` is that
            # caller: it wants the house exporting, and the device saying "I
            # will give you 3150 of the 3158 you asked for" is a yes.
            #
            # The decade verdicts are classified first and excluded here, so
            # this can never absorb the error the whole procedure exists to
            # find: a decade short is 90 % short, nowhere near the tolerance.
            short = expected - raw
            clamped = (
                allow_clamp
                and verdict != SCALED
                and 0 < raw < expected
                and short <= CLAMP_TOLERANCE * expected
            )
            if not clamped:
                self._note(
                    f"forced charge was not commanded: register "
                    f"{probe.spec_register} holds {raw} where {expected} was "
                    f"expected ({verdict})"
                )
                return verdict
            self._note(
                f"the battery clamped the manufactured discharge: asked for "
                f"{power:.0f} W, the pack accepted {self.accepted_forced_w:.0f} W "
                f"-- its own limit moves with charge and temperature, and the "
                f"check went ahead against what it accepted"
            )
        if (failure := await self._write(EMS_MODE, EMS_FORCED)) is not None:
            return failure
        return await self._write(FORCED_CMD, direction)

    async def _unforce(self) -> None:
        """Stop forcing, in the order that leaves no intermediate state worth having."""
        await self._write(FORCED_CMD, FORCE_STOP)
        original = self.snapshot.values.get(EMS_MODE.field)
        if original is not None:
            await self._write(EMS_MODE, float(original))
        probe = next(
            row
            for row in PROBES
            if row.field == "battery_forced_charge_discharge_power"
        )
        power = self.snapshot.values.get(probe.field)
        if power is not None:
            await self._write(probe, float(power))

    def _forced_power(self) -> float | None:
        """Return the power the forced checks command: `FORCED_EFFECT_W`, clamped.

        Not `choose_probe`, which falls back from the decade window to the
        whole range once earlier probes have spent the window's values. That is
        right for a readback, where the number is only written and read, and
        wrong here, where it is *commanded*: against a 5883 W ceiling it picks
        a 5800 W forced charge, at night 5.8 kW off the grid.

        A stated constant cannot do that. It is clamped to the register's live
        bounds, so a pack too small for 1250 W gets what it can take rather than
        a refusal, and `None` when the bounds cannot hold anything at all.
        """
        probe = next(
            (
                row
                for row in self.plan
                if row.field == "battery_forced_charge_discharge_power"
            ),
            None,
        )
        if probe is None:
            return None
        low, high = self.snapshot.bounds[probe.field]
        if high <= 0 or high < low:
            return None
        power = min(max(FORCED_EFFECT_W, low), high)
        if power <= 0:
            return None
        if power not in self._taken:
            self._taken.append(power)
        return power

    async def _effects(self) -> list[EffectResult]:
        """Run the behavioural checks the house is actually in a state for."""
        results: list[EffectResult] = []
        if self.options.simulated:
            # Not a shortcut to save time, though it does. A simulator stores
            # raw words and computes no power flows, so every window would read
            # the same seeded number before, during and after -- which this
            # phase would correctly report as "nothing measurable happened", a
            # verdict that says something about the simulator and nothing about
            # any inverter. Skipping it is the honest answer; running it would
            # fill a report with rows that look like evidence.
            self._note(
                "no behavioural checks: a simulator has no power flows to change, "
                "so there was nothing for a setting to have an effect on"
            )
            return results
        soc = self.conditions.get("soc_percent")
        power = self._forced_power()
        minimum = self.snapshot.values.get("battery_min_soc")

        if power is None:
            self._note(
                "no behavioural check of the battery: its forced charge power could "
                "not be resolved, so nothing could be commanded"
            )
        else:
            charge = self._under_cap("battery_max_charge_power", power, "charge")
            if charge is None:
                pass
            elif soc is not None and float(soc) < SOC_CHARGE_CEILING:
                if not self._expired("effect"):
                    self._step(f"forced charge at {charge:g} W")
                    results.append(
                        await self._bracket(
                            "forced charge",
                            self._charging,
                            "battery charge power",
                            charge,
                            lambda: self._forced(FORCE_CHARGE, charge),
                            self._unforce,
                            setpoint=True,
                        )
                    )
            else:
                self._note(
                    "no forced charge check: the battery is too full for a charge "
                    "to measure the setting rather than the pack's own taper"
                )
            floor = float(minimum) if minimum is not None else 0.0
            discharge = self._under_cap(
                "battery_max_discharge_power", power, "discharge"
            )
            if discharge is None:
                pass
            elif soc is not None and float(soc) > floor + SOC_MARGIN:
                if not self._expired("effect"):
                    self._step(f"forced discharge at {discharge:g} W")
                    results.append(
                        await self._bracket(
                            "forced discharge",
                            self._discharging,
                            "battery discharge power",
                            discharge,
                            lambda: self._forced(FORCE_DISCHARGE, discharge),
                            self._unforce,
                            setpoint=True,
                        )
                    )
            else:
                self._note(
                    "no forced discharge check: the battery is at or near its "
                    "minimum state of charge, so there is nothing to discharge"
                )

        results.extend(await self._soc_ceiling_effect())
        results.extend(await self._export_effect())
        results.extend(await self._pv_cut_effect())
        results.extend(await self._charge_window_effect())
        results.extend(await self._discharge_window_effect())
        results.extend(await self._import_limit_effect())
        if self._expired("effect"):
            self._worst(3)
            self._note("the behavioural phase ran out of time before every check ran")
        return results

    def _under_cap(self, field: str, power: float, direction: str) -> float | None:
        """Return the power a forced `direction` may command under the house's cap.

        `battery_max_charge_power` and `battery_max_discharge_power` are the
        house's own limits, and the inverter obeys them over a forced command:
        a house that holds them at 10 W -- one does, to keep its battery idle
        -- turns a 1250 W command into nothing, and "nothing measurable
        happened" would then blame the inverter for obeying its owner. So the
        command goes under the cap where that is still measurable, and the
        check is skipped, with the cap named, where it is not. The cap is the
        snapshot's value: leg B restored it before this phase. **A 0 is not a
        cap**: a dongle answers 0 for what it does not forward (see
        `capabilities.ZERO_MEANS_ABSENT`), so only a positive limit counts.
        """
        cap = self.snapshot.values.get(field)
        if cap is None or float(cap) <= 0 or float(cap) >= power:
            return power
        cap = float(cap)
        low, _high = self.snapshot.bounds.get(
            "battery_forced_charge_discharge_power", [0.0, power]
        )
        if cap < max(EFFECT_FLOOR_W, float(low)):
            self._note(
                f"no forced {direction} check: the house holds {field} at "
                f"{cap:g} W, so a forced {direction} could only show that limit"
            )
            self._worst(3)
            return None
        self._note(
            f"forced {direction} commanded at {cap:g} W rather than {power:g} W, "
            f"under the house's own {field}"
        )
        return cap

    async def _soc_ceiling_effect(self) -> list[EffectResult]:
        """Lower the charge ceiling under the battery and watch the charge stop.

        The only safe behavioural test of a state-of-charge limit, and the
        reason is the direction: it **stops** a charge rather than commanding
        one. The mirror-image test on `battery_min_soc` -- raise the floor above
        where the battery sits -- is an instruction to buy electricity, which is
        why the guards refuse it and why it is not written.

        What it establishes that a readback cannot: that this register is a
        ceiling the inverter actually enforces, not merely a number it stores.
        A scale error here is invisible to leg C in either direction, though --
        95 % and 9.5 % are both below a charging battery, so both would stop the
        charge. That is leg B's to catch, and the report says so rather than
        letting a `CONFIRMED` here be read as more than it is.

        Preconditions, all of which self-skip: the battery must be charging
        (nothing to stop otherwise), the state of charge must leave room above
        the register's own 50 % floor, and `battery_max_soc` must be in the plan.
        """
        probe = next((row for row in self.plan if row.field == "battery_max_soc"), None)
        if probe is None:
            return []
        soc = self.conditions.get("soc_percent")
        if soc is None or float(soc) < SOC_CEILING_FLOOR:
            self._note(
                "no charge-ceiling check: the battery is too low for the ceiling "
                f"to be put under it, since {probe.field} cannot go below "
                f"{probe.minimum:g} %"
            )
            return []
        sample = await self._sample()
        charging = self._charging(sample) or 0.0
        if charging < STOPPED_W:
            self._note(
                f"no charge-ceiling check: the battery was not charging "
                f"({charging:.0f} W), so there was no charge to stop"
            )
            return []
        if self._expired("effect"):
            return []

        original = self.snapshot.values.get(probe.field)
        target = float(soc) - SOC_CEILING_MARGIN
        low, high = self.snapshot.bounds[probe.field]
        target = min(max(target, low), high)
        self._step(f"charge ceiling at {target:g} %")

        async def apply() -> str | None:
            return await self._write(probe, target)

        async def undo() -> None:
            if original is not None:
                await self._write(probe, float(original))

        return [
            await self._bracket(
                "charge ceiling",
                self._charging,
                "battery charge power",
                target,
                apply,
                undo,
                # The one check whose commanded value is not a power. Without
                # this a state of charge prints as "62.4 W" in a table full of
                # real watts, where nothing about it looks wrong.
                commanded_unit="%",
                setpoint=False,
                expect_stop=True,
            )
        ]

    async def _pv_cut_effect(self) -> list[EffectResult]:
        """Cut PV through register 31211 and watch DC power go to zero.

        The check `capabilities.CONFIRMED_ON_FIRMWARE` is seeded from. Leg C
        alone, and nothing weaker would do: the register is outside the
        specification, so there is no scale for leg B to check, and a readback
        proves only that a word was stored -- through a dongle not even that.
        What matters is whether the inverter stops generating.

        Like the charge ceiling it stops something rather than starting it,
        and it is undone by the snapshot's own word, not by an assumed
        "allowed". Needs leave (`Options.cut_pv`), the register, and enough
        PV for a stop to be told from a cloud.
        """
        original = self.snapshot.values.get(PV_CUT.field)
        if original is None:
            # Not capable, or not readable: preflight has already said which.
            return []
        if not self.options.cut_pv:
            self._note(
                "no PV cut check: this run was not given leave to cut PV "
                "generation, so register 31211 was read and never written"
            )
            return []
        sample = await self._sample()
        pv = sample.pv or 0.0
        if pv < PV_CUT_MIN_W:
            self._note(
                f"no PV cut check: PV was {pv:.0f} W, under the {PV_CUT_MIN_W:.0f} W "
                "a stop needs to be told from the sky"
            )
            return []
        if self._expired("effect"):
            return []
        self._step("PV generation cut")

        async def apply() -> str | None:
            return await self._write(PV_CUT, PV_CUT_ON)

        async def undo() -> None:
            await self._write(PV_CUT, float(original))

        result = await self._bracket(
            "PV generation cut",
            self._pv,
            "total DC power",
            None,
            apply,
            undo,
            setpoint=False,
            expect_stop=True,
            settle=PV_CUT_SETTLE,
            recovery=PV_RECOVERY,
        )
        if (
            result.after is not None
            and result.before is not None
            and result.before >= PV_CUT_MIN_W
            and result.after < STOPPED_W
        ):
            self._worst(3)
            self._note(
                f"PV generation cut: PV was still at {result.after:.0f} W "
                f"{PV_RECOVERY:.0f} s after register 31211 was put back, so the "
                "recovery is slower than measured elsewhere or did not happen"
            )
        return [result]

    def _pv(self, sample: Sample) -> float | None:
        return sample.pv

    async def _forced_startup_effect(self) -> list[EffectResult]:
        """Wake an inverter in low-SoC standby through register 13017.

        The whole of the forced startup mode: preflight has already refused
        anything but standby with the battery at its minimum and no PV. Write
        0xAA and watch the running state, through Starting, reach Running;
        then write 0x55 and watch it go back to standby. The restore puts the
        register back afterwards. Judged by the running state alone, which no
        dongle caches.
        """
        if FORCED_STARTUP.field not in self.snapshot.raw:
            return []
        self._step("forced startup under low SoC")
        before = await self._running_word()
        detail: list[str] = []
        failure = await self._write(FORCED_STARTUP, FORCED_STARTUP_ON)
        if failure is not None:
            return [
                self._state_result(
                    before, None, None, None, NO_EFFECT, f"0xAA was {failure}"
                )
            ]
        starting, _word, _ = await self._await_state(
            FORCED_STARTUP_WAKE, lambda word: is_starting(word) or is_running(word)
        )
        running, during, _ = await self._await_state(
            FORCED_STARTUP_WAKE - (starting or 0.0), is_running
        )
        if starting is not None:
            detail.append(f"left standby after {starting:.0f} s")
        if running is None:
            await self._write(FORCED_STARTUP, FORCED_STARTUP_OFF)
            verdict = NO_EFFECT if starting is None else INCONCLUSIVE
            detail.append(
                f"not running {FORCED_STARTUP_WAKE:.0f} s after 0xAA"
                if starting is not None
                else f"still in standby {FORCED_STARTUP_WAKE:.0f} s after 0xAA"
            )
            return [
                self._state_result(
                    before, during, None, starting, verdict, "; ".join(detail)
                )
            ]
        detail.append(f"running after {(starting or 0.0) + running:.0f} s")
        failure = await self._write(FORCED_STARTUP, FORCED_STARTUP_OFF)
        if failure is not None:
            detail.append(f"0x55 was {failure}")
            return [
                self._state_result(
                    before, during, None, running, INCONCLUSIVE, "; ".join(detail)
                )
            ]
        asleep, after, _ = await self._await_state(
            FORCED_STARTUP_SLEEP, lambda word: word in RUNNING_STATES_STOPPED
        )
        if asleep is None:
            detail.append(f"still awake {FORCED_STARTUP_SLEEP:.0f} s after 0x55")
            verdict = INCONCLUSIVE
        else:
            detail.append(f"back in standby {asleep:.0f} s after 0x55")
            verdict = CONFIRMED
        return [
            self._state_result(
                before,
                during,
                after,
                (starting or 0.0) + running,
                verdict,
                "; ".join(detail),
            )
        ]

    def _state_result(
        self,
        before: int | None,
        during: int | None,
        after: int | None,
        seconds: float | None,
        verdict: str,
        detail: str,
    ) -> EffectResult:
        """Report the forced startup check: running-state words, and the wait."""
        return EffectResult(
            check="forced startup under low SoC",
            observable="running state word",
            commanded=float(FORCED_STARTUP_ON),
            commanded_unit="",
            before=None if before is None else float(before),
            during=None if during is None else float(during),
            after=None if after is None else float(after),
            before_mad=None,
            during_mad=None,
            after_mad=None,
            drift=None,
            delta=seconds,
            ratio=None,
            verdict=verdict,
            detail=detail,
        )

    # -- the timed windows ----------------------------------------------------

    async def _inverter_now(self) -> datetime | None:
        """Read the inverter's own clock, holding 5000-5005, or None."""
        try:
            words = await self.inverter.async_read_words("holding", reg(5000), 6)
        except (ModbusError, TimeoutError, OSError) as err:
            _LOGGER.debug("capability test: the inverter's clock did not read: %s", err)
            return None
        return inverter_clock(words)

    def _snapshotted(self, probes: tuple[Probe, ...]) -> bool:
        """Whether every register a check would write has a word to go back to."""
        return all(probe.field in self.snapshot.raw for probe in probes)

    async def _charge_window_effect(self) -> list[EffectResult]:
        """Write a forced-charging window around now and watch a charge start.

        The schedule acts by itself at a time it names, which no readback can
        stand in for, so leg C alone: the battery's charge power, bracketed by
        the house before and after. The window is set against the inverter's
        own clock, the target a few percent above the battery so a charge has
        somewhere to go, and the enable is written last and undone first.
        Needs leave (`Options.charge_window`) and the schedule, and is skipped
        where the owner's own schedule is on, so it is never disturbed.
        """
        if not self.options.charge_window:
            return []
        if not self._snapshotted(CHARGE_WINDOW):
            self._note(
                "no charge window check: the forced-charging schedule "
                "did not answer or could not be read before the run"
            )
            return []
        if self.snapshot.raw[CHARGE_ENABLE.field] == MODE_ON:
            self._note(
                "no charge window check: the owner's forced-charging schedule "
                "is on, and this run does not overwrite it"
            )
            return []
        soc = self.conditions.get("soc_percent")
        if soc is None:
            self._note(
                "no charge window check: the battery's state of charge did not read"
            )
            return []
        # A dongle's 0 for a register it does not forward is no ceiling.
        ceiling = float(self.snapshot.values.get("battery_max_soc") or 100.0)
        target = int(min(100.0, ceiling, float(soc) + CHARGE_WINDOW_SOC_STEP))
        if target < float(soc) + CHARGE_WINDOW_SOC_STEP / 2:
            self._note(
                "no charge window check: the battery is too full for a window "
                "to have anything to charge"
            )
            return []
        now = await self._inverter_now()
        window = (
            None
            if now is None
            else window_around(now, CHARGE_WINDOW_BEFORE, CHARGE_WINDOW_AFTER)
        )
        if now is None or window is None:
            self._note(
                "no charge window check: "
                + (
                    "the inverter's clock did not read"
                    if now is None
                    else "the window would cross midnight on the inverter's clock"
                )
            )
            return []
        self.conditions["inverter_clock"] = now.isoformat()
        if self._expired("effect"):
            return []
        self._step("forced-charging window")
        start_hour, start_minute, end_hour, end_minute = window
        enable, days, *times, target_probe = CHARGE_WINDOW
        writes = (
            (days, 1),
            *zip(times, (start_hour, start_minute, end_hour, end_minute), strict=True),
            (target_probe, target),
            (enable, MODE_ON),
        )

        async def apply() -> str | None:
            for probe, value in writes:
                if (failure := await self._write(probe, value)) is not None:
                    return failure
            return None

        async def undo() -> None:
            await self._write(enable, self.snapshot.raw[enable.field])

        return [
            await self._bracket(
                "forced-charging window",
                self._charging,
                "battery charge power",
                None,
                apply,
                undo,
                setpoint=False,
                expect_start=True,
                settle=WINDOW_SETTLE,
                recovery=WINDOW_RECOVERY,
            )
        ]

    async def _discharge_window_effect(self) -> list[EffectResult]:
        """Move every discharge window away from now and watch discharge stop.

        Registers outside Sungrow's document (#785), so this is the write that
        would let the integration offer them as controls: whether the battery,
        discharging into the house, stops when no window covers now and starts
        again when they are put back. Every window on both days is moved,
        because which day's applies is the inverter's call, and all of them go
        back by their snapshot words. Needs leave (`Options.discharge_window`),
        the schedule, and a battery discharging enough for a stop to show.
        """
        if not self.options.discharge_window:
            return []
        if not self._snapshotted(DISCHARGE_WINDOW):
            self._note(
                "no discharge window check: the discharge schedules did not "
                "answer or could not be read before the run"
            )
            return []
        sample = await self._sample()
        discharging = self._discharging(sample) or 0.0
        if discharging < STOP_BRACKET_W:
            self._note(
                f"no discharge window check: the battery was discharging "
                f"{discharging:.0f} W, under the {STOP_BRACKET_W:.0f} W a stop "
                "needs to be told from the house"
            )
            return []
        now = await self._inverter_now()
        if now is None:
            self._note("no discharge window check: the inverter's clock did not read")
            return []
        self.conditions["inverter_clock"] = now.isoformat()
        if self._expired("effect"):
            return []
        self._step("discharge windows moved away from now")
        away = window_away(now)
        writes = [
            (probe, away[index % 4]) for index, probe in enumerate(DISCHARGE_WINDOW)
        ]

        async def apply() -> str | None:
            for probe, value in writes:
                if (failure := await self._write(probe, value)) is not None:
                    return failure
            return None

        async def undo() -> None:
            for probe in DISCHARGE_WINDOW:
                await self._write(probe, self.snapshot.raw[probe.field])

        return [
            await self._bracket(
                "discharge windows away from now",
                self._discharging,
                "battery discharge power",
                None,
                apply,
                undo,
                setpoint=False,
                expect_stop=True,
                settle=WINDOW_SETTLE,
                recovery=WINDOW_RECOVERY,
            )
        ]

    # -- the site import limit ----------------------------------------------

    async def _import_limit_effect(self) -> list[EffectResult]:
        """Cap grid import under a forced charge and watch import meet the cap.

        Register 32998 is outside Sungrow's document (discussion #546), so
        this is the write that would let the integration offer it as a
        control. A forced charge makes the house import; a cap halfway
        between that import and what the house imports with no charge at all
        (load less PV) is one the inverter can only meet by cutting the
        charge, which is what it did on the maintainer's SH10RT (P020). Judged
        as a cap: import during, against the cap commanded, bracketed by the
        house under the same forced charge before and after. A decade off is
        a wrong scale, the finding a slider would otherwise ship with.

        Then, with the charge stopped, the words around the register's range
        (`IMPORT_LIMIT_PROBE_WORDS`) once each, to record which the device
        refuses. Every write is followed by the snapshot's word, and the
        ordinary restore puts it back again. Needs leave
        (`Options.import_limit`), a battery with room to charge, and the
        forced charge power.
        """
        if not self.options.import_limit:
            return []
        if not self._snapshotted((IMPORT_LIMIT,)):
            self._note(
                "no import limit check: register 32998 did not answer or could "
                "not be read before the run"
            )
            return []
        original = self.snapshot.raw[IMPORT_LIMIT.field]
        if original == 0:
            # A dongle's 0 for a register it does not forward is no limit,
            # and 0 is not a word the device takes (`IMPORT_LIMIT_PROBE_WORDS`).
            self._note(
                "no import limit check: register 32998 read 0, which is not a "
                "limit the inverter takes"
            )
            return []
        power = self._forced_power()
        if power is None:
            self._note(
                "no import limit check: the forced charge power could not be "
                "resolved, so no charge could be commanded to cap"
            )
            return []
        charge = self._under_cap("battery_max_charge_power", power, "charge")
        if charge is None:
            return []
        soc = self.conditions.get("soc_percent")
        if soc is None or float(soc) >= SOC_CHARGE_CEILING:
            self._note(
                "no import limit check: "
                + (
                    "the battery's state of charge did not read"
                    if soc is None
                    else "the battery is too full for a forced charge to cap"
                )
            )
            return []
        if self._expired("effect"):
            return []
        self._step("site import limit")
        if self.options.dry_run:
            return [
                await self._bracket(
                    "site import limit",
                    self._importing,
                    "grid import power",
                    None,
                    self._nothing,
                    self._nothing_undone,
                    setpoint=False,
                )
            ]
        results: list[EffectResult] = []
        failure = await self._forced(FORCE_CHARGE, charge)
        try:
            if failure is not None:
                self._worst(3)
                self._note(f"no import limit check: the forced charge {failure}")
                return []
            await self.clock.sleep(SETTLE)
            sizing = await self._window(self._importing)
            cap = None if not sizing else self._import_cap(median(sizing), charge)
            if cap is None:
                return []
            word = round(cap / 1000 / IMPORT_LIMIT.spec_units_per_count)

            async def apply() -> str | None:
                return await self._write(
                    IMPORT_LIMIT, word * IMPORT_LIMIT.spec_units_per_count
                )

            async def undo() -> None:
                await self._write_word(IMPORT_LIMIT, original)

            results.append(
                await self._bracket(
                    "site import limit",
                    self._importing,
                    "grid import power",
                    cap,
                    apply,
                    undo,
                    setpoint=False,
                )
            )
        finally:
            await self._unforce()
        await self._import_limit_words(original)
        return results

    async def _nothing(self) -> str | None:
        """Change nothing: the apply of a dry run, which `_bracket` never calls."""
        return None

    async def _nothing_undone(self) -> None:
        """Undo nothing: the undo of a dry run, which `_bracket` never calls."""

    def _import_cap(self, importing: float, charge: float) -> float | None:
        """Return the cap, in W, the check commands, or None with a note.

        Halfway between the import under the forced charge and the import the
        house needs with no charge at all, so a cap obeyed moves import by
        half the charge either way. Rounded down to the register's 10 W.
        """
        accepted = self.accepted_forced_w or charge
        floor = max(0.0, importing - accepted)
        cap = max(IMPORT_LIMIT_MIN_W, floor + (importing - floor) / 2)
        cap = math.floor(cap / 10) * 10
        self.conditions["import_limit_sizing_w"] = round(importing)
        if importing - cap < 2 * EFFECT_FLOOR_W:
            self._worst(3)
            self._note(
                f"no import limit check: the forced charge drew only "
                f"{importing:.0f} W from the grid, too little for a cap under it "
                "to be told from the house moving; PV was covering it, and a run "
                "after dark measures it"
            )
            return None
        return float(cap)

    async def _import_limit_words(self, original: int) -> None:
        """Write each of `IMPORT_LIMIT_PROBE_WORDS` once and record the answer.

        Three answers, in `conditions`: taken, refused with the exception the
        device came back with (0x04 is the device saying the word is out of
        range), or not answered -- a lost link or a timeout, which says
        nothing about the register. Each is followed by the snapshot's word,
        so a 0 that is taken caps import for one write's time. Through a
        WiNet-S a refusal is not proof the word did not land, which the
        report's transport says.
        """
        if self.options.dry_run or self._expired("effect"):
            return
        address = (
            self.inverter.component(IMPORT_LIMIT.component)
            .resolved_fields[IMPORT_LIMIT.field]
            .address
        )
        answers: dict[str, str] = {}
        for word in IMPORT_LIMIT_PROBE_WORDS:
            await self._touch(IMPORT_LIMIT.field)
            try:
                await self.inverter.async_write_word(address, word)
            except ModbusExceptionError as err:
                answers[str(word)] = f"refused: {type(err).__name__}: {err}"
            except (ModbusError, TimeoutError, OSError) as err:
                answers[str(word)] = f"not answered: {type(err).__name__}: {err}"
            else:
                answers[str(word)] = "taken"
            await self._write_word(IMPORT_LIMIT, original)
        self.conditions["import_limit_words"] = answers

    async def _force_export(self, sample: Sample) -> float | None:
        """Make the house export by discharging the battery, or say why not.

        The export limit check needs power actually leaving, and most houses
        never offer it: a battery soaks up the surplus while the sun is up, and
        at night there is no surplus. Without this, the register with the one
        firmware quirk this project has found is measurable only on a lucky
        afternoon.

        Discharging is the lever that works whenever the battery has charge,
        including after dark. Commanding more than the house is using sends the
        difference to the grid by definition -- no weather required.

        Returns the power it commanded, or None with a note saying which
        precondition was not met. Note what this costs: a minute of somebody's
        battery through a round trip. Small, but not nothing, which is why it
        is only reached when the house is not exporting on its own.
        """
        if Capability.BATTERY not in self.capabilities:
            self._note(
                "could not make the house export: no battery to discharge, and it "
                "was not exporting on its own"
            )
            return None

        soc = self.conditions.get("soc_percent")
        floor = float(self.snapshot.values.get("battery_min_soc") or 0.0)
        if soc is None or float(soc) <= floor + SOC_MARGIN:
            self._note(
                "could not make the house export: the battery is at "
                f"{soc}% against a floor of {floor:g}%, so there is nothing to "
                "spend on making one"
            )
            return None

        # Enough to cover the house and clear the threshold with room to spare,
        # because load moves while the windows are being taken. Derived from the
        # same figure the verdict uses rather than picked.
        load = abs(sample.load or 0.0)
        # Rounded to a whole watt, and not for tidiness. These registers hold
        # integers, and `NumberField.encode` takes a fast path on a factor-1
        # field -- `raw = int(value)`, which **truncates**. A fractional command
        # would land one count low, fail its own verification, and abandon the
        # discharge with "off by something else".
        want = float(round(load + MIN_EXPORT_W * FORCE_EXPORT_MARGIN))
        ceiling = self.snapshot.battery_ceiling
        if ceiling is not None:
            # Aim below the ceiling rather than at it. The figure was read at
            # preflight and the pack's real limit drifts underneath it, so
            # asking for the last few per cent is asking to be clamped.
            usable = float(round(ceiling * (1.0 - FORCE_EXPORT_HEADROOM) / 10.0)) * 10
            want = min(want, usable)
        cap = self.snapshot.values.get("battery_max_discharge_power")
        if cap is not None and 0 < float(cap) < want:
            # The house's own discharge limit binds before the pack's does.
            want = float(cap)
            if want - load < MIN_EXPORT_W:
                self._note(
                    "could not make the house export: the house holds "
                    f"battery_max_discharge_power at {want:g} W against a "
                    f"{load:.0f} W house"
                )
                return None
        if want - load < MIN_EXPORT_W:
            self._note(
                f"could not make the house export: {want:.0f} W is the most this "
                f"battery will give against a {load:.0f} W house, which leaves "
                f"{want - load:.0f} W of export where a cap needs "
                f"{MIN_EXPORT_W:.0f} W to bind"
            )
            return None

        self._step(f"discharging {want:g} W to make the house export")
        failure = await self._forced(FORCE_DISCHARGE, want, allow_clamp=True)
        if failure is not None:
            await self._unforce()
            self._note(f"could not make the house export: the discharge {failure}")
            return None
        await self.clock.sleep(SETTLE)
        # What the pack accepted, not what was asked for: a clamp is allowed
        # here, so the figure the report quotes has to be the real one.
        return self.accepted_forced_w if self.accepted_forced_w is not None else want

    def _cap_can_bind(
        self, target: float, exporting: float, *, made: bool = False
    ) -> bool:
        """Whether a cap of `target` lands measurably below `exporting`.

        `EFFECT_FLOOR_W` below it, the same floor a verdict needs, or the check
        could only ever report that nothing happened. Notes why not.
        `made` says the export would be manufactured by discharging.
        """
        if exporting - target >= EFFECT_FLOOR_W:
            return True
        source = (
            f"a discharge could make about {exporting:.0f} W of export"
            if made
            else f"the house was exporting {exporting:.0f} W"
        )
        self._note(
            f"no export limit check: the lowest export limit this inverter "
            f"accepts gives a cap of {target:.0f} W, and {source}, so the cap "
            f"could not come {EFFECT_FLOOR_W:.0f} W below it"
        )
        return False

    async def _export_effect(self) -> list[EffectResult]:
        """Limit the export, if the house is exporting and limiting is allowed.

        Worth being plain about what this can and cannot show. A cap is only
        observable while the uncapped quantity exceeds it, so a limit read ten
        times too large leaves the export exactly where it was -- which is
        indistinguishable from the write doing nothing, from the mode being off,
        and from a cloud. This check can catch a limit applied a decade too
        *small*; the decade too large is leg B's to find, and only leg B's.
        """
        probe = next(
            (row for row in self.plan if row.field == "export_power_limit"), None
        )
        if probe is None:
            return []
        mode = self.snapshot.values.get(EXPORT_MODE.field)
        if mode != MODE_ON and not self.options.enable_export_limit:
            self._note(
                "no export limit check: feed-in limitation is switched off on this "
                "inverter, and this run was not given leave to switch it on"
            )
            return []
        # The cap is known before anything is commanded: the stated effect,
        # clamped to the register's live bounds. Where the lowest limit the
        # inverter accepts is above what the house exports, no cap it would
        # take can bind -- measured on a master whose 13074 minimum is
        # 11880 W, exporting 7.4 kW. Said up front, and before a battery is
        # discharged to manufacture an export the cap would still sit above.
        target = export_cap()
        low, high = self.snapshot.bounds[probe.field]
        target = min(max(target, low), high)
        sample = await self._sample()
        exporting = self._exporting(sample) or 0.0
        if exporting < MIN_EXPORT_W and not self._cap_can_bind(
            target, MIN_EXPORT_W * FORCE_EXPORT_MARGIN, made=True
        ):
            return []

        # Not exporting on its own? Make it, rather than skipping. The discharge
        # is held across all three windows deliberately: released between them,
        # the "after" reading would be measuring the discharge stopping rather
        # than the limit being lifted, and the drift gate would fail a check
        # that had worked.
        discharging: float | None = None
        if exporting < MIN_EXPORT_W:
            discharging = await self._force_export(sample)
            if discharging is None:
                return []
            exporting = self._exporting(await self._sample()) or 0.0
            if exporting < MIN_EXPORT_W:
                await self._unforce()
                self._note(
                    f"no export limit check: discharging {discharging:.0f} W still "
                    f"only produced {exporting:.0f} W of export, under the "
                    f"{MIN_EXPORT_W:.0f} W a cap needs to bind against"
                )
                return []

        if self._expired("effect") or not self._cap_can_bind(target, exporting):
            if discharging is not None:
                await self._unforce()
            return []
        self._step(f"export limit at {target:g} W")

        async def apply() -> str | None:
            if (
                mode != MODE_ON
                and (failure := await self._write(EXPORT_MODE, MODE_ON)) is not None
            ):
                return failure
            return await self._write(probe, target)

        async def undo() -> None:
            original = self.snapshot.values.get(probe.field)
            if original is not None:
                await self._write(probe, float(original))
            if mode is not None and mode != MODE_ON:
                await self._write(EXPORT_MODE, float(mode))

        try:
            result = await self._bracket(
                "export power limit",
                self._exporting,
                "export power",
                target,
                apply,
                undo,
                setpoint=False,
            )
        finally:
            if discharging is not None:
                await self._unforce()
        if discharging is not None:
            note = f"export was made by discharging {discharging:.0f} W"
            result = result._replace(
                detail=f"{result.detail}; {note}" if result.detail else note
            )
        return [result]
