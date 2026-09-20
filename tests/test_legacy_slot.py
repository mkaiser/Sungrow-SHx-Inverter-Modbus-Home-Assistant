"""Working out which of the YAML package's inverter slots an entry is.

The legacy entity ids are global and unprefixed, so only one device can hold
them. A house with two inverters ran `modbus_sungrow.yaml` alongside
`modbus_sungrow_multiple_inverters_2.yaml`, which appends `_inv_2` to every
unique_id -- and until this existed, the second inverter's entry was silently
never asked, so it could only ever have taken the first one's history.

The question "which slot is this device?" has exactly one honest answer, and
it is not a question for the owner: the YAML's serial sensor for each slot
holds that inverter's serial as its **state**, and the entry already knows
which serial it is talking to. A match is proof. No match is ignorance, and
these tests are mostly about keeping those two apart.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.sungrow_modbus.migration import (
    LEGACY_SERIAL_DOMAIN,
    LEGACY_SERIAL_PLATFORM,
    LEGACY_SERIAL_UNIQUE_ID,
    LEGACY_SUFFIXES,
    async_legacy_suffix,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

FIRST = "A123456789"
SECOND = "A987654321"


def _yaml_serial_sensor(hass: HomeAssistant, suffix: str, serial: str) -> str:
    """Register a YAML serial sensor for one slot, and give it its state."""
    entry = er.async_get(hass).async_get_or_create(
        LEGACY_SERIAL_DOMAIN,
        LEGACY_SERIAL_PLATFORM,
        f"{LEGACY_SERIAL_UNIQUE_ID}{suffix}",
        suggested_object_id=f"sungrow_inverter_serial{suffix}",
    )
    hass.states.async_set(entry.entity_id, serial)
    return entry.entity_id


async def test_a_single_inverter_install_is_the_unsuffixed_slot(
    hass: HomeAssistant,
) -> None:
    """The overwhelmingly common case, and it must keep behaving as it did."""
    _yaml_serial_sensor(hass, "", FIRST)

    assert async_legacy_suffix(hass, FIRST) == ""


async def test_each_inverter_finds_its_own_slot(hass: HomeAssistant) -> None:
    """The point of the whole thing.

    Two entries, two devices, two sets of legacy ids -- and each entry finds
    the set belonging to the inverter it is actually talking to, rather than
    the set that happens to be unclaimed.
    """
    _yaml_serial_sensor(hass, "", FIRST)
    _yaml_serial_sensor(hass, "_inv_2", SECOND)

    assert async_legacy_suffix(hass, FIRST) == ""
    assert async_legacy_suffix(hass, SECOND) == "_inv_2"


async def test_an_inv_1_file_is_found_too(hass: HomeAssistant) -> None:
    """A two-inverter house need not have used the plain file at all.

    The generator produces an `_inv_1` variant, so both shapes exist in the
    wild. Searching the suffixes rather than computing one from an index is
    what makes that a non-issue.
    """
    _yaml_serial_sensor(hass, "_inv_1", FIRST)
    _yaml_serial_sensor(hass, "_inv_2", SECOND)

    assert async_legacy_suffix(hass, FIRST) == "_inv_1"
    assert async_legacy_suffix(hass, SECOND) == "_inv_2"


async def test_no_match_is_none_and_never_the_first_slot(
    hass: HomeAssistant,
) -> None:
    """The distinction the whole design rests on.

    `None` means "cannot tell", and a caller must not read it as `""`. A second
    inverter handed the first one's ids takes its years of history, silently,
    and no later guess undoes that.
    """
    _yaml_serial_sensor(hass, "", FIRST)

    assert async_legacy_suffix(hass, SECOND) is None


async def test_a_package_that_is_not_running_answers_nothing(
    hass: HomeAssistant,
) -> None:
    """Registered but stateless, which is what an unavailable YAML looks like.

    The entity survives in the registry long after the package stops polling,
    so its existence is not evidence. Only its state is.
    """
    entry = er.async_get(hass).async_get_or_create(
        LEGACY_SERIAL_DOMAIN,
        LEGACY_SERIAL_PLATFORM,
        LEGACY_SERIAL_UNIQUE_ID,
        suggested_object_id="sungrow_inverter_serial",
    )
    hass.states.async_set(entry.entity_id, "unavailable")

    assert async_legacy_suffix(hass, FIRST) is None
    assert entry.entity_id  # it is there; it just cannot answer


async def test_an_entry_without_a_serial_asks_nothing(hass: HomeAssistant) -> None:
    """No serial, no evidence, no claim."""
    _yaml_serial_sensor(hass, "", FIRST)

    assert async_legacy_suffix(hass, None) is None
    assert async_legacy_suffix(hass, "") is None


async def test_the_lookup_uses_the_platform_that_registered_the_sensor(
    hass: HomeAssistant,
) -> None:
    """`modbus` registered it, even though it is a `sensor`.

    Written because the first draft looked it up under `sensor`/`sensor`, which
    fails in the quietest possible way: it never matches, and a two-inverter
    house migrates as though it had one.
    """
    assert LEGACY_SERIAL_PLATFORM == "modbus"
    assert LEGACY_SERIAL_DOMAIN == "sensor"

    # Registered under the wrong platform, it must not be found.
    entry = er.async_get(hass).async_get_or_create(
        "sensor", "sensor", LEGACY_SERIAL_UNIQUE_ID
    )
    hass.states.async_set(entry.entity_id, FIRST)
    assert async_legacy_suffix(hass, FIRST) is None


@pytest.mark.parametrize("suffix", [s for s in LEGACY_SUFFIXES if s])
def test_the_serial_unique_id_is_really_in_the_generated_package(
    suffix: str,
) -> None:
    """Read out of the YAML the generator writes, not asserted about it.

    This is the assertion that keeps the detector honest. Every part of it is
    a claim about a file in this repository -- that
    `modbus_sungrow_multiple_inverters_<n>.yaml` exists, and that the serial
    sensor in it carries `sg_inverter_serial_inv_<n>` -- so a change to the
    generator's suffix scheme fails here rather than in somebody's migration.
    """
    number = suffix.removeprefix("_inv_")
    package = (
        Path(__file__).resolve().parent.parent
        / "legacy"
        / f"modbus_sungrow_multiple_inverters_{number}.yaml"
    )
    assert package.exists(), f"{package.name} is generated and committed"
    assert f"{LEGACY_SERIAL_UNIQUE_ID}{suffix}" in package.read_text(encoding="utf-8")


def test_the_plain_package_carries_the_unsuffixed_serial() -> None:
    """And the single-inverter file is the unsuffixed slot, as `""` claims."""
    package = Path(__file__).resolve().parent.parent / "legacy" / "modbus_sungrow.yaml"
    text = package.read_text(encoding="utf-8")
    assert f"unique_id: {LEGACY_SERIAL_UNIQUE_ID}\n" in text


# -- what the slot is actually for ------------------------------------------


def _yaml_entity(
    hass: HomeAssistant, domain: str, platform: str, unique_id: str, object_id: str
) -> str:
    """Register one of the YAML package's entities."""
    return (
        er.async_get(hass)
        .async_get_or_create(domain, platform, unique_id, suggested_object_id=object_id)
        .entity_id
    )


