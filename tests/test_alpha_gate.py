"""The first alpha offers only diagnostics mode, and says so rather than hiding it.

`ONLY_DIAGNOSIS_MODE` shuts the two doors that create a devices entry: the
question the config flow opens with, and the promotion toggle on a diagnostics
entry's options page. Everything behind those doors stays built and stays
tested -- `tests/conftest.py`'s `devices_mode_offered` fixture is what keeps
that true -- so this file tests the doors themselves, from both sides.

Both halves matter. Shut, because shipping an irreversible entity-id decision
in an alpha is the thing being avoided. Open, because the flag's whole promise
is that flipping it restores exactly what was there before, and a promise
nothing checks is a promise that quietly stops being kept.

While the gate is shut the opening menu offers only the diagnosis, and its
description says why the ordinary setup is not there.

One way past it is meant: a switch on the diagnostics setup's last dialog,
off by default and offered only while the gate is shut, that creates the
entities for testing, under new ids and never the YAML package's.
"""

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_ADD_DEVICES,
    CONF_ENTITY_IDS,
    CONF_MODE,
    CONF_TEST_ENTITIES,
    CONF_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_NEW,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
    SECTION_ADVANCED,
    SECTION_CAPABILITY_TEST,
    SECTION_DIAGNOSIS,
    SECTION_EXTERNAL,
    SECTION_PERMISSIONS,
    SECTION_POLLING,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import entity_registry as er

from .conftest import SERIAL


class _TemporaryUnit:
    """What `async_get_temporary_unit` returns: a unit, in a context manager."""

    def __init__(self, unit: MockModbusUnit) -> None:
        self._unit = unit

    async def __aenter__(self) -> MockModbusUnit:
        return self._unit

    async def __aexit__(self, *args: object) -> None:
        return None


def _selector_config(schema: dict, key: str) -> dict:
    """Return the selector config the frontend will see for one field.

    Asserted on rather than on a rendered dialog because `read_only` is
    precisely what the frontend keys off: it turns the field into
    `disabled: true` and then leaves its value out of what it submits. If it
    survives to here, the greying happens.
    """
    for marker, value in schema.items():
        if marker == key or getattr(marker, "schema", None) == key:
            return value.config
    raise AssertionError(f"{key} is not in the schema")


async def _diagnostics_entry(
    hass: HomeAssistant, unit: MockModbusUnit
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.178.35",
            CONF_PORT: 502,
            CONF_UNIT_ID: 1,
            CONF_MODE: MODE_DIAGNOSTICS,
        },
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _options(**sections: dict) -> dict:
    """Build a full options submission, overriding one section at a time."""
    payload: dict = {
        SECTION_POLLING: {},
        SECTION_PERMISSIONS: {},
        SECTION_EXTERNAL: {},
        SECTION_ADVANCED: {},
        SECTION_DIAGNOSIS: {},
        SECTION_CAPABILITY_TEST: {},
    }
    payload.update(sections)
    return payload


# -- the door at setup ---------------------------------------------------------


async def test_only_the_diagnosis_is_offered(
    hass: HomeAssistant,
) -> None:
    """An answer that cannot be taken is not put on the menu, nor introduced."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["setup_diagnostics"]
    assert result["description_placeholders"]["mode_intro"] == ""


async def test_the_menu_warns_before_the_button_is_pressed(
    hass: HomeAssistant,
) -> None:
    """Cheaper than finding out afterwards, and the menu has room for it."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    said = result["description_placeholders"]["mode_choice"]
    assert "not in this release" in said
    assert "later release" in said
    # And nothing is left for the dialog to render as a literal placeholder.
    assert "{" not in said


async def test_the_working_answer_is_untouched(
    hass: HomeAssistant,
) -> None:
    """The gate must not make the mode that *is* shipping any harder to reach."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_diagnostics"}
    )

    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {"search", "manual"}


async def test_the_unavailable_answer_cannot_be_posted_by_hand(
    hass: HomeAssistant,
) -> None:
    """The refusal that matters, and the one a screen control cannot make.

    A menu step id is chosen by the client, so leaving the answer off the
    menu is only a courtesy unless posting it anyway gets nowhere.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )


# -- the test switch on the last setup dialog ----------------------------------


