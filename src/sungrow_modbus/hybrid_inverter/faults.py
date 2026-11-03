"""What the inverter's fault and alarm words say, bit by bit.

Fifteen U32s at input 13050-13079, each a set of flags, and Appendix 4 of
Sungrow's *Communication Protocol of Residential Hybrid Inverter* (V1.1.11)
names every bit. The table below is that appendix, transcribed by script
from the published document rather than typed, with the bits it calls
"Reserved" left out -- a reserved bit that reads set is not a fault anybody
can name, and the high word of BMS alarm 2 reads 0xFFFF on every cable
surveyed, which would otherwise be sixteen alarms that do not exist.

The words are sent low word first, like every other 32-bit value here, and
one survey shows it rather than assumes it: fwitten's slave inverter, which
has no meter of its own, reads 0x4000 in the **high** word of the inverter
alarm on both its cable and its dongle -- bit 30, "Meter Communication
Alarm".

Two kinds, because they ask for different things of an owner: an **alarm**
is a warning the inverter runs through, a **fault** (protections included)
is the inverter or the pack stopping something. The BMS words are the
battery's own, forwarded by the inverter (the specification's note 2).

No entity per bit. About two hundred named flags, nearly all of them zero
for the life of an installation, do not belong in anybody's entity list; a
word is one sensor counting its set flags and naming them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, NamedTuple

from ..addresses import reg

Kind = Literal["alarm", "fault"]

#: A whole word of ones is the specification's "unavailable", not 32 flags.
UNAVAILABLE = 0xFFFFFFFF


class FaultWord(NamedTuple):
    """One of the fifteen words: where it is, what kind, and its named bits."""

    field: str
    name: str
    address: int
    """The protocol address, from `reg()` -- one below Sungrow's number."""
    kind: Kind
    bits: Mapping[int, str]


