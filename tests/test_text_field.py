"""A Sungrow string ends at its first NUL.

An SH6.0RS on SUNSTONE-H_B000.V001.P068 answers its battery firmware (input
13280-13294) as the version, a NUL, and two characters left over from a longer
string. Stripping only the trailing NULs, as `modbus_connection` does, kept
them: invisible in a log, and enough for the string to match nothing.
"""

from __future__ import annotations

from modbus_connection.model import string as connection_string
import pytest

from sungrow_modbus.hybrid_inverter.registers import InverterFirmwareBlockBattery
from sungrow_modbus.model import TextField, string, words_text

#: The SH6.0RS's answer, as its survey (#786) recorded it.
SBR_WITH_LEFTOVER = [
    *(0x5342, 0x5242, 0x4355, 0x2D53, 0x5F32, 0x3230, 0x3131, 0x2E30),
    *(0x312E, 0x3330, 0x0034, 0x3400, 0, 0, 0),
]


def test_the_leftover_after_the_terminator_is_dropped() -> None:
    assert string(0, 15).decode(SBR_WITH_LEFTOVER) == "SBRBCU-S_22011.01.30"
    assert words_text(SBR_WITH_LEFTOVER) == "SBRBCU-S_22011.01.30"
    # What the connection library's own string kept.
    assert "\x00" in connection_string(0, 15).decode(SBR_WITH_LEFTOVER)


@pytest.mark.parametrize(
    ("words", "text"),
    [
        ([0x4142, 0x4344, 0, 0], "ABCD"),
        ([0x4142, 0x4300, 0, 0], "ABC"),
        ([0, 0, 0, 0], ""),
        # Leading NULs are padding too, as `words_text` has always read them.
        ([0, 0x4142, 0, 0], "AB"),
    ],
)
def test_a_clean_string_reads_as_before(words: list[int], text: str) -> None:
    assert string(0, 4).decode(words) == text
    assert words_text(words) == text


def test_the_firmware_strings_are_read_this_way() -> None:
    assert isinstance(InverterFirmwareBlockBattery.battery_firmware_version, TextField)
