"""Repairs flows for the Sungrow SHx integration.

This module drives two separate issues:

* ``legacy_yaml_present`` — the user has migrated to the UI integration but
  still has the old ``modbus_sungrow*.yaml`` package loaded as a
  ``modbus:`` hub named ``SungrowSHx*``. Not fixable programmatically
  because the package lives in ``configuration.yaml``; we simply point
  them at the migration guide.

* ``imported_from_yaml_{entry_id}`` — raised by the config flow after a
  successful ``source=import`` handoff, telling the user to delete the
  transient ``sungrow_shx:`` YAML stanza now that a real ConfigEntry
  exists. Fixable via a simple confirm-style repairs flow that dismisses
  the issue.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

LEGACY_YAML_ISSUE_ID = "legacy_yaml_present"
IMPORTED_FROM_YAML_ISSUE_PREFIX = "imported_from_yaml_"

MIGRATION_GUIDE_URL = (
    "https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant"
    "/blob/main/doc/migration_guide.md"
)


def _probe_legacy_modbus_hub(hass: HomeAssistant) -> str | None:
    """Best-effort detection of a live legacy ``SungrowSHx*`` modbus hub.

    The built-in ``modbus:`` integration does not expose a stable public
    API for listing hubs, so we probe a couple of known locations and
    fall back to silent ``None`` if neither is accessible (forward-
    compatible with HA refactors).
    """
    # ``hass.data["modbus"]`` is a dict-like mapping of hub-name -> hub.
    try:
        modbus_data: Any = hass.data.get("modbus")
    except Exception:  # noqa: BLE001 - defensive only
        modbus_data = None

    if isinstance(modbus_data, dict):
        for name in modbus_data:
            if isinstance(name, str) and name.startswith("SungrowSHx"):
                return name

    # Fall back to the raw YAML config snapshot. The ``modbus`` key there
    # is a list of hub dicts each carrying a ``name:``.
    try:
        raw = hass.config.as_dict()
    except Exception:  # noqa: BLE001
        return None

    hubs = raw.get("modbus") if isinstance(raw, dict) else None
    if isinstance(hubs, list):
        for hub in hubs:
            if not isinstance(hub, dict):
                continue
            name = hub.get("name")
            if isinstance(name, str) and name.startswith("SungrowSHx"):
                return name

    return None


async def async_check_legacy_yaml(hass: HomeAssistant) -> None:
    """Raise or clear the ``legacy_yaml_present`` repair.

    Called from ``async_setup_entry`` after the coordinator is ready.
    If a ``modbus:`` hub named ``SungrowSHx*`` is still loaded, the
    legacy YAML package is shadowing the new integration and the user
    must clean it up.

    Declared ``async`` purely so callers can ``await`` it without worrying
    about timing — all the work is synchronous in-memory lookups.
    """
    hub_name = _probe_legacy_modbus_hub(hass)
    if hub_name is None:
        ir.async_delete_issue(hass, DOMAIN, LEGACY_YAML_ISSUE_ID)
        return

    _LOGGER.warning(
        "Legacy Sungrow modbus hub %r still loaded alongside the UI "
        "integration; raising repairs issue",
        hub_name,
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        LEGACY_YAML_ISSUE_ID,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="legacy_yaml_present",
        translation_placeholders={"hub_name": hub_name},
        learn_more_url=MIGRATION_GUIDE_URL,
    )


@callback
def async_raise_imported_from_yaml_issue(
    hass: HomeAssistant, entry_id: str, title: str
) -> None:
    """Tell the user their YAML import succeeded — now remove the block."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{IMPORTED_FROM_YAML_ISSUE_PREFIX}{entry_id}",
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="imported_from_yaml",
        translation_placeholders={"title": title},
        learn_more_url=MIGRATION_GUIDE_URL,
        data={"entry_id": entry_id},
    )


class ImportedFromYamlFlow(RepairsFlow):
    """Confirm-and-dismiss flow for the ``imported_from_yaml_*`` issue.

    The user clicks "Fix" in the Repairs panel; we show a confirmation
    form and, on submit, simply resolve the issue. The actual cleanup
    (deleting the YAML block) has to happen in ``configuration.yaml`` by
    the user — this flow only acknowledges it.
    """

    def __init__(self, issue_id: str) -> None:
        self.issue_id = issue_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data={})

        issue_registry = ir.async_get(self.hass)
        placeholders: dict[str, str] | None = None
        if issue := issue_registry.async_get_issue(DOMAIN, self.issue_id):
            placeholders = issue.translation_placeholders

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders=placeholders,
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Dispatch a Repairs fix flow for a given issue.

    Called by the ``repairs`` integration via the module-level
    ``async_create_fix_flow`` name. Only fixable issues reach this path;
    ``legacy_yaml_present`` is not fixable so it never arrives here.
    """
    if issue_id.startswith(IMPORTED_FROM_YAML_ISSUE_PREFIX):
        return ImportedFromYamlFlow(issue_id)

    # Fallback — unknown issue. Returning a stubbed confirm flow beats
    # raising, which would leave the Repairs panel in a bad state.
    return ImportedFromYamlFlow(issue_id)
