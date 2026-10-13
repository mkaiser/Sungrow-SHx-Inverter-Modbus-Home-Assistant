"""A raw Modbus TCP client over a plain socket, for the block read test.

A measuring instrument, not a second copy of the library's client. It reads
the reply byte by byte, which is what lets `blocks.py --client raw` name the
count a padded frame needs: `modbus-connection` rightly rejects such a frame
and throws away the number that would have read. Everything else in the
survey talks through the library.

**It only reads.** Only the two Modbus read function codes are implemented in
this file -- there is no code here that can write a register, and you are
welcome to check: search for `_FC_` below.
"""

from __future__ import annotations

import socket
import struct
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

    An `OSError`, so a caller tolerating a lost link catches it the way it
    catches the operating system's own.

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