FAULT_WORDS: tuple[FaultWord, ...] = (
    FaultWord(
        "inverter_alarm",
        "Inverter alarm",
        reg(13050),
        "alarm",
        {
            0: "Fan Alarm",
            1: "Lightning Protection Alarm on AC Side",
            2: "Lightning Protection Alarm on DC Side",
            3: "Bypass Switch Abnormal",
            4: "Communication Alarm",
            5: "Parallel Communication Alarm",
            6: "Device Abnormality",
            7: "Junction Box leakage Protector Alarm",
            8: "PV1 Abnormal Warn",
            9: "PV2 Abnormal Warn",
            10: "PV3 Abnormal Warn",
            11: "PV4 Abnormal Warn",
            12: "Fan 2 Rotate Low Speed Alarm",
            13: "Fan 2 Stall Alarm",
            14: (
                "The energy meter input and output ports are reversed, "
                "or the meter is connected to other wrong terminals"
            ),
            15: "Software Version Mismatch",
            16: "SPD or Fuse Alarm",
            17: "FRAM Read Alarm",
            18: "SPI Com Alarm",
            19: "Ambient Temperature Sensor Open Circuit Alarm",
            20: "Ambient Temperature Sensor Short Circuit Alarm",
            21: "Inversion T Sensor Open Circuit Alarm",
            22: "Inversion T Sensor Short Circuit Alarm",
            23: "Boost T Sensor Open Circuit Alarm",
            24: "Boost T Sensor Short Circuit Alarm",
            25: "Input Cfg Alarm In DC Source Mode Or Clock Reset Abnormal Alarm",
            26: "PV HV Flt",
            27: "Ambient Low Temperature Sensor Open Circuit Alarm",
            28: "Fan 1 Low Rotation Speed Alarm",
            29: "Fan 1 Stall Alarm",
            30: "Meter Communication Alarm",
            31: "BOOST Short Circuit Alarm",
        },
    ),
    FaultWord(
        "grid_side_fault",
        "Grid-side fault",
        reg(13052),
        "fault",
        {
            0: "Grid Overvoltage",
            1: "Grid Transient V-over",
            2: "Grid Under-voltage",
            3: "Grid V-low",
            5: "AC C-over",
            6: "Grid Over-frequency",
            7: "Grid Under-frequency",
            8: "Grid Power Outage",
            9: "Device Abnormality",
            10: "Excessive Leakage Current",
            11: "Grid Abnormal",
            12: "10 Minutes Grid Overvoltage",
            13: "High Grid Voltage",
            14: "Output Overload",
            15: "Grid Voltage Imbalance",
            16: "Inversion C-over Hardware Flt",
            17: "High Grid Frequency",
            18: "Grid F-low",
            19: "V-Grid Uniform Fault",
            20: "Grid Frequency Uniform Fault",
            21: "Network Side Protection Self-test Failed",
            22: "Grounding Cable Fault",
            23: "Inversion V DC Ject V-over Flt",
            24: "AC Side Under-voltage",
            25: "AC Side Overvoltage",
            26: "AC Side Under-frequency",
            27: "AC Side Over-frequency",
            28: "Vac Unbal",
            29: "Bypass Instantaneous Overcurrent",
            30: "Bypass Switch Over Current",
        },
    ),
    FaultWord(
        "system_fault_1",
        "System fault 1",
        reg(13054),
        "fault",
        {
            0: "Inversion Switch Tube Over-temperature",
            1: "BOOST Switch Tube T-over",
            2: "PV IR Flt",
            3: "Bypass Switch Fault",
            4: "EPS Relay Failure",
            5: "Junction Box Relay Fault",
            6: "Input and Output Mismatch Fault",
            7: "PV HV P-over Alarm or Prot",
            8: "Redundancy Fault",
            9: "R-phase inverter voltage sampling channel abnormal",
            10: "S-phase inverter voltage sampling channel abnormal",
            11: "T-phase inverter voltage sampling channel abnormal",
            12: "R-phase DC component sampling channel abnormal",
            13: "S-phase DC component sampling channel abnormal",
            14: "T-phase DC component sampling channel abnormal",
            15: "PV 1 current sampling channel abnormal",
            16: "PV 2 current sampling channel abnormal",
            17: "PV 1 MPPT current sampling channel abnormal",
            18: "PV 2 MPPT current sampling channel abnormal",
            19: "Control Board Power Supply Under-voltage Fault",
            20: "Leak Current CT Self-detection Fault",
            21: "SPI Com Flt",
            22: "LCD and Main DSP Communication Fault",
            24: "PV3 current sampling channel failure",
            25: "N-wire current sampling channel abnormal",
            26: "Balance bridge current sampling channel abnormal",
        },
    ),
    FaultWord(
        "system_fault_2",
        "System fault 2",
        reg(13056),
        "fault",
        {
            0: "Module Over-temperature",
            1: "Excessively High Ambient Temperature",
            2: "Device Abnormality",
            3: "Low System Insulation Resistance",
            4: "Device Abnormality",
            5: "Device Abnormality",
            6: "Device Abnormality",
            7: "Low Ambient Temperature",
            8: "Device Abnormality",
            9: "Device Abnormality",
            10: "Device Abnormality",
            11: "Input Configuration Abnormality",
            12: "Device Abnormality",
            13: "Device Abnormality",
            14: "Device Abnormality",
            15: "Backup Load Overpower Fault",
        },
    ),
    FaultWord(
        "dc_side_fault",
        "DC-side fault",
        reg(13058),
        "fault",
        {
            0: "Device Abnormality",
            1: "Device Abnormality",
            2: "Device Abnormality",
            3: "Device Abnormality",
            4: "PV Access Failure",
            5: "Device Abnormality",
            6: "Device Abnormality",
            9: "PV1 Reverse Connection Fault",
            10: "PV2 Reverse Connection Fault",
            11: "Device Abnormality",
            12: "Device Abnormality",
            13: "Device Abnormality",
            14: "Device Abnormality",
            15: "Device Abnormality",
            16: "Bus Overvoltage Hardware Fault",
            17: "Busbar Average Under-voltage",
            18: "PV Hardware Overcurrent Fault",
            19: "PV Voltage Exceeds Bus Voltage",
            20: "BOOST1 Short Circuit Fault",
            21: "BOOST2 Short Circuit Fault",
            22: "DC C-over",
            23: "PV3 Overcurrent",
            24: "PV3 Reverse Connection Fault",
            25: "BOOST3 short circuit fault",
            26: "Half-bus overvoltage hardware fault",
            27: "Balance bridge overcurrent hardware fault",
            28: "PV4 Reverse Connection Fault",
        },
    ),
    FaultWord(
        "permanent_fault",
        "Permanent fault",
        reg(13060),
        "fault",
        {
            0: "PV Overcurrent Permanent Fault",
            1: "Inversion Overcurrent Permanent Fault",
            2: "High DC Injection Permanent Fault",
            3: "Bus V-over Perm. Flt",
            4: "Relay Perm Fault",
            5: "PV1 Self-check Permanent Fault",
            6: "PV2 Self-check Permanent Fault",
            7: "Inversion Open-loop Self-detection Perm. Flt",
            8: "Entire Temperature Sensor Failure",
            9: "BOOST3 open-loop self-check permanent fault",
            10: "Balance bridge overcurrent permanent fault",
            11: "Half-bus overvoltage permanent fault",
        },
    ),
    FaultWord(
        "bdc_side_fault",
        "BDC-side fault",
        reg(13062),
        "fault",
        {
            0: "BDC Charge Transient I-over",
            1: "BDC Discharge Transient I-over",
            2: "Clamping Capacitance V-low Fault",
            3: "Clamping Capacitance Transient V-over",
            5: "Battery Pre-charge Relay Failure",
            8: "BDC Self-detect Flt",
            12: "BDC T-over Flt",
            16: "BDC Hardware I-over",
            20: "BDC Current Sampling Channel Abnormality",
            22: "Leakage Current Sampling Channel Abnormality",
            23: "Secondary DSP Communication Fault",
            24: "BDC Soft Start Flt",
        },
    ),
    FaultWord(
        "bdc_side_permanent_fault",
        "BDC-side permanent fault",
        reg(13064),
        "fault",
        {
            0: "BDC I-over Perm. Flt",
            2: "Battery Overvoltage Permanent Fault",
            4: "BDC Self-detect Permanent Flt",
            7: "BDC Soft Start Perm. Flt",
        },
    ),
    FaultWord(
        "battery_fault",
        "Battery fault",
        reg(13066),
        "fault",
        {
            3: "Battery Average Under-voltage Fault",
            7: "Battery Over-temperature Fault",
            8: "Battery Low Temperature Fault",
            11: "Battery Transient Overvoltage",
            12: "Battery Average Overvoltage Fault",
            14: "BMS Communication Fault",
            15: "Battery Hardware Overvoltage",
            16: "Abnormal Battery Connection(Reversed Polarity)",
            17: "BMS and Battery Fault",
        },
    ),
    FaultWord(
        "battery_alarm",
        "Battery alarm",
        reg(13068),
        "alarm",
        {
            0: "BDC T Sensor Open Circuit Alarm",
            1: "BDC T Sensor Short Circuit Alarm",
        },
    ),
    FaultWord(
        "bms_alarm",
        "BMS alarm",
        reg(13070),
        "alarm",
        {
            0: "Overvoltage Alarm",
            1: "Over-temperature Alarm",
            2: "Low Temperature Alarm",
            3: "Charge/Discharge Overcurrent Alarm",
            5: "Battery Voltage Unbalance",
            7: "Under-voltage Alarm",
            8: "Abnormal SD Card",
            9: "Cell Voltage Imbalance Alarm",
            10: "Cell Temperature Difference Alarm",
            11: "Battery Module Inconsistency Alarm",
            12: "Mixed Cell Alarm",
        },
    ),
    FaultWord(
        "bms_protection",
        "BMS protection",
        reg(13072),
        "fault",
        {
            0: "Overvoltage Protection",
            1: "Over-temperature Protection",
            2: "Low Temperature Protection",
            3: "Charge/Discharge Overcurrent Protection",
            4: "Over Charge Power Limit Fault",
            5: "Over Discharge Power Limit Fault",
            7: "Low Voltage Protection",
            8: "Slave Battery Fault",
            9: "Pre-Charge Failed",
            10: "Abnormal External Power Line Status",
            11: "Current Sampling Fault",
            12: "Temperature Sampling Fault",
            13: "Voltage Sampling Fault",
            14: "Battery Internal Communication Failure",
            15: "DC Contactor Failure",
        },
    ),
    FaultWord(
        "bms_fault_1",
        "BMS fault 1",
        reg(13074),
        "fault",
        {
            0: "FET Failure/Battery Switch Failure",
            1: "Failure in Battery Internal Hardware",
            2: "Overcurrent Fault",
            3: "Battery Short Circuit Fault",
            4: "Internal Communication Fault",
            5: "Input Overvoltage",
            7: "Software Version Mismatch Fault",
            8: "Heating Alarm",
            9: "Heating Circuit Abnormal",
            12: "Battery Self-test Fault",
        },
    ),
    FaultWord(
        "bms_fault_2",
        "BMS fault 2",
        reg(13076),
        "fault",
        {},  # every bit reserved
    ),
    FaultWord(
        "bms_alarm_2",
        "BMS alarm 2",
        reg(13078),
        "alarm",
        {
            0: "BMS Internal Alarm",
        },
    ),
)

#: The words by the field name the register map gives them.
BY_FIELD: dict[str, FaultWord] = {word.field: word for word in FAULT_WORDS}


def active(field: str, value: int | None) -> tuple[str, ...] | None:
    """Return the named flags set in one word, in bit order, or None.

    None for a word that was not read or reads the unavailable sentinel. A
    label the appendix gives to several bits ("Device Abnormality") is
    listed once.
    """
    if value is None or value == UNAVAILABLE:
        return None
    labels: list[str] = []
    for bit, label in BY_FIELD[field].bits.items():
        if value >> bit & 1 and label not in labels:
            labels.append(label)
    return tuple(labels)


def reported(kind: Kind, values: Mapping[str, int | None]) -> bool | None:
    """Return whether any word of this kind has a named flag set.

    None when no word of the kind could be read at all, which is a different
    claim from "nothing is wrong".
    """
    flags = [
        active(word.field, values.get(word.field))
        for word in FAULT_WORDS
        if word.kind == kind
    ]
    known = [found for found in flags if found is not None]
    if not known:
        return None
    return any(known)
