"""Sensor descriptions for the inverter's energy history, one per month and year.

Source, edited by hand: built rather than written out, because eighty-one
typed entries is where a wrong month would hide. The registers are
`_energy_history`'s (`sungrow_modbus.hybrid_inverter.registers`), read over
the inverter's own LAN port only; the wiki's energy-history page has what
they hold. A month is this calendar year's, and starts again at the new year.

The YAML package had the months and the years 2019 on of PV generation and
export until 2025-11-10; those keep its ids. A year is created only where the
inverter holds something for it (`sensor._year_holds_something`).

From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT),
where `doc/architecture.md` records which document or measurement each
register comes from. Keep this line with any copy -- `doc/attribution.md`.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory
from sungrow_modbus import Capability
from sungrow_modbus.hybrid_inverter.registers import HISTORY_FIRST_YEAR, HISTORY_YEARS

from .entity import SungrowSensorDescription

#: English on purpose and not `calendar.month_name`, which follows the locale:
#: the YAML package's ids are English.
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

#: Quantity -> the YAML package's monthly and yearly names and unique ids, and
#: the years it had; None where it had none.
QUANTITIES: dict[str, tuple[str, str, str, str, range] | None] = {
    "pv_generation": (
        "Monthly PV generation",
        "sg_monthly_pv_generation",
        "Yearly PV generation",
        "sg_yearly_pv_generation",
        range(2019, 2030),
    ),
    "direct_consumption": None,
    "export_from_pv": (
        "Monthly export",
        "sg_monthly_export",
        "Yearly Export",
        "sg_yearly_export",
        range(2019, 2029),
    ),
}


def _description(
    quantity: str, key: str, field: str, legacy: tuple[str, str] | None
) -> SungrowSensorDescription:
    return SungrowSensorDescription(
        key=key,
        component=f"{quantity}_history",
        field=field,
        translation_key=key,
        legacy_name=None if legacy is None else legacy[0],
        legacy_unique_id=None if legacy is None else legacy[1],
        legacy_platform=None if legacy is None else "modbus",
        entity_category=EntityCategory.DIAGNOSTIC,
        requires=Capability.ENERGY_HISTORY,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="kWh",
        suggested_display_precision=1,
    )


def _all() -> tuple[SungrowSensorDescription, ...]:
    out: list[SungrowSensorDescription] = []
    for quantity, old in QUANTITIES.items():
        for number, month in enumerate(MONTHS, start=1):
            legacy = None
            if old is not None:
                legacy = (
                    f"{old[0]} ({number:02d} {month})",
                    f"{old[1]}_{number:02d}_{month.lower()}",
                )
            out.append(
                _description(
                    quantity,
                    f"{quantity}_month_{number}",
                    f"{quantity}_month_{number:02d}",
                    legacy,
                )
            )
        for year in range(HISTORY_FIRST_YEAR, HISTORY_FIRST_YEAR + HISTORY_YEARS):
            legacy = None
            if old is not None and year in old[4]:
                legacy = (f"{old[2]} ({year})", f"{old[3]}_{year}")
            out.append(
                _description(
                    quantity,
                    f"{quantity}_year_{year}",
                    f"{quantity}_year_{year}",
                    legacy,
                )
            )
    return tuple(out)


HISTORY_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = _all()

#: The year each yearly entity stands for, by key.
YEAR_OF: dict[str, int] = {
    d.key: int(d.key.rpartition("_")[2])
    for d in HISTORY_DESCRIPTIONS
    if "_year_" in d.key
}
