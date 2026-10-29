"""The top-level Sungrow inverter object.

Consumers construct one of these from a ``ModbusUnit`` and then read plain
Python attributes; nothing here knows about Home Assistant.
"""

from __future__ import annotations

import logging

from modbus_connection import ModbusConnectionError, ModbusError, ModbusUnit
from modbus_connection.model import Component

from ..addresses import Address, read
from ..const import model_for
from ..model import RegisterValue, UpdateReport, present
from .capabilities import Capability, absent_on_firmware, probe, resolve
from .components import InverterControl, InverterIdentity
from .derived import Derived
from .registers import COMPONENTS, TIER_COMPONENTS

_LOGGER = logging.getLogger(__name__)

#: The components a capability's absence takes off the wire, for the
#: capabilities `capabilities.ABSENT_ON_FIRMWARE` can rule out. Only those:
#: the family table decides which entities exist and leaves the polling alone,
#: because a family entry is a remark and a probe outranks it. A firmware
#: entry is a measurement of a register that hangs up the link, and not
#: reading it is the whole fix.
FIRMWARE_GATED_COMPONENTS: dict[Capability, tuple[str, ...]] = {
    Capability.FIRMWARE_VERSIONS: (
        "firmware_block_inverter",
        "firmware_block_communication_module",
        "firmware_block_battery",
    ),
    Capability.METER_CHANNEL_2: ("meter_channel_2",),
}

#: What `async_update_firmware` reads, in order: the component carrying 2582,
#: then the one carrying 13250, which 2582 may rule out.
FIRMWARE_COMPONENTS: tuple[str, ...] = ("slowest_input", "firmware_block_inverter")


class SungrowInverter:
    """A Sungrow inverter on one Modbus unit.

    The register map is split across components by poll interval, so a caller
    refreshes a tier at a time rather than the whole map at once — which is
    what lets a 5-second reading stay 5 seconds old without dragging the
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

    @property
    def field_names(self) -> frozenset[str]:
        """Every field name this device can be asked for, by `field()`.

        Public because callers outside the library need to enumerate what a
        device offers -- the survey publishes one value per field, and the
        diagnostics download does the same. Reading `_fields` instead would be
        worse here than it usually is: this library is pinned by version in
        the integration's manifest, so renaming a private attribute would ship
        as a perfectly good release and break the integration at runtime.
        """
        return frozenset(self._fields)

    def field(self, name: str) -> RegisterValue:
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
    def firmware(self) -> str | None:
        """The ARM firmware version (register 2582), or None until it is read.

        One of the two strings the firmware tables are keyed by, and what
        changes when the inverter is updated -- `sungrow_version_1` reads
        `SAPPHIRE-H_01011.95.14`, where the hardware strings beside it do not
        move. `async_update_firmware` reads it before the first poll, so a
        gate keyed on it never costs a round of the reads it exists to skip.
        """
        return self._text("sungrow_version_1")

    @property
    def inverter_firmware(self) -> str | None:
        """The inverter firmware string (register 13250), or None.

        `SAPPHIRE-H_B001.V000.P023`: the other string the firmware tables are
        keyed by, and the one that decides register 31211 -- two inverters on
        95.12 differ there, and their 13250 strings say why. None where it
        has not been read, where it answered empty, and on firmware that
        hangs up on it, which is never asked.
        """
        return self._text("inverter_firmware_version")

    @property
    def firmware_strings(self) -> tuple[str | None, str | None]:
        """Both firmware strings, as the capability tables match them."""
        return (self.firmware, self.inverter_firmware)

    def _text(self, name: str) -> str | None:
        """Return a string field trimmed, or None where it says nothing."""
        value = self._read_or_none(name)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def skipped_components(self) -> frozenset[str]:
        """Components this firmware is measured not to answer, so never read."""
        return frozenset(
            name
            for capability in absent_on_firmware(self.firmware_strings)
            for name in FIRMWARE_GATED_COMPONENTS.get(capability, ())
        )

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
        return resolve(
            self.device_type_code, self.output_type, probed, self.firmware_strings
        )

    def probed_capabilities(self) -> frozenset[Capability]:
        """Return the capabilities whose registers actually answered.

        The raw probe, before `resolve` weighs it against what the model is
        *known* to have. `capabilities()` is what callers normally want; this
        is for the diagnostics download, which reports the two side by side so
        that a table disagreeing with the hardware is visible rather than
        silently overruled.
        """
        return probe(self._read_or_none)

    def _read_or_none(self, name: str) -> object:
        """Return a register's value, or None if this device has no such field."""
        try:
            return self.field(name)
        except AttributeError:
            return None

    async def async_read_words(self, space: str, address: int, count: int) -> list[int]:
        """Read raw words at one address, for a survey probe.

        The seam a capability survey needs and the components cannot give it:
        `survey_document.PROBES` asks about addresses chosen to answer a
        *question* -- is there a third tracker, does this path forward the
        6100 block -- and several of them are not in any component this
        library maps. Raises, because only the caller can tell a refusal from
        a timeout and the difference is the whole point of asking.
        """
        if space == "holding":
            return list(await self._unit.read_holding_registers(address, count))
        return list(await self._unit.read_input_registers(address, count))

    async def async_read(self, where: Address) -> list[int]:
        """Read one named block -- see `addresses`. Raises, like `async_read_words`."""
        return await read(self._unit, where)

    async def async_write_word(self, address: int, word: int) -> None:
        """Write one raw holding word, bypassing every field's scale.

        The control test's restore needs it: putting back the word a register
        held is the one write whose correctness does not depend on the scale
        under test. Raises, like `async_read_words`.
        """
        await self._unit.write_register(address, word)

    async def async_update_identity(self) -> None:
        """Read the identity block. Raises on failure; the caller decides."""
        await self.identity.async_update()

    async def async_update_firmware(self) -> UpdateReport:
        """Read both firmware strings, before anything decides on them.

        Firmware first, then everything it gates: what is read, and what the
        device is judged to have. 2582 arrives with `slowest_input`, and 13250
        is asked only once 2582 is known, because one measured firmware closes
        the connection on it. A block that refuses is a None like any other;
        a lost link raises, as a poll does.
        """
        return await self._async_update_components(FIRMWARE_COMPONENTS)

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

        A lost connection gets one retry per component first, because it is
        not always a dead link. fwitten's SH10RT-V112 times out on its three
        firmware strings over its own LAN port and then **closes the session**,
        so without a retry the next read in the tier reports a lost connection
        and the whole tier is abandoned -- enough to keep an entry from ever
        setting up. The retry reconnects; a link that is really dead fails it
        too, and the poll ends.
        """
        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for name in names:
            # Asked per component rather than once per tier, so a string read
            # by an earlier component gates a later one -- which is how
            # `async_update_firmware` learns 2582 before deciding on 13250.
            if name in self.skipped_components():
                # Neither updated nor failed: never asked. Its entities do not
                # exist, because the same table took their capability away.
                continue
            try:
                try:
                    await self.component(name).async_update()
                except ModbusConnectionError as err:
                    _LOGGER.debug("%s lost the connection, retrying: %s", name, err)
                    await self.component(name).async_update()
            except ModbusConnectionError:
                raise
            except ModbusError as err:
                _LOGGER.debug("%s failed to refresh: %s", name, err)
                failed[name] = err
            else:
                updated.add(name)
        return UpdateReport(frozenset(updated), failed)
