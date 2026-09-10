"""The two entities that exist only when another inverter shares the supply.

Fourth hand-written description module, and the reason is new: these are not
registers. `sensor_descriptions.py` is generated from the YAML package's
entity map, the battery's and the wallbox's are hand-written because the
package never covered those devices -- but all three describe something a
Modbus read returns. These describe **arithmetic over another integration's
entities**, so there is nothing to generate them from and no register behind
them. `external.py` has the reasoning and the sign convention.

**Why only two, and no kWh.** The temptation is a matching pair of energy
totals, and it is the wrong instinct: Home Assistant's Energy dashboard
already accepts **several solar sources**, so a household with a Fronius
beside a Sungrow adds both there and gets a correct total with no help from
this integration. Inventing `total_site_pv_energy` would put a second,
divergent answer next to the one the dashboard already computes -- and it
would have to survive restarts and unavailable sources to be trustworthy,
which a summed power reading does not.

Power is different, because nothing in Home Assistant corrects a *load*
figure that another integration computed wrongly. That is the gap here.

**Neither has a legacy id, and neither should.** The YAML package had no
concept of a foreign inverter, so no history is attached to either name and
`legacy_only` never applies. They are also the only entities in this
integration whose existence depends on an **option** rather than on what the
hardware answered, which is why `sensor.py` gates them on the runtime data
rather than on a `Capability`.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower

from .entity import SungrowExternalSensorDescription

EXTERNAL_SENSORS: tuple[SungrowExternalSensorDescription, ...] = (
    # The reason this milestone exists. `load_power` is computed by the
    # inverter from its own output and its grid meter, so a generator behind
    # the same meter makes it low by exactly that generator's output -- and
    # negative once the generator outproduces the house. Not clamped at
    # zero: a persistently negative load is the signature of unmetered
    # generation and worth seeing.
    SungrowExternalSensorDescription(
        key="corrected_load_power",
        component="realtime_input",
        field="load_power",
        depends_on=("load_power",),
        translation_key="corrected_load_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        behind_meter_only=True,
    ),
    # What the whole site is generating. `total_dc_power` is measured on the
    # Sungrow's **DC** side while a foreign inverter almost certainly reports
    # its **AC** output, so the two halves are not measured at the same
    # point and the sum runs a few percent high on the Sungrow half. Said
    # here rather than corrected: an inverter efficiency this integration
    # would have to invent is a worse error than a documented one, and no
    # register reports it.
    SungrowExternalSensorDescription(
        key="total_site_pv_power",
        component="fast_input",
        field="total_dc_power",
        depends_on=("total_dc_power",),
        translation_key="total_site_pv_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
)
