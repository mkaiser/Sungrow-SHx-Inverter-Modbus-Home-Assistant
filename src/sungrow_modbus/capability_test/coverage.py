"""Which fields the procedure writes, and how it judges each write.

A field the readback walk writes (`PROBES`) is judged by its raw word against
the specification's scale. A field a behavioural check writes is judged by
what the inverter does. This module names the second set, check by check, from
the same `Probe` tables the checks write through, so a page that says what the
procedure covers cannot drift from what it does.
"""

from __future__ import annotations

from .procedure import (
    CHARGE_WINDOW,
    DISCHARGE_WINDOW,
    EMS_MODE,
    EXPORT_MODE,
    FORCED_CMD,
    FORCED_STARTUP,
    IMPORT_LIMIT,
    PROBES,
    PV_CUT,
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
}

#: Every field the readback walk writes and checks by raw word.
WRITTEN: frozenset[str] = frozenset(probe.field for probe in PROBES)

#: Every field a behavioural check writes.
WATCHED: frozenset[str] = frozenset(
    field for fields in EFFECT_FIELDS.values() for field in fields
)
