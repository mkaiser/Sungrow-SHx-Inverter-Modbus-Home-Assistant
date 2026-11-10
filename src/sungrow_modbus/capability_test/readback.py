"""Legs A and B: write each control and read it back, by library and by word."""

from __future__ import annotations

import logging
import math

from modbus_connection import ModbusError

from ..hybrid_inverter import export_scale
from .preflight import PreflightSteps
from .procedure import (
    CLAMPED,
    DECADE_OUT_OF_RANGE,
    DEVICE,
    DROPPED,
    EXPORT_MODE,
    INCONCLUSIVE,
    LIBRARY,
    MATCH,
    MODE_ON,
    OFF_BY,
    OUT_OF_TIME,
    SCALED,
    SKIPPED,
    SLOPE_WRONG,
    STALE_READBACK,
    STOPPED,
    UNCHANGED,
    UNSAFE_STATE,
    Probe,
    ProbeResult,
    _admissible,
    choose_probe,
    classify_ratio,
    visibility,
)

_LOGGER = logging.getLogger(__name__)


class ReadbackSteps(PreflightSteps):
    """Write each control and check what the register then holds."""

    # -- readback: legs A and B ----------------------------------------------

    #: Controls worth a second probe value a decade below the first. A single
    #: point cannot tell a correct scale from a clamp that happens to sit on it
    #: -- both read back as the value asked for. Two points give a slope, and a
    #: clamp has a slope of zero, which no scale error can imitate.
    TWO_POINT = frozenset(
        {
            "battery_max_charge_power",
            "battery_max_discharge_power",
            "battery_forced_charge_discharge_power",
            "export_power_limit",
        }
    )

    def _expected_raw(self, probe: Probe, value: float) -> int:
        """Return what the register should hold, by the specification.

        No offset term: none of these registers has one, which V1.1.11 states
        for each. Taking the offset from `field.offset` would be the same
        mistake as taking the scale from `field.scale`.
        """
        return round(value / probe.spec_units_per_count)

    def _implicates(self, probe: Probe) -> str:
        """Say which side a decade error is on, where that can be told.

        If the map's factor already disagrees with the specification, this
        library encoded the value wrongly and the static test should have caught
        it long before any hardware was involved. If the two agree and the
        register still holds something else, the *device* is the one doing the
        arithmetic differently -- which is a finding about firmware, and the one
        worth publishing.
        """
        component = self.inverter.component(probe.component)
        resolved = component.resolved_fields.get(probe.field)
        scale = getattr(resolved.field, "scale", None) if resolved else None
        if scale is not None and not math.isclose(
            float(scale), probe.spec_units_per_count
        ):
            return LIBRARY
        return DEVICE

    async def _probe_once(
        self, probe: Probe, value: float, bounds: tuple[float, float]
    ) -> ProbeResult:
        """Write one value and read it back on both legs."""
        original = self.snapshot.values.get(probe.field)
        expected = self._expected_raw(probe, value)
        blank = ProbeResult(
            field=probe.field,
            register=probe.spec_register,
            spec_units_per_count=probe.spec_units_per_count,
            unit=probe.unit,
            original=original,
            written=value,
            library_read=None,
            raw_word=None,
            expected_raw=expected,
            ratio=None,
            slope=None,
            expected_slope=1.0 / probe.spec_units_per_count,
            verdict=MATCH,
            visibility=visibility(value, *bounds),
            implicates=None,
            detail=None,
        )

        failure = await self._write(probe, value)
        if failure is not None:
            self._worst(3)
            return blank._replace(
                verdict=failure, detail=self.refusals.get(probe.field)
            )
        if self.options.dry_run:
            return blank._replace(
                verdict=SKIPPED, detail="dry run: nothing was written"
            )

        await self.clock.sleep(self.WRITE_SETTLE)
        await self._refresh(probe.component)
        library_read = self._value(probe.field)
        raw = await self._raw(probe)
        if raw is None:
            self._worst(3)
            return blank._replace(library_read=library_read, verdict=DROPPED)

        held = self.snapshot.raw.get(probe.field)
        if raw == held and expected != held:
            if self.direct is not True:
                # A WiNet-S answers with the word it held before it forwarded
                # the write: its old value says nothing about the register.
                return blank._replace(
                    library_read=library_read,
                    raw_word=raw,
                    verdict=INCONCLUSIVE,
                    detail=STALE_READBACK,
                )
            self._worst(3)
            return blank._replace(
                library_read=library_read, raw_word=raw, verdict=UNCHANGED
            )

        verdict, ratio = classify_ratio(raw, expected)
        implicates = self._implicates(probe) if verdict == SCALED else None
        detail = None
        if verdict == SCALED:
            self._worst(4)
        elif verdict == OFF_BY and library_read is not None:
            low, high = bounds
            if math.isclose(float(library_read), low) or math.isclose(
                float(library_read), high
            ):
                verdict = CLAMPED
                detail = "the readback sits exactly on a bound"
            self._worst(3)
        return blank._replace(
            library_read=library_read,
            raw_word=raw,
            ratio=ratio,
            verdict=verdict,
            implicates=implicates,
            detail=detail,
        )

    async def _readback(self) -> list[ProbeResult]:
        """Walk the plan, writing and checking each control, then putting it back.

        Each control is restored the moment its own check is done rather than at
        the end of the phase, so at no point is the house carrying more than one
        of this run's values.
        """
        results: list[ProbeResult] = []
        taken = self._taken
        for probe in self.plan:
            if self._skips(probe.field):
                continue
            if self._expired("readback"):
                results.append(
                    self._skipped(probe, STOPPED if self.stopped else OUT_OF_TIME)
                )
                self._worst(3)
                continue
            # Unpacked rather than `tuple(...)`, which gives `tuple[float, ...]`
            # and loses the one thing that matters: these are a *pair*. The
            # snapshot stores them as a list because it is written to JSON, so
            # the pair-ness is a convention until something checks it. This
            # raises rather than passing a three-element bound down the call.
            low, high = self.snapshot.bounds[probe.field]
            bounds = (low, high)
            current = self.snapshot.values.get(probe.field)
            value, seen = choose_probe(probe, low, high, current, taken)
            if value is None:
                results.append(self._skipped(probe, "no admissible probe value"))
                self._worst(3)
                continue
            if not self._safe_soc_probe(probe, value):
                results.append(self._skipped(probe, UNSAFE_STATE))
                self._note(
                    f"{probe.field}: not written, because every admissible value "
                    "was too close to the battery's actual level to be safe"
                )
                self._worst(3)
                continue
            taken.append(value)
            self._step(f"{probe.field}, writing {value:g} {probe.unit}".strip())
            lifted = await self._lift_export_mode(probe)
            if probe.field == "export_power_limit":
                await self._measure_export_scale()
            first = await self._probe_once(probe, value, bounds)
            if seen == DECADE_OUT_OF_RANGE:
                self._note(
                    f"{probe.field}: its bounds have no room for a value ten times "
                    "larger or smaller, so a scale error here could only ever show "
                    "as a refusal"
                )
            if probe.field in self.TWO_POINT and first.verdict in (MATCH, SCALED):
                first = await self._slope(probe, first, bounds, taken)
            results.append(first)
            await self._put_back(probe)
            if lifted:
                # Straight back down, before the next probe rather than at the
                # end of the phase. While it is up the house is capped at
                # whatever 13074 holds, and 13074 is holding a probe value --
                # so every second of this is a second of real curtailment.
                #
                # Back to the *snapshot's* word, not to a named "off". Nothing
                # in this module restores a register to a default, because a
                # default is a guess about what the owner wanted and the
                # snapshot is a measurement of it.
                was = self.snapshot.values.get(EXPORT_MODE.field)
                if was is not None:
                    await self._write(EXPORT_MODE, float(was))
        if (
            "export_power_limit" in self.options.skip
            and "export power limit" not in self.options.skip
            and any(probe.field == "export_power_limit" for probe in self.plan)
        ):
            # The export check still writes 13074, and at the wrong factor it
            # lands a decade off: the scale is asked whether or not the
            # readback of the same register was left out.
            await self._measure_export_scale()
        return results

    async def _slope(
        self,
        probe: Probe,
        first: ProbeResult,
        bounds: tuple[float, float],
        taken: list[float],
    ) -> ProbeResult:
        """Add a second point a decade down, and check the slope between them."""
        second_value = first.written / 10 if first.written else None
        # Checked against the register's own resolution rather than against the
        # entity's step. The step is what a slider offers a person, and a decade
        # below a step-sized value is usually not step-sized itself -- 70 W is a
        # tenth of 700 W and not a multiple of the 100 W the number entity moves
        # in. The register holds tens of watts and will take it, which is all
        # this second point needs; the *first* point stays on the step, because
        # that one is meant to be a value a user could also have written.
        if second_value is None or not _admissible(
            second_value,
            bounds[0],
            bounds[1],
            probe.spec_units_per_count,
            probe.spec_units_per_count,
            None,
        ):
            return first._replace(
                detail="one point only: no admissible second value a decade away"
            )
        taken.append(second_value)
        self._step(f"{probe.field}, second point {second_value:g} {probe.unit}".strip())
        second = await self._probe_once(probe, second_value, bounds)
        if second.raw_word is None or first.raw_word is None:
            return first._replace(
                detail="one point only: the second read did not answer"
            )
        span = first.written - second_value  # type: ignore[operator]
        if span == 0:
            return first
        slope = (first.raw_word - second.raw_word) / span
        expected = 1.0 / probe.spec_units_per_count
        verdict = first.verdict
        detail = first.detail
        if math.isclose(slope, 0.0, abs_tol=1e-9):
            verdict = CLAMPED
            detail = "two points, one answer: the device is clamping"
            self._worst(3)
        elif not math.isclose(slope, expected, rel_tol=0.01):
            verdict = SLOPE_WRONG
            self._worst(4)
        return first._replace(slope=slope, verdict=verdict, detail=detail)

    def _skipped(self, probe: Probe, reason: str) -> ProbeResult:
        """Return a recorded non-result: never a pass, never a failure."""
        return ProbeResult(
            field=probe.field,
            register=probe.spec_register,
            spec_units_per_count=probe.spec_units_per_count,
            unit=probe.unit,
            original=self.snapshot.values.get(probe.field),
            written=None,
            library_read=None,
            raw_word=None,
            expected_raw=None,
            ratio=None,
            slope=None,
            expected_slope=1.0 / probe.spec_units_per_count,
            verdict=SKIPPED,
            visibility=DECADE_OUT_OF_RANGE,
            implicates=None,
            detail=reason,
        )

    async def _lift_export_mode(self, probe: Probe) -> bool:
        """Switch feed-in limitation on for an export-limit probe, if allowed.

        Without this, leg B never runs on register 13074 at a house whose mode
        is off -- which is most of them. The register ignores writes entirely
        while 13087 is off, so the probe reports `UNCHANGED` and the one leg
        that can catch a cap read a decade *too large* is simply not performed.
        Leg C cannot cover for it: a cap ten times too big leaves the export
        where it was, which is indistinguishable from the write doing nothing.

        So without it the register with the only firmware quirk this project
        has found is also the one whose readback is routinely unavailable. It
        is lifted only where the owner granted `--enable-export-limit`, because
        switching this on curtails a real house.

        Returns whether it was lifted, so the caller can put it straight back.
        """
        if probe.field != "export_power_limit" or not self.options.enable_export_limit:
            return False
        if self.snapshot.values.get(EXPORT_MODE.field) == MODE_ON:
            return False
        return await self._write(EXPORT_MODE, MODE_ON) is None

    async def _measure_export_scale(self) -> None:
        """Ask how this firmware writes 13074, before writing it.

        The firmwares differ -- three houses multiply the word by ten, fwitten
        stores it as handed -- and a probe written at the wrong factor is
        refused or lands a decade off, which leg B would then report as a
        finding about the register when it is a finding about this run. So
        the run writes at the factor the device states, as the integration's
        entity does, and leg B checks the *register*: whatever the factor, a
        right write leaves the watts asked for.

        Never lifts the mode itself: `_lift_export_mode` has already done that
        where it was allowed, and where it was not the register ignores every
        write anyway. The probe's one write changes nothing on either firmware.

        A simulator is not asked. It stores every word as handed, so it is a
        1:1 firmware by construction, and where the probe declines -- the
        seed's held limit leaves no word that changes nothing -- the run
        would otherwise divide by ten and report the simulator's arithmetic
        as a wrong slope.
        """
        if self.options.simulated:
            self.export_write_scale = 1
            self.conditions["export_write_scale"] = None
            self._note(
                "a simulator stores the export limit's word as handed, so it "
                "was written 1:1 rather than asked"
            )
            return
        try:
            result = await export_scale.async_probe(
                self.inverter, dry_run=self.options.dry_run
            )
        except ModbusError as err:
            self.conditions["export_write_scale"] = None
            self._note(
                "the export limit's write scale could not be asked, so it was "
                f"written divided by ten: {type(err).__name__}: {err}"
            )
            return
        self.conditions["export_write_scale"] = export_scale.document(result)
        if result.left_changed:
            self._worst(5)
        self.export_write_scale = result.write_units_per_count
        if result.write_units_per_count is None:
            self._note(
                "the export limit's write scale was not determined, so it was "
                f"written divided by ten: {result.reason}"
            )

    async def _put_back(self, probe: Probe) -> None:
        """Restore one control immediately after its own check."""
        original = self.snapshot.values.get(probe.field)
        if original is None or probe.field not in self._written:
            return
        restored, _detail = await self._write_back(
            probe, float(original), self.snapshot.raw.get(probe.field)
        )
        if restored:
            self._written.pop(probe.field, None)
