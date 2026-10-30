"""Register 31211, and the firmware read that decides it.

Two things are under test, and the second exists because of the first. PV can
be cut through a register Sungrow never documented, and whether it answers is
a matter of firmware -- so the firmware has to be known before anything
decides what an inverter has. And because a register answering says nothing
about what writing it does, the switch waits for firmware on which the
control test watched a write take DC power to zero.
"""

from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.sungrow_modbus.const import (
    CONF_CONTROL_TEST_PV_CUT,
    CONF_UNIT_ID,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from sungrow_modbus import SungrowInverter
from sungrow_modbus.control_test import (
    CONFIRMED,
    INCONCLUSIVE,
    PV_CUT,
    PV_CUT_SETTLE,
    PV_RECOVERY,
    ControlTest,
    Options,
    Sample,
)
from sungrow_modbus.inverter import capabilities
from sungrow_modbus.inverter.capabilities import (
    Capability,
    absent_on_firmware,
    probe,
    resolve,
)

from .conftest import SERIAL, encode_string
from .corpus import INVERTER_DOCUMENTS

#: Every committed inverter document, read once.
DOCUMENTS = [
    (path, json.loads(path.read_text(encoding="utf-8"))) for path in INVERTER_DOCUMENTS
]

SH10RT = 0x0E03
PV_CUT_ADDRESS = 31210
VERSION_ADDRESS = 2581
INVERTER_FIRMWARE_ADDRESS = 13249
METER_CHANNEL_2_ADDRESS = 13199
ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: The firmware strings committed surveys answer 0x55 on, at 13250.
ANSWERING = {
    "SAPPHIRE-H_B001.V000.P022",
    "SAPPHIRE-H_B001.V000.P023",
    "PEARL-H_B000.V000.P071",
}


def _reads(values: dict[str, Any]):
    return lambda name: values.get(name)


# -- the probe ---------------------------------------------------------------


@pytest.mark.parametrize("word", [0x55, 0xAA])
def test_either_mode_code_grants_the_read(word: int) -> None:
    found = probe(_reads({"pv_generation_cut_raw": word}))
    assert Capability.PV_GENERATION_CUT in found


@pytest.mark.parametrize("word", [None, 0, 1, 0x1234])
def test_anything_else_grants_nothing(word: int | None) -> None:
    """0xFFFF decodes to None; a dongle's 0 is not a mode; nor is junk."""
    found = probe(_reads({"pv_generation_cut_raw": word}))
    assert Capability.PV_GENERATION_CUT not in found


def test_the_control_is_never_probed() -> None:
    """A register answering says it is there, not what writing it does."""
    found = probe(_reads({"pv_generation_cut_raw": 0x55}))
    assert Capability.PV_GENERATION_CUT_CONTROL not in found
    # On a firmware no control test has confirmed, the answer alone grants
    # nothing. P071 reads 0x55 as P023 does, and nobody has watched it cut.
    assert Capability.PV_GENERATION_CUT_CONTROL not in resolve(
        SH10RT, 1, found, ("PEARL-H_B000.V000.P071",)
    )


def test_confirmed_firmware_grants_the_control_where_the_register_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        capabilities.CONFIRMED_ON_FIRMWARE,
        Capability.PV_GENERATION_CUT_CONTROL,
        frozenset({"SAPPHIRE-H_B001.V000.P023"}),
    )
    answered = frozenset({Capability.PV_GENERATION_CUT})
    firmware = ("SAPPHIRE-H_01011.95.14", "SAPPHIRE-H_B001.V000.P023")

    assert Capability.PV_GENERATION_CUT_CONTROL in resolve(
        SH10RT, 1, answered, firmware
    )
    # The same firmware on a device whose register did not answer: nothing.
    assert Capability.PV_GENERATION_CUT_CONTROL not in resolve(
        SH10RT, 1, frozenset(), firmware
    )
    # The register answering on firmware nobody confirmed: the read only.
    other = ("SAPPHIRE-H_01011.95.13", "SAPPHIRE-H_B001.V000.P022")
    resolved = resolve(SH10RT, 1, answered, other)
    assert Capability.PV_GENERATION_CUT in resolved
    assert Capability.PV_GENERATION_CUT_CONTROL not in resolved


