"""The stdlib-only Modbus client, register decoder and plan loader.

What `sungrow_survey.py`, `probe.py` and `blocks.py` build on when
`sungrow_modbus` is not installed, which for a contributor is the usual case.
Nothing here runs by itself: run `sungrow_survey.py`.

**It only reads.** Only the two Modbus read function codes are implemented in
this file — there is no code here that can write a register, and you are
welcome to check: search for `_FC_` below.
"""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
import socket
import struct
import sys
import time

# The only two function codes this file knows. Both are reads: 4 is "read
# input registers", 3 is "read holding registers". Writing would need 6 or 16,
# which are deliberately absent.
_FC_READ_INPUT = 4
_FC_READ_HOLDING = 3


class ModbusError(Exception):
    """The device answered, but refused the request."""


class Dropped(OSError):
    """The device hung up rather than answering.

    An `OSError`, so that code written against the library's exceptions
    catches it too: `modbus-connection` surfaces a lost connection as its own
    `ModbusConnectionError`, and every caller in the scanner already writes
    `except (ModbusError, TimeoutError, OSError)`. Deriving from `OSError` is
    what lets one set of handlers serve both clients.

    Sungrow hardware does this for some requests instead of returning a
    Modbus exception, so it has to be survivable *and* recorded: a register
    that reliably drops the link is a hazard the integration must avoid, and
    is worth knowing about separately from one that is politely refused.
    """


class Connection:
    """A Modbus TCP connection that reopens itself when the device hangs up.

    Without this the first dropped connection would poison everything after
    it: every remaining register would be reported as refused, and a report
    full of false negatives is worse than no report.
    """

    def __init__(self, host, port, timeout, delay):
        """Remember where to connect, without connecting yet."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self.delay = delay
        self.sock = None
        self.reconnects = 0

    def _connect(self):
        """Open the socket."""
        self.sock = socket.create_connection((self.host, self.port), self.timeout)
        self.sock.settimeout(self.timeout)

    def close(self):
        """Close the socket if one is open."""
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    #: How long to wait before each retry. Sungrow hardware drops a connection
    #: every so often regardless of which register was asked for, and an
    #: immediate reconnect is often refused as well — but it recovers within a
    #: second or two. Escalating waits turn most of those drops back into
    #: readings, which matters because a register wrongly recorded as missing
    #: is worse than a slow report.
    BACKOFF = (0.0, 0.5, 1.5)

    def read(self, unit, function, address, count):
        """Read registers, reconnecting and waiting if the device hangs up."""
        last = None
        for attempt, pause in enumerate(self.BACKOFF):
            if self.sock is None:
                if pause:
                    time.sleep(pause)
                try:
                    self._connect()
                except OSError as err:
                    last = Dropped(str(err))
                    continue
                if attempt:
                    self.reconnects += 1
            try:
                return self._read_once(unit, function, address, count)
            except Dropped as err:
                last = err
                self.close()
            except OSError as err:
                last = Dropped(str(err))
                self.close()
        raise last or Dropped("unreachable")

    def _read_once(self, unit, function, address, count):
        request = struct.pack(">HHHBBHH", 1, 0, 6, unit, function, address, count)
        self.sock.sendall(request)
        header = _recv_exactly(self.sock, 8)
        length = struct.unpack(">H", header[4:6])[0]
        body = _recv_exactly(self.sock, max(0, length - 2))
        answered_function = header[7]
        if answered_function != function:
            raise ModbusError(f"exception 0x{body[0] if body else 0:02X}")
        if len(body) < 1 or body[0] != count * 2:
            raise ModbusError("short answer")
        values = struct.unpack(f">{count}H", body[1 : 1 + count * 2])
        if self.delay:
            time.sleep(self.delay)
        return list(values)


def _recv_exactly(sock, size):
    """Read exactly `size` bytes, or raise."""
    chunks = []
    while size > 0:
        chunk = sock.recv(size)
        if not chunk:
            raise Dropped("the device closed the connection")
        chunks.append(chunk)
        size -= len(chunk)
    return b"".join(chunks)


def _decode_string(values):
    """Turn registers into the ASCII string they hold."""
    raw = b"".join(struct.pack(">H", v) for v in values)
    return raw.decode("ascii", "replace").strip("\x00").strip()


#: Field names never written into a report, whatever else is. Mirrors
#: `probe.NEVER_PUBLISH`, and for the same reason: the stand-in serial exists
#: so the real one does not leave the machine, and a sweep of the whole map
#: walks straight into a field that holds it.
NEVER_PUBLISH = ("serial",)


class PortableParams:
    """Where to connect, in the shape `ModbusTcpParams` has."""

    def __init__(self, host, port=502):
        """Remember the address."""
        self.host = host
        self.port = port


class PortableUnit:
    """One unit id on a `PortableConnection`, with the library's read API.

    The point of the shape is that nothing else has to know which client it
    got. `probe.py` reads registers through `read_input_registers` and
    `read_holding_registers` and catches `(ModbusError, TimeoutError,
    OSError)`; both clients now satisfy that, so the identity reads, the
    firmware strings, the curated probes, the other-unit probes, the transport
    signals and the raw dump all work unchanged with nothing installed.

    Async because the library's are, not because anything here awaits: the
    socket is blocking and deliberately so. A survey reads one register block
    at a time on purpose -- a Sungrow grants very few sessions -- so there is
    no concurrency to gain and a synchronous client is one less thing to get
    wrong.
    """

    def __init__(self, connection, unit_id):
        """Bind a unit id to a connection."""
        self._connection = connection
        self._unit_id = unit_id

    async def read_input_registers(self, address, count):
        """Read input registers, as the library's unit does."""
        return self._connection.link.read(self._unit_id, _FC_READ_INPUT, address, count)

    async def read_holding_registers(self, address, count):
        """Read holding registers, as the library's unit does."""
        return self._connection.link.read(
            self._unit_id, _FC_READ_HOLDING, address, count
        )