async def test_each_inverter_is_offered_only_its_own_legacy_ids(
    hass: HomeAssistant,
) -> None:
    """The bug this closes, stated as a test.

    The legacy ids are global and unprefixed, so before the slot existed both
    entries asked the same question and got the same answer: the *first*
    inverter's ids. The second inverter could only ever have been handed
    another device's years of readings, or -- once those were claimed -- have
    been told there was nothing to migrate and never asked at all.
    """
    from custom_components.sungrow_modbus.migration import async_legacy_ids_known

    first = _yaml_entity(
        hass, "sensor", "modbus", "sg_total_dc_power", "total_dc_power"
    )
    second = _yaml_entity(
        hass, "sensor", "modbus", "sg_total_dc_power_inv_2", "total_dc_power_inv_2"
    )

    assert first in async_legacy_ids_known(hass, "")
    assert second not in async_legacy_ids_known(hass, "")

    assert second in async_legacy_ids_known(hass, "_inv_2")
    assert first not in async_legacy_ids_known(hass, "_inv_2")


def test_the_suffix_lands_on_the_name_the_way_the_generator_puts_it_there() -> None:
    """`Total DC power` becomes `Total DC power inv 2`, then gets slugified.

    Appending `_inv_2` to the finished id reaches the same answer today and
    would stop doing so the first time a legacy name contained something
    `slugify` treats differently -- a bracket, an ampersand, a double space.
    Deriving it the way Home Assistant derived it keeps that from mattering.
    """
    from custom_components.sungrow_modbus.entity import SungrowEntityDescription
    from custom_components.sungrow_modbus.migration import legacy_entity_id

    description = SungrowEntityDescription(
        key="total_dc_power",
        component="fast_input",
        field="total_dc_power",
        legacy_name="Total DC power (array)",
    )

    assert legacy_entity_id("sensor", description) == "sensor.total_dc_power_array"
    assert (
        legacy_entity_id("sensor", description, "_inv_2")
        == "sensor.total_dc_power_array_inv_2"
    )


