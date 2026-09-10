"""The model table, pinned against Sungrow's own specification.

`DEVICE_TYPES` decides what an inverter is called and, in modern mode, what
its entities are called — so a wrong or missing entry is user-visible. This
holds it against Appendix 1 of the *Communication Protocol of Residential and
Small Industrial Hybrid Inverter* V1.1.16, transcribed below because the PDF
is not in the repository.
"""

from __future__ import annotations

from sungrow_modbus.const import DEVICE_TYPES, model_for

#: Appendix 1, "Adaptive Inverter Models", V1.1.16 (2026-07-03). All 49.
#:
#: Note the ordering of the 0x0D2x block: the MG codes are **interrupted** by
#: SH5RL to SH10RL and resume above them. That is what falsified the
#: code-range family classifier this table's consumer used to have, so the
#: transcription keeps the specification's own order rather than sorting it.
SPECIFICATION = {
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
    0x0E39: "SH100CX",
    0x0E3A: "SH110CX",
    0x0E3D: "SH125CX",
    0x0E51: "SH50CX",
    0x0E52: "SH80CX",
}

#: Removed from the specification by protocol V1.1.0 in 2023, but still real
#: hardware. Anything else appearing as an extra is a mistake, not a decision.
DELIBERATE_EXTRAS = {
    0x0D03: "SH5K-V13",
    0x0D06: "SH3K6",
    0x0D07: "SH4K6",
    0x0D09: "SH5K-20",
    0x0D0A: "SH3K6-30",
    0x0D0B: "SH4K6-30",
    0x0D0C: "SH5K-30",
}


def test_every_model_in_the_specification_is_known() -> None:
    missing = {c: n for c, n in SPECIFICATION.items() if c not in DEVICE_TYPES}
    assert not missing, f"models in V1.1.16 that DEVICE_TYPES does not know: {missing}"


def test_names_agree_with_the_specification() -> None:
    disagree = {
        code: (DEVICE_TYPES[code], name)
        for code, name in SPECIFICATION.items()
        if DEVICE_TYPES.get(code) != name
    }
    assert not disagree, f"(ours, spec) disagreements: {disagree}"


def test_extras_are_only_the_withdrawn_k_series() -> None:
    extras = {c: n for c, n in DEVICE_TYPES.items() if c not in SPECIFICATION}
    assert extras == DELIBERATE_EXTRAS, (
        "a model outside the specification was added without recording why"
    )


def test_the_reference_inverter_resolves() -> None:
    # The code read from the maintainer's SH10RT.
    assert model_for(0x0E03) == "SH10RT"
    assert model_for(None) is None
    assert model_for(0xBEEF) is None