class PortableConnection:
    """A `ModbusConnection` stand-in built on the stdlib socket client."""

    def __init__(self, params, timeout=10.0, message_spacing=0.0):
        """Open nothing yet; `Connection` connects on its first read."""
        self.link = Connection(params.host, params.port, timeout, message_spacing)

    def for_unit(self, unit_id):
        """Return the unit with that address."""
        return PortableUnit(self, unit_id)

    async def close(self):
        """Close the socket."""
        self.link.close()


def decode(field, words):
    """Decode one register block from its `scan_plan.json` description.

    This is the second decoder in the project, and a second implementation of
    anything is a liability -- so it exists for one reason and is guarded one
    way. The reason: `scripts/sungrow_survey/` is run by contributors with
    nothing installed, and the first decoder lives in `sungrow_modbus`, which
    they will not have. The guard: `tests/test_portable_decoder.py` decodes
    every field in the map both ways and compares, so the two cannot drift
    apart quietly.

    Everything it needs travels in the field description, including the
    decimal precision -- deliberately, because rounding is the part that would
    otherwise be reimplemented from a rule and get it subtly wrong.

    This mirrors the library's *field* decoder and stops there. Turning an
    empty string into "no reading" is a separate step in the library, done a
    layer up, and it is `present()` below -- keeping the same seam means the
    two can be compared at the same level, which is what makes the test
    meaningful rather than approximate.
    """
    if field["kind"] == "string":
        return _decode_string(words)

    ordered = words if field["word_order"] == "big" else list(reversed(words))
    raw = 0
    for word in ordered:
        raw = (raw << 16) | (word & 0xFFFF)

    # The sentinel is matched against the raw, unsigned pattern, before any
    # sign folding -- 0x7FFFFFFF is "unavailable" for a signed 32-bit field
    # and must not first become a large positive number.
    if raw in field["nan"]:
        return None

    bits = 16 * len(words)
    value = raw - (1 << bits) if field["signed"] and raw >= 1 << (bits - 1) else raw

    scale = field["scale"]
    offset = field["offset"]
    if scale == 1.0 and offset == 0.0:
        return value  # keep integers integral when there is nothing to scale
    scaled = value * scale + offset
    decimals = field["decimals"]
    return int(scaled) if decimals == 0 else round(scaled, decimals)


def present(value):
    """Return the value, or None where the device said it has none.

    The numeric "unavailable" codes are declared per field and `decode`
    handles them. A UTF-8 field Sungrow cannot fill is **all 0x00**, which is
    not declared anywhere and decodes to the empty string -- so without this
    it would reach a report as a reading of "".

    Mirrors `sungrow_modbus.model.present`, and matters for the same reason it
    does there: an absent Sungrow battery's empty firmware string would
    otherwise count as evidence of a Sungrow battery.

    Kept separate from `decode` so the seam sits where the library's does --
    `decode` is `Field.decode`, this is `Device.field`'s wrapper -- and
    pinned against the library's own by `tests/test_portable_decoder.py`.
    """
    if isinstance(value, str) and not value.strip("\x00").strip():
        return None
    return value


