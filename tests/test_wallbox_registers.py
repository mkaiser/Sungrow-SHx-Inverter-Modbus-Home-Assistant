"""The wallbox port, checked against the measurement it came from.

Unlike the inverter, and unlike even the SBR, there is no YAML to check this
against: the YAML package never covered a wallbox, and Sungrow publishes no
register document for one. `doc/wallbox_registers.md` is the whole source,
and it is what three independent measurements agree on -- one reading taken
here plus the two community projects.

So the guard is the reading itself. `doc/device-fingerprints/` holds a
committed fingerprint carrying the raw words an AC22E-01 answered **and** the
readings an independent decoder -- the survey's own, before it moved into the
library -- made of them. This file holds the library to both: its document
decoder must reproduce the committed readings exactly, and its components must
read the same values from the same words.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from modbus_connection.mock import MockModbusConnection
import pytest

from sungrow_modbus.dump import WALLBOX_MASKED, masked
from sungrow_modbus.wallbox import readings
from sungrow_modbus.wallbox_registers import (
    CHARGING_STATUS,
    COMPONENTS,
    MODELS,
    WallboxLive,
    WallboxSettings,
)

REPO = Path(__file__).resolve().parent.parent

#: The completed session (status 6) the tests keep, since the published
#: document was replaced by an idle reading.
FINGERPRINT = REPO / "tests" / "data" / "wallbox_ac22e01_completed_session.json"


def _words() -> dict[str, dict[int, int]]:
    """Return the raw words the AC22E-01 answered, by register space."""
    document = json.loads(FINGERPRINT.read_text(encoding="utf-8"))
    dump = document["wallbox"]["register_dump"]
    return {
        space: {int(a): v for a, v in values.items() if v is not None}
        for space, values in dump.items()
    }


WORDS = _words()


def _component(klass):
    """Drive one component against the measured words."""
    unit = MockModbusConnection().for_unit(3)
    unit.input = dict(WORDS.get("input", {}))
    unit.holding = dict(WORDS.get("holding", {}))
    instance = klass(unit)
    asyncio.run(instance.async_update())
    return instance


#: The document's section, as committed.
SECTION = json.loads(FINGERPRINT.read_text(encoding="utf-8"))["wallbox"]

#: What the independent decoder published from those words, by field name.
SURVEY = {name: entry["value"] for name, entry in SECTION["readings"].items()}


def test_the_committed_dump_decodes_to_the_committed_readings() -> None:
    """The golden test: byte for byte, from the masked words.

    The committed readings were made by the survey's own decoder before it
    moved into the library, so this is the move's proof as well as a guard
    against a later change to a scale, a code table or a confidence mark.
    """
    assert (
        readings(masked(SECTION["register_dump"], WALLBOX_MASKED))
        == (SECTION["readings"])
    )


@pytest.mark.parametrize(
    "field",
    [
        "model_name",
        "version_string",
        "nominal_voltage",
        "rated_current",
        "minimum_charging_power",
        "maximum_charging_power",
        "lifetime_energy",
        "session_energy",
        "control_pilot_voltage",
        "available_current",
        "output_current_setting",
        "mileage_per_kwh",
        "phase_a_voltage",
        "phase_a_current",
    ],
)
def test_every_value_matches_what_the_survey_decoded(field: str) -> None:
    """The components and the published readings agree on every scale.

    A transposed scale reads a plausible number: 22080 W at the wrong scale
    is 2208 W, which is a believable wallbox and completely wrong. So each
    value the poll reads is compared against the committed decoding of the
    same register rather than against an expectation written twice.
    """
    for klass in COMPONENTS.values():
        if field in klass.declared_fields:
            value = getattr(_component(klass), field)
            break
    else:
        pytest.fail(f"no component declares {field}")

    expected = SURVEY[field]
    if isinstance(expected, str):
        assert value == expected
    else:
        assert value == pytest.approx(expected), (
            f"{field}: library {value!r}, committed {expected!r}"
        )


def test_the_codes_become_words_and_an_unknown_code_becomes_nothing() -> None:
    """A code table is only worth having if it refuses to guess.

    `unknown` as a string would sort among real readings and look like one.
    None is the honest form, and it is what an entity needs to go
    unavailable rather than to report a label nobody can act on.
    """
    live = _component(WallboxLive)
    assert live.charging_status_raw == 6
    assert live.charging_status == "completed"
    # Measured: a finished session reads 6, and only a source with the whole
    # table distinguishes that from idle.
    assert CHARGING_STATUS[6] == "completed"
    assert live.charging is False, "completed is not charging"
    assert live.start_mode == "start with EMS"

    live.charging_status_raw = 99  # type: ignore[misc]
    assert live.charging_status is None, "an unknown code must not be labelled"


def test_the_start_stop_polarity_is_named_for_the_value_it_holds() -> None:
    """The trap in this map: 0 is start and 1 is stop.

    Which is the opposite way round from `charger_enabled` two registers
    earlier, where 1 is enabled -- and both were read as 1 on a wallbox that
    had finished charging and was not stopped. A property called
    `start_stop` would be read backwards by everybody, so it is called
    `stopped` and the polarity is in the name.
    """
    settings = _component(WallboxSettings)
    assert settings.charger_enabled_raw == 1
    assert settings.charger_enabled is True
    assert settings.start_stop_raw == 1
    assert settings.stopped is True


def test_a_model_code_no_reading_has_seen_is_still_recognised() -> None:
    """Two of the three codes come from the community projects, not from here.

    Which is the point of carrying them: a contributor plugging in an
    AC011E-01 gets a named device on the first attempt, from evidence this
    repository never gathered.
    """
    assert MODELS[0x3F80] == "AC22E-01", "the one measured here"
    assert MODELS[0x20DA] == "AC011E-01"
    assert MODELS[0x20ED] == "AC007-00"
    identity = _component(COMPONENTS["wallbox_identity"])
    assert identity.device_type_code == 0x3F80
    assert identity.model == "AC22E-01"


def test_nothing_writes_to_a_wallbox() -> None:
    """Read-only, and asserted rather than assumed.

    Starting somebody's car charging from a stale automation is not a thing
    to enable on one measurement of one unit, so no wallbox register is
    declared writable and none is in `scripts/generate/tables/writes.py`.
    """
    for klass in COMPONENTS.values():
        for name, descriptor in klass.declared_fields.items():
            assert not getattr(descriptor, "writable", False), (
                f"{klass.__name__}.{name} is writable"
            )


def test_no_dump_block_splits_a_wallbox_string() -> None:
    """Every string field is read whole by the wallbox dump.

    The wallbox answers a read that starts inside a string with zeros for the
    rest of it, so a block boundary inside a string publishes a truncated
    value -- the firmware string came out as `LE-01.1E1.001.` that way.
    """
    from modbus_connection.model import StringField

    from sungrow_modbus.dump import BLOCK, WALLBOX_BANDS
    from sungrow_modbus.wallbox_registers import COMPONENTS

    reads = [
        (space, start + offset, min(BLOCK, count - offset))
        for space, start, count, _why in WALLBOX_BANDS
        for offset in range(0, count, BLOCK)
    ]
    for component in COMPONENTS.values():
        for name, field in component.declared_fields.items():
            if not isinstance(field, StringField):
                continue
            first, last = field.address, field.address + field.count - 1
            inside = [
                (start, count)
                for space, start, count in reads
                if space == component.register_space
                and start <= first
                and last < start + count
            ]
            assert inside, f"{name} ({first}-{last}) is split between dump reads"


#: Where an AC22E-01 answers a read over TLS on its own LAN address (unit
#: 248): the first register of each data point, measured with one-register
#: reads at every address (input 21199-21205, the serial, not read). A read
#: starting anywhere else times out. Protocol addresses.
TLS_READ_STARTS = {
    "input": {
        21210,
        21212,
        21214,
        21215,
        21223,
        21224,
        21225,
        21240,
        21243,
        21258,
        *range(21261, 21273),
        *range(21274, 21280),
        *range(21281, 21300, 2),
        *range(21301, 21308),
        21309,
        *range(21311, 21318),
        21319,
        21321,
        21322,
        21326,
        21330,
        21331,
        21336,
        21337,
        *range(21339, 21346),
        21347,
        *range(21349, 21356),
        21357,
        *range(21359, 21366),
        21369,
        21373,
        21374,
    },
    "holding": {
        21200,
        21202,
        21203,
        21204,
        21206,
        21208,
        21210,
        21211,
        21212,
        21214,
        21215,
        21216,
        21220,
        21222,
        *range(21223, 21234),
        21249,
        21281,
        *range(21297, 21302),
        *range(21311, 21318),
    },
}


async def test_every_wallbox_read_starts_where_the_direct_path_answers() -> None:
    """A pooled read must begin on a data point, or TLS refuses it by silence.

    Through a WiNet-S any start answers, so nothing else would catch a new
    field that moves a block's start: it would work through the dongle and
    time out on the wallbox's own address.
    """
    from sungrow_modbus.block_test import component_blocks
    from sungrow_modbus.wallbox_registers import COMPONENTS

    for name, klass in COMPONENTS.items():
        for block in await component_blocks(name, klass):
            assert block.address in TLS_READ_STARTS[block.space], (
                f"{name} reads {block.space} {block.address}, which the wallbox "
                "does not answer as a start over TLS"
            )
