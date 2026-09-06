#!/usr/bin/env python3
"""Report what your Sungrow inverter answers, so we can support it properly.

This project has one register map for every model, but which parts of it a
given device answers depends on the model, the phase count, what is wired up,
how you connect, and the firmware. Nobody has that knowledge centrally — it
has accumulated as comments in a YAML file, one issue thread at a time. A
report from your machine is the single most useful thing you can contribute,
especially for an RS, an MG, a T-series, a wallbox, an SBR battery or a
Logger, none of which the maintainer owns.

    python collect_fingerprint.py 192.168.1.50

**It only reads.** Only the two Modbus read function codes are implemented in
this file — there is no code here that can write a register, and you are
welcome to check: search for `_FC_` below.

**It needs nothing installed.** Plain Python 3.9 or newer, no packages.

**Expect it to say the device hung up.** Sungrow inverters accept very few
Modbus sessions at once, so if Home Assistant is already polling this
inverter, your connection and its connection compete and the device drops one
of them repeatedly. The script reconnects around each drop, so the report is
still complete.

**It does not publish anything by itself.** It writes one JSON file and tells
you where. Look at it, then attach it to a GitHub issue if you are happy to.
Your serial number is replaced with a stand-in of the same shape and the
address of your inverter is left out, because the file is meant to be public.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import socket
import struct
import sys
import time

# The only two function codes this script knows. Both are reads: 4 is "read
# input registers", 3 is "read holding registers". Writing would need 6 or 16,
# which are deliberately absent.
_FC_READ_INPUT = 4
_FC_READ_HOLDING = 3

#: Sungrow's protocol defines these as "unavailable": U16, then signed.
UNAVAILABLE = (0xFFFF, 0x7FFF)

#: Addresses are protocol addresses — one below the register number printed in
#: Sungrow's documentation. (label, space, address, count)
REGISTERS = [
    ("serial number", "input", 4989, 10),
    ("device type code (reg 5000)", "input", 4999, 1),
    ("nominal output power (reg 5001)", "input", 5000, 1),
    ("output type (reg 5002)", "input", 5001, 1),
    ("ARM software version", "input", 4953, 15),
    ("DSP software version", "input", 4968, 15),
    ("daily output energy", "input", 5002, 1),
    ("total output energy", "input", 5003, 2),
    ("inverter temperature", "input", 5007, 1),
    ("MPPT1 voltage", "input", 5010, 1),
    ("MPPT2 voltage", "input", 5012, 1),
    ("MPPT3 voltage", "input", 5014, 1),
    ("MPPT4 voltage", "input", 5114, 1),
    ("total DC power", "input", 5016, 2),
    ("phase A voltage", "input", 5018, 1),
    ("phase B voltage", "input", 5019, 1),
    ("phase C voltage", "input", 5020, 1),
    ("meter phase A voltage (reg 5741)", "input", 5740, 1),
    ("meter phase A current (reg 5744)", "input", 5743, 1),
    ("meter active power (reg 5601)", "input", 5600, 2),
    ("battery voltage", "input", 13019, 1),
    ("battery current", "input", 13020, 1),
    ("battery level", "input", 13022, 1),
    ("battery temperature", "input", 13024, 1),
    ("battery capacity", "input", 5637, 1),
    ("running state", "input", 12999, 1),
    ("firmware block (reg 13250)", "input", 13249, 4),
    ("meter channel 2 (reg 13200)", "input", 13199, 4),
    ("PV power limitation (reg 13018)", "holding", 13017, 1),
    ("export power limit (reg 13074)", "holding", 13073, 1),
    ("EMS mode (reg 13050)", "holding", 13049, 1),
]

#: Sungrow's protocol says the 6100-6195 block is "not supported" when
#: forwarded by a WiNet-S over Ethernet TCP/IP. So whether it answers tells us
#: which way in we came, which matters because the transport is one of the
#: things that decides what a device exposes. A direct connection to the
#: inverter's own LAN port should answer; a dongle should not.
TRANSPORT_PROBE = ("PV power of today (reg 6100)", "input", 6099, 2)

#: Other devices that may answer on the same host, at their own unit ids.
COMPANIONS = [
    ("wallbox (via WiNet-S)", 3, "input", 21200, 4),
    ("wallbox (direct RS485)", 248, "input", 21200, 4),
    ("SBR battery modules", 200, "input", 10740, 2),
    ("Logger1000/3000", 247, "input", 7999, 1),
]

OUTPUT_TYPE = {0: "single phase", 1: "three phase (3P4L)", 2: "three phase (3P3L)"}


class ModbusError(Exception):
    """The device answered, but refused the request."""


class Dropped(Exception):
    """The device hung up rather than answering.

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


def _has_web_ui(host, timeout):
    """Say whether something serves HTTP on port 80.

    A WiNet-S dongle does; the inverter's own LAN port does not.
    """
    try:
        with socket.create_connection((host, 80), min(timeout, 3.0)) as sock:
            sock.settimeout(min(timeout, 3.0))
            sock.sendall(b"GET / HTTP/1.0\r\n\r\n")
            return sock.recv(16).startswith(b"HTTP")
    except OSError:
        return False


def _decode_string(values):
    """Turn registers into the ASCII string they hold."""
    raw = b"".join(struct.pack(">H", v) for v in values)
    return raw.decode("ascii", "replace").strip("\x00").strip()


