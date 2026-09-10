"""Correcting for a generator Sungrow cannot see.

A non-Sungrow inverter on the same supply is invisible to the Sungrow, and
that is not a cosmetic gap: it makes a **published reading wrong**, silently
and plausibly.

**Why the load reading is wrong.** The inverter does not measure house load;
it computes it, from its own AC output and its grid meter:

    reported load = inverter output + grid import

which is right when the inverter is the only generator. Put a Fronius, a
SolarEdge or a microinverter behind the same meter and the true load is

    true load = inverter output + grid import + foreign production

so the reported figure is **low by exactly the foreign production**, and goes
**negative** once that production exceeds what the house is using. Nothing in
the register map hints at this; the number looks like a measurement because
every input to it was one.

So the correction is a sum, and this module exists for the two decisions
around it rather than the arithmetic:

**Where the foreign inverter sits changes the arithmetic**, which is why the
options flow asks instead of guessing. Behind the same meter its output
offsets grid import and the load figure needs correcting. Separately metered
-- its own supply point, its own meter -- none of it flows through the
Sungrow's meter, the load figure is already right for the supply it describes,
and correcting it would introduce the error rather than remove it. That is
why `corrected_load_power` is not created at all in the separately-metered
case: an entity that is knowingly a copy of another is worse than no entity.

**A missing source makes the answer unknown, not zero.** Treating an
unavailable generator as producing nothing gives back exactly the error this
module removes -- a load figure too low by whatever it was making -- and it
would be indistinguishable from a correct reading. So one silent source makes
the corrected value unknown, and the entity says which source it was.

The cost is real and worth stating: a PV integration that reports
`unavailable` overnight rather than `0 W` takes the corrected entities to
unknown overnight with it. That is the honest report -- nothing here knows the
sun is down -- and the options flow says so, because picking a source that
reports zero is the fix and only the owner can do it.

This module reads other integrations' entities, which the register library
deliberately cannot do. That makes it the one place in this integration where
a value comes from Home Assistant rather than from Modbus, and the reason it
lives here and not in `sungrow_modbus`.
"""

from __future__ import annotations

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.unit_conversion import PowerConverter


def external_power(
    hass: HomeAssistant, entity_ids: tuple[str, ...] | list[str]
) -> tuple[float | None, tuple[str, ...]]:
    """Return the total foreign generation in watts, and what did not answer.

    `(watts, ())` when every named source reported a number, and
    `(None, ("sensor.x", …))` when any did not -- never a partial sum. See
    the module docstring: a partial sum is the original error wearing the
    shape of a measurement.

    An empty list of sources is a total of zero rather than unknown. Nothing
    is being corrected for, which is a known quantity.
    """
    total = 0.0
    missing: list[str] = []
    for entity_id in entity_ids:
        watts = _watts(hass.states.get(entity_id))
        if watts is None:
            missing.append(entity_id)
            continue
        total += watts
    if missing:
        return None, tuple(missing)
    return total, ()


def _watts(state: State | None) -> float | None:
    """Return one source's reading in watts, or None if it is not usable.

    The unit is **required**, not assumed. A power sensor is very likely in W
    or kW and guessing between them is an error of 1000x that would look
    entirely plausible in the corrected figure -- the one failure mode this
    whole module exists to prevent. A source whose unit is missing or is not
    a power unit therefore counts as not reporting, and is named as such
    rather than quietly dropped.
    """
    if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, ""):
        return None
    try:
        value = float(state.state)
    except (TypeError, ValueError):
        return None
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    if unit == UnitOfPower.WATT:
        return value
    try:
        return PowerConverter.convert(value, unit, UnitOfPower.WATT)
    except (HomeAssistantError, TypeError):
        return None


def combined(base: float | None, external: float | None) -> float | None:
    """Add the foreign production to a Sungrow reading, or return None.

    Both corrections are this addition, which is worth saying plainly because
    the two entities read as different ideas: house load is understated by the
    foreign production, and site production simply omits it. Same sum.

    The sign convention, stated so a test can hold it: `load_power` is
    positive when the house consumes, a generation sensor is positive when it
    generates, and a house making more than it uses lands at a **negative**
    corrected load -- which is a true statement about the supply and is left
    alone. Clamping it at zero would hide the very condition that tells an
    owner their generator is unmetered.
    """
    if base is None or external is None:
        return None
    return base + external
