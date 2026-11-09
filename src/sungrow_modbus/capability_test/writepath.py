"""Writes that change nothing the house runs on, for the controls nothing else writes.

The readback walk writes the controls with a scale; the behavioural checks
write the ones whose effect can be watched. That leaves controls the
integration offers that no run ever wrote: backup mode, load control, the
weekend discharge enable, the forced-charging schedule's second window, and
every option of the EMS mode but forced. And it leaves the numbers' bounds,
which the integration's sliders take from a table, never from a device.

Each check here writes only what cannot change how the house runs, and puts
the snapshot's word back straight after:

- **write path**: the snapshot's own word, written back to itself. Taken is
  the write path proven; refused is the register not taking writes.
- **window 2 encoding**: the second forced-charging window and the days,
  written to other values and read back by raw word -- only while the
  schedule is off, when no window can start a charge, and only over a cable,
  where a readback is the register.
- **upper bound**: one value a step above each number's maximum. Refused is
  the bound enforced; taken is a bound the firmware does not enforce, and the
  word goes back at once. A state-of-charge floor is raised only where the
  battery stands well above it, as the readback walk guards it.
- **EMS mode options**: each documented option of 13050 written once, the
  snapshot's word straight after each. Refused is an option this firmware
  does not have.

Every write is touched into the snapshot first, and the ordinary restore puts
every word back again, checked.
"""

from __future__ import annotations

from modbus_connection import ModbusError

from .base import refused
from .effects import EffectSteps
from .procedure import (
    BACKUP_MODE,
    CLAMPED,
    CONFIRMED,
    DROPPED,
    EMS_MODE,
    EMS_OPTIONS,
    INCONCLUSIVE,
    LOAD_ENABLE,
    LOAD_MODE,
    NO_EFFECT,
    REFUSED,
    UNCURABLE,
    WEEKEND_DISCHARGE,
    WINDOW_2,
    WINDOW_2_ENABLE,
    WINDOW_OFF,
    EffectResult,
    Probe,
    bound_check,
    bounded_probes,
)

#: The no-op checks: a name, and the registers it writes back to themselves.
WRITE_PATHS: tuple[tuple[str, tuple[Probe, ...]], ...] = (
    ("backup mode write path", (BACKUP_MODE,)),
    ("load control write path", (LOAD_ENABLE, LOAD_MODE)),
    ("weekend discharge enable write path", (WEEKEND_DISCHARGE,)),
)

WINDOW_2_CHECK = "forced-charging window 2 encoding"
EMS_CHECK = "EMS mode options"


def row(
    check: str,
    verdict: str,
    detail: str,
    *,
    commanded: float | None = None,
    unit: str = "",
) -> EffectResult:
    """Return a check's row: what was written and what came of it."""
    return EffectResult(
        check=check,
        observable="the register's answer",
        commanded=commanded,
        commanded_unit=unit,
        before=None,
        during=None,
        after=None,
        before_mad=None,
        during_mad=None,
        after_mad=None,
        drift=None,
        delta=None,
        ratio=None,
        verdict=verdict,
        detail=detail,
    )


