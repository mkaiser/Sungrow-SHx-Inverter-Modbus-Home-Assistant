"""Constants shared by the Sungrow Modbus device library."""

from __future__ import annotations

MANUFACTURER = "Sungrow"

#: Inverter model by the code in input register 5000 (protocol address 4999).
#:
#: Checked against Appendix 1 of Sungrow's *Communication Protocol of
#: Residential and Small Industrial Hybrid Inverter* V1.1.16 (2026-07-03),
#: which lists 49 models. All 49 are here and the names agree.
#:
#: Seven entries are **not** in that appendix: the SH*K series, which protocol
#: V1.1.0 removed from the list of valid device types in 2023. They stay,
#: because the hardware is still in the field even where the current
#: specification has stopped describing it.
#:
#: **The codes are not allocated in one block per family.** An earlier version
#: of this project classified families by code range, on the stated assumption
#: that "new models land inside those blocks". V1.1.12 to V1.1.16 falsified it:
#: MG and SH*RL interleave inside 0x0D2x -- MG5RL to MG10RL at 0x0D27-0x0D2A,
#: then SH5RL to SH10RL at 0x0D2B-0x0D2E, then MG12RL again at 0x0D2F. A range
#: extended over that gap would have called four single-phase inverters
#: three-phase MG. `family_for` reads the model *name* from this table
#: instead.
DEVICE_TYPES: dict[int, str] = {
    0x0D03: "SH5K-V13",
    0x0D06: "SH3K6",
    0x0D07: "SH4K6",
    0x0D09: "SH5K-20",
    0x0D0A: "SH3K6-30",
    0x0D0B: "SH4K6-30",
    0x0D0C: "SH5K-30",
    0x0D0D: "SH3.6RS",
    0x0D0F: "SH5.0RS",
    0x0D10: "SH6.0RS",
    0x0D17: "SH3.0RS",
    0x0D18: "SH4.0RS",
    0x0D1A: "SH8.0RS",
    0x0D1B: "SH10RS",
    0x0D27: "MG5RL",
    0x0D28: "MG6RL",
    0x0D29: "MG8RL",
    0x0D2A: "MG10RL",
    # V1.1.12 onward, interleaved with the MG codes above and below.
    0x0D2B: "SH5RL",
    0x0D2C: "SH6RL",
    0x0D2D: "SH8RL",
    0x0D2E: "SH10RL",
    0x0D2F: "MG12RL",
    0x0D31: "MG7.5RL",
    0x0D41: "SH3RL",
    0x0D42: "SH3.6RL",
    0x0D43: "SH4RL",
    0x0E00: "SH5.0RT",
    0x0E01: "SH6.0RT",
    0x0E02: "SH8.0RT",
    0x0E03: "SH10RT",
    0x0E08: "SH5.0RT-V122",
    0x0E09: "SH6.0RT-V122",
    0x0E0A: "SH8.0RT-V122",
    0x0E0B: "SH10RT-V122",
    0x0E0C: "SH5.0RT-V112",
    0x0E0D: "SH6.0RT-V112",
    0x0E0E: "SH8.0RT-V112",
    0x0E0F: "SH10RT-V112",
    0x0E10: "SH5.0RT-20",
    0x0E11: "SH6.0RT-20",
    0x0E12: "SH8.0RT-20",
    0x0E13: "SH10RT-20",
    0x0E20: "SH5T",
    0x0E21: "SH6T",
    0x0E22: "SH8T",
    0x0E23: "SH10T",
    0x0E24: "SH12T",
    0x0E25: "SH15T",
    0x0E26: "SH20T",
    0x0E28: "SH25T",
    # V1.1.14 and V1.1.15. Ten MPP trackers, where every other model here has
    # two to four, and no reading from one exists -- see `Family.CX`.
    0x0E39: "SH100CX",
    0x0E3A: "SH110CX",
    0x0E3D: "SH125CX",
    0x0E51: "SH50CX",
    0x0E52: "SH80CX",
}


def model_for(device_type_code: int | None) -> str | None:
    """Return the model name for a device type code, or None if unknown."""
    if device_type_code is None:
        return None
    return DEVICE_TYPES.get(device_type_code)
