"""The survey lives on the device page, and these are the things that buys.

It used to run inside the options flow behind an indeterminate spinner. Three
of its problems were structural rather than cosmetic, and each has a test
here: a modal cannot be left while it works, a spinner cannot say how far
along a quarter-hour read is, and a config flow has nowhere to put a download
button.

The fourth is the one that reshaped the integration. A device reaches the
registry only when an entity carrying its `device_info` is added -- so a
diagnostics-only entry, which deliberately had no entities at all, had no
device page to put any of this on. It has five entities now, and nothing
else: that set is what these tests pin.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.sungrow_modbus.const import (
    CONF_MODE,
    CONF_PUBLISH_ADDRESS,
    CONF_REPORTER,
    CONF_SURVEY_PROXY,
    CONF_SURVEY_TRANSPORT,
    CONF_UNIT_ID,
    DOMAIN,
    LINK_VALID,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
)
from custom_components.sungrow_modbus.survey import SurveyRunner, SurveyState
from custom_components.sungrow_modbus.survey_entities import SURVEY_ENTITIES
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: What a diagnostics-only entry creates, and the whole of it.
DIAGNOSTIC_ENTITIES = {
    "button.sh10rt_run_capability_survey",
    # Part B, which writes. Present in this mode too: the contributor who set
    # an entry up to send a reading is exactly the person whose hardware this
    # project needs a write measurement from.
    "button.sh10rt_run_control_write_test",
    "sensor.sh10rt_survey_progress",
    "sensor.sh10rt_survey_step",
    "sensor.sh10rt_survey_finished",
}


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


async def test_a_diagnostics_entry_has_the_survey_and_nothing_else(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Five entities: the two buttons, and the three that watch them.

    The promise of this mode is that somebody who offered to send a reading
    does not get their house filled with entities. That still holds -- there
    is not one reading among these -- but "no entities at all" was too strong
    and left the mode without a device page.
    """
    await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    entities = {
        state.entity_id
        for state in hass.states.async_all()
        if state.entity_id.startswith(("sensor.sh10rt", "button.sh10rt"))
    }
    assert entities == DIAGNOSTIC_ENTITIES


