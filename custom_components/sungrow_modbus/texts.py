"""The flows' and the notifications' sentences, in the language Home Assistant speaks.

A dialog's description is translated, but a placeholder is inserted as it is:
a sentence built in code and handed over as a placeholder stays English in a
German dialog. So every sentence the flows choose between lives in
`strings.json`, under the selector key `flow_text` (selector options are the
one translatable table an integration can read back), and the generator
writes its German beside the rest. A placeholder then carries only values.

The language is Home Assistant's own (`hass.config.language`), the one its
entity names follow too. A user whose profile asks for another language sees
these sentences in the system's, which is the closest a flow can get: it is
not told the language of the browser that opened it.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.translation import (
    async_get_cached_translations,
    async_get_translations,
)

from .const import DOMAIN

#: The selector key that holds them, and the prefix Home Assistant flattens
#: a translation to.
KEY = "flow_text"
PREFIX = f"component.{DOMAIN}.selector.{KEY}.options."


class Texts:
    """Look a sentence up by key and fill in its values."""

    def __init__(self, local: dict[str, str], english: dict[str, str]) -> None:
        """Hold both tables; English answers what a translation lacks."""
        self._local = local
        self._english = english

    def __call__(self, key: str, **values: object) -> str:
        """Return the sentence `key`, its `{placeholders}` filled from `values`.

        Raises `KeyError` for a key in neither table: a missing sentence is a
        bug to see in a test, not a blank to show a user.
        """
        text = self._local.get(PREFIX + key) or self._english[PREFIX + key]
        return text.format(**values) if values else text


async def async_texts(hass: HomeAssistant) -> Texts:
    """Return the sentences in Home Assistant's language, English beside them."""
    english = await async_get_translations(hass, "en", "selector", [DOMAIN])
    language = hass.config.language
    if language == "en":
        return Texts(english, english)
    local = await async_get_translations(hass, language, "selector", [DOMAIN])
    return Texts(local, english)


@callback
def async_cached_texts(hass: HomeAssistant) -> Texts:
    """Return the sentences without waiting, for a notification.

    From what Home Assistant holds already: `async_setup` loads it, and Home
    Assistant loads a language again when it changes.
    """
    return Texts(
        async_get_cached_translations(hass, hass.config.language, "selector", DOMAIN),
        async_get_cached_translations(hass, "en", "selector", DOMAIN),
    )
