"""The one question about a device this project cannot see.

A Sungrow does not measure house load. It computes it, from its own output
plus what the grid meter reports coming in — so a second, non-Sungrow inverter
feeding the same meter makes `load_power` low by exactly that inverter's
output. Continuously, while every register answers normally and every block
reads clean.

From a maintainer's end that is indistinguishable from a decoding fault, and
no register can settle it, because the inverter cannot see the thing that is
confusing it. So it is asked, and the answer is published.

**Yes opens a second question; no does not.** That shape is the reason these
tests exist: a config flow form is built before it is sent and cannot reveal a
field when an answer changes, so "ask what it is, but only if there is one"
has to be a step of its own, in both the setup flow and the options page.
"""

import json
from pathlib import Path
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant.common import MockConfigEntry

import custom_components.sungrow_modbus as component
from custom_components.sungrow_modbus.const import (
    CONF_DIAGNOSIS_OTHER_INVERTER,
    CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL,
    CONF_MODE,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DIAGNOSTICS,
    SECTION_ADVANCED,
    SECTION_CAPABILITY_TEST,
    SECTION_DIAGNOSIS,
    SECTION_EXTERNAL,
    SECTION_PERMISSIONS,
    SECTION_POLLING,
)
from custom_components.sungrow_modbus.diagnosis_document import async_build, summarise
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from sungrow_modbus.diagnosis_document import OTHER_INVERTER_CLAIMS, OTHER_INVERTER_YES

from .conftest import SERIAL


class _TemporaryUnit:
    """What `async_get_temporary_unit` returns: a unit, in a context manager."""

    def __init__(self, unit: MockModbusUnit) -> None:
        self._unit = unit

    async def __aenter__(self) -> MockModbusUnit:
        return self._unit

    async def __aexit__(self, *args: object) -> None:
        return None


def _options(**sections: dict) -> dict:
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


async def _entry(
    hass: HomeAssistant, unit: MockModbusUnit, options: dict | None = None
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.178.35",
            CONF_PORT: 502,
            CONF_UNIT_ID: 1,
            CONF_MODE: MODE_DIAGNOSTICS,
        },
        options=options or {},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


# -- on the options page -------------------------------------------------------


async def test_the_options_page_asks_the_follow_up_too(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Somebody who gains a second inverter changes their answer here.

    And everything else typed on the page has to survive the detour: options
    are only written when a flow ends, so the page is held while the question
    is put — the same reason `async_step_promote` works that way.
    """
    entry = await _entry(hass, sungrow_unit)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            _options(
                **{
                    SECTION_DIAGNOSIS: {
                        CONF_DIAGNOSIS_OTHER_INVERTER: OTHER_INVERTER_YES,
                        "reporter": "martin",
                    }
                }
            ),
        )
        assert result["step_id"] == "other_inverter"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL: "5 kW on the south roof"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (
        entry.options[CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL] == "5 kW on the south roof"
    )
    # The rest of the page was not lost on the way through the question.
    assert entry.options["reporter"] == "martin"


async def test_an_answer_already_given_is_not_asked_for_again(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Changing a poll interval should not re-put a question already answered."""
    entry = await _entry(
        hass,
        sungrow_unit,
        {
            CONF_DIAGNOSIS_OTHER_INVERTER: OTHER_INVERTER_YES,
            CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL: "Fronius Symo 8.2",
        },
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            _options(
                **{
                    SECTION_DIAGNOSIS: {
                        CONF_DIAGNOSIS_OTHER_INVERTER: OTHER_INVERTER_YES
                    }
                }
            ),
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL] == "Fronius Symo 8.2"


# -- and into the file ---------------------------------------------------------


async def test_the_document_carries_the_answer(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """In `user_inputs`, where every claim lives and no reading does."""
    entry = await _entry(
        hass,
        sungrow_unit,
        {
            CONF_DIAGNOSIS_OTHER_INVERTER: OTHER_INVERTER_YES,
            CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL: "Fronius Symo 8.2",
        },
    )

    document = await async_build(hass, entry)

    assert document["user_inputs"]["other_inverter"] == OTHER_INVERTER_YES
    assert document["user_inputs"]["other_inverter_detail"] == "Fronius Symo 8.2"
    assert document["user_inputs"]["other_inverter"] in OTHER_INVERTER_CLAIMS
    # A claim, never a measurement: nothing outside `user_inputs` repeats it.
    readings = {key: value for key, value in document.items() if key != "user_inputs"}
    assert "Fronius" not in str(readings)


async def test_the_summary_says_so_where_a_contributor_will_see_it(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The notification is the only part of a document most people read.

    And this is the line that stops a maintainer chasing a load figure that
    was never wrong.
    """
    entry = await _entry(
        hass,
        sungrow_unit,
        {
            CONF_DIAGNOSIS_OTHER_INVERTER: OTHER_INVERTER_YES,
            CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL: "Fronius Symo 8.2",
        },
    )

    said = summarise(await async_build(hass, entry))

    assert "non-Sungrow inverter" in said
    assert "Fronius Symo 8.2" in said
    # And a one-inverter house is told nothing about it.
    plain = summarise(await async_build(hass, await _entry(hass, sungrow_unit)))
    assert "non-Sungrow" not in plain


async def test_the_last_screen_says_where_the_file_will_be(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The wizard ends having read nothing, and has to say so.

    The diagnosis is a button somebody has to find, and its document arrives
    in a notification they have no reason to be watching. Both were reported
    by a contributor who ran the diagnosis and then asked where the file had
    gone. This used to be answered on the diagnostics path's own success
    dialog; that path is gone, so it is on the only one left, which everybody
    now sees.
    """
    strings = json.loads((Path(component.__file__).parent / "strings.json").read_text())
    said = strings["config"]["create_entry"]["default"]

    assert "Diagnosis: start" in said
    assert "Download diagnostics" in said
    assert "{diagnosis_issue_url}" in said
