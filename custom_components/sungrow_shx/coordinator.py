"""Data update coordinator for the Sungrow SHx Inverter integration.

The coordinator owns the :class:`SungrowModbusClient` and polls all
:data:`descriptions.MODBUS_SENSORS` registers, grouping the polls by
:class:`descriptions.ScanGroup` so that slow-changing registers aren't
hammered every few seconds. The HA ``DataUpdateCoordinator`` ticks at
the *fastest* configured interval (the realtime group); every tick we
look at each group's ``last_fetched`` and skip the ones that aren't
due yet.

Decoded values are exposed keyed by sensor ``key`` in
``self.decoded``; raw register data is kept in ``self.data`` keyed by
``(input_type, address)`` tuples (and ``(input_type, address, 'sbr')``
for SBR-slave reads) so that entities can read a register in multiple
decodings if needed.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Final

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_SBR_SLAVE,
    CONF_SCAN_INTERVAL_FAST,
    CONF_SCAN_INTERVAL_MEDIUM,
    CONF_SCAN_INTERVAL_REALTIME,
    CONF_SCAN_INTERVAL_SLOWEST,
    CONF_SLAVE,
    DEFAULT_SBR_SLAVE,
    DEFAULT_SCAN_FAST,
    DEFAULT_SCAN_MEDIUM,
    DEFAULT_SCAN_REALTIME,
    DEFAULT_SCAN_SLOWEST,
    DEFAULT_SLAVE,
    DOMAIN,
)
from .descriptions import (
    COMPUTED_BINARY_SENSORS,
    COMPUTED_SENSORS,
    DEVICE_TYPE_MAP,
    FAMILY_UNAPPLICABLE_KEYS,
    MODBUS_SENSORS,
    SCAN_INTERVALS,
    ModbusSensorDescription,
    ScanGroup,
    family_for_device_code,
)

from .modbus_client import SungrowModbusError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .modbus_client import SungrowModbusClient

_LOGGER: Final = logging.getLogger(__name__)

# Key identifying the Sungrow inverter serial register in MODBUS_SENSORS.
_SERIAL_KEY: Final = "sg_inverter_serial"
_DEV_TYPE_KEY: Final = "sg_dev_code"
_FIRMWARE_KEY: Final = "sg_inverter_firmware_version"


@dataclass
class _GroupState:
    """Mutable bookkeeping for a scan group."""

    interval: int
    last_fetched: float = 0.0  # monotonic-ish seconds since epoch (UTC timestamp)


class SungrowModbusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll Sungrow SHx modbus registers, grouped by scan interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SungrowModbusClient,
    ) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.client = client
        options = {**entry.data, **entry.options}
        self.inverter_slave: int = options.get(CONF_SLAVE, DEFAULT_SLAVE)
        self.sbr_slave: int = options.get(CONF_SBR_SLAVE, DEFAULT_SBR_SLAVE)

        # Build per-group state using configured intervals (fall back to
        # the YAML-derived SCAN_INTERVALS table).
        self._groups: dict[ScanGroup, _GroupState] = {
            ScanGroup.REALTIME: _GroupState(
                interval=options.get(
                    CONF_SCAN_INTERVAL_REALTIME,
                    DEFAULT_SCAN_REALTIME,
                )
                or SCAN_INTERVALS[ScanGroup.REALTIME]
            ),
            ScanGroup.FAST: _GroupState(
                interval=options.get(
                    CONF_SCAN_INTERVAL_FAST,
                    DEFAULT_SCAN_FAST,
                )
                or SCAN_INTERVALS[ScanGroup.FAST]
            ),
            ScanGroup.MEDIUM: _GroupState(
                interval=options.get(
                    CONF_SCAN_INTERVAL_MEDIUM,
                    DEFAULT_SCAN_MEDIUM,
                )
                or SCAN_INTERVALS[ScanGroup.MEDIUM]
            ),
            ScanGroup.SLOWEST: _GroupState(
                interval=options.get(
                    CONF_SCAN_INTERVAL_SLOWEST,
                    DEFAULT_SCAN_SLOWEST,
                )
                or SCAN_INTERVALS[ScanGroup.SLOWEST]
            ),
        }

        # Tick at the fastest group's interval.
        fastest = min(g.interval for g in self._groups.values())
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{entry.entry_id}",
            update_interval=timedelta(seconds=fastest),
        )

        # Per-address raw registers and per-key decoded values.
        # Computed-sensor outputs share the same dict — they're keyed
        # by the description's ``key`` so platforms read all values
        # uniformly through ``self.decoded[desc.key]``.
        self._raw: dict[tuple[str, int], list[int]] = {}
        self.decoded: dict[str, Any] = {}

        # Device identity fields — populated on first refresh.
        self.serial: str = "unknown"
        self.model: str = "Sungrow SHx"
        self.firmware: str | None = None
        self.device_code: int | None = None
        self.family: str | None = None

        # Cache descriptions by group for fast iteration.
        self._by_group: dict[ScanGroup, list[ModbusSensorDescription]] = {
            group: [d for d in MODBUS_SENSORS if d.scan_group is group]
            for group in ScanGroup
        }

        # Sensor keys whose register the slave has reported as unsupported
        # (Modbus exception 1/2). We stop polling these on subsequent
        # refreshes so a single missing register doesn't burn cycles or
        # spam the log every tick.
        self._unsupported: set[str] = set()
        # First-refresh register probe: maps (input_type, address) to a
        # status dict — see :meth:`_probe_registers`.
        self.register_probe: dict[tuple[str, int], dict[str, Any]] = {}
        # Whether the configured separate SBR (battery) slave answers.
        # ``None`` until probed, ``True`` if reachable, ``False`` if it
        # times out — in which case we skip future per-tick pings so a
        # dead slave doesn't burn ~30 s of pymodbus retries every refresh.
        self._sbr_reachable: bool | None = None

    # ------------------------------------------------------------------
    # HA integration surface
    # ------------------------------------------------------------------
    async def async_config_entry_first_refresh(self) -> None:  # type: ignore[override]
        """Probe registers, then force all groups to fetch on first refresh."""
        # Probe before the first poll so we know up-front which registers
        # the slave rejects and can mark them unsupported. This populates
        # ``self._unsupported`` so subsequent reads skip them.
        await self._probe_registers()
        for state in self._groups.values():
            state.last_fetched = 0.0
        await super().async_config_entry_first_refresh()
        self._populate_device_info()

    async def _async_update_data(self) -> dict[str, Any]:
        """Read all registers whose scan group is due.

        Per-register Modbus exception responses (illegal function /
        illegal data address) are tolerated: the offending key is added
        to :attr:`_unsupported` and skipped on subsequent refreshes. We
        only raise :class:`UpdateFailed` when *every* attempted read in
        a refresh fails — that's the signature of a real connection
        loss vs. a model that simply doesn't expose certain registers.
        """
        now = dt_util.utcnow().timestamp()
        fetched_any = False
        attempted = 0
        succeeded = 0
        last_transport_error: SungrowModbusError | None = None

        for group, state in self._groups.items():
            if (now - state.last_fetched) + 0.1 < state.interval and state.last_fetched:
                continue
            for desc in self._by_group[group]:
                if desc.key in self._unsupported:
                    continue
                attempted += 1
                try:
                    await self._read_description(desc)
                except SungrowModbusError as err:
                    if err.is_unsupported:
                        self._mark_unsupported(desc, err)
                        continue
                    last_transport_error = err
                except Exception as err:  # noqa: BLE001
                    raise UpdateFailed(
                        f"Error updating Sungrow SHx data: {err}"
                    ) from err
                else:
                    succeeded += 1
            state.last_fetched = now
            fetched_any = True

        if attempted and succeeded == 0 and last_transport_error is not None:
            # Every read failed at the transport layer — treat as a
            # connection issue so HA marks the integration unavailable.
            raise UpdateFailed(
                f"All Sungrow register reads failed: {last_transport_error}"
            ) from last_transport_error

        # SBR (battery) slave liveness ping. Skipped entirely once we've
        # established the slave is dead (see :meth:`_probe_registers`)
        # so a misconfigured sbr_slave doesn't burn ~30 s of pymodbus
        # retries every refresh.
        if (
            fetched_any
            and self.sbr_slave
            and self.sbr_slave != self.inverter_slave
            and self._sbr_reachable is not False
        ):
            try:
                await self.client.read_holding(13000, 1, slave=self.sbr_slave)
            except SungrowModbusError:
                self._sbr_reachable = False
                _LOGGER.debug(
                    "SBR ping failed; disabling further SBR pings",
                    exc_info=True,
                )
            else:
                self._sbr_reachable = True

        # Compute derived (template-replacement) sensor values so the
        # entity platforms can read them out of ``self.decoded`` like
        # any other modbus value. Computed sensors may depend on each
        # other; ``COMPUTED_SENSORS`` is in dependency order.
        self._compute_derived()

        return self.decoded

    def _compute_derived(self) -> None:
        """Populate ``self.decoded`` with computed-sensor and binary outputs.

        Each entry's ``requires`` keys must be present and non-``None``
        in :attr:`decoded`; otherwise the computed value is ``None``
        (and the entity reports unavailable).
        """
        for desc in COMPUTED_SENSORS:
            if any(self.decoded.get(k) is None for k in desc.requires):
                self.decoded[desc.key] = None
                continue
            try:
                self.decoded[desc.key] = desc.compute(self.decoded)
            except (TypeError, ValueError, ZeroDivisionError):
                _LOGGER.debug(
                    "Compute for %s raised; leaving None", desc.key, exc_info=True
                )
                self.decoded[desc.key] = None
        for desc in COMPUTED_BINARY_SENSORS:
            if any(self.decoded.get(k) is None for k in desc.requires):
                self.decoded[desc.key] = None
                continue
            try:
                self.decoded[desc.key] = bool(desc.compute(self.decoded))
            except (TypeError, ValueError):
                _LOGGER.debug(
                    "Compute for %s raised; leaving None", desc.key, exc_info=True
                )
                self.decoded[desc.key] = None

    async def _probe_registers(self) -> None:
        """Walk every distinct (input_type, address, count) once.

        Run before the first poll. For each unique read we record the
        outcome — ``ok``, ``illegal_function``, ``illegal_address``,
        ``error`` (transport / other modbus error), or ``no_response``
        — into :attr:`register_probe`, keyed by ``(input_type,
        address)``. Registers reported as unsupported are added to
        :attr:`_unsupported` so the regular refresh skips them.

        The probe is best-effort: a connection failure here is not
        fatal — the regular first-refresh below will surface it via
        :class:`UpdateFailed` if the slave really is unreachable.
        """
        # Collapse descriptions that share an address+input_type so we
        # only pay one read per physical register block. We use the
        # widest count seen at the address so a 2-register int32 read
        # also covers the int16 alias if any description uses one.
        targets: dict[tuple[str, int], tuple[int, list[str]]] = {}
        for desc in MODBUS_SENSORS:
            key = (desc.input_type, desc.address)
            count, keys = targets.get(key, (0, []))
            targets[key] = (max(count, desc.count), [*keys, desc.key])

        ok = 0
        illegal = 0
        errored = 0
        for (input_type, address), (count, keys) in sorted(targets.items()):
            status: str
            exc_code: int | None = None
            raw: list[int] | None = None
            if input_type not in ("input", "holding"):
                status = "unknown_input_type"
            else:
                try:
                    if input_type == "input":
                        raw = await self.client.read_input(
                            address, count, slave=self.inverter_slave
                        )
                    else:
                        raw = await self.client.read_holding(
                            address, count, slave=self.inverter_slave
                        )
                except SungrowModbusError as err:
                    exc_code = err.exception_code
                    if exc_code == 1:
                        status = "illegal_function"
                    elif exc_code == 2:
                        status = "illegal_address"
                    elif exc_code is not None:
                        status = f"modbus_exception_{exc_code}"
                    else:
                        status = "transport_error"
                else:
                    status = "ok" if raw is not None else "no_response"

            self.register_probe[(input_type, address)] = {
                "count": count,
                "keys": keys,
                "status": status,
                "exception_code": exc_code,
                "registers": raw,
            }
            if status == "ok":
                ok += 1
            elif status in ("illegal_function", "illegal_address"):
                illegal += 1
                for k in keys:
                    self._unsupported.add(k)
            else:
                errored += 1

        # Resolve device family from register 4999 (sg_dev_code) and
        # mark family-inapplicable keys unsupported. This handles the
        # "phantom zero" case where the slave answers OK but the value
        # is meaningless (e.g. phase B/C on a single-phase RS unit).
        dev_info = self.register_probe.get(("input", 4999))
        if dev_info and dev_info["status"] == "ok" and dev_info["registers"]:
            self.device_code = dev_info["registers"][0]
            self.family = family_for_device_code(self.device_code)
            family_keys = FAMILY_UNAPPLICABLE_KEYS.get(self.family or "", frozenset())
            if family_keys:
                self._unsupported |= family_keys
                _LOGGER.info(
                    "Sungrow device code 0x%04X classified as %s family;"
                    " %d additional key(s) marked unsupported",
                    self.device_code,
                    self.family,
                    len(family_keys),
                )
            else:
                _LOGGER.debug(
                    "Sungrow device code 0x%04X family %s — no extra key filter",
                    self.device_code,
                    self.family,
                )

        _LOGGER.info(
            "Sungrow register probe: %d ok, %d unsupported, %d other"
            " (out of %d distinct addresses); skipping %d sensor key(s)",
            ok,
            illegal,
            errored,
            len(targets),
            len(self._unsupported),
        )

        # Probe the separate SBR (battery) slave once. If it doesn't
        # answer, mark it dead and never ping it again — otherwise each
        # refresh wastes ~30 s on pymodbus retries. WiNet-S TCP installs
        # typically proxy all BMS data through the inverter slave so a
        # separate sbr_slave is unnecessary.
        if self.sbr_slave and self.sbr_slave != self.inverter_slave:
            try:
                await self.client.read_holding(13000, 1, slave=self.sbr_slave)
            except SungrowModbusError as err:
                self._sbr_reachable = False
                _LOGGER.warning(
                    "Sungrow SBR slave %d did not answer (%s);"
                    " disabling per-tick SBR ping. Battery data is normally"
                    " proxied through inverter slave %d on TCP installs —"
                    " set sbr_slave=0 in the integration options to suppress"
                    " this entirely",
                    self.sbr_slave,
                    err,
                    self.inverter_slave,
                )
            else:
                self._sbr_reachable = True
                _LOGGER.debug(
                    "Sungrow SBR slave %d reachable", self.sbr_slave
                )
        if illegal:
            unsupported_pairs = sorted(
                (input_type, address)
                for (input_type, address), info in self.register_probe.items()
                if info["status"] in ("illegal_function", "illegal_address")
            )
            _LOGGER.debug(
                "Sungrow unsupported registers: %s",
                ", ".join(f"{t}:{a}" for t, a in unsupported_pairs),
            )

    def _mark_unsupported(
        self, desc: ModbusSensorDescription, err: SungrowModbusError
    ) -> None:
        """Record a register as unsupported and warn once."""
        self._unsupported.add(desc.key)
        _LOGGER.warning(
            "Sungrow register %s (%s:%d+%d) reported unsupported by slave"
            " (exception code %s); skipping on future refreshes",
            desc.key,
            desc.input_type,
            desc.address,
            desc.count,
            err.exception_code,
        )

    # ------------------------------------------------------------------
    # Reading / decoding
    # ------------------------------------------------------------------
    async def _read_description(self, desc: ModbusSensorDescription) -> None:
        """Read one register group and store both raw + decoded values.

        Lets :class:`SungrowModbusError` propagate so the caller can
        decide whether the failure means "skip this register" (Modbus
        exception 1/2) or "treat as a transport problem".
        """
        if desc.input_type == "input":
            raw = await self.client.read_input(
                desc.address, desc.count, slave=self.inverter_slave
            )
        elif desc.input_type == "holding":
            raw = await self.client.read_holding(
                desc.address, desc.count, slave=self.inverter_slave
            )
        else:
            raise UpdateFailed(
                f"Unknown input_type {desc.input_type!r} for {desc.key}"
            )

        self._raw[(desc.input_type, desc.address)] = raw
        self.decoded[desc.key] = self._decode(desc, raw)

    @staticmethod
    def _decode(desc: ModbusSensorDescription, registers: list[int]) -> Any:
        """Decode a raw register list per the description's data_type/swap."""
        data_type = desc.data_type
        swap = desc.swap

        if data_type == "string":
            # Two bytes per register, big-endian, stop at first NUL.
            buf = bytearray()
            for reg in registers:
                buf.append((reg >> 8) & 0xFF)
                buf.append(reg & 0xFF)
            end = buf.find(b"\x00")
            if end != -1:
                buf = buf[:end]
            try:
                return buf.decode("ascii", errors="replace").strip()
            except UnicodeDecodeError:
                return buf.decode("latin-1", errors="replace").strip()

        if data_type == "uint16":
            value = registers[0] & 0xFFFF
            # 0xFFFF is Sungrow's "not set / not available" sentinel for
            # unsigned 16-bit registers (e.g. active power limitation,
            # battery start-power thresholds). Surface as None instead
            # of returning a scaled nonsense value like 6553.5.
            if value == 0xFFFF:
                return None
        elif data_type == "int16":
            value = registers[0] & 0xFFFF
            if value >= 0x8000:
                value -= 0x10000
        elif data_type in {"uint32", "int32"}:
            if len(registers) < 2:
                return None
            if swap == "word":
                lo, hi = registers[0], registers[1]
            else:
                hi, lo = registers[0], registers[1]
            combined = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
            # 0xFFFFFFFF is Sungrow's "not set" sentinel for uint32
            # totals (lifetime kWh counters before first poll, etc.).
            if data_type == "uint32" and combined == 0xFFFFFFFF:
                return None
            if data_type == "int32" and combined >= 0x80000000:
                combined -= 0x100000000
            value = combined
        elif data_type in {"float32"}:
            if len(registers) < 2:
                return None
            if swap == "word":
                packed = struct.pack(">HH", registers[1], registers[0])
            else:
                packed = struct.pack(">HH", registers[0], registers[1])
            return struct.unpack(">f", packed)[0]
        else:
            _LOGGER.debug("Unhandled data_type %r for %s", data_type, desc.key)
            return registers

        scaled = value * desc.scale + desc.offset
        if desc.precision is not None:
            if desc.precision == 0 and desc.scale == 1.0 and desc.offset == 0.0:
                return int(scaled)
            return round(scaled, desc.precision)
        if desc.scale == 1.0 and desc.offset == 0.0:
            return int(scaled)
        return scaled

    # ------------------------------------------------------------------
    # Device metadata
    # ------------------------------------------------------------------
    def _populate_device_info(self) -> None:
        """Resolve serial, model and firmware from the most recent decode."""
        serial = self.decoded.get(_SERIAL_KEY)
        if isinstance(serial, str) and serial.strip():
            self.serial = serial.strip()
        else:
            # Fall back to host:port+slave so unique_ids stay stable even
            # if the serial register temporarily fails to decode.
            host = self.entry.data.get("host", "unknown")
            self.serial = f"{host}-{self.inverter_slave}"

        dev_code = self.decoded.get(_DEV_TYPE_KEY)
        if isinstance(dev_code, int):
            self.model = DEVICE_TYPE_MAP.get(
                dev_code, f"SHx (0x{dev_code:04X})"
            )

        fw = self.decoded.get(_FIRMWARE_KEY)
        if isinstance(fw, str) and fw.strip():
            self.firmware = fw.strip()

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------
    def raw_registers(self, input_type: str, address: int) -> list[int] | None:
        """Return the cached raw registers for an address, or None."""
        return self._raw.get((input_type, address))

    def value_for(self, key: str) -> Any:
        """Return the latest decoded value for a sensor key."""
        return self.decoded.get(key)

    @property
    def unsupported_keys(self) -> frozenset[str]:
        """Sensor keys whose register the slave reports as unsupported."""
        return frozenset(self._unsupported)

