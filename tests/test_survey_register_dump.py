"""The raw band sweep a survey can be asked to do, and when it must not.

Two switches in this integration are called a register dump and they are not
the same thing. `register_dump` in the options' Advanced section re-reads the
addresses this library already maps and lands in the diagnostics file;
`survey_register_dump` here sweeps twelve bands of 1510 addresses, most of
which nothing maps, and lands in the survey document. The second is the one
that can discover a register, and the one that costs five minutes.

These tests pin the three things that make it safe to ship: it is off unless
somebody asks, it never runs behind a button somebody is waiting on, and the
serial number does not come out in it.
"""

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_MODE,
    CONF_SURVEY_DUMP,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DIAGNOSTICS,
)
from custom_components.sungrow_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.sungrow_modbus.fingerprint import async_build, summarise
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from sungrow_modbus.dump import DUMP_BANDS, DUMP_MASKED

from .conftest import SERIAL


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, options: dict | None = None
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.178.35",
            CONF_PORT: 502,
            CONF_UNIT_ID: 1,
            CONF_MODE: MODE_DIAGNOSTICS,
        },
        options=options or {},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_a_survey_does_not_dump_unless_it_is_asked_to(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The default, and the case every existing document was taken in."""
    entry = await _setup(hass, sungrow_unit)

    document = await async_build(hass, entry, allow_dump=True)

    assert "register_dump" not in document


async def test_the_option_alone_is_not_enough(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Both halves are required, and this is the half that is easy to lose.

    The owner's answer says they are willing; `allow_dump` says the caller can
    afford to wait. A call that forgets the second is the diagnostics
    download, and it must stay fast.
    """
    entry = await _setup(hass, sungrow_unit, {CONF_SURVEY_DUMP: True})

    document = await async_build(hass, entry)

    assert "register_dump" not in document


async def test_the_diagnostics_download_never_dumps_however_the_option_is_set(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Because somebody is watching a spinner while it builds.

    The same document, from the same code, with the expensive part left out.
    Five minutes behind a download button reads as a hang, and the owner who
    turned the option on was answering a question about *surveys*.
    """
    entry = await _setup(hass, sungrow_unit, {CONF_SURVEY_DUMP: True})

    report = await async_get_config_entry_diagnostics(hass, entry)

    assert "register_dump" not in report["fingerprint"]


async def test_an_asked_for_dump_covers_every_band(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """1510 addresses, in the shape the published documents already use.

    Keyed by address as a string and split by register space, because that is
    what `scripts/sungrow_scan/collect.py` writes and one generator reads
    both.
    """
    entry = await _setup(hass, sungrow_unit, {CONF_SURVEY_DUMP: True})

    document = await async_build(hass, entry, allow_dump=True)

    dump = document["register_dump"]
    assert set(dump) == {"input", "holding"}
    assert sum(len(values) for values in dump.values()) == sum(
        count for _space, _start, count, _why in DUMP_BANDS
    )
    for space, start, count, _why in DUMP_BANDS:
        assert str(start) in dump[space]
        assert str(start + count - 1) in dump[space]


async def test_the_serial_never_comes_out_in_the_dump(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The reason the mask exists, asserted against a device that has one.

    The serial sits at input 4990 inside the identity band, so a dump reads it
    whether anybody meant to or not. It is blanked rather than dropped, so the
    addresses still read as covered -- and the words are gone.
    """
    entry = await _setup(hass, sungrow_unit, {CONF_SURVEY_DUMP: True})

    document = await async_build(hass, entry, allow_dump=True)

    space, start, count = DUMP_MASKED[0]
    dump = document["register_dump"]
    for address in range(start, start + count):
        assert str(address) in dump[space]
        assert dump[space][str(address)] is None
    # And the real serial's characters are nowhere else in the file either.
    assert SERIAL not in str(document)


async def test_the_progress_bar_knows_the_dump_is_coming(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A denominator that grows halfway through is worse than no bar.

    So the dump's blocks are counted before the first read, which shows up as
    a fraction that rises monotonically to exactly 1.0 and steps that name
    which band is being swept.
    """
    entry = await _setup(hass, sungrow_unit, {CONF_SURVEY_DUMP: True})

    seen: list[tuple[float, str]] = []
    await async_build(
        hass,
        entry,
        on_progress=lambda fraction, step: seen.append((fraction, step)),
        allow_dump=True,
    )

    fractions = [fraction for fraction, _step in seen]
    assert fractions == sorted(fractions)
    assert fractions[-1] == pytest.approx(1.0)
    assert any("reading raw registers" in step for _fraction, step in seen)
    # Named by what the band is for, not by an address: "the block a WiNet-S
    # does not forward" is something a reader can check.
    assert any(
        "the block a WiNet-S does not forward" in step for _fraction, step in seen
    )


async def test_the_summary_says_the_sweep_happened(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Somebody who waited five minutes should see that it landed.

    The notification is the only place most contributors ever read the result,
    and a document twenty times the usual size with nothing in the summary to
    show for it invites the reasonable conclusion that the switch did nothing.
    """
    entry = await _setup(hass, sungrow_unit, {CONF_SURVEY_DUMP: True})

    document = await async_build(hass, entry, allow_dump=True)

    assert "Raw band sweep" in summarise(document)
    # And a survey without one does not mention it at all.
    assert "Raw band sweep" not in summarise(await async_build(hass, entry))