async def test_a_diagnostics_entry_polls_but_reports_no_readings(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The coordinators still run: a survey needs the readings behind them."""
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    assert entry.runtime_data.coordinators
    assert hass.states.get("sensor.sh10rt_total_dc_power") is None


async def test_the_entities_give_the_entry_a_device_page(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Which is the reason they exist at all, and it is worth asserting.

    A device is registered as a side effect of adding an entity that carries
    its `device_info`. With no entities there is no device, and with no
    device there is nowhere for a button to live -- which is what made "no
    entities at all" untenable once the survey moved out of the dialog.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert [device for device in devices if (DOMAIN, SERIAL) in device.identifiers]


async def test_an_ordinary_entry_gets_none_of_them(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Somebody who installed this for solar readings asked for solar readings.

    Deleting an entry removes its entities cleanly either way, so this is not
    about cleanup -- it is about not putting five diagnostic entities into
    every install's registry, history and entity pickers to begin with. That
    owner helps through the `run_survey` action, which leaves nothing behind
    at all.
    """
    await _setup(hass, sungrow_unit)

    for entity_id in DIAGNOSTIC_ENTITIES:
        assert hass.states.get(entity_id) is None, entity_id
    assert hass.states.get("sensor.sh10rt_total_dc_power") is not None


async def test_an_ordinary_entry_can_still_run_one_as_an_action(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Helping is not something only a diagnostics entry can do.

    The action is the whole survey: it reads, it builds the document, and it
    offers it in the same notification the button's run does.
    """
    entry = await _setup(hass, sungrow_unit)
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]

    await hass.services.async_call(
        DOMAIN,
        "run_survey",
        {"device_id": device.id},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.survey.state.document is not None
    # And nothing was created to make that possible.
    for entity_id in DIAGNOSTIC_ENTITIES:
        assert hass.states.get(entity_id) is None, entity_id


@pytest.mark.parametrize(("domain", "key"), SURVEY_ENTITIES)
async def test_every_survey_entity_is_a_diagnostic_one(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, domain: str, key: str
) -> None:
    """They describe the integration, not the inverter.

    Home Assistant files diagnostic entities under their own heading and
    keeps them out of the automatic dashboard, which is where something that
    reports "probing input 13049" belongs.
    """
    await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        Platform(domain), DOMAIN, f"{SERIAL}_{key}"
    )
    assert entity_id is not None, f"{domain}.{key} was never created"
    assert registry.async_get(entity_id).entity_category == "diagnostic"


# --- the runner, which is what the entities show ---------------------------


async def test_the_button_runs_a_survey_and_the_sensors_follow(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Press it, and the progress and step sensors report what happened."""
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.sh10rt_run_capability_survey"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = entry.runtime_data.survey.state
    assert state.running is False
    assert state.document is not None
    assert state.fields_read
    assert hass.states.get("sensor.sh10rt_survey_progress").state == "100"
    assert hass.states.get("sensor.sh10rt_survey_step").state == "finished"


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
        if event.data["entity_id"] == "sensor.sh10rt_survey_step":
            new = event.data["new_state"]
            if new is not None:
                seen.append(new.state)

    hass.bus.async_listen("state_changed", _watch)
    entry.runtime_data.survey.async_start()
    await hass.async_block_till_done()

    # Every probe announced itself, in order, before the run ended.
    assert len(seen) > 10
    assert seen[-1] == "finished"
    assert any("timing the link" in step for step in seen)


async def test_a_second_press_while_one_runs_is_refused(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Two surveys interleaving their reads on one serialized connection.

    A Sungrow grants very few sessions, so the second run is refused rather
    than queued -- and the button reports itself unavailable while one is in
    flight, which is the half of that a person can see.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)
    runner = entry.runtime_data.survey

    # The run has to be held open to test this at all. Against the mock unit
    # a survey finishes without ever yielding, so the first task is already
    # done by the time `async_start` returns -- which is a property of the
    # mock, not of a real link, where 24 reads take between a second and a
    # quarter of an hour.
    holding = asyncio.Event()

    async def _slow(*args, **kwargs):
        await holding.wait()
        return {"readings": {"values": {}}}

    with patch("custom_components.sungrow_modbus.fingerprint.async_build", _slow):
        assert runner.async_start() is True
        await hass.async_block_till_done()

        assert runner.state.running is True
        assert runner.async_start() is False
        # And the button says so, rather than looking pressable.
        assert hass.states.get("button.sh10rt_run_capability_survey").state == (
            STATE_UNAVAILABLE
        )

        holding.set()
        await hass.async_block_till_done()

    # Once it is over, it can run again.
    assert runner.state.running is False
    assert runner.async_start() is True
    await hass.async_block_till_done()


async def test_a_failed_survey_is_reported_rather_than_swallowed(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A link that cannot finish 24 reads is a finding in its own right."""
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    with patch(
        "custom_components.sungrow_modbus.fingerprint.async_build",
        side_effect=RuntimeError("Response timeout after 10.0 seconds"),
    ):
        entry.runtime_data.survey.async_start()
        await hass.async_block_till_done()

    state = entry.runtime_data.survey.state
    assert state.running is False
    assert "timeout" in state.error
    assert "failed" in hass.states.get("sensor.sh10rt_survey_step").state


async def test_the_finished_survey_offers_the_document(
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
        entry.runtime_data.survey.async_start()
        await hass.async_block_till_done()

    assert notify.called
    message = notify.call_args.args[1]
    assert f"/api/sungrow_modbus/survey/{entry.entry_id}" in message
    assert "compatibility_report.yml" in message
    assert "discord.gg" in message
    assert "stand-in" in message


async def test_the_download_link_is_an_anchor_the_frontend_will_follow(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A markdown link here is dead on arrival, which is not obvious.

    Home Assistant's frontend intercepts every same-origin anchor that has no
    `target`, no `download` and no `rel="external"`: it calls
    preventDefault() and hands the path to the client-side router instead of
    the browser. `/api/sungrow_modbus/survey/...` is not a panel, so the
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
        entry.runtime_data.survey.async_start()
        await hass.async_block_till_done()

    message = notify.call_args.args[1]
    assert f'<a href="/api/sungrow_modbus/survey/{entry.entry_id}' in message
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
        entry.runtime_data.survey.async_start()
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
    entry.runtime_data.survey.async_start()
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
    runner = entry.runtime_data.survey

    runner.async_start()
    await hass.async_block_till_done()
    # Most of the hour passes, then a second survey replaces the link.
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
    assert SurveyState(fraction=fraction).percent == percent


def test_a_runner_starts_idle(hass: HomeAssistant) -> None:
    """Nothing has run, which is different from something having run empty."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    state = SurveyRunner(hass, entry).state

    assert state.running is False
    assert state.fraction is None
    assert state.finished is None
    assert state.document is None


async def test_the_diagnostics_path_asks_before_it_finishes(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Somebody who chose this mode came to help, so ask them while they are here.

    The failure this fixes was reported from a real installation: the button
    produced a document in under ten seconds with every testimony field
    empty, and the contributor's reasonable reaction was "why was I not
    asked?". The questions were on an options page they had no reason to
    open.

    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_diagnostics"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )

    with (
        patch(
            "custom_components.sungrow_modbus.async_get_unit",
            return_value=sungrow_unit,
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
            # The probe uses it as an async context manager, so a bare mock
            # unit will not do.
            return_value=_TemporaryUnit(sungrow_unit),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1},
        )

        # Not straight to an entry: the questions come first.
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "testimony"
        assert "Already measured" in result["description_placeholders"]["measured"]

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_REPORTER: "a contributor",
                CONF_SURVEY_TRANSPORT: "direct_lan",
                CONF_SURVEY_PROXY: "no",
                CONF_PUBLISH_ADDRESS: False,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    # Straight into the options, which is where the survey reads them from.
    assert result["options"][CONF_REPORTER] == "a contributor"
    assert result["options"][CONF_SURVEY_TRANSPORT] == "direct_lan"


async def test_the_answers_reach_the_document(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Asking is only worth anything if the answers are published."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_MODE: MODE_DIAGNOSTICS},
        options={CONF_REPORTER: "gerd", CONF_SURVEY_PROXY: "no"},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entry.runtime_data.survey.async_start()
    await hass.async_block_till_done()

    said = entry.runtime_data.survey.state.document["user_inputs"]
    assert said["reporter"] == "gerd"
    assert said["modbus_proxy"] == "no"
