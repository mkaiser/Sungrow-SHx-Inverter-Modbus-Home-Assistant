"""What the run checks and reads before it writes anything."""

from __future__ import annotations

import logging

from ..battery import ceiling as battery_ceiling
from ..hybrid_inverter.capabilities import Capability, with_sungrow_battery
from ..hybrid_inverter.derived import RUNNING_STATES
from .procedure import (
    ENUMERATIONS,
    MIN_PV_W,
    NO_BOUNDS,
    NO_SNAPSHOT,
    NOT_CAPABLE,
    PROBES,
    SAMPLE_COMPONENTS,
    SNAPSHOT_PAUSE,
    SOC_MARGIN,
    STATE_COMPONENTS,
    Guard,
    Probe,
    Snapshot,
    is_running,
)
from .restore import RestoreSteps

_LOGGER = logging.getLogger(__name__)


class PreflightSteps(RestoreSteps):
    """Detect the transport, decide the guards, and take the snapshot."""

    # -- preflight -----------------------------------------------------------

    def _battery_ceiling(self) -> float | None:
        """Return what this battery will take, by the one shared ladder."""
        capacity = None
        if Capability.SUNGROW_BATTERY in self.capabilities:
            capacity = self._value("battery_capacity_high_precision")
        return battery_ceiling(
            sungrow_capacity_kwh=capacity,
            bms_max_charging_current_a=self._value("bms_max_charging_current"),
            battery_voltage_v=self._value("battery_voltage"),
            bdc_rated_power_w=self._value("bdc_rated_power"),
        )

    def _bounds(self, probe: Probe) -> tuple[float, float] | None:
        """Resolve one control's real bounds, asking the device where it knows.

        The inverter knows its own limits better than a table does, and for the
        export limit it states them outright in registers 5622 and 5623. The
        YAML package read them from there rather than hardcoding them and was
        right to; a hardcoded ceiling is a value that is wrong on some model
        nobody owns yet.
        """
        low = probe.minimum
        high = probe.maximum
        if probe.minimum_field is not None:
            value = self._value(probe.minimum_field)
            if value is None:
                return None
            low = float(value)
        if probe.maximum_field is not None:
            value = self._value(probe.maximum_field)
            if value is None:
                return None
            high = float(value)
        if probe.maximum_from_battery:
            ceiling = self.snapshot.battery_ceiling
            if ceiling is None:
                return None
            high = float(ceiling)
        if high <= low:
            return None
        return low, high

    def _guards(self) -> None:
        """Refuse a run the house is in no state for.

        In Home Assistant this list is the only protection a button press has,
        because a button has no confirmation dialog. So every refusal is worded
        as the whole explanation rather than as a code, and every one of them
        is checked *before* the snapshot is spent.
        """
        state = self._value("running_state_raw")
        if state is None:
            raise Guard(
                "The inverter did not report a running state, so this run cannot "
                "tell whether it is safe to write to it.",
                code=1,
            )
        if not is_running(int(state)):
            label = RUNNING_STATES.get(
                int(state), f"an unknown code, 0x{int(state):04X}"
            )
            raise Guard(
                f"The inverter reports {label!r} rather than running. Every "
                "measurement here is about what it does while it works, so start "
                "it and try again."
            )
        pv = self._value("total_dc_power")
        self.conditions["pv_w"] = pv
        if not self.options.allow_dark and (pv is None or pv < MIN_PV_W):
            raise Guard(
                f"Only {pv or 0:.0f} W of PV. The behavioural half of this test "
                "measures what the inverter does with the sun it has, so run it "
                "while it is generating, or ask for the readback half alone."
            )
        soc = self._value("battery_level")
        self.conditions["soc_percent"] = soc
        if Capability.BATTERY in self.capabilities and soc is None:
            raise Guard(
                "This inverter has a battery but did not report its state of "
                "charge, and every battery guard here is computed from it."
            )

    async def _snapshot_read(
        self, probe: Probe
    ) -> tuple[float | int | None, int | None]:
        """Read one control's current value and raw word, retrying the read.

        Retried because a control that cannot be read here is struck off the
        plan for the *whole run*, and on an inverter something else is polling
        one read can simply drop while the next answers perfectly. A dropped
        read on a contended link is a moment, not a state.
        """
        for attempt in (1, 2, 3):
            await self._refresh(probe.component)
            value = self._value(probe.field)
            raw = await self._raw(probe)
            if value is not None and raw is not None:
                return value, raw
            if attempt < 3:
                await self.clock.sleep(SNAPSHOT_PAUSE)
        _LOGGER.debug("control test: %s would not read before the run", probe.field)
        return None, None

    def _safe_soc_probe(self, probe: Probe, value: float) -> bool:
        """Whether a state-of-charge probe stays below where the battery sits.

        The one guard with a bill attached. A minimum state of charge raised
        above the level the battery is actually at is an instruction to charge,
        and a hybrid permitted to charge from the grid will do exactly that --
        with real money, and on some firmware it keeps going past the restore
        until it reaches the setting.
        """
        if probe.field not in ("battery_min_soc", "battery_reserved_soc_for_backup"):
            return True
        soc = self.conditions.get("soc_percent")
        if soc is None:
            return False
        return value < float(soc) - SOC_MARGIN

    async def _preflight(self) -> None:
        """Read everything, resolve the plan, and persist the before-state."""
        self._step("reading the inverter")
        await self._refresh(*STATE_COMPONENTS, *SAMPLE_COMPONENTS)
        self.capabilities = with_sungrow_battery(
            self.inverter.capabilities(),
            pack_found=self._sungrow_pack,
            capacity_kwh=self._value("battery_capacity_high_precision"),
        )
        self.direct = await self._detect_transport()
        self._transport_checked = True
        self.conditions["direct_connection"] = self.direct
        if self.direct is False:
            self._note(
                "this endpoint is a WiNet-S rather than the inverter's own "
                "port, and a WiNet-S answers a register stale after "
                "forwarding a write to it -- so every readback verdict here "
                "describes what the dongle reported, not what the register "
                "holds. Waiting does not help: polled every 5 s for two "
                "minutes one never reported a value the cable had confirmed. "
                "The behavioural checks are unaffected. The before-state is "
                "read through the same cache, so the restore puts back only "
                "what this run wrote, and puts it back to the word the dongle "
                "reported: a register changed over another path since the "
                "dongle last read it would go back to the dongle's figure"
            )
        elif self.direct is None:
            self._note(
                "the transport could not be settled: register 6100 was "
                "neither answered nor refused in "
                f"{self.TRANSPORT_ATTEMPTS} attempts -- the reads failed on "
                "the link itself, which is what contention looks like from "
                "this end. A cable answers that register and a dongle "
                "refuses it, but a lost read says neither. So the readback "
                "table below is reported as measured and carries whatever "
                "weight an unknown transport deserves: if this endpoint is "
                "in fact a dongle, those verdicts describe its cache rather "
                "than the register. The behavioural checks are unaffected"
            )
        self.conditions["capabilities"] = sorted(
            capability.value for capability in self.capabilities
        )
        self.conditions["model"] = self.inverter.model
        self._guards()

        snapshot = Snapshot(taken_at=self.clock.monotonic(), touched=[])
        snapshot.battery_ceiling = self._battery_ceiling()
        self.snapshot = snapshot
        self.conditions["battery_ceiling_w"] = snapshot.battery_ceiling

        plan: list[Probe] = []
        for probe in (*PROBES, *ENUMERATIONS):
            if probe.leave is not None and not getattr(self.options, probe.leave):
                continue
            if probe.requires is not None and probe.requires not in self.capabilities:
                self._note(
                    f"{probe.field}: {NOT_CAPABLE} "
                    f"({probe.requires.value} did not answer)"
                )
                continue
            value, raw = await self._snapshot_read(probe)
            if value is None or raw is None:
                snapshot.unreadable[probe.field] = NO_SNAPSHOT
                self._note(f"{probe.field}: {NO_SNAPSHOT}, so it was never written")
                self._worst(3)
                continue
            snapshot.values[probe.field] = value
            snapshot.raw[probe.field] = raw
            if probe in ENUMERATIONS:
                continue
            bounds = self._bounds(probe)
            if bounds is None:
                self._note(f"{probe.field}: {NO_BOUNDS}")
                self._worst(3)
                continue
            snapshot.bounds[probe.field] = list(bounds)
            plan.append(probe)
        self.plan = tuple(plan)

        if self._on_snapshot is not None:
            # Before the first write, and the caller is expected to flush. A
            # snapshot that reaches the disk after the first write describes a
            # house that has already been changed.
            await self._on_snapshot(snapshot)
        self._step("the before-state is saved")
