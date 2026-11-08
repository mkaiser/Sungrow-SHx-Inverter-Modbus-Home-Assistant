"""The diagnostics file has to answer the questions bug reports actually ask.

Nearly every report on this project starts with the same round trip: which
model, what is connected, which registers answer, and why is sensor X missing.
The integration knows all of that, so these tests pin that it says so — and
that it does not say the serial number or the host, because the file exists to
be pasted into a public issue.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_ENTITY_IDS,
    CONF_REGISTER_DUMP,
    CONF_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_NEW,
)
from custom_components.sungrow_modbus.diagnostics import (
    NO_BLOCK_READ_TEST,
    async_get_config_entry_diagnostics,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .conftest import SERIAL

ENTRY_DATA = {
    CONF_HOST: "192.168.1.50",
    CONF_PORT: 5020,
    CONF_UNIT_ID: 1,
    CONF_ENTITY_IDS: ENTITY_IDS_NEW,
}


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, options: dict | None = None
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        options=options or {},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit",
        return_value=unit,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_it_identifies_the_hardware(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit)
    report = await async_get_config_entry_diagnostics(hass, entry)

    assert report["device"]["model"] == "SH10RT"
    # The raw code as well as the name: a code this library does not know is
    # the whole point of some reports.
    assert report["device"]["device_type_code"] == "0x0E03"
    assert report["device"]["output_type"] == "3P4L"
    assert report["device"]["firmware"]["arm"].startswith("SAPPHIRE")


async def test_the_serial_and_host_are_redacted(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The file is written to be pasted into a public issue."""
    entry = await _setup(hass, sungrow_unit)
    report = await async_get_config_entry_diagnostics(hass, entry)

    assert report["device"]["serial_number"] != SERIAL
    assert report["entry"][CONF_HOST] != "192.168.1.50"
    # Redacting must not hide what is being diagnosed.
    assert report["entry"][CONF_PORT] == 5020
    assert report["entry"][CONF_UNIT_ID] == 1

    # And nowhere else in the document either.
    assert SERIAL not in str(report)
    assert "192.168.1.50" not in str(report)


async def test_it_says_why_an_entity_does_not_exist(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The most common report on this project, answered in the file itself."""
    entry = await _setup(hass, sungrow_unit)
    report = await async_get_config_entry_diagnostics(hass, entry)

    not_created = report["entities"]["not_created"]
    assert {"mppt3_voltage", "mppt3_power"} <= set(not_created["requires mppt3"])
    assert report["entities"]["created"] > 100


async def test_it_shows_how_each_capability_was_decided(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Not just the result: the sources, so a wrong table shows as a conflict."""
    entry = await _setup(hass, sungrow_unit)
    capabilities = (await async_get_config_entry_diagnostics(hass, entry))[
        "capabilities"
    ]

    assert "three_phase" in capabilities["resolved"]
    assert "mppt3" in capabilities["absent_for_this_model"]
    # An SH10RT's table and its registers agree, so there is nothing to report.
    assert capabilities["table_contradicted_by_device"] == []


async def test_it_separates_unavailable_registers_from_failed_blocks(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A 0xFFFF sentinel and a block that did not answer are different faults."""
    entry = await _setup(hass, sungrow_unit)
    report = await async_get_config_entry_diagnostics(hass, entry)

    assert "mppt3_voltage" in report["readings"]["reported_unavailable"]
    assert report["readings"]["values"]["total_dc_power"] is not None

    polling = report["polling"]
    assert polling["healthy"] == polling["of"] > 0
    assert polling["problems"] == []
    assert polling["interval_seconds"]["fast"] == 10


async def test_poll_health_lists_only_what_did_not_answer(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A healthy component is a count; one that failed keeps its whole row.

    The components of one tier share a coordinator, so a failed poll is every
    component of that tier.
    """
    entry = await _setup(hass, sungrow_unit)
    coordinators = entry.runtime_data.coordinators
    failed = coordinators["fast_input"]
    failed.last_update_success = False
    tier = sorted(name for name, c in coordinators.items() if c is failed)

    polling = (await async_get_config_entry_diagnostics(hass, entry))["polling"]

    assert polling["healthy"] == polling["of"] - len(tier)
    assert [row["component"] for row in polling["problems"]] == tier
    assert all(row["last_poll_succeeded"] is False for row in polling["problems"])


async def test_the_register_dump_is_off_unless_asked_for(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """It costs a second full read of the map, so it is opt-in."""
    entry = await _setup(hass, sungrow_unit)
    assert "register_dump" not in await async_get_config_entry_diagnostics(hass, entry)


async def test_the_register_dump_is_included_when_enabled(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit, options={CONF_REGISTER_DUMP: True})
    report = await async_get_config_entry_diagnostics(hass, entry)

    dump = report["register_dump"]
    # Every component, keyed by address space then address, as the register
    # document is. Addresses are strings so the file survives a JSON round
    # trip unchanged.
    assert {"fast_input", "slowest_input", "identity"} <= set(dump)
    assert "13002" in dump["slowest_input"]["input"]  # total_pv_generation
    assert dump["fast_input"]["input"]["5014"] == 0xFFFF  # MPPT3, absent

    # The serial number's registers are dropped: a dump is words, not
    # strings, so redacting keys never reaches it.
    assert not any(
        str(address) in space
        for component in dump.values()
        for space in component.values()
        if isinstance(space, dict)
        for address in range(4989, 4999)
    )


async def test_the_block_read_test_is_carried_from_the_last_diagnosis(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The download hands on the diagnosis's measurement rather than running one.

    The test reads every block several times -- minutes through a dongle --
    and a download is something somebody waits on.
    """
    entry = await _setup(hass, sungrow_unit)
    report = await async_get_config_entry_diagnostics(hass, entry)
    assert report["block_read_test"] == NO_BLOCK_READ_TEST

    measured = {"rounds": 3, "blocks": []}
    entry.runtime_data.diagnosis._set(
        document={"block_read_test": measured},
        finished=datetime(2026, 10, 17, 12, 0, tzinfo=UTC),
    )
    report = await async_get_config_entry_diagnostics(hass, entry)

    assert report["block_read_test"] == {
        "measured_at": "2026-10-17T12:00:00+00:00",
        **measured,
    }


async def test_the_capability_test_is_carried_into_the_diagnosis(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The download is the link that never lapses, so it holds part B too.

    The notification says Download diagnostics carries the same document. A
    download only reads, so the last run's capability test has to be carried,
    or that promise fails for the run that is hardest to repeat.
    """
    entry = await _setup(hass, sungrow_unit)
    report = await async_get_config_entry_diagnostics(hass, entry)
    assert "capability_test" not in report["diagnosis"]

    block = {"verdict": "pass", "controls": []}
    entry.runtime_data.diagnosis._set(capability_test=block)
    report = await async_get_config_entry_diagnostics(hass, entry)

    assert report["diagnosis"]["capability_test"] == block
