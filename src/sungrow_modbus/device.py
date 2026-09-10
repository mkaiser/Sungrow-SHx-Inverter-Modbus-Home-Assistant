"""The top-level Sungrow inverter object.

Consumers construct one of these from a ``ModbusUnit`` and then read plain
Python attributes; nothing here knows about Home Assistant.
"""

from __future__ import annotations

import logging

from modbus_connection import ModbusConnectionError, ModbusError, ModbusUnit
from modbus_connection.model import Component

from .capabilities import Capability, probe, resolve
from .components import InverterControl, InverterIdentity
from .const import model_for
from .derived import Derived
from .model import UpdateReport, present
from .registers import COMPONENTS, TIER_COMPONENTS

_LOGGER = logging.getLogger(__name__)


class SungrowInverter:
    """A Sungrow inverter on one Modbus unit.

    The register map is split across components by poll interval, so a caller
    refreshes a tier at a time rather than the whole map at once — which is
    what lets a 5-second reading stay 5 seconds old without dragging 38
    slow-moving totals along with it.
    """

    def __init__(self, unit: ModbusUnit) -> None:
        """Bind every component to a unit handle."""
        self._unit = unit
        self.identity = InverterIdentity(unit)
        # Write-only, and not in COMPONENTS, so no coordinator ever polls it.
        self.control = InverterControl(unit)
        for attribute, component in COMPONENTS.items():
            setattr(self, attribute, component(unit))
        self.derived = Derived(self)
        # Field names are unique across components, which the tests assert, so
        # a derived value can ask for one without knowing where it lives.
        self._fields = {
            name: attribute
            for attribute, component in COMPONENTS.items()
            for name in vars(component)
            if not name.startswith("_")
            and name not in {"register_space", "declared_fields"}
        }

    def component(self, attribute: str) -> Component:
        """Return one component by the name entity descriptions refer to it by."""
        return getattr(self, attribute)  # type: ignore[no-any-return]

    def field(self, name: str) -> object:
        """Return one register's value by name, wherever it lives."""
        attribute = self._fields.get(name)
        if attribute is None:
            raise AttributeError(f"no register named {name!r}")
        return present(getattr(self.component(attribute), name))

    @property
    def serial_number(self) -> str | None:
        """Serial number, or None until the identity has been read."""
        return self.identity.serial_number or None

    @property
    def device_type_code(self) -> int | None:
        """Raw model code, or None until the identity has been read."""
        return self.identity.device_type_code

    @property
    def model(self) -> str | None:
        """Model name, or None if the code is unknown to this library."""
        return model_for(self.device_type_code)

    @property
    def output_type(self) -> int | None:
        """What register 5002 says about phases, which beats inferring it."""
        return self.identity.output_type

    def capabilities(
        self, probed: frozenset[Capability] | None = None
    ) -> frozenset[Capability]:
        """Return what this device has, from what it said and what answered.

        With no probe supplied it takes one from the registers already read,
        so this is only meaningful after a poll — before that every optional
        block looks absent, which is why setup reads before it asks.
        """
        if probed is None:
            probed = probe(self._read_or_none)
        return resolve(self.device_type_code, self.output_type, probed)

    def _read_or_none(self, name: str) -> object:
        """Return a register's value, or None if this device has no such field."""
        try:
            return self.field(name)
        except AttributeError:
            return None

    async def async_read_words(self, space: str, address: int, count: int) -> list[int]:
        """Read raw words at one address, for a survey probe.

        The seam a capability survey needs and the components cannot give it:
        `fingerprint.PROBES` asks about addresses chosen to answer a
        *question* -- is there a third tracker, does this path forward the
        6100 block -- and several of them are not in any component this
        library maps. Raises, because only the caller can tell a refusal from
        a timeout and the difference is the whole point of asking.
        """
        if space == "holding":
            return list(await self._unit.read_holding_registers(address, count))
        return list(await self._unit.read_input_registers(address, count))

    async def async_update_identity(self) -> None:
        """Read the identity block. Raises on failure; the caller decides."""
        await self.identity.async_update()

    async def async_update_tier(self, tier: str) -> UpdateReport:
        """Poll every component belonging to one tier.

        Named rather than keyed by interval, because the interval is a
        setting: slowing the fast tier to 60 seconds must not merge it with
        the medium one.
        """
        return await self._async_update_components(TIER_COMPONENTS[tier])

    async def async_update(self) -> UpdateReport:
        """Read identity and every tier, as a config flow probe does."""
        await self.async_update_identity()
        report = UpdateReport()
        for tier in TIER_COMPONENTS:
            report = report | await self.async_update_tier(tier)
        return report

    async def _async_update_components(self, names: tuple[str, ...]) -> UpdateReport:
        """Refresh each named component, collecting per-component failures.

        A dead link fails the whole poll, because retrying the remaining
        components would only multiply the timeout. Anything else is recorded
        against the one component that raised it and the poll carries on: a
        Sungrow inverter answers a different subset of its map depending on
        model, wiring and firmware, so a block that does not answer is normal
        operation rather than a failure of the device.
        """
        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for name in names:
            try:
                await self.component(name).async_update()
            except ModbusConnectionError:
                raise
            except ModbusError as err:
                _LOGGER.debug("%s failed to refresh: %s", name, err)
                failed[name] = err
            else:
                updated.add(name)
        return UpdateReport(frozenset(updated), failed)
