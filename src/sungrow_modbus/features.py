"""Which feature sets a diagnosis found, and how far it tested each.

A feature set is what an owner thinks in -- *forced charging*, *the feed-in
limit* -- rather than a register: the controls that make it up, the
capability that gates them, and the parts of the capability test that judge
them. `feature_report` reads a finished diagnosis document and gives each set
one state, from the strongest evidence the document holds:

* **confirmed** -- a write was read back as written over a cable, or the
  inverter did as it was told while a behavioural check watched;
* **wrong scale** -- a write landed off by a decade, or acted on a value that
  was, or ran the wrong way: a finding, not a failure of the run;
* **write refused** -- the device answered a write with an exception;
* **inconclusive** -- tested, and nothing settled it either way;
* **readable** -- its registers answered, and nothing wrote to them;
* **not available** -- the integration does not grant its capability here;
* **not read** -- nothing in the document speaks for it.

The rules are the ones the rest of the evidence follows. A readback through a
WiNet-S is no evidence, because a dongle answers a written register stale; a
value that did not read is not a refusal; a simulator's or a dry run's block
settles nothing. The report is computed from the document alone, so any reader
can recompute it, and it is recomputed whenever a block is attached.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .addresses import field_address
from .capability_test import procedure
from .hybrid_inverter.capabilities import Capability

CONFIRMED = "confirmed"
WRONG_SCALE = "wrong scale"
REFUSED = "write refused"
INCONCLUSIVE = "inconclusive"
READABLE = "readable"
NOT_AVAILABLE = "not available"
NOT_READ = "not read"

#: Every state, strongest evidence first.
STATES: tuple[str, ...] = (
    CONFIRMED,
    WRONG_SCALE,
    REFUSED,
    INCONCLUSIVE,
    READABLE,
    NOT_AVAILABLE,
    NOT_READ,
)

#: Readback verdicts that are a finding about the scale.
_SCALE_FINDINGS = frozenset({procedure.SCALED, procedure.SLOPE_WRONG, procedure.OFF_BY})
#: Effect verdicts that are a finding about the scale or the direction.
_EFFECT_FINDINGS = frozenset({procedure.EFFECT_SCALED, procedure.SIGN_INVERTED})
#: Verdicts that say a test ran and settled nothing.
_UNSETTLED = frozenset(
    {
        procedure.UNCHANGED,
        procedure.CLAMPED,
        procedure.DROPPED,
        procedure.NO_EFFECT,
        procedure.INCONCLUSIVE,
    }
)


@dataclass(frozen=True)
class FeatureSet:
    """One thing an owner can do with the inverter, as the diagnosis sees it."""

    key: str
    name: str
    #: The fields its entities read and write.
    fields: tuple[str, ...]
    #: The capability that gates it, None where nothing does.
    requires: Capability | None = None
    #: Behavioural checks (`EffectResult.check`) that judge it.
    checks: tuple[str, ...] = ()
    #: Whether the restart (start/stop) judges it.
    restart: bool = False


_FORCED_CHARGING_FIELDS = tuple(
    f"forced_charging_{part}_{window}_{unit}"
    for window in (1, 2)
    for part in ("start", "end")
    for unit in ("hour", "minute")
)

FEATURE_SETS: tuple[FeatureSet, ...] = (
    FeatureSet(
        "forced_charge_discharge",
        "Forced charge and discharge",
        (
            "ems_mode_selection_raw",
            "battery_forced_charge_discharge_cmd_raw",
            "battery_forced_charge_discharge_power",
        ),
        Capability.BATTERY,
        ("forced charge", "forced discharge"),
    ),
    FeatureSet(
        "battery_soc_limits",
        "Battery state-of-charge limits",
        ("battery_min_soc", "battery_max_soc", "battery_reserved_soc_for_backup"),
        Capability.BATTERY,
        ("charge ceiling",),
    ),
    FeatureSet(
        "battery_power_limits",
        "Battery power limits",
        ("battery_max_charge_power", "battery_max_discharge_power"),
        Capability.BATTERY,
    ),
    FeatureSet(
        "battery_start_power",
        "Battery start thresholds",
        ("battery_charging_start_power", "battery_discharging_start_power"),
        Capability.BATTERY_START_POWER,
    ),
    FeatureSet(
        "export_limit",
        "Feed-in limit",
        ("export_power_limit_mode_raw", "export_power_limit"),
        None,
        ("export power limit",),
    ),
    FeatureSet(
        "pv_cut",
        "Cut PV generation",
        ("pv_generation_cut_raw",),
        Capability.PV_GENERATION_CUT,
        ("PV generation cut",),
    ),
    FeatureSet(
        "forced_charging_schedule",
        "Forced-charging schedule",
        (
            "forced_charging_raw",
            "forced_charging_days_raw",
            "forced_charging_target_soc_1",
            "forced_charging_target_soc_2",
            *_FORCED_CHARGING_FIELDS,
        ),
        Capability.FORCED_CHARGING,
        ("forced-charging window",),
    ),
    FeatureSet(
        "discharge_schedule",
        "Discharge schedules",
        tuple(probe.field for probe in procedure.DISCHARGE_WINDOW),
        Capability.DISCHARGE_SCHEDULE,
        ("discharge windows away from now",),
    ),
    FeatureSet(
        "site_import_limit",
        "Site import limit",
        (procedure.IMPORT_LIMIT.field,),
        Capability.BATTERY,
        ("site import limit",),
    ),
    FeatureSet("backup_mode", "Backup mode", ("backup_mode_raw",)),
    FeatureSet(
        "load_adjustment",
        "Load control",
        ("load_adjustment_mode_enable_raw", "load_adjustment_mode_selection_raw"),
    ),
    FeatureSet(
        "start_stop",
        "Stop and start",
        (procedure.START_WORD_PROBE.field,),
        restart=True,
    ),
)


def _block(document: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the capability test block, under either schema's key, or {}."""
    block = document.get("capability_test")
    schema = document.get("schema")
    if block is None and isinstance(schema, int) and schema < 25:
        block = document.get("control_test")
    return block if isinstance(block, Mapping) else {}


