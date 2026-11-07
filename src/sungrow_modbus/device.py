"""The seam every Sungrow device offers, and the base most of them share.

Hybrid, string inverter, battery and wallbox are separate packages because no
address means the same thing on two of them. What they share is how they are
asked: a set of components on one Modbus unit, each refreshed on its own, a
value by field name, and raw words for a diagnosis's dump. `Device` is that
seam, which the entity layer and the diagnosis type against; `MappedDevice` is
the implementation the SG, the battery and the wallbox are built on. The
hybrid meets `Device` on its own: its tiers skip what firmware rules out and
retry a lost connection, which no other device needs.

**A component failing costs only itself.** A Sungrow answers a different
subset of its map by model, firmware and what is wired up, so a refused block
is normal operation, recorded in the `UpdateReport` and nothing more.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from modbus_connection.model import Component

from .addresses import Address, read
from .model import UpdateReport, present

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

    from .identity import InverterIdentity


@runtime_checkable
class Device(Protocol):
    """What every device offers the entity layer and the diagnosis."""

    def component(self, attribute: str) -> Component:
        """Return one component by the name descriptions refer to it by."""
        ...

    @property
    def field_names(self) -> frozenset[str]:
        """Every field name this device can be asked for, by `field()`."""
        ...

    def field(self, name: str) -> object:
        """Return one value by name, wherever it lives."""
        ...

    async def async_read_words(self, space: str, address: int, count: int) -> list[int]:
        """Read raw words at one protocol address; raises, never guesses."""
        ...


@runtime_checkable
class Inverter(Device, Protocol):
    """A device that is an entry's own inverter: hybrid or string.

    Both answer the identity block (`identity.InverterIdentity`), which is
    what the device registry is built from.
    """

    identity: InverterIdentity

    @property
    def serial_number(self) -> str | None:
        """Serial number, or None until the identity has been read."""
        ...

    @property
    def model(self) -> str | None:
        """Model name, or None where the type code is unknown."""
        ...

    async def async_update_identity(self) -> None:
        """Read the identity block. Raises on failure; the caller decides."""
        ...


class MappedDevice:
    """A device made of the components in one map, on one Modbus unit.

    Every component is bound at construction and held as an attribute under
    its key in the map, so a subclass declares them for `mypy --strict`.
    """

    def __init__(
        self,
        unit: ModbusUnit,
        components: Mapping[str, type[Component]],
        unit_id: int,
    ) -> None:
        """Bind every component to a unit handle, remembering which id it is."""
        self._unit = unit
        #: Which unit id answered, kept because it is worth reporting: one
        #: device on two paths answers on two ids, which do not read alike.
        self.unit_id = unit_id
        self._components = tuple(components)
        for attribute, component in components.items():
            setattr(self, attribute, component(unit))
        # Properties included: a decoded meaning is asked for like a register.
        self._fields = {
            name: attribute
            for attribute, component in components.items()
            for name in vars(component)
            if not name.startswith("_")
            and name not in {"register_space", "declared_fields"}
        }

    def component(self, attribute: str) -> Component:
        """Return one component by the name descriptions refer to it by."""
        return getattr(self, attribute)  # type: ignore[no-any-return]

    @property
    def field_names(self) -> frozenset[str]:
        """Every field name this device can be asked for, by `field()`.

        Public because callers outside the library need to enumerate what a
        device offers -- the diagnosis publishes one value per field, and the
        diagnostics download does the same. Reading `_fields` instead would
        be worse here than it usually is: this library is pinned by version in
        the integration's manifest, so renaming a private attribute would ship
        as a perfectly good release and break the integration at runtime.
        """
        return frozenset(self._fields)

    def fields_of(self, attributes: Iterable[str]) -> frozenset[str]:
        """Every field name that lives in the named components.

        A diagnosis leaves a failed component's fields out of its report rather
        than publishing them as None: a None says the device reported the
        point unavailable, which a block that never answered did not.
        """
        wanted = set(attributes)
        return frozenset(
            name for name, attribute in self._fields.items() if attribute in wanted
        )

    def field(self, name: str) -> object:
        """Return one value by name, decoded meanings included."""
        attribute = self._fields.get(name)
        if attribute is None:
            raise AttributeError(f"no {type(self).__name__} value named {name!r}")
        return present(getattr(self.component(attribute), name))

    async def async_read_words(self, space: str, address: int, count: int) -> list[int]:
        """Read raw words at one protocol address, for a diagnosis's dump.

        Raises, because only the caller can tell a refusal from a timeout.
        """
        if space == "holding":
            return list(await self._unit.read_holding_registers(address, count))
        return list(await self._unit.read_input_registers(address, count))

    async def async_read(self, where: Address) -> list[int]:
        """Read one named block -- see `addresses`. Raises, like `async_read_words`."""
        return await read(self._unit, where)

    async def _async_update_components(
        self, attributes: Iterable[str] | None = None
    ) -> UpdateReport:
        """Refresh each named component (all by default), each failing alone."""
        from modbus_connection import ModbusError

        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for attribute in self._components if attributes is None else attributes:
            try:
                await self.component(attribute).async_update()
            except ModbusError as err:
                failed[attribute] = err
            else:
                updated.add(attribute)
        return UpdateReport(updated=frozenset(updated), failed=failed)
