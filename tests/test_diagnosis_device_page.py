"""The diagnosis lives on the device page, and these are the things that buys.

It used to run inside the options flow behind an indeterminate spinner. Three
of its problems were structural rather than cosmetic, and each has a test
here: a modal cannot be left while it works, a spinner cannot say how far
along a quarter-hour read is, and a config flow has nowhere to put a download
button.

The fourth is the one that reshaped the integration. A device reaches the
registry only when an entity carrying its `device_info` is added -- so a
diagnostics-only entry, which deliberately had no entities at all, had no
device page to put any of this on. It has eight entities now, and nothing
else: that set is what these tests pin.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
import json
from pathlib import Path
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

import custom_components.sungrow_modbus as component
from custom_components.sungrow_modbus.const import (
    CONF_DIAGNOSIS_OTHER_INVERTER,
    CONF_DIAGNOSIS_PROXY,
    CONF_DIAGNOSIS_TRANSPORT,
    CONF_MODE,
    CONF_REPORTER,
    CONF_UNIT_ID,
    DIAGNOSIS_ISSUE_URL,
    DIAGNOSIS_MODE_AUTO_REPEAT,
    DIAGNOSIS_MODE_READ_ONLY,
    DOMAIN,
    LINK_VALID,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
    SECTION_DIAGNOSIS,
)
from custom_components.sungrow_modbus.diagnosis import DiagnosisRunner, DiagnosisState
from custom_components.sungrow_modbus.diagnosis_entities import DIAGNOSIS_ENTITIES
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
from sungrow_modbus import block_test, diagnosis_document as diagnosis

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: What a diagnostics-only entry creates, and the whole of it.
DIAGNOSTIC_ENTITIES = {
    # What Start runs: read-only, or with part B, which writes. Offered in
    # this mode too: the contributor who set an entry up to send a reading is
    # exactly the person whose hardware this project needs a write
    # measurement from.
    "select.sh10rt_diagnosis_mode",
    "button.sh10rt_diagnosis_start",
    "button.sh10rt_diagnosis_stop",
    "sensor.sh10rt_diagnosis_progress",
    "sensor.sh10rt_diagnosis_current_step",
    "sensor.sh10rt_diagnosis_last_finished",
    # When auto repeat may start next, and how many runs are kept.
    "sensor.sh10rt_diagnosis_next_attempt",
    "sensor.sh10rt_diagnosis_test_runs",
    # The capability test runs kept over a day, and the way to start again.
    "button.sh10rt_diagnosis_tests_clear_history",
    # The readings' checks gather for days and are cleared on their own, so
    # starting the runs afresh does not throw them away.
    "button.sh10rt_diagnosis_readings_clear_history",
    "sensor.sh10rt_diagnosis_test_summary",
    # Whether a single run leaves out what earlier runs established; kept.
    "switch.sh10rt_diagnosis_skip_completed_tests",
    # The kept runs' checks, counted by outcome; the five add up to the total.
    "sensor.sh10rt_diagnosis_tests_passed",
    "sensor.sh10rt_diagnosis_tests_failed",
    "sensor.sh10rt_diagnosis_tests_not_supported",
    "sensor.sh10rt_diagnosis_tests_inconclusive",
    "sensor.sh10rt_diagnosis_tests_not_run_yet",
}

#: Every entry gets this, whatever its mode: how the endpoint is reached,
#: which decides what a diagnosis can read.
CONNECTION = "sensor.sh10rt_connection"


class _TemporaryUnit:
    """What `async_get_temporary_unit` returns: a unit, in a context manager."""

    def __init__(self, unit: MockModbusUnit) -> None:
        self._unit = unit

    async def __aenter__(self) -> MockModbusUnit:
        return self._unit

    async def __aexit__(self, *args: object) -> None:
        return None


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, mode: str = MODE_DEVICES
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_MODE: mode},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


# --- what a diagnostics-only entry is made of ------------------------------


async def test_a_diagnostics_entry_has_the_diagnosis_and_nothing_else(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The mode, start, stop and history controls, a switch, and what watches the runs.

    The promise of this mode is that somebody who offered to send a reading
    does not get their house filled with entities. That still holds -- there
    is not one reading among these -- but "no entities at all" was too strong
    and left the mode without a device page.
    """
    await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    entities = {
        state.entity_id
        for state in hass.states.async_all()
        if state.entity_id.startswith(
            ("sensor.sh10rt", "button.sh10rt", "switch.sh10rt", "select.sh10rt")
        )
    }
    assert entities == DIAGNOSTIC_ENTITIES | {CONNECTION}