def test_nothing_is_confirmed_without_a_document_that_shows_it() -> None:
    """The rule for getting in, as for the absence table: evidence, cited.

    A firmware here must be named by a committed survey whose control
    test confirmed the cut on exactly that firmware.
    """
    for capability, versions in capabilities.CONFIRMED_ON_FIRMWARE.items():
        for version in versions:
            assert any(
                version in json.dumps(document.get("firmware"))
                and any(
                    row.get("check") == "PV generation cut"
                    and row.get("verdict") == CONFIRMED
                    for row in (document.get("control_test") or {}).get("effects", [])
                )
                for _, document in DOCUMENTS
            ), f"{capability.value} on {version} cites no passing run"


def test_absence_matches_either_firmware_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        capabilities.ABSENT_ON_FIRMWARE,
        "SAPPHIRE-H_B001.V000.P020",
        frozenset({Capability.METER_CHANNEL_2}),
    )
    assert Capability.METER_CHANNEL_2 in absent_on_firmware(
        ("SAPPHIRE-H_01011.95.12", "SAPPHIRE-H_B001.V000.P020")
    )
    assert Capability.FIRMWARE_VERSIONS in absent_on_firmware(
        ("SAPPHIRE-H_01011.95.03", None)
    )
    assert absent_on_firmware((None, None)) == frozenset()
    assert absent_on_firmware("  ") == frozenset()


