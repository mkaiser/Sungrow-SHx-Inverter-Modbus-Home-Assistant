"""The wallbox port, checked against the measurement it came from.

Unlike the inverter, and unlike even the SBR, there is no YAML to check this
against: the YAML package never covered a wallbox, and Sungrow publishes no
register document for one. `doc/wallbox_registers.md` is the whole source,
and it is what three independent measurements agree on -- one reading taken
here plus the two community projects.

So the guard is the reading itself. `doc/device-fingerprints/` holds a
committed fingerprint carrying the raw words an AC22E-01 answered, and the
survey decodes them with its own decoder in `probe.WALLBOX_FIELDS`. This file
drives the **library's** components against the same words and requires the
two to agree -- which is the same discipline
`tests/test_portable_decoder.py` applies to the inverter, arrived at from the
other direction.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

from modbus_connection.mock import MockModbusConnection
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "sungrow_scan"))

from probe import WALLBOX_FIELDS, _wallbox_readings  # noqa: E402

from sungrow_modbus.wallbox_registers import (  # noqa: E402
    CHARGING_STATUS,
    COMPONENTS,
    MODELS,
    WallboxLive,
    WallboxSettings,
)

#: The one committed fingerprint that carries a wallbox.
FINGERPRINT = next((REPO / "doc" / "device-fingerprints").glob("*wallbox*.json"))


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


#: What the survey decoded from the same words, keyed by its own field names.
#: Fed the **raw** dump, string keys and all, because that is what
#: `_wallbox_readings` reads -- it decodes a document's dump in place rather
#: than a parsed one, which is how a fingerprint carries both the words and
#: their meaning without a second read.
SURVEY = {
    name: entry["value"]
    for name, entry in _wallbox_readings(
        json.loads(FINGERPRINT.read_text(encoding="utf-8"))["wallbox"]["register_dump"]
    ).items()
}


@pytest.mark.parametrize(
    ("field", "space", "address"),
    [(f[0], f[1], f[2]) for f in WALLBOX_FIELDS],
    ids=[f[0] for f in WALLBOX_FIELDS],
)
def test_the_library_reads_every_register_the_survey_decodes(
    field: str, space: str, address: int
) -> None:
    """Neither side may know a register the other does not.

    The survey has decoded 32 of these into every fingerprint since before
    the library could read any of them, so it is the older and better-tested
    of the two. A register it names and the library cannot read is a gap in
    the port; the reverse would be a register nothing has ever recorded.
    """
    # Flattened: which addresses the library reads, per space.
    by_space: dict[str, set[int]] = {}
    for klass in COMPONENTS.values():
        addresses = by_space.setdefault(klass.register_space, set())
        for descriptor in klass.declared_fields.values():
            count = getattr(descriptor, "count", 1) or 1
            addresses.update(range(descriptor.address, descriptor.address + count))
    assert address in by_space.get(space, set()), (
        f"the survey decodes {space} {address} (reg {address + 1}) as "
        f"{field!r} and no library component reads it"
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
    """Two decoders, one set of words, and the scales are where it goes wrong.

    A transposed scale reads a plausible number: 22080 W at the wrong scale
    is 2208 W, which is a believable wallbox and completely wrong. So each
    value is compared against the survey's independent decoding of the same
    register rather than against an expectation written twice.
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
            f"{field}: library {value!r}, survey {expected!r}"
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
    declared writable and none is in `scripts/writes.py`.
    """
    for klass in COMPONENTS.values():
        for name, descriptor in klass.declared_fields.items():
            assert not getattr(descriptor, "writable", False), (
                f"{klass.__name__}.{name} is writable"
            )
