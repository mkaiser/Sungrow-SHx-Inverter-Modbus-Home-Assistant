"""The register dump's bands and its mask, which the survey and the integration share.

Both producers read `sungrow_modbus.dump.DUMP_BANDS`, so a document's
`register_dump` means the same addresses whichever tool wrote it. What is left
to check is that the mask still guards something, and that the progress
denominator is honest.
"""

from sungrow_modbus.dump import DUMP_BANDS, DUMP_MASKED, block_count


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
    assert sum(count for _space, _start, count, _why in DUMP_BANDS) == 1550