def _stand_in_serial(real):
    """Return a stand-in of the same shape, derived from the real one.

    Same length, because the string decoding is itself being tested. Derived
    from a hash rather than random, so one machine always maps to one
    stand-in — two reports from the same inverter can be recognised as such
    without the real serial ever leaving your network.
    """
    if not real:
        return ""
    digest = hashlib.sha256(real.encode("ascii", "replace")).hexdigest()
    digits = "".join(str(int(c, 16) % 10) for c in digest)
    prefix = "".join(c for c in real[:2] if c.isalpha()).upper() or "A0"
    return (prefix + digits)[: len(real)]


def collect(host, port, unit, timeout, delay):
    """Read everything, print it, and return the report to be written."""
    report = {
        "collected_by": "collect_fingerprint.py",
        "read_on": datetime.now(UTC).strftime("%Y-%m-%d"),
        "unit": unit,
        "port": port,
        "registers": {},
    }
    link = Connection(host, port, timeout, delay)
    try:
        for label, space, address, count in REGISTERS:
            function = _FC_READ_INPUT if space == "input" else _FC_READ_HOLDING
            try:
                values = link.read(unit, function, address, count)
            except Dropped as err:
                report["registers"][label] = {"status": "dropped", "why": str(err)}
                print(f"  {label:<34} DROPPED THE CONNECTION")
                continue
            except (ModbusError, OSError) as err:
                report["registers"][label] = {"status": "refused", "why": str(err)}
                print(f"  {label:<34} refused ({err})")
                continue

            if all(v in UNAVAILABLE for v in values):
                report["registers"][label] = {"status": "unavailable"}
                print(f"  {label:<34} unavailable")
                continue

            entry = {"status": "present", "values": values}
            shown = values
            if label == "serial number":
                real = _decode_string(values)
                entry = {"status": "present", "stand_in": _stand_in_serial(real)}
                shown = "{}  (reported as {})".format(real, entry["stand_in"])
            elif "software version" in label:
                entry["text"] = _decode_string(values)
                shown = entry["text"]
            elif label.startswith("device type"):
                entry["code"] = f"0x{values[0]:04X}"
                report["device_type_code"] = entry["code"]
                shown = entry["code"]
            elif label.startswith("output type"):
                entry["meaning"] = OUTPUT_TYPE.get(values[0], "unknown")
                report["output_type"] = entry["meaning"]
                shown = entry["meaning"]
            report["registers"][label] = entry
            print(f"  {label:<34} {shown}")

        # Which way in did we come? Two independent signals.
        label, space, address, count = TRANSPORT_PROBE
        function = _FC_READ_INPUT if space == "input" else _FC_READ_HOLDING
        try:
            values = link.read(unit, function, address, count)
            forwarded_block = (
                "unavailable" if all(v in UNAVAILABLE for v in values) else "present"
            )
        except (ModbusError, Dropped, OSError):
            forwarded_block = "refused"
        web_ui = _has_web_ui(host, timeout)
        if forwarded_block == "present" and not web_ui:
            transport = "probably direct to the inverter's LAN port"
        elif forwarded_block != "present" and web_ui:
            transport = "probably through a WiNet-S dongle"
        else:
            transport = "unclear"
        report["transport"] = {
            "guess": transport,
            "winet_restricted_block": forwarded_block,
            "web_ui_on_port_80": web_ui,
        }
        print(f"\n  Connection looks like: {transport}")
        print(f"  ({label} is {forwarded_block}; web UI on port 80: {web_ui})")

        print("\n  Other devices on this connection:")
        for label, companion_unit, space, address, count in COMPANIONS:
            function = _FC_READ_INPUT if space == "input" else _FC_READ_HOLDING
            key = f"{label} (unit {companion_unit})"
            try:
                values = link.read(companion_unit, function, address, count)
            except (ModbusError, Dropped, OSError):
                report["registers"][key] = {"status": "no answer"}
                print(f"  {label:<34} not present")
                continue
            if all(v in UNAVAILABLE for v in values):
                report["registers"][key] = {"status": "unavailable"}
                print(f"  {label:<34} answered, no data")
                continue
            report["registers"][key] = {"status": "present", "values": values}
            print(f"  {label:<34} PRESENT {values}")
    finally:
        link.close()
    report["reconnects"] = link.reconnects
    if link.reconnects:
        print(
            f"\n  The device hung up {link.reconnects} time(s); "
            "each was reconnected around."
        )
    return report


def main():
    """Collect one report and write it out."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("host", help="the IP address of your inverter or dongle")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument(
        "--unit",
        type=int,
        default=1,
        help="Modbus unit id, sometimes called the device address (default 1)",
    )
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument(
        "--delay",
        type=float,
        default=0.03,
        help="pause between reads; raise it if a WiNet-S drops the connection",
    )
    parser.add_argument("--out", help="where to write the report")
    args = parser.parse_args()

    print(f"Reading {args.host}:{args.port}, unit {args.unit}. This only reads.\n")
    try:
        report = collect(args.host, args.port, args.unit, args.timeout, args.delay)
    except OSError as err:
        print(f"\nCould not reach {args.host}:{args.port} — {err}")
        print("Check the address, and that Modbus is enabled on the device.")
        return 1

    model = report.get("device_type_code", "unknown").replace("0x", "")
    name = args.out or "sungrow-fingerprint-{}-{}.json".format(model, report["read_on"])
    with open(name, "w") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"\nWrote {name}")
    print("It has no serial number and no IP address in it — have a look.")
    print("If you are happy to share it, attach it to an issue at")
    print(
        "https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues"
    )
    if report.get("device_type_code"):
        print("\nDevice type {}.".format(report["device_type_code"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
