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

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_MODE,
    CONF_SURVEY_OTHER_INVERTER,
    CONF_SURVEY_OTHER_INVERTER_DETAIL,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DIAGNOSTICS,
    SECTION_ADVANCED,
    SECTION_EXTERNAL,
    SECTION_PERMISSIONS,
    SECTION_POLLING,
    SECTION_SURVEY,
)
from custom_components.sungrow_modbus.fingerprint import async_build, summarise
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from sungrow_modbus.fingerprint import OTHER_INVERTER_CLAIMS, OTHER_INVERTER_YES

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
        SECTION_SURVEY: {},
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


async def _to_testimony(hass: HomeAssistant, unit: MockModbusUnit) -> dict:
    """Walk the diagnostics path as far as the questions."""
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


# -- at setup ------------------------------------------------------------------


async def test_saying_no_does_not_ask_what_it_is(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Which is the whole reason this is a step and not a text box.

    Most installations have one inverter, and a box they have to look at and
    decide to leave empty is worse than a question they are never asked.
    """
    result = await _to_testimony(hass, sungrow_unit)

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SURVEY_OTHER_INVERTER: "no"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_SURVEY_OTHER_INVERTER] == "no"
    assert not result["options"].get(CONF_SURVEY_OTHER_INVERTER_DETAIL)


async def test_saying_yes_asks_what_it_is(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """And keeps the answer, because the size says how large the error is."""
    result = await _to_testimony(hass, sungrow_unit)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SURVEY_OTHER_INVERTER: OTHER_INVERTER_YES}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "other_inverter"

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_SURVEY_OTHER_INVERTER_DETAIL: "Fronius Symo 8.2"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_SURVEY_OTHER_INVERTER] == OTHER_INVERTER_YES
    assert result["options"][CONF_SURVEY_OTHER_INVERTER_DETAIL] == "Fronius Symo 8.2"


async def test_leaving_the_question_alone_records_nothing(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Empty is a real answer and it means the question was not put.

    The format has always kept that apart from a "no", and a field arriving
    must not turn every silence already in the corpus into a denial.
    """
    result = await _to_testimony(hass, sungrow_unit)

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert not result["options"].get(CONF_SURVEY_OTHER_INVERTER)


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
                    SECTION_SURVEY: {
                        CONF_SURVEY_OTHER_INVERTER: OTHER_INVERTER_YES,
                        "reporter": "martin",
                    }
                }
            ),
        )
        assert result["step_id"] == "other_inverter"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_SURVEY_OTHER_INVERTER_DETAIL: "5 kW on the south roof"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SURVEY_OTHER_INVERTER_DETAIL] == "5 kW on the south roof"
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
            CONF_SURVEY_OTHER_INVERTER: OTHER_INVERTER_YES,
            CONF_SURVEY_OTHER_INVERTER_DETAIL: "Fronius Symo 8.2",
        },
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            _options(
                **{SECTION_SURVEY: {CONF_SURVEY_OTHER_INVERTER: OTHER_INVERTER_YES}}
            ),
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SURVEY_OTHER_INVERTER_DETAIL] == "Fronius Symo 8.2"


# -- and into the file ---------------------------------------------------------


async def test_the_document_carries_the_answer(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """In `user_inputs`, where every claim lives and no reading does."""
    entry = await _entry(
        hass,
        sungrow_unit,
        {
            CONF_SURVEY_OTHER_INVERTER: OTHER_INVERTER_YES,
            CONF_SURVEY_OTHER_INVERTER_DETAIL: "Fronius Symo 8.2",
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
            CONF_SURVEY_OTHER_INVERTER: OTHER_INVERTER_YES,
            CONF_SURVEY_OTHER_INVERTER_DETAIL: "Fronius Symo 8.2",
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

    A diagnostics entry is created and then does nothing: the survey is a
    button somebody has to find, and its document arrives in a notification
    they have no reason to be watching. Both were reported by a contributor
    who ran the survey and then asked where the file had gone. The success
    dialog is the last place left to answer that before they close it.
    """
    result = await _to_testimony(hass, sungrow_unit)

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    # The key the frontend looks up as `config.create_entry.<description>`.
    assert result["description"] == "diagnostics"
