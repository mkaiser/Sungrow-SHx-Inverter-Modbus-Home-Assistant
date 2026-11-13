"""What a Sungrow device calls itself on the network, beside Modbus.

Three things a router or a LAN can say about a device that no register does,
and that Home Assistant can discover a device by without being told its
address:

- **mDNS.** A WiNet-S and a wallbox at its own address advertise
  `_http._tcp` with a TXT record naming the device, its serial and its units;
  the dongle's names the inverter and the battery behind it as well. Measured
  at one house, by unicast questions (wiki: *Does a WiNet-S advertise over
  mDNS?*). The inverter's own LAN port advertised nothing there.
- **The reverse-DNS name**, which on most home networks is the name the
  device gave the router's DHCP server: what a `dhcp` matcher would key on.
- **The MAC address's vendor prefix** (the first three octets), the other
  thing a `dhcp` matcher keys on. A prefix names a manufacturer, never one
  device.

`network_section` turns them into the diagnosis's `network_names` section,
with every serial replaced by its stand-in and no address. A record is a
hint, never an identity: what a device is, is decided by what answers over
Modbus.

Nothing here imports Home Assistant. `zeroconf` is the optional
`discovery` extra and is imported only when a browse runs.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
import ipaddress
from pathlib import Path
import re
import sys
from typing import Any

#: The one service type a Sungrow device was measured advertising.
SERVICE_TYPE = "_http._tcp.local."

#: What the board key's first field says on every Sungrow record measured.
VENDOR = "SUNGROW"

#: How long a browse listens. A responder answers a query within a second;
#: the rest is for a device on WLAN that is slow to wake.
BROWSE_SECONDS = 5.0

#: Which field of a TXT value holds what, by key, as measured on one WiNet-S
#: (`SAPPHIRE`-class firmware not known) and one AC22E-01, 2026-11-11. One
#: house: a key laid out differently elsewhere parses to fewer facts, never
#: to wrong ones, because a serial is kept only when it has a serial's shape.
#:
#: `board=SUNGROW;1;WiNet-S;<serial>;1;` and
#: `board=SUNGROW;3;AC22E-01;<serial>;1;248;`
#: `inverter=1;3598;<serial>;1;516;SH8.0RT;1;4;`
#: `battery1=2;200;8423;<serial>;1;516;SBR096;`
LAYOUTS: dict[str, dict[str, int]] = {
    "board": {"model": 2, "serial": 3},
    "inverter": {"unit": 0, "device_type_code": 1, "serial": 2, "model": 5},
    "battery": {"unit": 0, "serial": 3, "model": 6},
}

#: A field read as a serial only in this shape: letters and digits, long
#: enough not to be a unit or a count.
_SERIAL = re.compile(r"^[A-Za-z0-9]{8,20}$")

#: Anything left that looks like a serial once the known ones are replaced.
#: Wider than a Sungrow serial's own shape on purpose: a record field nobody
#: has explained is not published on the guess that it is harmless.
_SERIAL_LIKE = re.compile(r"[A-Za-z]*\d[A-Za-z0-9]{7,}")

#: What replaces a serial-like string that is not one of the parsed serials.
UNEXPLAINED = "<unexplained>"

_MAC = re.compile(
    r"([0-9A-Fa-f]{1,2})[:-]([0-9A-Fa-f]{1,2})[:-]([0-9A-Fa-f]{1,2})"
    r"[:-][0-9A-Fa-f]{1,2}[:-][0-9A-Fa-f]{1,2}[:-][0-9A-Fa-f]{1,2}"
)

#: An IPv4 or IPv6 address inside a record's text: never published.
_ADDRESS = re.compile(
    r"\b\d{1,3}(?:\.\d{1,3}){3}\b|\b[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}\b"
)


@dataclass(frozen=True)
class Advertised:
    """One device a TXT record names: what each measured field said."""

    key: str
    model: str | None = None
    serial: str | None = None
    unit: int | None = None
    device_type_code: int | None = None


@dataclass(frozen=True)
class Advert:
    """One mDNS service instance, as it answered."""

    instance: str
    service_type: str = SERVICE_TYPE
    port: int | None = None
    server: str | None = None
    addresses: tuple[str, ...] = ()
    properties: Mapping[str, str] = field(default_factory=dict)

    @property
    def devices(self) -> tuple[Advertised, ...]:
        """Every device the TXT record names, in key order."""
        return tuple(
            parsed
            for key, value in sorted(self.properties.items())
            if (parsed := parse_field(key, value)) is not None
        )

    @property
    def board(self) -> Advertised | None:
        """The device that answered, from its `board` key."""
        return next((d for d in self.devices if d.key == "board"), None)

    @property
    def inverter(self) -> Advertised | None:
        """The first inverter a dongle names behind it."""
        return next((d for d in self.devices if _role(d.key) == "inverter"), None)

    @property
    def is_sungrow(self) -> bool:
        """Whether this record is a Sungrow device's."""
        board = self.properties.get("board", "")
        if board.split(";", 1)[0].upper() == VENDOR:
            return True
        return self.instance.upper().startswith((VENDOR, "WINET"))

    @property
    def kind(self) -> str:
        """`dongle`, `wallbox` or `unknown`, from the board's model.

        A dongle by its model (`WiNet...`), a wallbox by an `AC`/`DC` model
        and its TLS port. Anything else is reported as it is.
        """
        board = self.board
        model = (board.model if board else "") or ""
        if model.upper().startswith("WINET"):
            return "dongle"
        if model.upper().startswith(("AC", "DC")):
            return "wallbox"
        return "unknown"

    @property
    def serials(self) -> tuple[str, ...]:
        """Every serial the record names, longest first."""
        found = {d.serial for d in self.devices if d.serial}
        return tuple(sorted(found, key=lambda s: (-len(s), s)))


