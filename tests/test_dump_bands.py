"""The two register dumps must cover exactly the same ground.

There are two implementations of the band dump and there have to be. The
integration's runs inside Home Assistant against the library; the standalone
survey's runs from a zip on a stranger's laptop with nothing installed, which
is the whole point of `scripts/sungrow_scan/` and rules out importing the
library there.

What must not happen is the two quietly covering different addresses. A
document says `register_dump` and a maintainer reads it as "these bands were
read"; if the two tools disagree about which bands those are, the same key
means two things and nobody finds out from the file. Worse for the mask: the
serial's ten registers are blanked by a tuple in each file, and a dump that
forgets one publishes a real serial number.

So: the bands and the mask are compared here, and adding a band means adding
it twice on purpose rather than once by accident.
"""

from pathlib import Path
import sys

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "scripts" / "sungrow_scan")
)

from probe import DUMP_BANDS as SCANNER_BANDS, DUMP_MASKED as SCANNER_MASKED

from sungrow_modbus.dump import DUMP_BANDS, DUMP_MASKED, block_count


def test_the_two_dumps_read_the_same_bands() -> None:
    """Including the reason strings, which land in `bands_not_reached`."""
    assert DUMP_BANDS == SCANNER_BANDS


def test_the_two_dumps_mask_the_same_addresses() -> None:
    """The one drift that would publish a real serial number."""
    assert DUMP_MASKED == SCANNER_MASKED


def test_the_serial_is_inside_a_band_that_is_dumped() -> None:
    """Otherwise the mask is decoration.

    The masking only matters because a band genuinely covers the serial: it
    sits at input 4990 inside the 4949+210 identity band. If a future edit
    moved that band, the mask would keep passing its own test while guarding
    nothing.
    """
    serial_space, serial_start, serial_count = DUMP_MASKED[0]
    covered = any(
        space == serial_space
        and start <= serial_start
        # A band covers the serial only if it reaches the last of its ten
        # registers, not merely the first.
        and start + count >= serial_start + serial_count
        for space, start, count, _why in DUMP_BANDS
    )
    assert covered


def test_the_block_count_matches_what_the_bands_ask_for() -> None:
    """The progress denominator is computed before a single read is made.

    A bar whose total grows halfway through is worse than no bar, so this is
    the one number the survey commits to in advance.
    """
    assert block_count() == sum(
        len(range(0, count, 32)) for _space, _start, count, _why in DUMP_BANDS
    )
    assert sum(count for _space, _start, count, _why in DUMP_BANDS) == 1510