async def test_a_diagnostics_entry_polls_but_reports_no_readings(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The coordinators still run: a diagnosis needs the readings behind them."""
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    assert entry.runtime_data.coordinators
    assert hass.states.get("sensor.sh10rt_total_pv_input_power") is None


async def test_the_entities_give_the_entry_a_device_page(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Which is the reason they exist at all, and it is worth asserting.

    A device is registered as a side effect of adding an entity that carries
    its `device_info`. With no entities there is no device, and with no
    device there is nowhere for a button to live -- which is what made "no
    entities at all" untenable once the diagnosis moved out of the dialog.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert [device for device in devices if (DOMAIN, SERIAL) in device.identifiers]


async def test_an_ordinary_entry_gets_them_too(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """They used to be a diagnostics entry's alone, and that was the bug.

    An owner who installed this for solar readings is also the owner of a
    model whose register support this project can only measure. Leaving the
    diagnosis off their entry meant the only way to contribute was to give up
    the readings they came for, or to find an action in Developer tools. They
    are diagnostic-category entities, so Home Assistant keeps them under
    their own heading and out of the automatic dashboard.
    """
    await _setup(hass, sungrow_unit)

    for entity_id in DIAGNOSTIC_ENTITIES:
        assert hass.states.get(entity_id) is not None, entity_id
    assert hass.states.get("sensor.sh10rt_total_pv_input_power") is not None


async def test_an_ordinary_entry_can_also_run_one_as_an_action(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The button is not the only route, and the action predates it here.

    The action is the whole diagnosis: it reads, it builds the document, and
    it offers it in the same notification the button's run does. It is also
    what a script or an automation can call, which no button is.
    """
    entry = await _setup(hass, sungrow_unit)
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]

    await hass.services.async_call(
        DOMAIN,
        "run_diagnosis",
        {"device_id": device.id},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.diagnosis.state.document is not None


@pytest.mark.parametrize(("domain", "key"), DIAGNOSIS_ENTITIES)
async def test_every_diagnosis_entity_is_a_diagnostic_one(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, domain: str, key: str
) -> None:
    """They describe the integration, not the inverter.

    Home Assistant files diagnostic entities under their own heading and
    keeps them out of the automatic dashboard, which is where something that
    reports "probing input 13049" belongs.
    """
    await _setup(hass, sungrow_unit)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        Platform(domain), DOMAIN, f"{SERIAL}_{key}"
    )
    assert entity_id is not None, f"{domain}.{key} was never created"
    assert registry.async_get(entity_id).entity_category == "diagnostic"


# --- the runner, which is what the entities show ---------------------------


async def _choose(hass: HomeAssistant, mode: str) -> None:
    """Put *Diagnosis: mode* on one mode before Start is pressed.

    Explicit since the default became auto repeat (2026-11-16): a press with
    the mode untouched now arms the repeating extended test, so a test that
    means "one read-only run" has to say so.
    """
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.sh10rt_diagnosis_mode", "option": mode},
        blocking=True,
    )


