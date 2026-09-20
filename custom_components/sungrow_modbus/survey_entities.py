"""The device page's survey controls: a button, and three things to watch.

These are the entities that replace the options flow's spinner. They are
deliberately ordinary Home Assistant entities rather than anything clever,
because that is what buys the things a modal dialog could not do:

- the **history** of `survey_step` is the log of what was probed, in order,
  with timestamps, kept by the recorder like any other state;
- `survey_progress` is a number, so it draws a bar on a dashboard, and can
  be watched by an automation on a link where a survey takes a quarter of an
  hour;
- the button can be pressed by a script, so a maintainer walking somebody
  through a problem can say "run this" rather than "click through there".

All four are `EntityCategory.DIAGNOSTIC`: they describe the integration
rather than the inverter, and they belong under the diagnostic heading of
the device page rather than among the readings.

They exist in **both** modes. A diagnostics-only entry has no other entities
at all, and these are the reason it was set up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

if TYPE_CHECKING:
    from .coordinator import SungrowRuntimeData
    from .survey import SurveyRunner

#: Domain and translation key of every entity in this module.
#:
#: Here rather than in the generator so that adding one cannot forget to name
#: it: `scripts/generate_strings.py` reads this, and these keys have no legacy
#: name to derive from -- they are named in `naming.OVERRIDES` like the SBR
#: pack's, which are hand-written for the same reason.
SURVEY_ENTITIES: tuple[tuple[str, str], ...] = (
    ("button", "run_survey"),
    ("button", "run_control_test"),
    ("sensor", "survey_progress"),
    ("sensor", "survey_step"),
    ("sensor", "survey_finished"),
)

#: The longest a step label may be. Home Assistant refuses to record a state
#: over 255 characters, and a probe label is nowhere near that -- but a
#: failure message inherited from the stack can be, and a survey that
#: silently stopped being recorded is worse than a truncated line.
MAX_STATE = 255


def _findings(control_test: dict[str, Any]) -> int | None:
    """Count the decade findings in part B's block, or None if it never ran."""
    readback = control_test.get("readback")
    if readback is None:
        return None
    return sum(1 for row in readback if "decade" in str(row.get("verdict", "")))


class SurveyEntity(Entity):
    """Common wiring: which device, which runner, and how updates arrive.

    Not a `CoordinatorEntity`: a survey is not polled. It is pushed, from the
    reading loop, through one dispatcher signal per config entry -- so the
    entity updates when something actually happened rather than on a timer
    that would be wrong in both directions on a slow link.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime_data: SungrowRuntimeData, key: str) -> None:
        """Attach to the entry's inverter device."""
        self._runtime = runtime_data
        self._runner: SurveyRunner = runtime_data.survey
        coordinator = next(iter(runtime_data.coordinators.values()))
        serial = coordinator.device.serial_number
        assert serial is not None
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_translation_key = key
        self._attr_device_info: DeviceInfo = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        """Listen for survey state changes for as long as this entity lives."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._runner.signal, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class SurveyButton(SurveyEntity, ButtonEntity):
    """Start a capability survey."""

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for what pressing it does."""
        super().__init__(runtime_data, "run_survey")

    @property
    def available(self) -> bool:
        """Unavailable while one is running, so it cannot be pressed twice.

        The runner refuses a second run anyway. This is the half of that
        which the person can see: a button that looks pressable and does
        nothing is worse than one that is visibly busy.
        """
        return not self._runner.state.running

    async def async_press(self) -> None:
        """Run the survey with the testimony already saved in the options."""
        self._runner.async_start()


class ControlTestButton(SurveyEntity, ButtonEntity):
    """Run the survey and then the control test, which **writes** registers.

    A separate button rather than an option on the first one, so that nothing a
    person presses expecting a survey can write to their inverter.

    Worth stating plainly, because Home Assistant gives a button no
    confirmation dialog: pressing this changes settings on the device. It moves
    the state-of-charge limits, commands a charge and a discharge at a power
    derived from the battery's own rating, and -- where the entry's options say
    it may -- limits export and restarts the inverter. Every one of those is
    put back and read back before the run reports success, and anything that
    could not be put back becomes a repair on the next start rather than a line
    in a log.

    What protects it is therefore not a dialog but the guard list in
    `sungrow_modbus.control_test`, which refuses the run outright when the
    inverter is not running, when there is no sun, when another client is
    polling, or when the battery is at a state of charge that would make a
    probe value unsafe.
    """

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for what pressing it does."""
        super().__init__(runtime_data, "run_control_test")

    @property
    def available(self) -> bool:
        """Unavailable while either part is running.

        One runner owns both parts and refuses a second run, because they share
        a serialized connection. With writes in the picture that stops being a
        politeness: two runs at once would restore each other's probe values.
        """
        return not self._runner.state.running

    async def async_press(self) -> None:
        """Run part A and then part B."""
        self._runner.async_start(control_test=True)


class SurveyProgressSensor(SurveyEntity, SensorEntity):
    """How far through the current survey is, in percent.

    **No `state_class`, deliberately.** A measurement state class makes the
    recorder keep long-term statistics, and those are the one thing here that
    would outlive the integration: deleting the config entry takes the
    entities, the device and their states with it -- measured -- but
    statistics rows survive their entity and turn into an "entity no longer
    exists" repair for somebody who uninstalled weeks ago. Hourly averages of
    a progress bar are meaningless anyway; what is worth keeping is the
    *step* sensor's plain history, which the recorder purges on its ordinary
    schedule.
    """

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for the fraction it reports."""
        super().__init__(runtime_data, "survey_progress")

    @property
    def native_value(self) -> int | None:
        """Percent complete, or None before the first run."""
        return self._runner.state.percent


class SurveyStepSensor(SurveyEntity, SensorEntity):
    """What the survey is reading right now.

    Its recorded history is the point of it: 19 probes and five timing reads
    in the order they happened, which is what tells a maintainer *where* a
    slow link stalls rather than that it did.
    """

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for the step it reports."""
        super().__init__(runtime_data, "survey_step")

    @property
    def native_value(self) -> str | None:
        """The current step, the last failure, or idle."""
        state = self._runner.state
        if state.running:
            return (state.step or f"starting the {state.part or 'survey'}")[:MAX_STATE]
        if state.error:
            return f"failed: {state.error}"[:MAX_STATE]
        if state.finished:
            return "finished"
        return "never run"


class SurveyResultSensor(SurveyEntity, SensorEntity):
    """When the last survey finished, with what it found beside it."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for the run it describes."""
        super().__init__(runtime_data, "survey_finished")

    @property
    def native_value(self) -> Any:
        """When the last run ended, or None if none has."""
        return self._runner.state.finished

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The numbers a summary line needs, without a second entity each."""
        state = self._runner.state
        control_test = state.control_test or {}
        return {
            "fields_read": state.fields_read,
            "error": state.error,
            "has_document": state.document is not None,
            # None rather than 0 when part B did not run, so a reader cannot
            # mistake "this run only read" for "the write test found nothing".
            "control_test_outcome": control_test.get("outcome_means"),
            "control_test_findings": _findings(control_test),
        }