PLAN_FILE = Path(__file__).resolve().parent / "scan_plan.json"

#: The plan, once. Verifying it drives every component against a mock unit,
#: which is quick but not free, and `model_for` is called from inside loops.
_PLAN = None


def load_plan():
    """Return the committed plan, verified against the library where possible.

    Lives here, beside the decoder, because this is the file that *reads* the
    plan: `read_fields` takes it, `blocks.py` measures it, and `probe.py`
    surveys with it. Three copies of "load the JSON and check it" is how one
    of them ends up trusting a stale file.

    Two sources for one fact is what this file used to be wrong about: it
    re-derived the pooling itself, agreed with the library by luck, and would
    have gone on agreeing right up until somebody added a scale register. So
    there is one source now -- the JSON -- and where the library happens to be
    importable it is used to *check* that source rather than to replace it.

    A mismatch stops the run. A stale plan does not produce a wrong answer
    loudly; it measures a plan the integration no longer uses and reports that
    everything is fine, which is worse than measuring nothing.
    """
    global _PLAN
    if _PLAN is not None:
        return _PLAN

    if not PLAN_FILE.exists():
        raise SystemExit(
            f"{PLAN_FILE.name} is missing. It sits beside these scripts and is\n"
            "written by scripts/generate/generate_scan_plan.py; a downloaded copy of\n"
            "this directory should already contain it."
        )
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "generate"))
        from generate_scan_plan import derive, models
    except (ModuleNotFoundError, ImportError):
        plan["verified"] = False
        _PLAN = plan
        return plan

    try:
        components, fields, tables = _derived(derive, models)
    except ModuleNotFoundError:
        # The generator is here but the library is not, which is the ordinary
        # case for a downloaded directory sitting inside a checkout.
        plan["verified"] = False
        _PLAN = plan
        return plan

    # The model tables are checked too, and not because a name is as important
    # as an address: a stale `device_types` names the *wrong inverter* in the
    # document and in its filename, which is the one kind of staleness a
    # reader cannot spot afterwards.
    stale = components != plan["components"] or fields != plan["fields"]
    stale = stale or any(plan.get(key) != value for key, value in tables.items())
    if stale:
        raise SystemExit(
            f"{PLAN_FILE.name} does not match the installed library.\n\n"
            "Run scripts/generate/generate_scan_plan.py and commit the result. Until\n"
            "then any measurement here describes a plan the integration does\n"
            "not use."
        )
    plan["verified"] = True
    _PLAN = plan
    return plan


def address(plan: dict, name: str, device: str = "inverter") -> tuple[str, int, int]:
    """Return ``(space, address, count)`` for one register, by name.

    The survey's copy of ``sungrow_modbus.addresses.field_address``, reading
    the plan instead of the library. A mapped field comes from ``fields``; the
    few registers no component maps come from ``addresses``, under the name
    the library gives them. The device is part of the question because names
    repeat across devices -- an inverter and a wallbox both have a
    ``device_type_code`` -- and an ambiguous name is refused, not guessed.
    """
    named = plan.get("addresses", {}).get(name)
    if named is not None:
        return named["space"], named["address"], named["count"]
    roles = {
        row["component"]: row.get("unit", "inverter") for row in plan["components"]
    }
    found = {
        (row["space"], row["address"], row["count"])
        for row in plan["fields"]
        if row["name"] == name and roles.get(row["component"], "inverter") == device
    }
    if len(found) != 1:
        raise KeyError(f"{name!r} on the {device}: {len(found)} addresses in the plan")
    return found.pop()


async def read_block(unit, where: tuple[str, int, int]) -> list[int]:
    """Read one ``(space, address, count)`` from ``address``. Raises, like the unit."""
    space, start, count = where
    if space == "holding":
        return list(await unit.read_holding_registers(start, count))
    return list(await unit.read_input_registers(start, count))


