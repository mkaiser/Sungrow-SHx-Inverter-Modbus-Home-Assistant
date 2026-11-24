"""The diagnosis's options, as the dashboard's Diagnosis view shows and saves them.

The same options **Configure** holds, under the same keys, so there is one
answer to each question. Saving one never reloads the entry: each is read when
a run starts, and a reload would end a collection (`_built_from` leaves
`RUN_OPTIONS` out).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from sungrow_modbus.diagnosis_document import (
    OTHER_INVERTER_CLAIMS,
    PROXY_CLAIMS,
    TRANSPORT_CLAIMS,
)

from . import testimony
from .const import (
    CAPABILITY_TEST_PERMISSION_DEFAULT,
    CONF_CAPABILITY_TEST_CHARGE_WINDOW,
    CONF_CAPABILITY_TEST_DISCHARGE_WINDOW,
    CONF_CAPABILITY_TEST_EXPORT,
    CONF_CAPABILITY_TEST_IMPORT_LIMIT,
    CONF_CAPABILITY_TEST_PV_CUT,
    CONF_CAPABILITY_TEST_RESTART,
    CONF_CAPABILITY_TEST_WALLBOX,
    CONF_DIAGNOSIS_BATTERY,
    CONF_DIAGNOSIS_COMMENT,
    CONF_DIAGNOSIS_DUMP,
    CONF_DIAGNOSIS_OTHER_INVERTER,
    CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL,
    CONF_DIAGNOSIS_POLLERS,
    CONF_DIAGNOSIS_PROXY,
    CONF_DIAGNOSIS_TRANSPORT,
    CONF_KIND,
    CONF_PUBLISH_ADDRESS,
    CONF_REPORTER,
    CONF_WALLBOX_MANAGED_BY,
    CONF_WALLBOX_MAX_AMPS,
    CONF_WALLBOX_STANDALONE,
    DEFAULT_CAPABILITY_TEST_WALLBOX,
    DEFAULT_DIAGNOSIS_DUMP,
    DEFAULT_WALLBOX_STANDALONE,
    KIND_STRING_INVERTER,
    KIND_WALLBOX,
    UNIT_247_KINDS,
)
from .coordinator import SungrowConfigEntry

#: What each field of a part may hold: a kind, and its choices or default.
type Field = tuple[str, Any]

#: The two parts of the view: what the owner says, and what they allow.
ANSWERS = "answers"
TESTS = "tests"

_SAID: dict[str, Field] = {
    CONF_REPORTER: ("text", ""),
    CONF_DIAGNOSIS_TRANSPORT: ("select", tuple(TRANSPORT_CLAIMS)),
    CONF_DIAGNOSIS_PROXY: ("select", tuple(PROXY_CLAIMS)),
    CONF_DIAGNOSIS_POLLERS: ("text", ""),
    CONF_DIAGNOSIS_OTHER_INVERTER: ("select", tuple(OTHER_INVERTER_CLAIMS)),
    CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL: ("text", ""),
    CONF_DIAGNOSIS_BATTERY: ("text", ""),
    CONF_DIAGNOSIS_COMMENT: ("multiline", ""),
    # What a run does while the owner has not answered: no address goes out.
    CONF_PUBLISH_ADDRESS: ("boolean", False),
    CONF_DIAGNOSIS_DUMP: ("boolean", DEFAULT_DIAGNOSIS_DUMP),
}
_WALLBOX_SAID: dict[str, Field] = {
    key: _SAID[key]
    for key in (CONF_REPORTER, CONF_DIAGNOSIS_COMMENT, CONF_PUBLISH_ADDRESS)
}
_ALLOWED: dict[str, Field] = dict.fromkeys(
    (
        CONF_CAPABILITY_TEST_RESTART,
        CONF_CAPABILITY_TEST_EXPORT,
        CONF_CAPABILITY_TEST_PV_CUT,
        CONF_CAPABILITY_TEST_CHARGE_WINDOW,
        CONF_CAPABILITY_TEST_DISCHARGE_WINDOW,
        CONF_CAPABILITY_TEST_IMPORT_LIMIT,
    ),
    ("boolean", CAPABILITY_TEST_PERMISSION_DEFAULT),
)
_WALLBOX_ALLOWED: dict[str, Field] = {
    CONF_CAPABILITY_TEST_WALLBOX: ("boolean", DEFAULT_CAPABILITY_TEST_WALLBOX),
    CONF_WALLBOX_STANDALONE: ("boolean", DEFAULT_WALLBOX_STANDALONE),
    CONF_WALLBOX_MAX_AMPS: ("number", (6, 32)),
}

#: Read when a run starts and by nothing at setup.
RUN_OPTIONS = frozenset({*_SAID, *_ALLOWED})

#: What an extended test is refused without.
_REQUIRED = frozenset(key for key, _ in testimony.REQUIRED)

#: Where an answer ends, so a paste cannot fill the config entry's storage.
MAX_TEXT = 2000


def parts(entry: SungrowConfigEntry) -> dict[str, dict[str, Field]]:
    """Return the fields this entry has, by part; none where nothing is asked."""
    kind = entry.data.get(CONF_KIND)
    if kind in UNIT_247_KINDS:
        return {ANSWERS: {}, TESTS: {}}
    if kind == KIND_WALLBOX:
        return {ANSWERS: _WALLBOX_SAID, TESTS: _WALLBOX_ALLOWED}
    if kind == KIND_STRING_INVERTER:
        return {ANSWERS: _SAID, TESTS: {}}
    return {ANSWERS: _SAID, TESTS: _ALLOWED}


def view(hass: HomeAssistant, entry: SungrowConfigEntry) -> dict[str, Any]:
    """Return what the view shows: each field, what it holds and may hold.

    `missing` is what an extended test is refused without, and the entry whose
    answers those are: a managed wallbox's are its inverter's.
    """
    wallbox = entry.data.get(CONF_KIND) == KIND_WALLBOX
    shown: dict[str, list[dict[str, Any]]] = {}
    for part, fields in parts(entry).items():
        rows = shown[part] = []
        for key, (kind, extra) in fields.items():
            fixed = kind in ("select", "number")
            row: dict[str, Any] = {
                "key": key,
                "kind": kind,
                "value": entry.options.get(key, None if fixed else extra),
            }
            if key in _REQUIRED:
                row["required"] = True
            if kind == "select":
                row["options"] = list(extra)
            if kind == "number":
                row["min"], row["max"] = extra
            rows.append(row)
    answering, missing = testimony.missing_keys(hass, entry)
    asked = parts(answering)[ANSWERS]
    return {
        "entry_id": entry.entry_id,
        "missing": {
            "entry_id": answering.entry_id,
            "title": answering.title,
            "keys": [key for key in missing if key in asked],
        },
        "step": "wallbox" if wallbox else "init",
        "running": entry.runtime_data.diagnosis.state.running,
        **shown,
    }


def _valid(kind: str, extra: Any, value: Any) -> bool:
    """Whether a field of this kind may hold `value`; empty is taken apart."""
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "select":
        return value in extra
    if kind == "number":
        low, high = extra
        return (
            isinstance(value, int | float)
            and not isinstance(value, bool)
            and low <= value <= high
        )
    return isinstance(value, str) and len(value) <= MAX_TEXT


def changed(
    entry: SungrowConfigEntry, part: str, values: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the options with `values` in, or raise `ValueError` naming the key.

    A part takes its own keys only: the answers are not behind the lock, so
    nothing that allows a test may be saved through them.
    """
    fields = parts(entry)[part]
    options = dict(entry.options)
    for key, value in values.items():
        if key not in fields:
            raise ValueError(key)
        kind, extra = fields[key]
        if value is None and kind in ("select", "number"):
            # An answer taken back.
            options.pop(key, None)
        elif _valid(kind, extra, value):
            options[key] = value
        else:
            raise ValueError(key)
    if options.get(CONF_WALLBOX_STANDALONE) and options.get(CONF_WALLBOX_MANAGED_BY):
        # Two answers that contradict each other, as in Configure.
        raise ValueError(CONF_WALLBOX_STANDALONE)
    return options
