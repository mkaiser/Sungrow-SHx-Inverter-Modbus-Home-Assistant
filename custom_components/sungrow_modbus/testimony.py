"""What the owner must answer before a capability test writes anything.

A capability test's findings are read against the house they were taken in.
Which path the words travelled, whether a proxy rebuilt every frame, whether
a second inverter is feeding the same meter -- none of it is in a register,
and a run whose document cannot say is a run whose surprises cannot be
attributed. So the three questions that have an answer for *every* house are
asked before the first write, and the test refuses until they are answered.

**Three, and not the rest.** Each of these is a dropdown whose list already
holds the honest answer for somebody who does not know (`unsure`, `unknown`)
or whose house does not have the thing (`no`), so requiring them asks nobody
to guess. The free-text questions -- the battery's make, anything else worth
knowing -- are not required: a house may have no battery and nothing else to
say, and an empty box would then be a true answer indistinguishable from an
unopened form. The name is not required either: contributing anonymously is
a choice this project offers on purpose.

**A wallbox entry answers through its inverter.** The three are about an
inverter, and a wallbox entry's options have none of them: a managed
wallbox's run is read against the house of the inverter entry that manages
it, so that entry's answers are the ones asked for; a wallbox no inverter
entry manages has no inverter to describe, and is asked none.

**Only an extended run.** A read-only diagnosis writes nothing, and a
reading with no testimony is still a reading worth having -- refusing it
would turn the easiest contribution into a form to fill in first. It gets
the notification instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.translation import async_get_cached_translations

from .const import (
    CONF_DIAGNOSIS_OTHER_INVERTER,
    CONF_DIAGNOSIS_PROXY,
    CONF_DIAGNOSIS_TRANSPORT,
    CONF_KIND,
    CONF_REPORTER,
    DOMAIN,
    KIND_WALLBOX,
)
from .texts import async_cached_texts

if TYPE_CHECKING:
    from .coordinator import SungrowConfigEntry

#: The questions an extended run is refused without, and their wording on the
#: options page. The labels are English here; the notification says them in
#: Home Assistant's language (`_question`), and the *refusal* is a translated
#: exception (`testimony_missing`) that names them in the reader's, because a
#: sentence built in code and handed over as a placeholder would stay English
#: in a German dialog (`texts.py`).
REQUIRED: tuple[tuple[str, str], ...] = (
    (CONF_DIAGNOSIS_TRANSPORT, "How this inverter is connected"),
    (CONF_DIAGNOSIS_PROXY, "Is a Modbus proxy in the path?"),
    (
        CONF_DIAGNOSIS_OTHER_INVERTER,
        "Is there another inverter here that is not a Sungrow?",
    ),
)

#: Worth having, never required: anonymous is a choice, not an omission.
SUGGESTED: tuple[tuple[str, str], ...] = ((CONF_REPORTER, "Your name or handle"),)


def answering_entry(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> SungrowConfigEntry | None:
    """Return the entry whose options answer `REQUIRED` for `entry`, or None.

    The entry itself, but for a wallbox entry the inverter entry that manages
    it, and None when no inverter entry does: its options have no inverter
    questions, and there is no inverter to describe.
    """
    if entry.data.get(CONF_KIND) != KIND_WALLBOX:
        return entry
    from .wallbox_capability_test import managing_entry

    return managing_entry(hass, entry)


def missing_keys(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> tuple[SungrowConfigEntry, list[str]]:
    """Return the entry that answers `REQUIRED`, and the keys it has no answer for."""
    answering = answering_entry(hass, entry)
    if answering is None:
        return entry, []
    return answering, [
        key for key, _ in REQUIRED if not str(answering.options.get(key) or "").strip()
    ]


def unanswered(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    questions: tuple[tuple[str, str], ...] = REQUIRED,
) -> list[str]:
    """Return the labels of `questions` this entry has no answer for."""
    answering = answering_entry(hass, entry) if questions is REQUIRED else entry
    if answering is None:
        return []
    return [
        label
        for key, label in questions
        if not str(answering.options.get(key) or "").strip()
    ]


@callback
def async_refuse_if_unanswered(hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
    """Raise rather than start an extended run on an unanswered entry.

    `ServiceValidationError`, so the dialog a button press raises and an
    automation's error log say the same thing, and neither is a traceback.
    """
    if unanswered(hass, entry):
        answering = answering_entry(hass, entry) or entry
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="testimony_missing",
            translation_placeholders={"title": answering.title},
        )


@callback
def _question(hass: HomeAssistant, key: str) -> str:
    """Return a question as the options page words it, in Home Assistant's language."""
    path = f"component.{DOMAIN}.options.step.init.sections.diagnosis.data.{key}"
    for language in (hass.config.language, "en"):
        found = async_get_cached_translations(hass, language, "options", DOMAIN)
        if path in found:
            return found[path]
    return dict((*REQUIRED, *SUGGESTED))[key]


@callback
def async_check(hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
    """Say which answers are missing, before anything is started.

    At the moment an extended mode is chosen and again when Start is pressed,
    rather than in the notification that arrives when a run is over: there is
    still time to answer. One notification id per entry, so arming a mode and
    then starting it replaces rather than stacks, and answering dismisses it.
    """
    notification_id = f"{DOMAIN}_testimony_{entry.entry_id}"
    _, required = missing_keys(hass, entry)
    suggested = [
        key for key, _ in SUGGESTED if not str(entry.options.get(key) or "").strip()
    ]
    if not required and not suggested:
        persistent_notification.async_dismiss(hass, notification_id)
        return

    texts = async_cached_texts(hass)
    asked = [f"- **{_question(hass, key)}**" for key in required]
    name = [_question(hass, key) for key in suggested]
    if required:
        parts = [texts("notice_refused"), "\n".join(asked), texts("notice_no_guess")]
        if name:
            parts.append(texts("notice_suggested", question="**, **".join(name)))
    else:
        parts = [
            texts("notice_name_missing"),
            "\n".join(f"- **{label}**" for label in name),
            texts("notice_anonymous"),
        ]
    parts.append(texts("notice_answer_where"))
    persistent_notification.async_create(
        hass,
        "\n\n".join(parts),
        title=texts(
            "notice_title_unanswered",
            title=(answering_entry(hass, entry) or entry).title,
        ),
        notification_id=notification_id,
    )
