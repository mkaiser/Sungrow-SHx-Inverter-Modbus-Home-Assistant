"""A Sungrow Logger's identity block, the only part of it mapped here.

Sungrow documents its Loggers in *Logger Communication Protocol* (AW0,
1.0.2.5 to 1.0.2.9), which this repository has not read: the copies found
are behind a login. So nothing here is **spec**. The identity block is what
two independent maps agree on -- Voyanti/ha-sungrow, which cites the
document, and RafAustralia's Logger1000A YAML from discussion #262 -- and it
has the iHomeManager's layout, which is the same protocol family:

* input 8000, the device type code, which names the model (`MODELS`);
* 8001-8002, the protocol number, as text;
* 8003-8004, the protocol version;
* 8005 and 8006, devices connected and devices in fault.

Everything else a Logger answers is published raw by the survey, the way the
wallbox's map began: the first reading is the map. A Logger also gives each
inverter and meter behind it a unit id of its own on the same endpoint;
those are surveyed as what they are, not from here.

Read only. Two people report writes to a Logger failing; nothing here tries.
"""

from __future__ import annotations

from modbus_connection.model import Component, integer, string, uint32

from ..addresses import reg

#: Where a Logger answers on its own endpoint.
UNIT = 247

#: Which Logger a type code at input 8000 names.
MODELS: dict[int, str] = {
    0x0705: "Logger3000",
    0x0710: "Logger1000",
    0x0718: "Logger4000",
}


class LoggerIdentity(Component):
    """What it is and how many devices it fronts. Named elsewhere, not spec."""

    register_space = "input"

    device_type_code = integer(reg(8000), signed=False)
    protocol_number = string(reg(8001), 2)
    protocol_version_raw = uint32(reg(8003), word_order="little", nan=0xFFFFFFFF)
    connected_devices = integer(reg(8005), signed=False, nan=0xFFFF)
    devices_in_fault = integer(reg(8006), signed=False, nan=0xFFFF)


#: The components, by the name a document groups them under.
COMPONENTS: dict[str, type[Component]] = {"identity": LoggerIdentity}

#: Every field rests on two community maps, none on a document read here.
CONFIDENCE: dict[str, str] = {
    name.removesuffix("_raw"): "named elsewhere"
    for component in COMPONENTS.values()
    for name in component.declared_fields
}
