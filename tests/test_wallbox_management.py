"""What drives a wallbox, inferred from its output current setting.

Nothing a wallbox reports says who drives it, so the inference is behaviour:
an inverter under whose management a wallbox charges rewrites holding 21203
every few seconds (gerd's, over the cable and through the WiNet-S alike).
These hold the two halves apart, which is the point of the whole thing:

* the inference decides what is **shown**, on the device page;
* the owner's answer in the entry's options decides what may be **written**,
  because a wrong *standalone* writes registers an inverter overwrites within
  seconds and measures nothing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus import wallbox_capability_test as wbt
from custom_components.sungrow_modbus.const import (
    CONF_CAPABILITY_TEST_WALLBOX,
    CONF_WALLBOX_STANDALONE,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from sungrow_modbus.wallbox import management
from sungrow_modbus.wallbox.capability_test import CHARGING

from .conftest import SERIAL

#: The inverter entry's entity prefix, as every other test spells it.
SLUG = "ac22e_01"

# -- the inference itself ---------------------------------------------------


def _feed(
    settings: list[float | None], *, charging: bool = True
) -> management.Management:
    inference = management.Management()
    for setting in settings:
        inference.observe(setting, charging=charging)
    return inference


def test_a_setting_that_moves_during_a_charge_means_an_inverter_drives_it() -> None:
    """The one piece of evidence there is: 21203 rewritten every few seconds."""
    inference = _feed([6.0, 8.0, 10.0, 12.0])

    state, detail = inference.verdict()

    assert state == management.MANAGED
    assert "moved 3 times" in detail


def test_one_move_is_not_enough_because_an_owner_can_make_one() -> None:
    """A change in Sungrow's app looks exactly like the inverter's first write."""
    state, _detail = _feed([6.0, 8.0]).verdict()

    assert state == management.UNKNOWN


def test_a_setting_that_holds_still_through_a_charge_suggests_standalone() -> None:
    """Suggests, and no more: it is shown, and the owner is asked."""
    polls = management.STEADY_POLLS_FOR_STANDALONE

    state, detail = _feed([16.0] * polls).verdict()

    assert state == management.STANDALONE
    assert f"{polls} polls" in detail


def test_one_poll_short_of_the_charge_says_so_rather_than_guessing() -> None:
    inference = _feed([16.0] * (management.STEADY_POLLS_FOR_STANDALONE - 1))

    state, detail = inference.verdict()

    assert state == management.UNKNOWN
    assert f"of {management.STEADY_POLLS_FOR_STANDALONE} polls" in detail


def test_an_idle_wallbox_says_nothing_however_long_it_is_watched() -> None:
    """Stillness with no car on it is not evidence.

    An inverter has nothing to write then, and counting those polls would
    declare every idle wallbox standalone.
    """
    inference = _feed([16.0] * 500, charging=False)

    state, detail = inference.verdict()

    assert state == management.UNKNOWN
    assert "no charge seen yet" in detail
    assert inference.charging_polls == 0


def test_a_move_across_a_gap_is_not_counted() -> None:
    """A setting that did not read, or a charge that stopped between polls.

    The move may have happened while nothing was watching, and counting it
    would be inventing evidence.
    """
    inference = management.Management()
    inference.observe(6.0, charging=True)
    inference.observe(None, charging=True)
    inference.observe(12.0, charging=True)
    inference.observe(6.0, charging=False)
    inference.observe(12.0, charging=True)

    assert inference.moves == 0


def test_a_change_under_one_count_is_not_a_move() -> None:
    """21203 is a 0.1 A register: a count is the smallest change it can hold."""
    assert _feed([16.0, 16.04, 16.0, 16.04]).moves == 0


def test_the_inference_is_published_with_its_counts() -> None:
    """What the device page shows: the verdict, the reading, and the evidence."""
    published = _feed([6.0, 8.0, 10.0]).as_dict()

    assert published["management"] == management.MANAGED
    assert published["setting_moves"] == 2
    assert published["charging_polls"] == 3
    assert "which nothing here wrote" in published["management_detail"]


# -- what it decides, and what it does not ----------------------------------


def _entry(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"kind": "wallbox"},
        options=options,
        unique_id="W123456789",
        title="AC22E-01",
    )
    entry.add_to_hass(hass)
    return entry


def test_only_the_owners_word_declares_a_wallbox_standalone(
    hass: HomeAssistant,
) -> None:
    """Not the inference, however sure it is: a wrong yes writes for nothing."""
    assert not wbt.declared_standalone(_entry(hass))
    assert wbt.declared_standalone(_entry(hass, **{CONF_WALLBOX_STANDALONE: True}))


def test_the_owners_word_opens_the_wallboxs_own_checks(hass: HomeAssistant) -> None:
    """Which is the whole reason the question exists.

    Without it a wallbox no inverter manages ran none of its own registers'
    checks and nobody was ever asked why (`check_options`).
    """
    on = {CONF_CAPABILITY_TEST_WALLBOX: True}
    with_leave = wbt.check_options(_entry(hass, **on), hass)
    assert not with_leave["standalone"]

    declared = wbt.check_options(
        _entry(hass, **on, **{CONF_WALLBOX_STANDALONE: True}), hass
    )
    assert declared["standalone"]


async def test_a_wallbox_entry_is_asked_the_question_in_configure(
    hass: HomeAssistant,
) -> None:
    """Beside the leave it depends on, and off until it is answered."""
    from .test_wallbox_entry import _setup

    entry = await _setup(hass)
    assert not wbt.declared_standalone(entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "wallbox"
    done = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "capability_test": {
                CONF_CAPABILITY_TEST_WALLBOX: True,
                CONF_WALLBOX_STANDALONE: True,
            },
            "diagnosis": {"publish_address": False},
        },
    )
    await hass.async_block_till_done()

    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_WALLBOX_STANDALONE] is True
    assert wbt.declared_standalone(entry)


# -- fed by the readings observer, at no extra read -------------------------


async def test_the_runner_feeds_it_the_polls_the_readings_checks_get(
    hass: HomeAssistant,
) -> None:
    """One poll answers both questions, which is why it costs no session.

    The wallbox's own entry here, because that is the one whose owner may be
    asked; an inverter entry reading a wallbox at unit 3 keeps the same
    inference from the same polls.
    """
    from .test_wallbox_entry import _setup

    entry = await _setup(hass)
    runner = entry.runtime_data.diagnosis
    assert runner.wallbox_present

    # The one seam: what the poll read. The fixture's own session had already
    # completed (status 6), and a wallbox with no car on it is the case the
    # inference deliberately says nothing about.
    reading = wbt.readings_of(entry.runtime_data.wallbox.device)
    for setting in (6.0, 8.0, 10.0):
        charging = {
            **reading,
            "output_current_setting": setting,
            "charging_status_raw": float(CHARGING),
        }
        with patch(
            "custom_components.sungrow_modbus.diagnosis.wallbox_readings_of",
            return_value=charging,
        ):
            entry.runtime_data.wallbox.slow_reads += 1
            # The tick, not `async_observe` alone: it is what tells the
            # entities, and an inference nothing shows is no use.
            runner._async_observe_tick(dt_util.utcnow())
    await hass.async_block_till_done()

    assert runner.wallbox_management.charging_polls == 3
    published = runner.wallbox_management.as_dict()
    summary = hass.states.get(f"sensor.{SLUG}_diagnosis_test_summary")
    assert summary is not None
    assert summary.attributes["management"] == published["management"]
    assert summary.attributes["charging_polls"] == 3

    # The same setting again, not read anew, is no evidence that it held.
    with patch(
        "custom_components.sungrow_modbus.diagnosis.wallbox_readings_of",
        return_value=charging,
    ):
        for _ in range(40):
            runner._async_observe_tick(dt_util.utcnow())
    assert runner.wallbox_management.charging_polls == 3


async def test_no_wallbox_no_attribute(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """An inverter with no wallbox gets no claim about one, not "unknown"."""
    from .test_wallbox_one_device import ENTRY_DATA

    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    empty = MockModbusUnit
    with patch(
        "custom_components.sungrow_modbus.async_get_unit",
        side_effect=lambda _h, _e, _p, unit_id: (
            sungrow_unit if unit_id == 1 else _nothing(empty)
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    summary = hass.states.get("sensor.sh10rt_diagnosis_test_summary")
    assert summary is not None
    assert "management" not in summary.attributes


def _nothing(_kind: object) -> Any:
    """Return a unit that answers nothing, for the no-wallbox case."""
    from modbus_connection.mock import MockModbusConnection

    unit = MockModbusConnection().for_unit(9)
    unit.input = {}
    unit.holding = {}
    return unit


@pytest.mark.parametrize("state", [management.MANAGED, management.STANDALONE])
def test_every_answer_it_can_give_is_a_word_the_options_text_explains(
    state: str,
) -> None:
    """The device page shows these words, so the question must define them."""
    import json
    from pathlib import Path

    strings = json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "custom_components"
            / "sungrow_modbus"
            / "strings.json"
        ).read_text(encoding="utf-8")
    )
    text = strings["options"]["step"]["wallbox"]["sections"]["capability_test"][
        "data_description"
    ][CONF_WALLBOX_STANDALONE]
    assert state in text
    assert management.UNKNOWN in text