class WritePathSteps(EffectSteps):
    """The checks above, after the behavioural phase and before the restore."""

    async def _write_paths(self) -> list[EffectResult]:
        """Run every check this run has the snapshot and the leave for."""
        if self.options.simulated or not self.options.write_paths:
            return []
        if self.options.dry_run:
            # Every one of them judges what a write did; a dry run sends none.
            return []
        results: list[EffectResult] = []
        for check, probes in WRITE_PATHS:
            results.extend(await self._no_op(check, probes))
        results.extend(await self._window_2())
        if self.options.bounds:
            for probe in bounded_probes():
                results.extend(await self._upper_bound(probe))
        results.extend(await self._ems_options())
        return results

    # -- helpers ---------------------------------------------------------------

    async def _word(self, probe: Probe, word: int) -> str | None:
        """Write one raw word, keeping the exception a refusal came back with."""
        if self.options.dry_run:
            return None
        await self._touch(probe.field)
        component = self.inverter.component(probe.component)
        resolved = component.resolved_fields.get(probe.field)
        if resolved is None or resolved.count != 1:
            return REFUSED
        try:
            await self.inverter.async_write_word(resolved.address, word)
        except (ModbusError, TimeoutError, OSError) as err:
            self.refusals[probe.field] = f"{type(err).__name__}: {err}"
            return REFUSED if refused(err) else DROPPED
        return None

    def _ready(self, check: str, probes: tuple[Probe, ...]) -> bool:
        """Whether this run may write `probes` for `check`, noting why not."""
        if self._skips(check):
            return False
        if self._expired("effect"):
            self._note(f"{check}: not run, the run ran out of time")
            return False
        leave = next((p.leave for p in probes if p.leave is not None), None)
        if leave is not None and not getattr(self.options, leave):
            self._note(f"{check}: not given leave ({leave.replace('_', ' ')})")
            return False
        missing = [p.field for p in probes if p.field not in self.snapshot.raw]
        if missing:
            self._note(
                f"{check}: not run, {', '.join(missing)} could not be read "
                f"before the run or this model does not have it, {UNCURABLE}"
            )
            return False
        return True

    # -- the checks --------------------------------------------------------------

    async def _no_op(self, check: str, probes: tuple[Probe, ...]) -> list[EffectResult]:
        """Write each register's own word back to it."""
        if not self._ready(check, probes):
            return []
        self._step(check)
        answers = []
        for probe in probes:
            word = self.snapshot.raw[probe.field]
            failure = await self._word(probe, word)
            answers.append((probe, word, failure))
        failures = [(p, f) for p, _w, f in answers if f is not None]
        detail = "; ".join(
            f"{probe.spec_register} took its own word {word}"
            if failure is None
            else f"{probe.spec_register} {failure}: {self.refusals.get(probe.field)}"
            for probe, word, failure in answers
        )
        if not failures:
            return [row(check, CONFIRMED, detail)]
        self._worst(3)
        if any(f == DROPPED for _p, f in failures):
            return [row(check, DROPPED, detail)]
        return [row(check, REFUSED, detail)]

    async def _window_2(self) -> list[EffectResult]:
        """Write the second window and the days elsewhere, and read them back."""
        if not self._ready(WINDOW_2_CHECK, (WINDOW_2_ENABLE, *WINDOW_2)):
            return []
        if self.snapshot.raw[WINDOW_2_ENABLE.field] != WINDOW_OFF:
            self._note(
                f"{WINDOW_2_CHECK}: not run, the forced-charging schedule is on, "
                f"so a window written could charge from the grid, {UNCURABLE}"
            )
            return []
        if self.direct is not True:
            self._note(
                f"{WINDOW_2_CHECK}: not run, a readback is only the register over "
                f"a cable, {UNCURABLE}"
            )
            return []
        self._step(WINDOW_2_CHECK)
        mismatches: list[str] = []
        failures: list[str] = []
        for probe in WINDOW_2:
            original = self.snapshot.raw[probe.field]
            word = _elsewhere(probe, original)
            failure = await self._word(probe, word)
            if failure is not None:
                failures.append(f"{probe.spec_register} {failure}")
                continue
            await self.clock.sleep(self.WRITE_SETTLE)
            raw = await self._raw(probe)
            if raw != word:
                mismatches.append(f"{probe.spec_register} wrote {word}, read {raw}")
            await self._word(probe, original)
        if failures:
            self._worst(3)
            verdict = DROPPED if any(DROPPED in f for f in failures) else REFUSED
            return [row(WINDOW_2_CHECK, verdict, "; ".join(failures + mismatches))]
        if mismatches:
            self._worst(3)
            return [row(WINDOW_2_CHECK, NO_EFFECT, "; ".join(mismatches))]
        return [
            row(
                WINDOW_2_CHECK,
                CONFIRMED,
                f"{len(WINDOW_2)} registers read back the word written, schedule off",
            )
        ]

    async def _upper_bound(self, probe: Probe) -> list[EffectResult]:
        """Offer one step above the maximum, and see what the device makes of it."""
        check = bound_check(probe.field)
        if not self._ready(check, (probe,)):
            return []
        bounds = self.snapshot.bounds.get(probe.field)
        if bounds is None:
            self._note(f"{check}: not run, its bounds could not be resolved")
            return []
        high = float(bounds[1])
        value = high + probe.step
        if not self._safe_soc_probe(probe, value):
            self._note(
                f"{check}: not run, {value:g} {probe.unit} is not well below the "
                "battery's level, and a floor raised past it would charge from the grid"
            )
            return []
        if probe.field == "battery_forced_charge_discharge_power" and (
            self.snapshot.raw.get(EMS_MODE.field) == 2
        ):
            self._note(
                f"{check}: not run, the house is in forced mode itself, so a forced "
                f"power above the maximum would act, {UNCURABLE}"
            )
            return []
        self._step(check)
        word = round(value / probe.spec_units_per_count)
        original = self.snapshot.raw[probe.field]
        failure = await self._word(probe, word)
        if failure == REFUSED:
            return [
                row(
                    check,
                    CONFIRMED,
                    f"refused {value:g} {probe.unit}, above the maximum {high:g}: "
                    f"{self.refusals.get(probe.field)}",
                    commanded=value,
                    unit=probe.unit,
                )
            ]
        if failure is not None:
            self._worst(3)
            return [row(check, DROPPED, failure, commanded=value, unit=probe.unit)]
        raw: int | None = None
        if self.direct is True:
            await self.clock.sleep(self.WRITE_SETTLE)
            raw = await self._raw(probe)
        await self._word(probe, original)
        if self.direct is not True:
            return [
                row(
                    check,
                    INCONCLUSIVE,
                    f"took {value:g} {probe.unit}; a dongle's readback cannot say "
                    "whether it was stored",
                    commanded=value,
                    unit=probe.unit,
                )
            ]
        if raw is not None and raw < word:
            return [
                row(
                    check,
                    CLAMPED,
                    f"took {value:g} {probe.unit} and stored the word {raw}",
                    commanded=value,
                    unit=probe.unit,
                )
            ]
        return [
            row(
                check,
                NO_EFFECT,
                f"took and stored {value:g} {probe.unit}, above the maximum "
                f"{high:g}: the bound is not enforced",
                commanded=value,
                unit=probe.unit,
            )
        ]

    async def _ems_options(self) -> list[EffectResult]:
        """Write each documented EMS mode once, the snapshot's word after each."""
        if not self._ready(EMS_CHECK, (EMS_MODE,)):
            return []
        self._step(EMS_CHECK)
        original = self.snapshot.raw[EMS_MODE.field]
        answers: dict[int, str] = {}
        for word in EMS_OPTIONS:
            if word == original:
                answers[word] = "held before the run"
                continue
            failure = await self._word(EMS_MODE, word)
            answers[word] = (
                "taken"
                if failure is None
                else f"{failure}: {self.refusals.get(EMS_MODE.field)}"
            )
            await self._word(EMS_MODE, original)
        self.conditions["ems_mode_options"] = {str(k): v for k, v in answers.items()}
        detail = "; ".join(f"{word}: {answer}" for word, answer in answers.items())
        if any(answer.startswith(DROPPED) for answer in answers.values()):
            self._worst(3)
            return [row(EMS_CHECK, DROPPED, detail)]
        if any(answer.startswith(REFUSED) for answer in answers.values()):
            return [row(EMS_CHECK, REFUSED, detail)]
        return [row(EMS_CHECK, CONFIRMED, detail)]


def _elsewhere(probe: Probe, original: int) -> int:
    """Return a legal word for `probe` that is not the one it holds."""
    if probe.exact:
        return next(word for word in probe.exact if word != original)
    low, high = int(probe.minimum), int(probe.maximum)
    span = high - low + 1
    return low + (original - low + span // 2) % span