# -- the claim itself, which is where history is won or lost -----------------


async def test_two_entries_claim_two_different_sets_of_ids(
    hass: HomeAssistant,
) -> None:
    """The end the whole slot mechanism exists for.

    Two inverters, two YAML slots, two entries -- and each entry registers its
    entities on the ids belonging to *its own* device. Asserted on the claim
    itself rather than on the detector, because the detector being right is
    only useful if the value reaches the registry.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.sungrow_modbus.const import CONF_LEGACY_SLOT, DOMAIN
    from custom_components.sungrow_modbus.migration import async_claim_legacy_ids
    from sungrow_modbus import Capability

    registry = er.async_get(hass)
    for unique_id, object_id in (
        ("sg_total_pv_generation", "total_pv_generation"),
        ("sg_total_pv_generation_inv_2", "total_pv_generation_inv_2"),
    ):
        registry.async_get_or_create(
            "sensor", "modbus", unique_id, suggested_object_id=object_id
        )

    claims: dict[str, list[str]] = {}
    for serial, slot in ((FIRST, ""), (SECOND, "_inv_2")):
        entry = MockConfigEntry(
            domain=DOMAIN, data={CONF_LEGACY_SLOT: slot}, unique_id=serial
        )
        entry.add_to_hass(hass)
        claims[serial] = async_claim_legacy_ids(
            hass, entry, serial, frozenset(Capability), frozenset()
        )

    assert "sensor.total_pv_generation" in claims[FIRST]
    assert "sensor.total_pv_generation_inv_2" in claims[SECOND]
    # And emphatically not the other way round.
    assert "sensor.total_pv_generation_inv_2" not in claims[FIRST]
    assert "sensor.total_pv_generation" not in claims[SECOND]


async def test_an_entry_with_no_stored_slot_behaves_exactly_as_before(
    hass: HomeAssistant,
) -> None:
    """Every entry that exists today has no slot stored.

    So the absent case is not an edge case, it is the whole installed base, and
    it has to keep claiming the unsuffixed ids it has always claimed.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.sungrow_modbus.const import DOMAIN
    from custom_components.sungrow_modbus.migration import async_claim_legacy_ids
    from sungrow_modbus import Capability

    er.async_get(hass).async_get_or_create(
        "sensor",
        "modbus",
        "sg_total_pv_generation",
        suggested_object_id="total_pv_generation",
    )
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=FIRST)
    entry.add_to_hass(hass)

    claimed = async_claim_legacy_ids(
        hass, entry, FIRST, frozenset(Capability), frozenset()
    )

    assert "sensor.total_pv_generation" in claimed


async def test_the_history_query_and_the_claim_use_the_same_slot(
    hass: HomeAssistant,
) -> None:
    """Both halves of the fallback must ask about the same inverter.

    `with_history` exists for entities whose registry entry is gone but whose
    recorder rows are not, and the claim derives an id from each key it names.
    Querying the unsuffixed history and then claiming suffixed ids from it
    would let a second inverter take its own ids on the strength of the first
    one's rows -- a claim that looks justified and rests on nothing.

    Asserted by reading the setup path, because the alternative is a recorder
    fixture for a bug about which question was asked.

    It reads `_async_take_over_legacy_ids` rather than `async_setup_entry`,
    which is where this moved when that function was split into named steps.
    A source-reading guard has to be pointed at the source, and that is the
    cost of this kind of test: it cannot fail when the code merely moves, so
    it must be repointed deliberately rather than quietly deleted.
    """
    import inspect

    from custom_components.sungrow_modbus import _async_take_over_legacy_ids

    source = inspect.getsource(_async_take_over_legacy_ids)
    assert "async_legacy_ids_with_history(hass, slot)" in source
    assert "keys_for(" in source
    # The slot reaches both, and comes from the entry rather than being
    # re-derived at a point where the YAML package is usually gone.
    assert "entry.data.get(CONF_LEGACY_SLOT)" in source