# -- the corpus ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "document"),
    [
        (path.name, document)
        for path, document in DOCUMENTS
        if "31210" in ((document.get("register_dump") or {}).get("holding") or {})
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_register_answers_by_firmware_in_every_committed_dump(
    name: str, document: dict
) -> None:
    """What the plan rests on, asserted against the readings themselves.

    0x55 on P022, P023 and P071; the sentinel on P020 and on 95.03, whose
    13250 string never reads. Two inverters on 95.12 answer the sentinel, so
    the 2582 string does not decide it and is not asserted on.
    """
    word = document["register_dump"]["holding"]["31210"]
    found = probe(
        _reads({"pv_generation_cut_raw": None if word in (None, 0xFFFF) else word})
    )
    inverter = (document.get("firmware") or {}).get("inverter")
    assert (Capability.PV_GENERATION_CUT in found) == (inverter in ANSWERING), name


# -- the firmware read --------------------------------------------------------


async def test_both_strings_are_read_and_2582_comes_first(
    sungrow_unit: MockModbusUnit,
) -> None:
    sungrow_unit.input[VERSION_ADDRESS] = encode_string("SAPPHIRE-H_01011.95.14", 11)
    sungrow_unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(
        "SAPPHIRE-H_B001.V000.P023", 15
    )
    asked: list[int] = []
    read = sungrow_unit.read_input_registers

    async def recording(address: int, count: int) -> list[int]:
        asked.append(address)
        return await read(address, count)

    sungrow_unit.read_input_registers = recording  # type: ignore[method-assign]
    inverter = SungrowInverter(sungrow_unit)

    await inverter.async_update_firmware()

    assert inverter.firmware_strings == (
        "SAPPHIRE-H_01011.95.14",
        "SAPPHIRE-H_B001.V000.P023",
    )
    assert asked.index(INVERTER_FIRMWARE_ADDRESS) > min(
        i for i, address in enumerate(asked) if address <= VERSION_ADDRESS
    )


async def test_firmware_that_hangs_up_on_13250_is_never_asked_for_it(
    sungrow_unit: MockModbusUnit,
) -> None:
    sungrow_unit.input[VERSION_ADDRESS] = encode_string("SAPPHIRE-H_01011.95.03", 11)
    asked: list[int] = []
    read = sungrow_unit.read_input_registers

    async def recording(address: int, count: int) -> list[int]:
        asked.append(address)
        return await read(address, count)

    sungrow_unit.read_input_registers = recording  # type: ignore[method-assign]
    inverter = SungrowInverter(sungrow_unit)

    report = await inverter.async_update_firmware()

    assert INVERTER_FIRMWARE_ADDRESS not in asked
    assert "firmware_block_inverter" not in report.failed
    assert inverter.firmware_strings == ("SAPPHIRE-H_01011.95.03", None)


# -- the integration ------------------------------------------------------------


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, **options: Any
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        options=options,
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_the_first_poll_already_skips_what_the_firmware_hangs_up_on(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """95.03 closes the link on the second meter channel, a fast-tier block.

    The fast tier is refreshed before the slowest, which used to carry the
    firmware string -- so the very first poll asked for it. Firmware is read
    before any tier now.
    """
    sungrow_unit.input[VERSION_ADDRESS] = encode_string("SAPPHIRE-H_01011.95.03", 11)
    asked: list[int] = []
    read = sungrow_unit.read_input_registers

    async def recording(address: int, count: int) -> list[int]:
        asked.append(address)
        return await read(address, count)

    sungrow_unit.read_input_registers = recording  # type: ignore[method-assign]

    entry = await _setup(hass, sungrow_unit)

    assert entry.runtime_data.firmware == ("SAPPHIRE-H_01011.95.03", None)
    assert METER_CHANNEL_2_ADDRESS not in asked
    assert INVERTER_FIRMWARE_ADDRESS not in asked


async def test_a_firmware_update_reloads_the_entry(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.input[VERSION_ADDRESS] = encode_string("SAPPHIRE-H_01011.95.12", 11)
    entry = await _setup(hass, sungrow_unit)
    assert entry.runtime_data.firmware[0] == "SAPPHIRE-H_01011.95.12"

    sungrow_unit.input[VERSION_ADDRESS] = encode_string("SAPPHIRE-H_01011.95.14", 11)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=601))
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    assert entry.runtime_data.firmware[0] == "SAPPHIRE-H_01011.95.14"


async def test_a_string_that_did_not_answer_at_setup_does_not_reload(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A dongle answering empty once and text the next is not an update."""
    entry = await _setup(hass, sungrow_unit)
    assert entry.runtime_data.firmware == (None, None)
    built = entry.runtime_data

    sungrow_unit.input[VERSION_ADDRESS] = encode_string("SAPPHIRE-H_01011.95.12", 11)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=601))
        await hass.async_block_till_done()

    assert entry.runtime_data is built


async def test_the_state_is_shown_where_the_register_answers_and_no_switch(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.holding[PV_CUT_ADDRESS] = 0x55
    await _setup(hass, sungrow_unit)
    registry = er.async_get(hass)

    state_id = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{SERIAL}_pv_generation_cut"
    )
    assert state_id is not None
    assert hass.states.get(state_id).state == "off"
    assert (
        registry.async_get_entity_id("switch", DOMAIN, f"{SERIAL}_cut_pv_generation")
        is None
    )


async def test_nothing_where_the_register_answers_the_sentinel(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit)
    registry = er.async_get(hass)

    assert (
        registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{SERIAL}_pv_generation_cut"
        )
        is None
    )


async def test_the_switch_appears_on_confirmed_firmware_and_cuts_pv(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        capabilities.CONFIRMED_ON_FIRMWARE,
        Capability.PV_GENERATION_CUT_CONTROL,
        frozenset({"SAPPHIRE-H_B001.V000.P023"}),
    )
    sungrow_unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(
        "SAPPHIRE-H_B001.V000.P023", 15
    )
    sungrow_unit.holding[PV_CUT_ADDRESS] = 0x55
    await _setup(hass, sungrow_unit)
    registry = er.async_get(hass)
    switch_id = registry.async_get_entity_id(
        "switch", DOMAIN, f"{SERIAL}_cut_pv_generation"
    )
    assert switch_id is not None
    assert hass.states.get(switch_id).state == "off"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": switch_id}, blocking=True
    )

    assert sungrow_unit.holding[PV_CUT_ADDRESS] == 0xAA
    assert hass.states.get(switch_id).state == "on"


async def test_the_control_test_leave_reaches_the_runner(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    from custom_components.sungrow_modbus.control_test import ControlTestRunner

    entry = await _setup(hass, sungrow_unit, **{CONF_CONTROL_TEST_PV_CUT: True})

    assert ControlTestRunner(hass, entry)._options().cut_pv is True


# -- the control test's check ---------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _pv_script(run: ControlTest, *windows: list[float]) -> None:
    values = iter([value for window in windows for value in window])
    last = windows[-1][-1]

    async def sample() -> Sample:
        return Sample(
            at=run.clock.monotonic(),
            pv=next(values, last),
            battery=0.0,
            export=0.0,
            load=0.0,
            soc=50.0,
        )

    run._sample = sample  # type: ignore[method-assign]


async def _prepared(unit: MockModbusUnit, **options: Any) -> ControlTest:
    unit.holding[PV_CUT_ADDRESS] = 0x55
    inverter = SungrowInverter(unit)
    await inverter.async_update()
    run = ControlTest(inverter, options=Options(**options), clock=_Clock())
    await run._preflight()
    return run


async def test_a_cut_that_stops_pv_is_confirmed_and_put_back(
    sungrow_unit: MockModbusUnit,
) -> None:
    run = await _prepared(sungrow_unit, cut_pv=True)
    written: list[int] = []
    sungrow_unit.on_write(
        lambda event: (
            written.extend(event.values) if event.address == PV_CUT_ADDRESS else None
        )
    )
    _pv_script(run, [3000.0] * 11, [0.0] * 10, [3000.0] * 10)

    results = await run._pv_cut_effect()

    assert [row.verdict for row in results] == [CONFIRMED]
    assert written == [0xAA, 0x55]
    assert sungrow_unit.holding[PV_CUT_ADDRESS] == 0x55
    # The ramp down is waited out before the window during, and the MPPT
    # search before the window after.
    assert PV_CUT_SETTLE in run.clock.slept
    assert PV_RECOVERY in run.clock.slept


@pytest.mark.parametrize(
    ("before", "after"),
    [(2066.0, 2516.0), (3063.0, 2201.0)],
    ids=["sun-rising", "sun-falling"],
)
async def test_a_cut_under_a_moving_sky_is_judged_by_its_bracket(
    sungrow_unit: MockModbusUnit, before: float, after: float
) -> None:
    """Two P022 runs at gerd's: 0 W between two windows of real power.

    Before and after differ by far more than the drift gate allows, and it
    does not matter: a cloud does not take PV to 0 W and give it back.
    """
    run = await _prepared(sungrow_unit, cut_pv=True)
    _pv_script(run, [before] * 11, [0.0] * 10, [after] * 10)

    results = await run._pv_cut_effect()

    assert [row.verdict for row in results] == [CONFIRMED]
    assert not any("PV generation cut" in note for note in run.unestablished)


async def test_a_stop_with_a_weak_neighbour_still_answers_to_drift(
    sungrow_unit: MockModbusUnit,
) -> None:
    """Under `STOP_BRACKET_W` on one side, the bracket proves nothing."""
    run = await _prepared(sungrow_unit, cut_pv=True)
    _pv_script(run, [3000.0] * 11, [0.0] * 10, [400.0] * 10)

    results = await run._pv_cut_effect()

    assert [row.verdict for row in results] == [INCONCLUSIVE]
    assert any("W different afterwards" in note for note in run.unestablished)


async def test_without_leave_the_register_is_read_and_never_written(
    sungrow_unit: MockModbusUnit,
) -> None:
    run = await _prepared(sungrow_unit)
    _pv_script(run, [3000.0] * 40)

    assert await run._pv_cut_effect() == []
    assert any("leave to cut PV" in note for note in run.unestablished)
    assert run.snapshot.values[PV_CUT.field] == 0x55


async def test_too_little_pv_to_tell_a_stop_from_the_sky(
    sungrow_unit: MockModbusUnit,
) -> None:
    run = await _prepared(sungrow_unit, cut_pv=True)
    _pv_script(run, [300.0] * 40)

    assert await run._pv_cut_effect() == []
    assert any("under the 500 W" in note for note in run.unestablished)


async def test_pv_that_does_not_come_back_is_said_out_loud(
    sungrow_unit: MockModbusUnit,
) -> None:
    run = await _prepared(sungrow_unit, cut_pv=True)
    _pv_script(run, [3000.0] * 11, [0.0] * 10, [0.0] * 10)

    await run._pv_cut_effect()

    assert sungrow_unit.holding[PV_CUT_ADDRESS] == 0x55
    assert any("still at 0 W" in note for note in run.unestablished)


async def test_a_cut_register_is_restored_from_the_snapshot(
    sungrow_unit: MockModbusUnit,
) -> None:
    """A run that died after the cut: the restore puts the snapshot's word back."""
    run = await _prepared(sungrow_unit, cut_pv=True)
    sungrow_unit.holding[PV_CUT_ADDRESS] = 0xAA

    results = await run.async_restore()

    row = next(r for r in results if r.field == PV_CUT.field)
    assert row.restored
    assert sungrow_unit.holding[PV_CUT_ADDRESS] == 0x55


def test_the_survey_names_the_cut_and_passes_it_under_its_one_yes() -> None:
    """A yes covers what the question named, so the question must name it."""
    script = (
        Path(__file__).resolve().parents[1]
        / "device-survey/scripts/python/sungrow_survey.py"
    ).read_text(encoding="utf-8")
    assert '"--cut-pv"' in script
    assert "PV generation cut for about half a minute" in script