async def test_the_button_runs_a_diagnosis_and_the_sensors_follow(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Press it, and the progress and step sensors report what happened."""
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    await _choose(hass, DIAGNOSIS_MODE_READ_ONLY)
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.sh10rt_diagnosis_start"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = entry.runtime_data.diagnosis.state
    assert state.running is False
    assert state.document is not None
    assert state.fields_read
    assert hass.states.get("sensor.sh10rt_diagnosis_progress").state == "100"
    assert hass.states.get("sensor.sh10rt_diagnosis_current_step").state == "finished"


async def test_the_button_runs_the_block_read_test_first(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The measurement `hybrid_inverter.layout` is changed from, without a terminal.

    Until it ran here only a contributor with Python and a checkout could take
    it, so somebody on Home Assistant OS could report "these entities stay empty"
    but never send the reading that says which register empties them. It runs
    before the probes, on an idle link, with every block the poll makes.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)
    seen: list[str] = []

    def _watch(event) -> None:
        if event.data["entity_id"] == "sensor.sh10rt_diagnosis_current_step":
            new = event.data["new_state"]
            if new is not None:
                seen.append(new.state)

    hass.bus.async_listen("state_changed", _watch)
    await _choose(hass, DIAGNOSIS_MODE_READ_ONLY)
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.sh10rt_diagnosis_start"},
        blocking=True,
    )
    await hass.async_block_till_done()

    document = entry.runtime_data.diagnosis.state.document
    measured = document["block_read_test"]
    assert len(measured["answered"]) == len(await block_test.inverter_blocks())
    assert measured["never_answered"] == []
    assert measured["client"] == block_test.CLIENT
    assert document["contention"]["block_read_test"].startswith("run")
    # First, before any probe: the probes are reads too.
    probes = {label for label, *_ in diagnosis.PROBES}
    last_block = max(i for i, step in enumerate(seen) if "block read" in step)
    first_probe = min(i for i, step in enumerate(seen) if step in probes)
    assert last_block < first_probe


async def test_the_step_sensor_records_what_is_being_read(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Its history is the log, which is the thing the spinner could not be.

    Asserted on the states the sensor passes through rather than on the
    runner: what a maintainer reads afterwards is the recorder's copy, and
    that only exists if the entity actually wrote each one.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    seen: list[str] = []

    def _watch(event) -> None:
        if event.data["entity_id"] == "sensor.sh10rt_diagnosis_current_step":
            new = event.data["new_state"]
            if new is not None:
                seen.append(new.state)

    hass.bus.async_listen("state_changed", _watch)
    entry.runtime_data.diagnosis.async_start()
    await hass.async_block_till_done()

    # Every probe announced itself, in order, before the run ended.
    assert len(seen) > 10
    assert seen[-1] == "finished"
    assert any("assembling the document" in step for step in seen)


async def test_a_second_press_while_one_runs_is_refused(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Two diagnoses interleaving their reads on one serialized connection.

    A Sungrow grants very few sessions, so the second run is refused rather
    than queued -- and the button reports itself unavailable while one is in
    flight, which is the half of that a person can see.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)
    runner = entry.runtime_data.diagnosis

    # The run has to be held open to test this at all. Against the mock unit
    # a diagnosis finishes without ever yielding, so the first task is already
    # done by the time `async_start` returns -- which is a property of the
    # mock, not of a real link, where 24 reads take between a second and a
    # quarter of an hour.
    holding = asyncio.Event()

    async def _slow(*args, **kwargs):
        await holding.wait()
        return {"readings": {"values": {}}}

    with patch(
        "custom_components.sungrow_modbus.diagnosis_document.async_build", _slow
    ):
        assert runner.async_start() is True
        await hass.async_block_till_done()

        assert runner.state.running is True
        assert runner.async_start() is False
        # And the button says so, rather than looking pressable.
        assert hass.states.get("button.sh10rt_diagnosis_start").state == (
            STATE_UNAVAILABLE
        )

        holding.set()
        await hass.async_block_till_done()

    # Once it is over, it can run again.
    assert runner.state.running is False
    assert runner.async_start() is True
    await hass.async_block_till_done()


async def test_a_failed_diagnosis_is_reported_rather_than_swallowed(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A link that cannot finish 24 reads is a finding in its own right."""
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    with patch(
        "custom_components.sungrow_modbus.diagnosis_document.async_build",
        side_effect=RuntimeError("Response timeout after 10.0 seconds"),
    ):
        entry.runtime_data.diagnosis.async_start()
        await hass.async_block_till_done()

    state = entry.runtime_data.diagnosis.state
    assert state.running is False
    assert "timeout" in state.error
    assert "failed" in hass.states.get("sensor.sh10rt_diagnosis_current_step").state


async def test_the_finished_diagnosis_offers_the_document(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A notification, because a sensor's attributes are not clickable.

    This is the one moment the integration has something to hand somebody,
    and the dialog it used to happen in was gone the moment it was dismissed.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as notify:
        entry.runtime_data.diagnosis.async_start()
        await hass.async_block_till_done()

    assert notify.called
    message = notify.call_args.args[1]
    assert f"/api/sungrow_modbus/diagnosis/{entry.entry_id}" in message
    assert DIAGNOSIS_ISSUE_URL in message
    assert "discord.gg" not in message
    assert "stand-in" in message


async def test_the_download_link_is_an_anchor_the_frontend_will_follow(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A markdown link here is dead on arrival, which is not obvious.

    Home Assistant's frontend intercepts every same-origin anchor that has no
    `target`, no `download` and no `rel="external"`: it calls
    preventDefault() and hands the path to the client-side router instead of
    the browser. `/api/sungrow_modbus/diagnosis/...` is not a panel, so the
    router does nothing and the link appears broken -- while the endpoint
    answers 200 to the identical URL from curl, which is how this was found.

    `target` is the escape to use because it is the only one of the three
    that survives the markdown sanitiser: its whitelist for an anchor is
    exactly ("target", "href", "title"), and `download` is added only when
    the element is asked to allow data URLs, which a notification is not.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as notify:
        entry.runtime_data.diagnosis.async_start()
        await hass.async_block_till_done()

    message = notify.call_args.args[1]
    assert f'<a href="/api/sungrow_modbus/diagnosis/{entry.entry_id}' in message
    assert 'target="_blank"' in message
    # The markdown form is the bug, so say so rather than only asserting the
    # cure: a later tidy-up that "simplifies" this back fails here.
    assert "[Download the document](" not in message


async def test_the_notification_says_when_the_link_stops_working(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Because the notification outlives the signature that makes it work.

    A signed path is valid for an hour; the notification sits in the sidebar
    until somebody dismisses it. An hour later the only visible thing is a
    link that 401s, which reads as a broken integration rather than as an
    expired grant. So the time is named, and the route that does not expire
    is named beside it.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as notify:
        entry.runtime_data.diagnosis.async_start()
        await hass.async_block_till_done()

    message = notify.call_args.args[1]
    assert "stops working at" in message
    assert "Download diagnostics" in message


async def test_an_expired_link_says_so_rather_than_sitting_there(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """When the hour is up the notification is rewritten, not removed.

    Removed would look like something went wrong, and the summary is worth
    keeping -- somebody may not have read it yet. What changes is the
    promise, which is the part that stopped being true.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)
    entry.runtime_data.diagnosis.async_start()
    await hass.async_block_till_done()

    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as notify:
        async_fire_time_changed(hass, dt_util.utcnow() + LINK_VALID + timedelta(1))
        await hass.async_block_till_done()

    message = notify.call_args.args[1]
    assert "has expired" in message
    assert "Download diagnostics" in message
    # The summary survives the rewrite: it is the part worth keeping.
    assert "registers probed" in message
    assert "authSig" not in message


async def test_a_second_run_does_not_inherit_the_first_one_s_expiry(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The timer belongs to a link, and a new run means a new link.

    Both notifications carry the same id, so a timer left over from the first
    run would overwrite the second run's message with "the link has expired"
    on a link that is minutes old.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)
    runner = entry.runtime_data.diagnosis

    runner.async_start()
    await hass.async_block_till_done()
    # Most of the hour passes, then a second diagnosis replaces the link.
    async_fire_time_changed(hass, dt_util.utcnow() + LINK_VALID - timedelta(minutes=1))
    await hass.async_block_till_done()
    runner.async_start()
    await hass.async_block_till_done()

    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as notify:
        # Past the first link's hour, well inside the second link's.
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
        await hass.async_block_till_done()

    assert not notify.called


# --- the state itself ------------------------------------------------------


@pytest.mark.parametrize(
    ("fraction", "percent"),
    [(None, None), (0.0, 0), (0.615, 62), (1.0, 100)],
)
def test_the_percentage_is_the_fraction_a_sensor_can_show(
    fraction: float | None, percent: int | None
) -> None:
    assert DiagnosisState(fraction=fraction).percent == percent


def test_a_runner_starts_idle(hass: HomeAssistant) -> None:
    """Nothing has run, which is different from something having run empty."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    state = DiagnosisRunner(hass, entry).state

    assert state.running is False
    assert state.fraction is None
    assert state.finished is None
    assert state.document is None


async def test_setup_points_at_the_questions_it_no_longer_asks(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A document with every testimony field empty was a real report.

    A contributor pressed the button, got a document in under ten seconds
    with nothing in it, and asked, reasonably, why they had not been asked.
    The diagnostics path answered that by putting the questions in the
    wizard; that path is gone, and what answers it now is the last screen of
    the one wizard there is, which names the section that holds them.

    So: the options page asks them, and the success dialog says where.
    """
    said = json.loads((Path(component.__file__).parent / "strings.json").read_text())[
        "config"
    ]["create_entry"]["default"]
    assert "Configure" in said

    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    section = next(
        value
        for marker, value in result["data_schema"].schema.items()
        if str(marker) == SECTION_DIAGNOSIS
    )
    asked = {str(key) for key in section.schema.schema}
    assert CONF_REPORTER in asked
    assert CONF_DIAGNOSIS_TRANSPORT in asked


async def test_the_answers_reach_the_document(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Asking is only worth anything if the answers are published."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_MODE: MODE_DIAGNOSTICS},
        options={CONF_REPORTER: "gerd", CONF_DIAGNOSIS_PROXY: "no"},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entry.runtime_data.diagnosis.async_start()
    await hass.async_block_till_done()

    said = entry.runtime_data.diagnosis.state.document["user_inputs"]
    assert said["reporter"] == "gerd"
    assert said["modbus_proxy"] == "no"


async def test_the_retired_diagnosis_controls_are_removed(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The two run buttons and the continuous switch the mode select replaced."""
    registry = er.async_get(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_MODE: MODE_DIAGNOSTICS},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    for domain, key in (
        ("button", "run_diagnosis"),
        ("button", "run_capability_test"),
        ("switch", "continuous_capability_test"),
    ):
        registry.async_get_or_create(
            domain, DOMAIN, f"{SERIAL}_{key}", config_entry=entry
        )
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    for domain, key in (
        ("button", "run_diagnosis"),
        ("button", "run_capability_test"),
        ("switch", "continuous_capability_test"),
    ):
        assert registry.async_get_entity_id(domain, DOMAIN, f"{SERIAL}_{key}") is None


async def test_choosing_an_extended_mode_says_the_questions_are_unanswered(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The warning a maintainer asked for, at the moment the mode is armed.

    Auto repeat can run for days, and a run whose document carries no
    testimony is one nobody can compare or ask about. So the questions are
    put when the mode is chosen, before Start is ever pressed.
    """
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.sungrow_modbus.async_get_unit",
            return_value=sungrow_unit,
        ),
        patch(
            "custom_components.sungrow_modbus.testimony"
            ".persistent_notification.async_create"
        ) as warned,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        await _choose(hass, DIAGNOSIS_MODE_AUTO_REPEAT)

    message = warned.call_args.args[1]
    assert "How this inverter is connected" in message
    assert "Is a Modbus proxy in the path?" in message
    assert "Is there another inverter here that is not a Sungrow?" in message
    # The name is in there as a suggestion, not among the refusals: this
    # project takes anonymous readings on purpose.
    assert "Your name or handle" in message


async def test_an_extended_run_is_refused_until_they_are_answered(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The gate itself: a press that writes, on an entry that cannot say where.

    A capability test's findings are read against the house they ran in, so
    the three questions no register answers are asked before the first write
    -- and refused as a `ServiceValidationError`, which is a dialog on a
    press and a line an automation can see, rather than a traceback.
    """
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        await _choose(hass, DIAGNOSIS_MODE_AUTO_REPEAT)
        # Asserted on the translation key rather than the rendered text: once
        # `exceptions.testimony_missing.message` existed, the error rendered
        # into English and a `match=` on the key stopped matching, though the
        # refusal itself was never in doubt. The key is the stable fact.
        with pytest.raises(ServiceValidationError) as refusal:
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": "button.sh10rt_diagnosis_start"},
                blocking=True,
            )
        assert refusal.value.translation_key == "testimony_missing"

    assert entry.runtime_data.diagnosis.continuous.active is False
    assert entry.runtime_data.diagnosis.state.running is False

    # Read-only is never refused: it writes nothing, and a reading with no
    # testimony is still a reading worth having.
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await _choose(hass, DIAGNOSIS_MODE_READ_ONLY)
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.sh10rt_diagnosis_start"},
            blocking=True,
        )
        await hass.async_block_till_done()

    assert entry.runtime_data.diagnosis.state.document is not None


async def test_an_entry_that_answered_them_gets_no_warning(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Answered is answered: the check is silent, and clears a stale warning."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        options={
            CONF_REPORTER: "gerd",
            CONF_DIAGNOSIS_TRANSPORT: "direct_lan",
            CONF_DIAGNOSIS_PROXY: "no",
            CONF_DIAGNOSIS_OTHER_INVERTER: "no",
        },
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.sungrow_modbus.async_get_unit",
            return_value=sungrow_unit,
        ),
        patch(
            "custom_components.sungrow_modbus.testimony"
            ".persistent_notification.async_create"
        ) as warned,
        patch(
            "custom_components.sungrow_modbus.testimony"
            ".persistent_notification.async_dismiss"
        ) as dismissed,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        await _choose(hass, DIAGNOSIS_MODE_AUTO_REPEAT)

    assert not warned.called
    assert dismissed.called