def _derived(derive, models):
    """Run the generator's two derivations, from sync code or from async.

    `derive()` calls `asyncio.run` -- it drives the library against a mock
    unit -- so calling it from inside a running loop raises, and every caller
    that matters here is async. A worker thread has no loop of its own, which
    makes it the one place `asyncio.run` is still allowed.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return (*derive(), models())
    with ThreadPoolExecutor(max_workers=1) as pool:
        return (*pool.submit(derive).result(), pool.submit(models).result())


def model_for(plan, device_type_code):
    """Return the inverter model for a device type code, or None.

    `sungrow_modbus.const.model_for` without the library. Takes the plan
    rather than reading a module-level table, so the caller cannot forget
    which artefact it came from.
    """
    if device_type_code is None:
        return None
    return plan["device_types"].get(f"0x{int(device_type_code):04X}")


def battery_model_for_capacity(plan, capacity_kwh):
    """Return the Sungrow pack whose rated capacity this matches, or None.

    `sungrow_modbus.battery.model_for_capacity` without the library, tolerance
    included -- meaningful only once the pack is known to be a Sungrow, since
    a third-party battery of the same size is not an SBR.

    The whole table row comes back, `{"name", "capacity_kwh"}`, because a
    caller that names a pack also prints its rated size.
    """
    if capacity_kwh is None:
        return None
    fraction = plan["battery_capacity_tolerance_fraction"]
    within = [
        model
        for model in plan["battery_models"]
        if abs(model["capacity_kwh"] - capacity_kwh) <= model["capacity_kwh"] * fraction
    ]
    return within[0] if len(within) == 1 else None


#: The library's `discovery.MAX_HOSTS`, kept as a literal because this is a
#: guard against a typed /8 rather than a fact about Sungrow. A sweep of more
#: than this is a mistake, not a long wait.
MAX_HOSTS = 1024


class NetworkTooLarge(ValueError):
    """Raised when a sweep would probe more addresses than MAX_HOSTS."""

    def __init__(self, network, hosts, limit):
        """Say what was asked for and what the limit is."""
        super().__init__(
            f"{network} holds {hosts} addresses, over the limit of {limit}"
        )
        self.network = network
        self.hosts = hosts
        self.limit = limit


def hosts_in(network, limit=MAX_HOSTS):
    """Return every usable address in a network, or raise if there are too many.

    `sungrow_modbus.discovery.hosts_in` without the library, down to checking
    the size **arithmetically before generating anything**: somebody who types
    /8 gets the answer immediately instead of after twenty seconds and several
    gigabytes.
    """
    parsed = ipaddress.ip_network(network, strict=False)
    if parsed.num_addresses <= 2:
        # A /31 or /32: no network and broadcast address to set aside.
        count = parsed.num_addresses
    else:
        count = parsed.num_addresses - 2
    if count > limit:
        raise NetworkTooLarge(str(parsed), count, limit)
    # A /32 has no "hosts" in the iterator's sense, but scanning one address
    # is a perfectly reasonable thing to ask for.
    return [str(host) for host in parsed.hosts()] or [str(parsed.network_address)]


def network_of(address, prefix):
    """Return the network an interface address belongs to, as a CIDR string."""
    return str(ipaddress.ip_interface(f"{address}/{prefix}").network)


async def read_fields(plan, unit, passes=8, role=None):
    """Read and decode every field in the plan, component by component.

    The one place this project reimplements what the library does, and it is
    here because a contributor running the survey has no library. Everything
    it needs is in `plan`: which blocks each component reads, and where each
    field sits inside them.

    The shape mirrors the library's, because the shape is a finding rather
    than a style. A component's blocks are read together and its fields
    sliced out of the words -- 105 fields in 27 reads instead of 105 -- and a
    component that misses is retried on a later pass rather than immediately,
    because a Sungrow's collisions are moments and not states. Whatever is
    still missing at the end is read one field at a time, so only the
    registers the device truly refuses are absent from the report.

    Returns the same structure `probe.py` builds with the library:
    `{"values": {...}, "components_that_did_not_answer": [...]}`, plus the
    fields that never read at all.

    `role` selects which components to read. `None` is the inverter's own --
    every component the plan does not mark otherwise -- and `"battery"` is
    the SBR's two, which live on their own unit id. Selecting rather than
    reading everything matters: the SBR's blocks read at the *inverter's*
    unit answer 0xFFFF, which is how the survey came to record that
    something answered at unit 200 without ever recording what it said.
    """
    import asyncio

    by_component = {
        entry["component"]: entry
        for entry in plan["components"]
        # The identity block is read separately, before this, and its fields
        # are reported as the device's identity rather than as readings --
        # which is also how the library's path draws the line.
        if entry["component"] != "identity"
        # And only this role's components: a plan entry carrying a `unit` is
        # somewhere else entirely, and reading it here would read the
        # battery's addresses at the inverter's unit id.
        and entry.get("unit") == role
    }
    fields_of = {}
    for field in plan["fields"]:
        # Never publish anything whose name mentions a serial. The whole
        # document is built around the real serial staying in `.testdata/`,
        # and a full sweep of the map otherwise walks straight into
        # `sungrow_inverter_serial` -- which it did, before this line.
        if any(word in field["name"] for word in NEVER_PUBLISH):
            continue
        fields_of.setdefault(field["component"], []).append(field)

    values = {}
    pending = [name for name in by_component if name in fields_of]

    for this_pass in range(1, max(1, passes) + 1):
        still_missing = []
        for name in pending:
            entry = by_component[name]
            words_at = {}
            try:
                for address, count in entry["blocks"]:
                    words = await _read(unit, entry["space"], address, count)
                    for offset, word in enumerate(words):
                        words_at[address + offset] = word
            except (ModbusError, OSError):
                still_missing.append(name)
                continue
            for field in fields_of[name]:
                # `present` on top of `decode`, because the library's
                # `Device.field` does exactly that and this report has to be
                # comparable with one taken through it. A field that did not
                # read is named in `fields_that_did_not_read`, so nothing is
                # lost by both of them being null here.
                values[field["name"]] = present(decode(field, _slice(words_at, field)))
        # Assigned before the test, for the reason `probe.py` carries at
        # length: the other order reports every component missed after a
        # flawless read.
        pending = still_missing
        if not pending:
            break
        if this_pass < max(1, passes):
            await asyncio.sleep(2.0)

    # Field by field, so one unreadable register does not cost its neighbours.
    # On gerd's inverter over WiNet-S this recovered nothing and proved
    # something: the two firmware registers its components asked for refused
    # individually as well, which is what makes them a device fact rather
    # than a casualty of block pooling.
    unreadable = []
    salvaged = []
    for name in pending:
        entry = by_component[name]
        for field in fields_of[name]:
            try:
                words = await _read(
                    unit, field["space"], field["address"], field["count"]
                )
            except (ModbusError, OSError):
                unreadable.append(field["name"])
                values.setdefault(field["name"], None)
                continue
            values[field["name"]] = present(decode(field, list(words)))
            salvaged.append(field["name"])

    # Shaped exactly like `probe.py`'s `_async_decoded_readings`, down to
    # omitting the empty lists rather than publishing them: a document is
    # read by comparing it with other documents, so a difference in shape
    # between the two paths would read as a difference between two houses.
    # `tests/test_portable_readings.py` compares the whole report, not just
    # its values, for that reason.
    report = {
        "values": {name: values.get(name) for name in sorted(values)},
        "components_that_did_not_answer": sorted(pending),
    }
    if salvaged:
        report["fields_read_individually"] = sorted(salvaged)
    if unreadable:
        report["fields_that_did_not_read"] = sorted(unreadable)
    return report


_DROPPED = None


def _dropped_types():
    """Return the exception types a read can fail with, per unit behind it.

    The seam in `_read` needs two halves and only had one. `PortableUnit`
    raises this file's `ModbusError`; the library's unit raises
    `modbus_connection.ModbusError`, which derives from plain `Exception` --
    so `except (ModbusError, OSError)` did not catch it, and a single dropped
    read on the library-backed path escaped every per-component tolerance and
    ended the survey. On an inverter somebody else is already polling that is
    not the unlikely case, it is the usual one.

    Imported lazily and optionally: a module-level import of the library
    would break the survey for everybody without it, and
    `tests/test_scan_is_standalone.py` fails the build if one appears.
    """
    global _DROPPED
    if _DROPPED is None:
        types = [ModbusError, Dropped, TimeoutError, OSError]
        try:
            from modbus_connection import ModbusError as LibraryError
        except ImportError:
            pass
        else:
            types.append(LibraryError)
        _DROPPED = tuple(types)
    return _DROPPED


async def _read(unit, space, address, count):
    """Read one block through whichever unit was handed over.

    Both clients expose the same two async methods, so this works against
    `PortableUnit` and against the library's unit without knowing which it
    has -- which is what lets the readings be produced either way and then
    compared.

    A failure is re-raised as `Dropped`, which is an `OSError`, so callers
    tolerate a miss the same way whichever unit produced it.
    """
    read = (
        unit.read_input_registers if space == "input" else unit.read_holding_registers
    )
    try:
        return list(await read(address, count))
    except _dropped_types() as err:
        raise Dropped(str(err) or type(err).__name__) from err


def _slice(words_at, field):
    """Return one field's words out of a component's block reads."""
    return [
        words_at.get(field["address"] + offset, 0) for offset in range(field["count"])
    ]
