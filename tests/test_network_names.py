"""What a Sungrow device says about itself on the network, and what of it is published.

The records are gerd's (wiki: *gerd's devices over mDNS*, 2026-11-11), with
invented serials. The load-bearing claim is the privacy one: a published
`network_names` section carries stand-ins, never a serial, a MAC address or
an IP address, whatever a record nobody has explained puts in its fields.
"""

from __future__ import annotations

import json

from sungrow_modbus.diagnosis_document import stand_in
from sungrow_modbus.network_names import (
    UNEXPLAINED,
    Advert,
    anonymised,
    instance_of,
    mac_prefix_in,
    network_section,
    text_properties,
)

INVERTER = "A123456789"
DONGLE = "B123456789"
BATTERY = "D123456789"
WALLBOX = "W123456789"

DONGLE_ADVERT = Advert(
    instance="WiNet-WebServer",
    port=80,
    server=f"SUNGROW{DONGLE}.local.",
    addresses=("192.0.2.10",),
    properties={
        "battery1": f"2;200;8423;{BATTERY};1;516;SBR096;",
        "ethinfo": "",
        "inverter": f"1;3598;{INVERTER};1;516;SH8.0RT;1;4;",
        "board": f"SUNGROW;1;WiNet-S;{DONGLE};1;",
    },
)

WALLBOX_ADVERT = Advert(
    instance=f"SUNGROW{WALLBOX}",
    port=516,
    server=f"SUNGROW{WALLBOX}.local.",
    addresses=("192.0.2.20",),
    properties={
        "board": f"SUNGROW;3;AC22E-01;{WALLBOX};1;248;",
        "info": "16256;516;1;",
    },
)


def test_the_dongle_record_names_the_inverter_and_battery_behind_it() -> None:
    assert DONGLE_ADVERT.is_sungrow
    assert DONGLE_ADVERT.kind == "dongle"
    board = DONGLE_ADVERT.board
    assert board is not None
    assert (board.model, board.serial) == ("WiNet-S", DONGLE)
    inverter = DONGLE_ADVERT.inverter
    assert inverter is not None
    assert inverter.model == "SH8.0RT"
    assert inverter.serial == INVERTER
    assert inverter.unit == 1
    # 3598 = 0x0E0E, SH8.0RT's device type code.
    assert inverter.device_type_code == 0x0E0E
    battery = next(d for d in DONGLE_ADVERT.devices if d.key == "battery1")
    assert (battery.model, battery.serial, battery.unit) == ("SBR096", BATTERY, 2)


def test_the_wallbox_record_is_a_wallbox() -> None:
    assert WALLBOX_ADVERT.is_sungrow
    assert WALLBOX_ADVERT.kind == "wallbox"
    assert WALLBOX_ADVERT.board is not None
    assert WALLBOX_ADVERT.board.serial == WALLBOX
    assert WALLBOX_ADVERT.inverter is None


def test_a_field_laid_out_differently_yields_no_serial_rather_than_a_wrong_one() -> (
    None
):
    advert = Advert(instance="WiNet-WebServer", properties={"inverter": "1;2;3"})
    assert advert.inverter is not None
    assert advert.inverter.serial is None


def test_something_else_on_http_is_not_sungrow() -> None:
    printer = Advert(instance="Office printer", properties={"ty": "Laser"})
    assert not printer.is_sungrow


def test_zeroconf_bytes_become_text() -> None:
    assert text_properties({b"board": b"SUNGROW;1", b"empty": None}) == {
        "board": "SUNGROW;1",
        "empty": "",
    }
    assert instance_of("WiNet-WebServer._http._tcp.local.") == "WiNet-WebServer"


def test_the_section_publishes_stand_ins_and_no_address() -> None:
    section = network_section(
        host="192.0.2.10",
        device_serials=[INVERTER],
        adverts=[DONGLE_ADVERT, WALLBOX_ADVERT],
        hostname=f"sungrow{DONGLE.lower()}.fritz.box",
        mac_prefix="AA:BB:CC",
    )
    text = json.dumps(section)
    for serial in (INVERTER, DONGLE, BATTERY, WALLBOX):
        assert serial not in text
        assert serial.lower() not in text
    assert "192.0.2" not in text
    assert "fritz" not in text
    mdns = section["mdns"]
    assert isinstance(mdns, dict)
    assert mdns["state"] == "answered"
    services = {s["instance"]: s for s in mdns["services"]}
    dongle = services["WiNet-WebServer"]
    assert dongle["this_device"] is True
    assert dongle["properties"]["inverter"] == (
        f"1;3598;{stand_in(INVERTER)};1;516;SH8.0RT;1;4;"
    )
    assert services[f"SUNGROW{stand_in(WALLBOX)}"]["this_device"] is False
    assert section["reverse_dns_label"] == f"sungrow{stand_in(DONGLE)}"
    assert section["mac_vendor_prefix"] == "AA:BB:CC"


def test_an_unexplained_field_with_a_serial_shape_is_not_published() -> None:
    text = anonymised("ethinfo=XY12345678ZZ;aa:bb:cc:dd:ee:ff;10.0.0.7", {})
    assert "XY12345678ZZ" not in text
    assert UNEXPLAINED in text
    assert "aa:bb" not in text
    assert "10.0.0.7" not in text


def test_nothing_heard_is_not_no_dongle() -> None:
    heard_nothing = network_section(host="192.0.2.10", adverts=[])
    assert heard_nothing["mdns"] == {
        "state": "nothing_answered",
        "browsed_seconds": 5.0,
        "services": [],
    }
    not_browsed = network_section(
        host="192.0.2.10", adverts=None, browse_error="zeroconf missing"
    )
    assert not_browsed["mdns"] == {"state": "not_browsed", "why": "zeroconf missing"}


def test_the_mac_prefix_comes_from_the_line_naming_the_address() -> None:
    linux = (
        "IP address       HW type     Flags       HW address          Mask  Device\n"
        "192.0.2.100      0x1         0x2         11:22:33:44:55:66     *        eth0\n"
        "192.0.2.10       0x1         0x2         a4:cf:12:01:02:03     *        eth0\n"
        "192.0.2.11       0x1         0x0         00:00:00:00:00:00     *        eth0\n"
    )
    assert mac_prefix_in(linux, "192.0.2.10") == "A4:CF:12"
    assert mac_prefix_in(linux, "192.0.2.11") is None
    assert mac_prefix_in(linux, "192.0.2.1") is None
    windows = "  192.0.2.10            a4-cf-12-01-02-03     dynamic\n"
    assert mac_prefix_in(windows, "192.0.2.10") == "A4:CF:12"
    macos = "? (192.0.2.10) at a4:cf:12:1:2:3 on en0 ifscope [ethernet]\n"
    assert mac_prefix_in(macos, "192.0.2.10") == "A4:CF:12"