def _role(key: str) -> str:
    """`inverter1` and `inverter` are both inverters: the trailing digit counts."""
    return key.rstrip("0123456789")


def _int(text: str) -> int | None:
    try:
        return int(text)
    except ValueError:
        return None


def parse_field(key: str, value: str) -> Advertised | None:
    """Read one TXT key by its measured layout, or None for an unknown key."""
    layout = LAYOUTS.get(_role(key))
    if layout is None:
        return None
    fields = value.split(";")

    def at(name: str) -> str | None:
        index = layout.get(name)
        if index is None or index >= len(fields):
            return None
        return fields[index].strip() or None

    serial = at("serial")
    return Advertised(
        key=key,
        model=at("model"),
        serial=serial if serial and _SERIAL.match(serial) else None,
        unit=_int(at("unit") or ""),
        device_type_code=_int(at("device_type_code") or ""),
    )


def text_properties(properties: Mapping[Any, Any] | None) -> dict[str, str]:
    """Return a TXT record as text: zeroconf hands bytes, Home Assistant strings."""
    out: dict[str, str] = {}
    for key, value in (properties or {}).items():
        name = key.decode(errors="replace") if isinstance(key, bytes) else str(key)
        if isinstance(value, bytes):
            text = value.decode(errors="replace")
        else:
            text = "" if value is None else str(value)
        out[name] = text
    return out


def instance_of(name: str, service_type: str = SERVICE_TYPE) -> str:
    """Return the instance part of a full service name."""
    suffix = "." + service_type
    return name[: -len(suffix)] if name.endswith(suffix) else name


async def async_browse(
    seconds: float = BROWSE_SECONDS, *, zeroconf: Any = None
) -> list[Advert]:
    """Browse `_http._tcp` and return every Sungrow record that answered.

    Pass ``zeroconf`` (a `zeroconf.Zeroconf`, such as Home Assistant's shared
    instance) to browse through it; without one, a private instance is
    opened and closed, which binds port 5353. Raises ``RuntimeError`` when the
    optional `zeroconf` package is missing.

    An empty list means nothing Sungrow answered **here**: a container, a
    VLAN or a firewall keeps multicast out as surely as an absent dongle.
    """
    try:
        from zeroconf import ServiceStateChange
        from zeroconf.asyncio import (
            AsyncServiceBrowser,
            AsyncServiceInfo,
            AsyncZeroconf,
        )
    except ModuleNotFoundError as err:
        raise RuntimeError(
            "mDNS needs the optional 'discovery' extra "
            "(pip install sungrow-modbus[discovery])"
        ) from err

    own = zeroconf is None
    azc = AsyncZeroconf() if own else None
    zc = azc.zeroconf if azc is not None else zeroconf
    names: set[str] = set()

    def on_change(
        zeroconf: Any,
        service_type: str,
        name: str,
        state_change: Any,
        **_: Any,
    ) -> None:
        if state_change is not ServiceStateChange.Removed:
            names.add(name)

    browser = AsyncServiceBrowser(zc, [SERVICE_TYPE], handlers=[on_change])
    try:
        await asyncio.sleep(seconds)
        adverts: list[Advert] = []
        for name in sorted(names):
            info = AsyncServiceInfo(SERVICE_TYPE, name)
            if not await info.async_request(zc, 3000):
                continue
            advert = Advert(
                instance=instance_of(name),
                port=info.port,
                server=info.server,
                addresses=tuple(info.parsed_addresses()),
                properties=text_properties(info.properties),
            )
            if advert.is_sungrow:
                adverts.append(advert)
        return adverts
    finally:
        await browser.async_cancel()
        if azc is not None:
            await azc.async_close()


def _arp_lines_linux() -> str:
    try:
        return Path("/proc/net/arp").read_text()
    except OSError:
        return ""


