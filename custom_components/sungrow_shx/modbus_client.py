"""Thin async Modbus-TCP client wrapper for the Sungrow SHx integration.

Wraps :class:`pymodbus.client.AsyncModbusTcpClient` with a small
surface that matches what the coordinator and entity platforms need:
``read_holding`` / ``read_input`` (returning a raw register list) and
``write_register`` / ``write_registers``. A configurable inter-message
delay is applied after every successful send, mirroring the legacy
YAML package's ``wait_ms`` behavior.

Connection and protocol errors are translated into
:class:`SungrowModbusError`, which the coordinator maps to
:class:`homeassistant.helpers.update_coordinator.UpdateFailed`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Final

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE,
    CONF_WAIT_MS,
    DEFAULT_PORT,
    DEFAULT_SLAVE,
    DEFAULT_WAIT_MS,
)

_LOGGER: Final = logging.getLogger(__name__)


# Standard Modbus exception codes worth distinguishing in callers.
MODBUS_EXC_ILLEGAL_FUNCTION: Final = 1
MODBUS_EXC_ILLEGAL_DATA_ADDRESS: Final = 2

# Exception codes that mean "this register/function does not exist on this
# slave" — i.e. permanently unsupported, not a transient connection issue.
MODBUS_UNSUPPORTED_EXCEPTION_CODES: Final = frozenset(
    {MODBUS_EXC_ILLEGAL_FUNCTION, MODBUS_EXC_ILLEGAL_DATA_ADDRESS}
)


class SungrowModbusError(Exception):
    """Raised for all client-side Modbus failures.

    ``exception_code`` is the standard Modbus exception code (1=illegal
    function, 2=illegal data address, 3=illegal data value, 4=slave
    device failure, ...) when the failure was a Modbus exception
    response. It is ``None`` for transport-layer or framing errors.
    """

    def __init__(self, message: str, exception_code: int | None = None) -> None:
        super().__init__(message)
        self.exception_code = exception_code

    @property
    def is_unsupported(self) -> bool:
        """True if the exception means the slave does not have this register."""
        return self.exception_code in MODBUS_UNSUPPORTED_EXCEPTION_CODES


class SungrowModbusClient:
    """Small async Modbus-TCP client for Sungrow SHx inverters."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        slave: int = DEFAULT_SLAVE,
        wait_ms: int = DEFAULT_WAIT_MS,
        timeout: float = 10.0,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.port = port
        self.slave = slave
        self.wait_ms = wait_ms
        self.timeout = timeout
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Establish the TCP connection. Returns True on success."""
        if self._client is None:
            self._client = AsyncModbusTcpClient(
                host=self.host, port=self.port, timeout=self.timeout
            )
        try:
            connected = await self._client.connect()
        except ModbusException as err:
            raise SungrowModbusError(f"Failed to connect to {self.host}:{self.port}: {err}") from err
        if not connected:
            raise SungrowModbusError(f"Failed to connect to {self.host}:{self.port}")
        _LOGGER.debug("SungrowModbusClient connected to %s:%s", self.host, self.port)
        return True

    async def close(self) -> None:
        """Close the TCP connection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001 - best-effort close
                _LOGGER.debug("Error while closing modbus client", exc_info=True)
            self._client = None

    @property
    def connected(self) -> bool:
        """Return True if the underlying client thinks it is connected."""
        return bool(self._client and self._client.connected)

    async def _ensure_connected(self) -> AsyncModbusTcpClient:
        if self._client is None or not self._client.connected:
            await self.connect()
        assert self._client is not None
        return self._client

    async def _post_send_wait(self) -> None:
        if self.wait_ms > 0:
            await asyncio.sleep(self.wait_ms / 1000.0)

    async def read_holding(
        self, address: int, count: int, slave: int | None = None
    ) -> list[int]:
        """Read ``count`` holding registers starting at ``address``."""
        unit = self.slave if slave is None else slave
        async with self._lock:
            client = await self._ensure_connected()
            try:
                result = await client.read_holding_registers(
                    address=address, count=count, device_id=unit
                )
            except ModbusException as err:
                raise SungrowModbusError(
                    f"read_holding(address={address}, count={count}, slave={unit}) failed: {err}"
                ) from err
            except ConnectionException as err:
                raise SungrowModbusError(str(err)) from err
            finally:
                await self._post_send_wait()
        if result is None or result.isError():
            raise SungrowModbusError(
                f"read_holding(address={address}, count={count}, slave={unit}) returned error: {result}",
                exception_code=getattr(result, "exception_code", None),
            )
        return list(result.registers)

    async def read_input(
        self, address: int, count: int, slave: int | None = None
    ) -> list[int]:
        """Read ``count`` input registers starting at ``address``."""
        unit = self.slave if slave is None else slave
        async with self._lock:
            client = await self._ensure_connected()
            try:
                result = await client.read_input_registers(
                    address=address, count=count, device_id=unit
                )
            except ModbusException as err:
                raise SungrowModbusError(
                    f"read_input(address={address}, count={count}, slave={unit}) failed: {err}"
                ) from err
            except ConnectionException as err:
                raise SungrowModbusError(str(err)) from err
            finally:
                await self._post_send_wait()
        if result is None or result.isError():
            raise SungrowModbusError(
                f"read_input(address={address}, count={count}, slave={unit}) returned error: {result}",
                exception_code=getattr(result, "exception_code", None),
            )
        return list(result.registers)

    async def write_register(
        self, address: int, value: int, slave: int | None = None
    ) -> None:
        """Write a single holding register."""
        unit = self.slave if slave is None else slave
        async with self._lock:
            client = await self._ensure_connected()
            try:
                result = await client.write_register(
                    address=address, value=value, device_id=unit
                )
            except ModbusException as err:
                raise SungrowModbusError(
                    f"write_register(address={address}, value={value}, slave={unit}) failed: {err}"
                ) from err
            finally:
                await self._post_send_wait()
        if result is None or result.isError():
            raise SungrowModbusError(
                f"write_register(address={address}, value={value}, slave={unit}) returned error: {result}"
            )

    async def write_registers(
        self, address: int, values: list[int], slave: int | None = None
    ) -> None:
        """Write multiple contiguous holding registers."""
        unit = self.slave if slave is None else slave
        async with self._lock:
            client = await self._ensure_connected()
            try:
                result = await client.write_registers(
                    address=address, values=values, device_id=unit
                )
            except ModbusException as err:
                raise SungrowModbusError(
                    f"write_registers(address={address}, values={values}, slave={unit}) failed: {err}"
                ) from err
            finally:
                await self._post_send_wait()
        if result is None or result.isError():
            raise SungrowModbusError(
                f"write_registers(address={address}, values={values}, slave={unit}) returned error: {result}"
            )


# Re-export the CONF_* names most relevant to this module.
__all__ = [
    "CONF_HOST",
    "CONF_PORT",
    "CONF_SLAVE",
    "CONF_WAIT_MS",
    "SungrowModbusClient",
    "SungrowModbusError",
]

# Silence unused-import warnings for values re-exported above.
_ = (CONF_HOST, CONF_PORT, CONF_SLAVE, CONF_WAIT_MS, DEFAULT_PORT, DEFAULT_SLAVE, DEFAULT_WAIT_MS)
_unused_any: Any  # type: ignore[valid-type]
