"""Which fields the procedure writes, and how it judges each write.

A field the readback walk writes (`PROBES`) is judged by its raw word against
the specification's scale. A field a behavioural check writes is judged by
what the inverter does. This module names the second set, check by check, from
the same `Probe` tables the checks write through, so a page that says what the
procedure covers cannot drift from what it does.
"""

from __future__ import annotations

from .procedure import (
    BACKUP_MODE,
    CHARGE_WINDOW,
    DISCHARGE_WINDOW,
    EMS_MODE,
    EXPORT_MODE,
    FORCED_CMD,
    FORCED_STARTUP,
    IMPORT_LIMIT,
    LOAD_ENABLE,
    LOAD_MODE,
    PROBES,
    PV_CUT,
    WEEKEND_DISCHARGE,
    WINDOW_2,
    bound_check,
    bounded_probes,
)

#: The forced charge and discharge write the EMS mode, the command and the
#: forced power; every battery check below runs through them.
_FORCED = (
    EMS_MODE.field,
    FORCED_CMD.field,
    "battery_forced_charge_discharge_power",
)

#: Behavioural check name (`EffectResult.check`) to the fields it writes.
EFFECT_FIELDS: dict[str, tuple[str, ...]] = {
    "forced charge": _FORCED,
    "forced discharge": _FORCED,
    "charge ceiling": (*_FORCED, "battery_max_soc"),
    "export power limit": (EXPORT_MODE.field, "export_power_limit"),
    "PV generation cut": (PV_CUT.field,),
    "forced-charging window": tuple(probe.field for probe in CHARGE_WINDOW),
    "discharge windows away from now": tuple(probe.field for probe in DISCHARGE_WINDOW),
    "site import limit": (*_FORCED, IMPORT_LIMIT.field),
    "forced startup under low SoC": (FORCED_STARTUP.field,),
    "charging start threshold": ("battery_charging_start_power",),
    "discharging start threshold": ("battery_discharging_start_power",),
    # The write-path checks (`writepath.py`): judged by the register's
    # answer, not by what the inverter does.
    "backup mode write path": (BACKUP_MODE.field,),
    "load control write path": (LOAD_ENABLE.field, LOAD_MODE.field),
    "weekend discharge enable write path": (WEEKEND_DISCHARGE.field,),
    "forced-charging window 2 encoding": tuple(probe.field for probe in WINDOW_2),
    "EMS mode options": (EMS_MODE.field,),
    **{bound_check(probe.field): (probe.field,) for probe in bounded_probes()},
}

#: The checks judged by a register's answer rather than by power: a write
#: taken, refused, or read back. Every one needs nothing but a run.
WRITE_PATH_CHECKS: frozenset[str] = frozenset(
    {
        "backup mode write path",
        "load control write path",
        "weekend discharge enable write path",
        "forced-charging window 2 encoding",
        "EMS mode options",
        *(bound_check(probe.field) for probe in bounded_probes()),
    }
)

#: The name a revision covers the whole readback walk by.
READBACK = "readback"

#: The name the restart's revision goes by (`ledger.RESTART`).
RESTART = "restart"

#: Which revision of its logic each check runs. **Raise a check's number with
#: any change that could change its verdict**: a kept run from an older
#: revision no longer counts as established for that check, so after an
#: update the integration measures that check again, and only that one. A run
#: from before this table counts as revision 1 throughout
#: (`ledger.run_revision`). `tests/test_capability_ledger.py` holds the keys
#: to `EFFECT_FIELDS`.
CHECK_REVISIONS: dict[str, int] = {
    READBACK: 1,
    RESTART: 1,
    "forced charge": 1,
    "forced discharge": 1,
    "charge ceiling": 1,
    "export power limit": 1,
    "PV generation cut": 1,
    "forced-charging window": 2,
    "discharge windows away from now": 1,
    "site import limit": 1,
    "forced startup under low SoC": 1,
    "charging start threshold": 1,
    "discharging start threshold": 1,
    **dict.fromkeys(WRITE_PATH_CHECKS, 1),
}

#: Every field the readback walk writes and checks by raw word.
WRITTEN: frozenset[str] = frozenset(probe.field for probe in PROBES)

#: Every field a behavioural check writes.
WATCHED: frozenset[str] = frozenset(
    field for fields in EFFECT_FIELDS.values() for field in fields
)
