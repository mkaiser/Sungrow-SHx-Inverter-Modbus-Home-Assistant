"""There is one setup, it makes entities, and it carries the diagnosis.

The preview opened with a question -- is this entry for your inverter, or for
a reading to send in? -- behind a release flag that allowed only the second
answer. Both are gone. Setup goes straight to the wiring, always creates a
devices entry, and puts the diagnosis and the capability test on the same
device page as the readings.

That last part is the half worth testing hardest. The diagnosis entities used
to exist only on an entry that had nothing else, which meant the one way this
project measures what a model answers was reachable only by somebody who had
given up their sensors to get it. Now every entry has both, and nothing but
these assertions keeps the platforms from quietly going back.

`MODE_DIAGNOSTICS` is still a mode, because entries made while it was offered
are still out there. They load, they keep their entities, and `add_devices` on
their options page is the way across to an ordinary one.
"""

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_ADD_DEVICES,
    CONF_ENTITY_IDS,
    CONF_MODE,
    CONF_UNIT_ID,
    DIAGNOSIS_MODE_AUTO_REPEAT,
    DIAGNOSIS_MODE_EXTENDED,
    DIAGNOSIS_MODE_READ_ONLY,
    DOMAIN,
    ENTITY_IDS_NEW,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from .conftest import SERIAL

HOST = "192.168.178.35"


class _TemporaryUnit:
    """What `async_get_temporary_unit` returns: a unit, in a context manager."""

    def __init__(self, unit: MockModbusUnit) -> None:
        self._unit = unit

    async def __aenter__(self) -> MockModbusUnit:
        return self._unit

    async def __aexit__(self, *args: object) -> None:
        return None


async def _set_up(hass: HomeAssistant, unit: MockModbusUnit) -> dict:
    """Walk the whole setup, by hand, from Add integration to the entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    with (
        patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
            return_value=_TemporaryUnit(unit),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST, CONF_UNIT_ID: 1}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    return result


def _entity_ids(hass: HomeAssistant, entry_id: str) -> list[str]:
    return [
        entity.entity_id
        for entity in er.async_entries_for_config_entry(er.async_get(hass), entry_id)
    ]


# -- the door that is no longer there ------------------------------------------


async def test_setup_opens_on_the_wiring_not_on_a_question(
    hass: HomeAssistant,
) -> None:
    """Add integration goes straight to "where is it?", with no mode to pick."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {"search", "manual"}


async def test_the_entry_it_makes_has_entities(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Devices mode, new ids, and readings -- without anybody choosing any of it."""
    result = await _set_up(hass, sungrow_unit)

    assert result["data"][CONF_MODE] == MODE_DEVICES
    assert result["data"][CONF_ENTITY_IDS] == ENTITY_IDS_NEW
    assert any(
        entity_id.endswith("_total_pv_input_power")
        for entity_id in _entity_ids(hass, result["result"].entry_id)
    )


async def test_the_success_dialog_asks_for_a_reading(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The ask used to live on the diagnostics path's own last screen.

    That path is gone, and with it the only place a new owner was ever told
    that this project measures rather than looks up. So it moved here, where
    everybody now lands, rather than being dropped with the dialog it was on.
    """
    result = await _set_up(hass, sungrow_unit)

    assert result["description"] == "default"
    assert "diagnosis_issue_url" in result["description_placeholders"]


# -- the diagnosis, on an ordinary entry ---------------------------------------


async def test_an_ordinary_entry_carries_the_diagnosis(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Mode select, start and stop, the test summary -- beside the readings.

    One assertion per platform, because each gates them separately and a
    regression would take one platform at a time.
    """
    result = await _set_up(hass, sungrow_unit)
    entity_ids = _entity_ids(hass, result["result"].entry_id)

    for suffix, domain in (
        ("_diagnosis_mode", "select"),
        ("_diagnosis_start", "button"),
        ("_diagnosis_stop", "button"),
        ("_diagnosis_progress", "sensor"),
        ("_diagnosis_test_summary", "sensor"),
        ("_diagnosis_skip_completed_tests", "switch"),
        ("_diagnosis_tests_clear_history", "button"),
    ):
        assert any(
            entity_id.startswith(f"{domain}.") and entity_id.endswith(suffix)
            for entity_id in entity_ids
        ), f"{domain}{suffix} is missing from an ordinary entry"


async def test_the_ordinary_entry_still_has_its_controls(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The diagnosis was added beside them, not in front of them.

    Selects and switches, not buttons: every button an ordinary entry has is
    a command gated on a capability a watched write grants, and this fixture
    grants none -- so an empty button list here says nothing either way.
    """
    result = await _set_up(hass, sungrow_unit)
    entity_ids = _entity_ids(hass, result["result"].entry_id)

    for domain in ("select", "switch"):
        assert any(
            entity_id.startswith(f"{domain}.") and "diagnosis" not in entity_id
            for entity_id in entity_ids
        ), f"the settings on the {domain} platform went missing"


async def test_every_mode_is_offered(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Read-only, one extended run and auto repeat, on a hybrid."""
    result = await _set_up(hass, sungrow_unit)
    mode = next(
        entity_id
        for entity_id in _entity_ids(hass, result["result"].entry_id)
        if entity_id.endswith("_diagnosis_mode")
    )

    state = hass.states.get(mode)
    assert state is not None
    assert set(state.attributes["options"]) == {
        DIAGNOSIS_MODE_READ_ONLY,
        DIAGNOSIS_MODE_EXTENDED,
        DIAGNOSIS_MODE_AUTO_REPEAT,
    }
    # Auto repeat is where a new entry sits (maintainer, 2026-11-16): one
    # read-only pass settles almost nothing still open, and the ledger is
    # built from a collection over a day and a night. So a press of Start on
    # an untouched entry arms the repeating extended test, which writes.
    assert state.state == DIAGNOSIS_MODE_AUTO_REPEAT


# -- the entries made while the other mode was offered -------------------------


async def test_a_diagnostics_entry_still_loads(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Nothing new makes one; the ones that exist are not broken by that."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_PORT: 502,
            CONF_UNIT_ID: 1,
            CONF_MODE: MODE_DIAGNOSTICS,
        },
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("sensor.sh10rt_total_pv_input_power") is None
    assert any(
        entity_id.endswith("_diagnosis_mode")
        for entity_id in _entity_ids(hass, entry.entry_id)
    )

    # And it is offered the way across, not greyed any more.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert CONF_ADD_DEVICES in str(result["data_schema"].schema)