def _evidence(block: Mapping[str, Any]) -> bool:
    """Whether a block's results speak for the device at all."""
    conditions = block.get("conditions") or {}
    return (
        bool(block)
        and not conditions.get("simulated")
        and not conditions.get("dry_run")
    )


def _dumped(dump: Mapping[str, Any], field: str) -> bool:
    """Whether the raw dump holds an answer for every word of a field."""
    try:
        where = field_address(field)
    except KeyError:
        return False
    band = dump.get(where.space) or {}
    keys = [str(where.address + offset) for offset in range(where.length)]
    return all(band.get(key) is not None for key in keys)


def _readable(document: Mapping[str, Any], fields: Sequence[str]) -> bool:
    """Whether any of the fields answered, decoded or in the raw dump.

    An answer, not a capability: a dongle answers 0 where the inverter has
    nothing, which is why a read alone never says more than *readable*.
    """
    values = (document.get("readings") or {}).get("values") or {}
    dump = document.get("register_dump") or {}
    return any(
        values.get(field) is not None or _dumped(dump, field) for field in fields
    )


def _states(feature: FeatureSet, block: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Return (state, why) for every capability test result about one set."""
    direct = bool((block.get("conditions") or {}).get("direct_connection"))
    found: list[tuple[str, str]] = []
    for row in block.get("readback") or []:
        field = row.get("field")
        verdict = row.get("verdict")
        if field not in feature.fields or verdict in (None, procedure.SKIPPED):
            continue
        if verdict == procedure.REFUSED:
            found.append((REFUSED, f"{field}: {verdict}"))
        elif not direct:
            # A WiNet-S answers a written register stale: no readback through
            # one confirms or refutes anything.
            found.append((INCONCLUSIVE, f"{field}: read back through a dongle"))
        elif verdict == procedure.MATCH:
            found.append((CONFIRMED, f"{field}: read back as written"))
        elif verdict in _SCALE_FINDINGS:
            found.append((WRONG_SCALE, f"{field}: {verdict}"))
        else:
            found.append((INCONCLUSIVE, f"{field}: {verdict}"))
    for effect in block.get("effects") or []:
        check = effect.get("check")
        verdict = effect.get("verdict")
        if check not in feature.checks:
            continue
        if verdict == procedure.CONFIRMED:
            found.append((CONFIRMED, f"{check}: {verdict}"))
        elif verdict in _EFFECT_FINDINGS:
            found.append((WRONG_SCALE, f"{check}: {verdict}"))
        elif verdict in _UNSETTLED:
            found.append((INCONCLUSIVE, f"{check}: {verdict}"))
    restart = block.get("restart") or {}
    if feature.restart and restart.get("verdict") not in (None, procedure.SKIPPED):
        verdict = restart["verdict"]
        state = CONFIRMED if verdict == procedure.CONFIRMED else INCONCLUSIVE
        found.append((state, f"restart: {verdict}"))
    return found


def _strongest(found: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Return the state the evidence settles on, and the lines behind it.

    A finding outranks a confirmation: one write off by a decade is worth
    reporting even where another write of the same set matched.
    """
    order = (WRONG_SCALE, REFUSED, CONFIRMED, INCONCLUSIVE)
    for state in order:
        why = [line for s, line in found if s == state]
        if why:
            return state, why
    return NOT_READ, []


def feature_report(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return one row per feature set: its key, name, state and why."""
    block = _block(document)
    evidence = _evidence(block)
    granted = (block.get("conditions") or {}).get("capabilities") if evidence else None
    rows: list[dict[str, Any]] = []
    for feature in FEATURE_SETS:
        found = _states(feature, block) if evidence else []
        state, why = _strongest(found)
        if state == NOT_READ:
            if (
                feature.requires is not None
                and isinstance(granted, list)
                and feature.requires.value not in granted
            ):
                state = NOT_AVAILABLE
                why = [f"the integration does not grant {feature.requires.value} here"]
            elif _readable(document, feature.fields):
                state = READABLE
                why = ["its registers answered; nothing wrote to them"]
        rows.append(
            {"feature": feature.key, "name": feature.name, "state": state, "why": why}
        )
    return rows


def format_report(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Return the report as aligned lines for a terminal or a notification."""
    width = max((len(str(row["name"])) for row in rows), default=0)
    return [f"{str(row['name']).ljust(width)}  {row['state']}" for row in rows]
