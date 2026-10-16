"""A strict raw Modbus TCP client, for the block read test.

A measuring instrument, not a second copy of `modbus-connection`. It reads
the reply byte by byte, which is what lets the block read test name the count
a padded frame needs: `modbus-connection` rightly rejects such a frame and
throws away the number that would have read. Everything else in this library
talks through `modbus-connection`.

Strict, because a lenient client is worse than none here. Measured on the
reference SH10RT at register 2613, asking for 11:

    -> 00 01 00 00 00 06 01 04 0a 34 00 0b     address 2612, count 11
    <- 00 01 00 00 00 21 01 04 16 53 55 42 ... 39 bytes

`mbap_len = 0x21 = 33`, so the frame carries 30 data bytes -- fifteen
registers. `byte_count = 0x16 = 22` says eleven, which is what was asked for
and what the first 22 bytes correctly contain. The device pads the frame and
does not say so. A client that trusts the byte count reports a clean read the
integration cannot make; this one raises `PaddedFrame` with both numbers and
the count that makes them agree -- the number that belongs in `layout.COUNTS`.

**It only reads.** The two Modbus read function codes are the only ones this
module knows; there is no code here that can write a register. Search for
`_FC_` to check.
"""

from __future__ import annotations

import asyncio
import contextlib
import struct

# The only two function codes this module knows. Both are reads: 4 is "read
# input registers", 3 is "read holding registers". Writing would need 6 or 16,
# which are deliberately absent.
_FC_READ_INPUT = 4
_FC_READ_HOLDING = 3

#: What the block read test's document says measured, when this client did.
LABEL = "raw socket -- strict, and reports the count that reconciles a padded frame"


class Refused(Exception):
    """The device answered with an exception response: it declined the read."""

    def __init__(self, code: int) -> None:
        """Remember the exception code, which is the device's own answer."""
        super().__init__(f"exception 0x{code:02X}")
        self.exception_code = code


class Dropped(OSError):
    """The device hung up rather than answering.

    An `OSError`, so a caller tolerating a lost link catches it the way it
    catches the operating system's own. Sungrow hardware does this for some
    requests instead of returning an exception, so it has to be survivable
    *and* recorded: a register that reliably drops the link is a hazard the
    integration must avoid.
    """


class TimedOut(Dropped):
    """No answer within the timeout: the link failing, not the device refusing."""


class WrongLength(Exception):
    """The device answered, with a number of registers nobody asked for."""

    def __init__(self, got: int, asked: int) -> None:
        """Remember both counts, because the fix is the one it sent."""
        super().__init__(f"asked {asked} registers, got {got}")
        self.got = got
        self.asked = asked


class PaddedFrame(Exception):
    """The frame is longer than the byte count it declares.

    The data is there and correct; the frame around it is not, and the
    shipping Modbus stack rejects it on that basis. `consistent_count` is the
    count to ask for so that the two numbers agree.
    """

    def __init__(self, declared: int, mbap_length: int, asked: int) -> None:
        """Work out the count that would make the frame self-consistent."""
        self.declared_registers = declared // 2
        self.frame_registers = (mbap_length - 3) // 2
        self.asked = asked
        self.consistent_count = self.frame_registers
        super().__init__(
            f"declared {self.declared_registers} registers but sent a frame "
            f"sized for {self.frame_registers}"
        )


class RawClient:
    """A Modbus TCP connection that reopens itself when the device hangs up.

    Without the reconnect the first dropped connection would poison every
    read after it. `reconnects` counts them, because a read that needed one
    is a read the integration cannot make -- a `Component` has no mid-block
    retry -- and `block_test.attempt` reports it as dropped.
    """

    label = LABEL

    #: How long to wait before each retry. Sungrow hardware drops a connection
    #: every so often regardless of which register was asked for, and an
    #: immediate reconnect is often refused as well, but it recovers within a
    #: second or two.
    BACKOFF = (0.0, 0.5, 1.5)

    def __init__(
        self, host: str, port: int, unit: int, timeout: float, delay: float = 0.0
    ) -> None:
        """Remember where to connect, without connecting yet."""
        self.host = host
        self.port = port
        self.unit = unit
        self.timeout = timeout
        self.delay = delay
        self.reconnects = 0
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._transaction = 0

    async def read(self, space: str, address: int, count: int) -> list[int]:
        """Read one block, reconnecting and waiting if the device hangs up."""
        function = _FC_READ_INPUT if space == "input" else _FC_READ_HOLDING
        last: Dropped | None = None
        for attempt, pause in enumerate(self.BACKOFF):
            if self._writer is None:
                if pause:
                    await asyncio.sleep(pause)
                try:
                    await self._connect()
                except OSError as err:
                    last = Dropped(str(err))
                    continue
                if attempt:
                    self.reconnects += 1
            try:
                words = await self._read_once(function, address, count)
            except Dropped as err:
                last = err
                await self.close()
            except OSError as err:
                last = Dropped(str(err))
                await self.close()
            else:
                if self.delay:
                    await asyncio.sleep(self.delay)
                return words
        raise last or Dropped("unreachable")

    async def close(self) -> None:
        """Close the connection if one is open."""
        writer, self._reader, self._writer = self._writer, None, None
        if writer is not None:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

    async def _connect(self) -> None:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), self.timeout
            )
        except TimeoutError as err:
            raise TimedOut(f"no connection within {self.timeout:.0f}s") from err

    async def _recv(self, size: int) -> bytes:
        """Read exactly `size` bytes, or raise `Dropped` / `TimedOut`."""
        assert self._reader is not None
        try:
            return await asyncio.wait_for(self._reader.readexactly(size), self.timeout)
        except TimeoutError as err:
            raise TimedOut(f"no answer within {self.timeout:.0f}s") from err
        except asyncio.IncompleteReadError as err:
            raise Dropped("the device closed the connection") from err

    async def _read_once(self, function: int, address: int, count: int) -> list[int]:
        """Read one block, raising when the frame is padded or the count wrong."""
        assert self._writer is not None
        self._transaction = (self._transaction + 1) & 0xFFFF
        self._writer.write(
            struct.pack(
                ">HHHBBHH", self._transaction, 0, 6, self.unit, function, address, count
            )
        )
        await self._writer.drain()
        header = await self._recv(8)
        length = struct.unpack(">H", header[4:6])[0]
        body = await self._recv(max(0, length - 2))
        if header[7] != function:
            raise Refused(body[0] if body else 0)
        if len(body) < 1:
            raise Dropped("empty answer")
        # A self-consistent answer has mbap_len == 3 + byte_count: one byte
        # each of unit, function and byte count, then the data.
        if length != 3 + body[0]:
            raise PaddedFrame(declared=body[0], mbap_length=length, asked=count)
        if body[0] != count * 2:
            raise WrongLength(body[0] // 2, count)
        return list(struct.unpack(f">{count}H", body[1 : 1 + count * 2]))
