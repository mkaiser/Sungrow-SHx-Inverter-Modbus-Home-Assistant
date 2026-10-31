"""The survey document's download link.

The notification at the end of a survey links here, signed and time-limited.
The view keeps Home Assistant's authentication: the signature is what lets
the link through, and nothing else does. Without one, a document carrying a
house's readings would be readable by anyone who can reach port 8123.
"""

from __future__ import annotations

from dataclasses import replace
from http import HTTPStatus
import json
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from custom_components.sungrow_modbus.download import URL, async_download_url
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from sungrow_modbus.survey_document import label_for

from .conftest import SERIAL
from .corpus import INVERTER_DOCUMENTS

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}


async def _entry(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _finish_a_survey(entry: MockConfigEntry) -> dict:
    """Give the entry a finished document, as a run would leave it."""
    document = json.loads(INVERTER_DOCUMENTS[0].read_text(encoding="utf-8"))
    runner = entry.runtime_data.survey
    runner.state = replace(runner.state, document=document)
    return document


async def test_the_signed_link_downloads_the_document_under_its_survey_name(
    hass: HomeAssistant, hass_client_no_auth, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _entry(hass, sungrow_unit)
    document = _finish_a_survey(entry)
    client = await hass_client_no_auth()

    response = await client.get(async_download_url(hass, entry))

    assert response.status == HTTPStatus.OK
    assert await response.json() == document
    disposition = response.headers["Content-Disposition"]
    assert disposition == f'attachment; filename="{label_for(document)}.json"'


async def test_without_a_signature_or_a_login_it_is_refused(
    hass: HomeAssistant, hass_client_no_auth, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _entry(hass, sungrow_unit)
    _finish_a_survey(entry)
    client = await hass_client_no_auth()

    response = await client.get(URL.format(entry_id=entry.entry_id))

    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_no_survey_yet_is_a_404_that_says_so(
    hass: HomeAssistant, hass_client, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _entry(hass, sungrow_unit)
    client = await hass_client()

    response = await client.get(URL.format(entry_id=entry.entry_id))

    assert response.status == HTTPStatus.NOT_FOUND
    assert "No survey has been run" in await response.text()


async def test_another_integration_s_entry_is_not_served(
    hass: HomeAssistant, hass_client, sungrow_unit: MockModbusUnit
) -> None:
    await _entry(hass, sungrow_unit)
    other = MockConfigEntry(domain="sofar", title="someone else's")
    other.add_to_hass(hass)
    client = await hass_client()

    response = await client.get(URL.format(entry_id=other.entry_id))

    assert response.status == HTTPStatus.NOT_FOUND