async def _to_testimony(hass: HomeAssistant, unit: MockModbusUnit) -> dict:
    """Walk the diagnostics setup as far as its last dialog."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_diagnostics"}
    )
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
            result["flow_id"], {CONF_HOST: "192.168.178.35", CONF_UNIT_ID: 1}
        )
    assert result["step_id"] == "testimony"
    return result


async def _finish(
    hass: HomeAssistant, unit: MockModbusUnit, result: dict, answers: dict
) -> dict:
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], answers
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    return result


def _entities(hass: HomeAssistant, result: dict) -> list[str]:
    return [
        entity.entity_id
        for entity in er.async_entries_for_config_entry(
            er.async_get(hass), result["result"].entry_id
        )
    ]


async def test_the_test_switch_is_offered_and_off(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Last on the page, and off unless somebody turns it on."""
    result = await _to_testimony(hass, sungrow_unit)

    keys = [str(key) for key in result["data_schema"].schema]
    assert keys[-1] == CONF_TEST_ENTITIES
    defaults = result["data_schema"]({})
    assert defaults[CONF_TEST_ENTITIES] is False


async def test_left_off_the_entry_is_diagnostics_only(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    result = await _finish(
        hass, sungrow_unit, await _to_testimony(hass, sungrow_unit), {}
    )

    assert result["data"][CONF_MODE] == MODE_DIAGNOSTICS
    assert CONF_TEST_ENTITIES not in result["options"]
    assert hass.states.get("sensor.sh10rt_total_pv_input_power") is None


async def test_turned_on_the_entities_are_created_under_new_ids(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A devices entry, and the YAML package's ids never: that is the gate's point."""
    result = await _finish(
        hass,
        sungrow_unit,
        await _to_testimony(hass, sungrow_unit),
        {CONF_TEST_ENTITIES: True},
    )

    assert result["data"][CONF_MODE] == MODE_DEVICES
    assert result["data"][CONF_ENTITY_IDS] == ENTITY_IDS_NEW
    # Not a setting: it decided the mode and is not kept.
    assert CONF_TEST_ENTITIES not in result["options"]
    assert any(
        entity_id.endswith("_total_pv_input_power")
        for entity_id in _entities(hass, result)
    )


async def test_the_open_gate_has_no_test_switch(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, devices_mode_offered: None
) -> None:
    """With the gate open the menu offers the real setup, so the switch goes."""
    result = await _to_testimony(hass, sungrow_unit)

    assert CONF_TEST_ENTITIES not in {str(key) for key in result["data_schema"].schema}


# -- the door on the options page ----------------------------------------------


async def test_the_promotion_toggle_is_shown_and_greyed(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Shown, because an owner should know the entry is not a dead end."""
    entry = await _diagnostics_entry(hass, sungrow_unit)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    config = _selector_config(result["data_schema"].schema, CONF_ADD_DEVICES)
    assert config["read_only"] is True
    assert "not in this release" in result["description_placeholders"]["devices_mode"]


async def test_promotion_asked_for_by_hand_does_not_happen(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Same reasoning as the setup step, and the worse outcome if it worked.

    Promotion is what creates entities and puts the entity-id question. A
    crafted payload reaching it would hand somebody the irreversible decision
    this release is deliberately not shipping.
    """
    entry = await _diagnostics_entry(hass, sungrow_unit)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], _options(**{CONF_ADD_DEVICES: True})
        )
        await hass.async_block_till_done()

    # The options were still saved -- the toggle is ignored, not fatal.
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_MODE] == MODE_DIAGNOSTICS
    assert hass.states.get("sensor.sh10rt_total_pv_input_power") is None


async def test_an_entry_that_is_already_devices_mode_still_works(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The gate is on creating one, not on having one.

    Somebody restoring a backup, or carrying an entry over from an earlier
    build, keeps their entities and their options page. A release flag that
    broke an existing installation would be a far worse bug than the one it
    is preventing.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.178.35",
            CONF_PORT: 502,
            CONF_UNIT_ID: 1,
            CONF_MODE: MODE_DEVICES,
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

    assert hass.states.get("sensor.sh10rt_total_pv_input_power") is not None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    # No promotion toggle, because there is nothing to promote -- which is
    # today's behaviour and nothing the gate changed.
    assert CONF_ADD_DEVICES not in str(result["data_schema"].schema)


# -- and the other side of the flag --------------------------------------------


async def test_opening_the_gate_restores_the_menu_exactly(
    hass: HomeAssistant, devices_mode_offered: None
) -> None:
    """The flag's whole promise, and the reason it is one line.

    Flipping it must bring back the menu and the working devices path, with
    no second edit anywhere. If this ever fails, the gate has grown into a
    fork and the release after the alpha becomes a merge.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {"setup_devices", "setup_diagnostics"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_devices"}
    )
    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {"search", "manual"}


async def test_the_open_gate_explains_the_choice_instead_of_the_restriction(
    hass: HomeAssistant, devices_mode_offered: None
) -> None:
    """One placeholder, two states, and neither leaves a brace on screen."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    said = result["description_placeholders"]["mode_choice"]
    assert "Both answers are fine" in said
    assert "not in this release" not in said
    assert "Set up my inverter" in result["description_placeholders"]["mode_intro"]
