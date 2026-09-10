"""How each id style behaves when the interface is not in English.

Home Assistant builds an entity_id from the user's own language when that
language is in `NATIVE_ENTITY_IDS`, and `de` is one of them. The integration
follows that rather than working around it, so these tests describe what each
of the two id styles then does — because they behave differently, and the
difference is what the migration depends on.
"""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockEntity, MockEntityPlatform

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

#: What a translated `de.json` supplies as the entity's name.
TRANSLATED = "Gesamte Gleichstromleistung"

#: The name the YAML package used, which its entity_id was slugified from.
LEGACY = "Total DC power"


class Modern(MockEntity):
    """Modern mode: device-scoped, and named through the translations."""

    _attr_has_entity_name = True

    def __init__(self, **kwargs) -> None:
        """Take the name the translation machinery resolved."""
        super().__init__(**kwargs)
        self._attr_name = TRANSLATED


class Legacy(MockEntity):
    """Legacy mode: the literal name the YAML used, never translated."""

    _attr_has_entity_name = False

    def __init__(self, **kwargs) -> None:
        """Take the legacy name verbatim."""
        super().__init__(**kwargs)
        self._attr_name = LEGACY


async def _add(hass: HomeAssistant) -> None:
    platform = MockEntityPlatform(hass, domain="sensor", platform_name="sungrow_modbus")
    await platform.async_add_entities(
        [
            Modern(unique_id="modern", entity_id=None),
            Legacy(unique_id="legacy", entity_id=None),
        ]
    )
    await hass.async_block_till_done()


def _entity_id(registry: er.EntityRegistry, unique_id: str) -> str:
    return next(
        e.entity_id for e in registry.entities.values() if e.unique_id == unique_id
    )


async def test_modern_ids_follow_the_interface_language(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    # Accepted rather than worked around: this is what Home Assistant intends
    # for a language in NATIVE_ENTITY_IDS, so a German user gets a German id.
    await _add(hass)
    assert _entity_id(entity_registry, "modern") == "sensor.gesamte_gleichstromleistung"


async def test_legacy_ids_stay_english_whatever_the_language(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    # The property the migration depends on, and it holds by construction:
    # `Entity._name_internal` returns `_attr_name` before consulting any
    # translation, so a legacy entity claims `sensor.total_dc_power` byte for
    # byte on a German instance exactly as on an English one.
    await _add(hass)
    assert _entity_id(entity_registry, "legacy") == "sensor.total_dc_power"


async def test_both_show_the_name_they_were_given(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    await _add(hass)
    modern = hass.states.get(_entity_id(entity_registry, "modern"))
    legacy = hass.states.get(_entity_id(entity_registry, "legacy"))
    assert modern.attributes["friendly_name"] == TRANSLATED
    assert legacy.attributes["friendly_name"] == LEGACY


async def test_renaming_later_does_not_move_an_existing_id(
    hass: HomeAssistant,
) -> None:
    """What a rename after release actually costs, which is not history.

    This was assumed the other way round for a while -- "the name *is* the
    id, so changing it after release breaks every dashboard and years of
    history" -- and that is wrong for anybody who already has the entity. The
    registry keys on `(domain, platform, unique_id)`, and a name only ever
    supplies the *suggested* object id, at creation. Come back a release later
    with a different name and the same unique_id and the entity keeps the id
    it was born with; only `original_name` moves.

    So the real cost of renaming during a preview is **divergence**: an early
    tester keeps `sensor.sh10rt_total_dc_power` while somebody installing
    afterwards gets the new one, and the two houses no longer answer the same
    question with the same id. That is a support and documentation problem,
    not a data one -- and where it matters, a registry rename moves the early
    tester's id and carries the history with it, which
    `tests/test_recorder_migration.py` establishes.

    Worth pinning because the whole alpha naming policy rests on it, and
    because it is a fact about Home Assistant's registry rather than about
    this integration.
    """
    registry = er.async_get(hass)
    first = registry.async_get_or_create(
        "sensor",
        "sungrow_modbus",
        "serial-total_dc_power",
        suggested_object_id="sh10rt_total_dc_power",
        original_name="Total DC power",
    )

    # The same entity, a release later, under a different name.
    again = registry.async_get_or_create(
        "sensor",
        "sungrow_modbus",
        "serial-total_dc_power",
        suggested_object_id="sh10rt_dc_power_total",
        original_name="DC power total",
    )

    assert again.entity_id == first.entity_id == "sensor.sh10rt_total_dc_power"
    assert again.original_name == "DC power total"
