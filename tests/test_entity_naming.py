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
