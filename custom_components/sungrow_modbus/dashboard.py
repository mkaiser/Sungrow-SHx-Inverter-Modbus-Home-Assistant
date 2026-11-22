"""Serve the dashboard module: the strategy and the controls lock card.

The integration's dashboard is built in the browser, from the entities a
house has (`frontend/sungrow-modbus.js`, `plans/T055-generated-dashboard.md`).
Home Assistant loads the module on every page once it is added as an extra
module URL, so neither the strategy nor the lock card needs HACS or a
dashboard resource. `frontend/layout.json` is served beside it and fetched
by the module.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

#: Where the files are served; one path per Home Assistant, not per entry.
URL_BASE = "/sungrow_modbus_frontend"
MODULE = "sungrow-modbus.js"
DIRECTORY = Path(__file__).parent / "frontend"


def _digest(directory: Path) -> str:
    """Fingerprint the served files, for the module URL's version.

    The manifest's version would not do: a development build carries the
    release's version with other code, and a browser that cached the old
    module would keep it.
    """
    sha = hashlib.sha256()
    for path in sorted(directory.iterdir()):
        if path.is_file():
            sha.update(path.name.encode())
            sha.update(path.read_bytes())
    return sha.hexdigest()[:12]


async def async_register(hass: HomeAssistant) -> None:
    """Serve the directory and add the module to every page. Called from `async_setup`.

    `frontend` is an after-dependency, not a dependency: every real Home
    Assistant runs it, and a test that sets up a bare `hass` has neither it
    nor `http`. Without them there is no page to load the module into, so
    this declines rather than failing setup.
    """
    if getattr(hass, "http", None) is None or DATA_EXTRA_MODULE_URL not in hass.data:
        _LOGGER.debug("No frontend; the Sungrow dashboard is not offered")
        return
    version = await hass.async_add_executor_job(_digest, DIRECTORY)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(DIRECTORY), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{URL_BASE}/{MODULE}?v={version}")
