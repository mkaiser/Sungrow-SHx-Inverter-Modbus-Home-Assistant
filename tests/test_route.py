"""Test how the device page names the path to the inverter."""

from __future__ import annotations

from unittest.mock import MagicMock

from modbus_connection import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ServerDeviceBusyError,
)
import pytest

from custom_components.sungrow_modbus.route import (
    async_direct,
    connection_text,
    route_key,
    web_interface,
)
from homeassistant.const import CONF_HOST, CONF_PORT


async def _answers() -> list[int]:
    return [0, 0]


def _raises(error: Exception):  # type: ignore[no-untyped-def]
    async def probe() -> list[int]:
        raise error

    return probe()


async def test_6100_answered_is_direct() -> None:
    assert await async_direct(_answers()) is True


async def test_6100_refused_is_a_module() -> None:
    assert await async_direct(_raises(IllegalDataAddressError("refused"))) is False


@pytest.mark.parametrize(
    "error",
    [ModbusConnectionError("lost"), ServerDeviceBusyError("busy"), TimeoutError()],
)
async def test_a_failed_read_says_nothing(error: Exception) -> None:
    """A lost or busy read is not a refusal."""
    assert await async_direct(_raises(error)) is None


@pytest.mark.parametrize(
    ("direct", "module", "key"),
    [
        (True, None, "direct"),
        # A cable in the LAN port with a WiNet-S fitted is still direct.
        (True, "WINET-SV200.001.00.P045", "direct"),
        (False, "WINET-SV300.001.03.P032", "winet"),
        (False, None, "module"),
        (None, "WINET-SV200.001.00.P045", None),
    ],
)
def test_route_key(direct: bool | None, module: str | None, key: str | None) -> None:
    assert route_key(direct, module) == key


def test_the_address_and_the_link() -> None:
    entry = MagicMock()
    entry.data = {CONF_HOST: "10.0.0.5", CONF_PORT: 502}
    assert connection_text(entry, "direct") == "10.0.0.5 · direct, no dongle"
    assert web_interface(entry, "winet") == "http://10.0.0.5"
    # The inverter's own port serves no page, and a link nowhere is worse.
    assert web_interface(entry, "direct") is None
    assert web_interface(entry, None) is None
    entry.data = {CONF_HOST: "10.0.0.5", CONF_PORT: 516}
    assert connection_text(entry, None) == "10.0.0.5:516"