async def _arp_lines_command(host: str) -> str:
    """`arp -a <host>` on Windows and macOS; empty when it cannot run."""
    try:
        process = await asyncio.create_subprocess_exec(
            "arp",
            "-a",
            host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(process.communicate(), 5)
    except (OSError, TimeoutError):
        return ""
    return out.decode(errors="replace")


def mac_prefix_in(text: str, host: str) -> str | None:
    """Return the vendor prefix of `host`'s MAC address in an ARP listing, or None.

    Only a line naming the address exactly counts, and an all-zero entry (an
    incomplete one, on Linux) is no answer.
    """
    for line in text.splitlines():
        if not re.search(rf"(?<![\d.]){re.escape(host)}(?![\d.])", line):
            continue
        if match := _MAC.search(line):
            octets = [part.zfill(2).upper() for part in match.groups()]
            if octets != ["00", "00", "00"]:
                return ":".join(octets)
    return None


async def async_mac_prefix(host: str) -> str | None:
    """Return the vendor prefix of the MAC address this machine knows `host` by.

    From the ARP cache, so only on the same network segment, and only after
    something has talked to the address: a diagnosis asks this after it has.
    Behind a router, a VPN or a container bridge there is no answer, which is
    `None`, never a statement about the device.
    """
    try:
        ipaddress.IPv4Address(host)
    except ValueError:
        return None
    if sys.platform.startswith("linux"):
        return mac_prefix_in(_arp_lines_linux(), host)
    return mac_prefix_in(await _arp_lines_command(host), host)


def _stand_ins(serials: Iterable[str]) -> dict[str, str]:
    from .diagnosis_document import stand_in

    return {serial: stand_in(serial) for serial in serials if serial}


def anonymised(text: str, serials: Mapping[str, str]) -> str:
    """Return `text` with nothing in it that identifies one device.

    Each known serial becomes its stand-in; a MAC address, an IP address or a
    serial-like string nobody parsed becomes a marker.
    """
    for serial, replacement in sorted(serials.items(), key=lambda s: -len(s[0])):
        text = re.compile(re.escape(serial), re.IGNORECASE).sub(
            replacement.replace("\\", "\\\\"), text
        )
    text = _MAC.sub("<mac>", text)
    text = _ADDRESS.sub(
        lambda m: "<address>" if m.group(0).strip(":") else m.group(0), text
    )
    kept = set(serials.values())

    def unexplained(match: re.Match[str]) -> str:
        word = match.group(0)
        if any(word in stand_in for stand_in in kept):
            return word
        return UNEXPLAINED

    return _SERIAL_LIKE.sub(unexplained, text)


def _first_label(name: str | None) -> str | None:
    """Return a host name's first label: the domain is the owner's, not the device's."""
    if not name:
        return None
    label = name.split(".", 1)[0]
    return label or None


def advert_entry(
    advert: Advert, serials: Mapping[str, str], *, this_device: bool
) -> dict[str, object]:
    """One advert, as the document publishes it: no address, no serial."""
    return {
        "this_device": this_device,
        "kind": advert.kind,
        "instance": anonymised(advert.instance, serials),
        "type": advert.service_type,
        "port": advert.port,
        "server": anonymised(_first_label(advert.server) or "", serials) or None,
        "properties": {
            key: anonymised(value, serials)
            for key, value in sorted(advert.properties.items())
        },
    }


def network_section(
    *,
    host: str,
    device_serials: Iterable[str] = (),
    adverts: Iterable[Advert] | None,
    browse_error: str | None = None,
    browse_seconds: float = BROWSE_SECONDS,
    hostname: str | None = None,
    mac_prefix: str | None = None,
) -> dict[str, object]:
    """Return the document's `network_names` section.

    `adverts` is None when no browse ran (and `browse_error` says why);
    an empty list is a browse that heard no Sungrow record, which is
    `nothing_answered` and says as much about the network between as about
    the device. Each advert is marked `this_device` when it was heard from
    `host` or names one of `device_serials`.

    `hostname` is published as its first label only, serials replaced: the
    domain is the owner's network, not the device.
    """
    adverts = list(adverts) if adverts is not None else None
    all_serials = set(device_serials)
    for advert in adverts or ():
        all_serials.update(advert.serials)
    serials = _stand_ins(all_serials)

    mdns: dict[str, object]
    if adverts is None:
        mdns = {"state": "not_browsed", "why": browse_error or "not asked"}
    else:
        own = set(device_serials)
        mdns = {
            "state": "answered" if adverts else "nothing_answered",
            "browsed_seconds": browse_seconds,
            "services": [
                advert_entry(
                    advert,
                    serials,
                    this_device=host in advert.addresses
                    or bool(own & set(advert.serials)),
                )
                for advert in sorted(adverts, key=lambda a: a.instance)
            ],
        }
    label = _first_label(hostname)
    return {
        "mdns": mdns,
        "reverse_dns_label": anonymised(label, serials) if label else None,
        "mac_vendor_prefix": mac_prefix,
    }
