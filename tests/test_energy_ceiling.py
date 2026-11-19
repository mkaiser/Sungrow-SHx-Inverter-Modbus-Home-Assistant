"""The ceiling on the energy counters, against the devices that needed it.

A lifetime counter with a broken high word reads a number, not a sentinel, so
`nan=` cannot catch it. The guard is a ceiling no house reaches, declared on
the field so that Home Assistant's sensors, the diagnosis's published readings
and the plausibility checks all refuse the same reading
(`sungrow_modbus.model.CeilingField`).

Two things are tested here, and the second is the one that matters in a year's
time: that the ceiling catches the reading that made it necessary, and that
**every** multi-word energy counter in every map declares one, so a counter
added later cannot quietly go back to publishing a broken word.
"""

from __future__ import annotations

import json
from typing import Any

from modbus_connection.model import Component
import pytest

from sungrow_modbus import model
from sungrow_modbus.battery import registers as battery_registers
from sungrow_modbus.hybrid_inverter import registers as inverter_registers
from sungrow_modbus.ihomemanager import registers as ihomemanager_registers
from sungrow_modbus.logger import registers as logger_registers
from sungrow_modbus.string_inverter import registers as string_registers
from sungrow_modbus.wallbox import registers as wallbox_registers

from . import corpus

#: Units an energy counter is declared in. A field in any other unit is not
#: an energy counter and gets no ceiling: a power, a voltage, an hour count.
ENERGY_UNITS = {"kWh", "Wh"}

MAPS = (
    inverter_registers,
    battery_registers,
    string_registers,
    ihomemanager_registers,
    wallbox_registers,
    logger_registers,
)


def _energy_fields() -> dict[str, Any]:
    """Return every energy field wider than one word, across every map."""
    found: dict[str, Any] = {}
    for module in MAPS:
        for value in vars(module).values():
            if not (
                isinstance(value, type)
                and issubclass(value, Component)
                and value is not Component
            ):
                continue
            for name, field in vars(value).items():
                unit = getattr(field, "unit", None)
                count = getattr(field, "count", 1)
                if unit in ENERGY_UNITS and count > 1:
                    found[f"{module.__name__.split('.')[-2]}.{name}"] = field
    return found


ENERGY_FIELDS = _energy_fields()


def test_the_maps_hold_the_counters_this_was_written_for() -> None:
    """A sanity floor: the sweep above found the fields, not an empty set."""
    assert len(ENERGY_FIELDS) > 60
    assert "hybrid_inverter.total_battery_charge" in ENERGY_FIELDS
    assert "battery.total_charge" in ENERGY_FIELDS
    assert "wallbox.lifetime_energy" in ENERGY_FIELDS


@pytest.mark.parametrize("name", sorted(ENERGY_FIELDS))
def test_every_multi_word_energy_counter_has_a_ceiling(name: str) -> None:
    """No energy counter is left to publish a broken word.

    This is the test that outlives the bug: a counter added with `uint32`
    rather than `energy_counter` fails here on the commit that adds it.
    """
    field = ENERGY_FIELDS[name]
    assert isinstance(field, model.CeilingField), name
    expected = (
        model.ENERGY_CEILING_KWH if field.unit == "kWh" else model.ENERGY_CEILING_WH
    )
    assert field.ceiling == expected, name


def test_the_ceiling_refuses_the_reading_it_was_written_for() -> None:
    """Maximo101's SH10RS: a sound low word under a high word of 0xFFFF.

    13041/13042 read `0x9F6D` and `0xFFFF`, low word first, which decodes to
    429,494,257.3 kWh. 0xFFFF alone is the specification's *unavailable*, but
    the double word is not 0xFFFFFFFF, so the field's `nan=` -- it has none,
    and could not have one -- is no help.
    """
    field = inverter_registers.InverterSlowestInput.__dict__["total_battery_charge"]
    assert field.decode([0x9F6D, 0xFFFF]) is None


def test_the_same_low_word_under_a_sound_high_word_reads() -> None:
    """The guard is about the size of the value, not about the register."""
    field = inverter_registers.InverterSlowestInput.__dict__["total_battery_charge"]
    assert field.decode([0x9F6D, 0x0001]) == pytest.approx(10634.9)
    assert field.decode([0x9F6D, 0x0000]) == pytest.approx(4081.3)


def test_a_refused_reading_is_logged_once_per_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A broken word is a line a day, not a line a poll."""
    field = model.energy_counter(100, scale=0.1)
    with caplog.at_level("WARNING", logger=model.__name__):
        for _ in range(3):
            assert field.decode([0x9F6D, 0xFFFF]) is None
        assert field.decode([0x9F6E, 0xFFFF]) is None
    lines = [record for record in caplog.records if "honestly reach" in record.message]
    assert len(lines) == 2


def test_an_energy_counter_refuses_a_unit_it_has_no_ceiling_for() -> None:
    """Rather than silently taking the kWh ceiling for a thousandth of it."""
    with pytest.raises(ValueError, match="no energy ceiling"):
        model.energy_counter(100, scale=0.1, unit="MWh")


#: Every energy field's ceiling, by the name a document publishes it under.
#: Two maps may hold a name (`total_pv_generation` is the hybrid's and the
#: SG's); they agree on the unit, and the assertion below checks that they do.
CEILING_BY_NAME: dict[str, float] = {}
for _key, _field in ENERGY_FIELDS.items():
    _name = _key.split(".", 1)[1]
    assert CEILING_BY_NAME.setdefault(_name, _field.ceiling) == _field.ceiling, _name


def _values(document: dict[str, Any]) -> dict[str, Any]:
    """Return a document's readings, whichever device wrote it."""
    readings = (document.get("readings") or {}).get("values")
    if readings is not None:
        return dict(readings)
    for kind in ("wallbox", "ihomemanager", "string_inverter", "logger"):
        block = document.get(kind)
        if isinstance(block, dict) and isinstance(block.get("readings"), dict):
            return dict(block["readings"])
    return {}


@pytest.mark.parametrize("path", corpus.ALL_DOCUMENTS, ids=lambda p: p.stem)
def test_no_honest_reading_in_the_corpus_is_above_the_ceiling(path: Any) -> None:
    """Every committed diagnosis, against the ceiling that now refuses it.

    The ceiling has to stand far above every real house or it would take a
    working sensor away. The only readings above it in the whole corpus are
    Maximo101's two, whose `total_battery_charge` is the fault this was built
    for; the largest honest counter anywhere is 79,459.6 kWh.
    """
    above = {
        name: value
        for name, value in _values(json.loads(path.read_text(encoding="utf-8"))).items()
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and name in CEILING_BY_NAME
        and value > CEILING_BY_NAME[name]
    }
    if "maximo101" in path.name:
        assert set(above) == {"total_battery_charge"}
        return
    assert above == {}


def test_the_corpus_test_above_is_reading_the_documents() -> None:
    """Otherwise it passes on every document by finding no counters at all."""
    seen = 0
    for path in corpus.ALL_DOCUMENTS:
        values = _values(json.loads(path.read_text(encoding="utf-8")))
        seen += len(set(values) & set(CEILING_BY_NAME))
    assert seen > 500
