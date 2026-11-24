"""The dashboard module is served, and added to every page.

The strategy and the lock card live in `frontend/sungrow-modbus.js`
(`plans/T055-generated-dashboard.md`); what is tested here is the part in
Python: the static path, the module URL and its version.
"""

from __future__ import annotations

from http import HTTPStatus
import importlib.util
from pathlib import Path
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus import dashboard
from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, UrlManager
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from sungrow_modbus import cards

from .conftest import SERIAL

SCRIPT = Path(__file__).parent.parent / "scripts" / "release" / "fetch_cards.py"
spec = importlib.util.spec_from_file_location("fetch_cards", SCRIPT)
assert spec is not None and spec.loader is not None
fetch_cards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_cards)

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}


def _module_urls(hass: HomeAssistant) -> list[str]:
    return [u for u in hass.data[DATA_EXTRA_MODULE_URL].urls if dashboard.URL_BASE in u]


async def _setup(hass: HomeAssistant, unit: MockModbusUnit, serial: str) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=serial, title=serial
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_the_module_is_added_and_served(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, hass_client
) -> None:
    # The frontend's module list, as `frontend` leaves it; the frontend itself
    # is not set up here, so its own files are not in the way.
    hass.data[DATA_EXTRA_MODULE_URL] = UrlManager(lambda *_: None, [])
    await _setup(hass, sungrow_unit, SERIAL)

    (url,) = _module_urls(hass)
    assert url.startswith(f"{dashboard.URL_BASE}/{dashboard.MODULE}?v=")

    client = await hass_client()
    for name in sorted(path.name for path in dashboard.DIRECTORY.iterdir()):
        response = await client.get(f"{dashboard.URL_BASE}/{name}")
        assert response.status == HTTPStatus.OK, name


async def test_the_version_follows_the_files(tmp_path) -> None:
    (tmp_path / "a.js").write_text("one")
    first = dashboard._digest(tmp_path)
    (tmp_path / "a.js").write_text("two")
    assert dashboard._digest(tmp_path) != first


async def test_without_a_frontend_setup_goes_on(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit, SERIAL)
    assert DATA_EXTRA_MODULE_URL not in hass.data


async def test_the_cards_are_served_where_the_library_has_them(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, hass_client, tmp_path
) -> None:
    hass.data[DATA_EXTRA_MODULE_URL] = UrlManager(lambda *_: None, [])
    for name in cards.BUNDLES:
        (tmp_path / name).write_text("export {};")
    with patch.object(cards, "DIRECTORY", tmp_path):
        await _setup(hass, sungrow_unit, SERIAL)
    client = await hass_client()
    flow = (dashboard.DIRECTORY / "flow.js").read_text()
    for name in cards.BUNDLES:
        path = f"{dashboard.CARDS_URL}/{name}"
        assert (await client.get(path)).status == HTTPStatus.OK
        # What the card asks for, and under which name.
        assert f'"{path}"' in flow
        assert f'"{fetch_cards.CARDS_BY_BUNDLE[name].tag}"' in flow


async def test_without_the_bundle_the_dashboard_is_still_offered(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, tmp_path
) -> None:
    hass.data[DATA_EXTRA_MODULE_URL] = UrlManager(lambda *_: None, [])
    with patch.object(cards, "DIRECTORY", tmp_path):
        await _setup(hass, sungrow_unit, SERIAL)
    assert _module_urls(hass)


@pytest.mark.parametrize("card", fetch_cards.CARDS_BY_BUNDLE.values())
def test_the_bundle_s_patches_must_match(card) -> None:
    bundle = "".join(old for old, _new in card.patches)
    patched = card.patched(bundle)
    assert all(new in patched for _old, new in card.patches)
    with pytest.raises(SystemExit):
        card.patched(bundle.replace(card.patches[0][0], ""))
    assert tuple(fetch_cards.CARDS_BY_BUNDLE) == cards.BUNDLES
    assert tuple(fetch_cards.LICENCES) == cards.LICENCES
    assert set(fetch_cards.LICENCES.values()) == {
        card.repo for card in fetch_cards.CARDS_BY_BUNDLE.values()
    }
