#!/usr/bin/env python3
"""Build the compatibility table from the diagnoses users have sent in.

Which parts of the register map a device answers varies by model, phase count,
wiring, transport and firmware. That cannot be derived from a document — the
specification says what exists, not what a particular machine does with it —
so the only honest source is a diagnosis from real hardware.

This turns [device-diagnosis/](../device-diagnosis/) into a table. It is
generated rather than maintained by hand for the usual reason: a table typed
twice disagrees with itself, and this one is meant to be somebody's answer to
"will it work with mine?".

**It only ever reports what a diagnosis actually contains.** A model with no
diagnosis is listed as untested rather than assumed to work, because
"probably fine" is exactly the claim that wastes a user's evening.

    python scripts/generate/generate_compatibility.py            # write the page
    python scripts/generate/generate_compatibility.py --check    # fail if it is stale
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from sungrow_modbus import DEVICE_TYPES, family_for, known_absent

REPO = Path(__file__).resolve().parents[2]
DOCUMENTS = REPO / "device-diagnosis" / "results" / "inverter"
SG_DOCUMENTS = REPO / "device-diagnosis" / "results" / "string_inverter"

from sungrow_modbus.diagnosis_document import REPORTED_TRANSPORTS  # noqa: E402
from sungrow_modbus.string_inverter import MODELS as SG_MODELS  # noqa: E402
from sungrow_modbus.string_inverter.registers import COMPONENTS as SG_COMPONENTS  # noqa: E402


def _connection_cell(connection: dict, user_inputs: dict) -> str:
    """Return the transport, short enough for a table cell.

    A contributor's `--transport` outranks the measured verdict and is marked
    as reported, so the distinction survives into the table. It has to
    outrank it for one thing the measurement cannot reach at all: a WiNet-S
    answers identically wired and over WiFi, so only a person can say which.

    Taken from `user_inputs` since schema 5 gathered every claim there, and
    from the connection block for documents written before that.

    A proxy in the path is noted here rather than given a column of its own,
    because it is a property of the *reading* and this is the column about how
    the reading was made. It belongs in the table at all because it changes how
    the rest of the row should be read: a proxy holds one connection to the
    inverter and lends it out, so blocks that never drop describe the proxy,
    and it rebuilds every frame, which can hide or create a length quirk.
    """
    reported = str(
        user_inputs.get("transport") or connection.get("reported_by_hand") or ""
    )
    if reported in REPORTED_TRANSPORTS and REPORTED_TRANSPORTS[reported].table:
        cell = f"{REPORTED_TRANSPORTS[reported].table} (reported)"
    else:
        verdict = str(connection.get("verdict", "") or "")
        if verdict.startswith("direct"):
            cell = "direct LAN port"
        elif verdict.startswith(
            ("through a communication module", "through a WiNet-S")
        ):
            cell = "WiNet-S / Logger"
        elif verdict.startswith("not determinable"):
            cell = "not determinable"
        else:
            cell = verdict or "—"

    if user_inputs.get("modbus_proxy") == "yes":
        cell += ", **via a Modbus proxy**"
    return cell


OUTPUT = REPO / "doc" / "compatibility.md"

#: Diagnosis register labels that answer a question a user actually asks,
#: and the column each becomes. Anything else in a diagnosis is detail for
#: the capability model rather than for this table.
COLUMNS: tuple[tuple[str, str], ...] = (
    ("Phases", "output type (5002)"),
    ("MPPT3", "MPPT3 voltage"),
    ("MPPT4", "MPPT4 voltage"),
    ("Battery", "battery level"),
    ("Sungrow battery", "unit 200 SBR battery module block"),
    ("Meter direct", "meter phase A voltage (5741)"),
    ("Firmware block", "firmware block (13250, spec V1.1.7+)"),
    ("PV power limit", "PV power limitation (13018, V1.1.10+)"),
)

MARKS = {"present": "yes", "unavailable": "no", None: "—"}

#: Columns whose "yes" is not to be trusted from a reading taken through a
#: communication module. A WiNet-S answers **0** where the inverter answers
#: the specification's 0xFFFF, which reads as a capability the machine does
#: not have. On gerd's SH8.0RT-V112, over its own LAN port, MPPT3, MPPT4 and
#: all four meter-channel-2 powers are unavailable; through its dongle,
#: minutes later, the same eight fields come back as zero. Both readings are
#: in `device-diagnosis/`, and without this the table would say the machine
#: has MPPT3 and MPPT4 on one row and does not on the other, with nothing to
#: say which to believe.
ZERO_MEANS_ABSENT_COLUMNS = ("MPPT3", "MPPT4", "Meter direct")

#: Columns whose "yes" is a zero, and therefore a no, whatever the transport.
#:
#: `Battery` is the one, and it is a different problem from the footnote
#: above. That one is about a *dongle* answering 0 for something absent, and
#: it is marked rather than resolved because a real tracker also reads 0 at
#: night. This one is about a **cluster slave**, which fills its own battery
#: block with 0x0000 because the battery belongs to the master -- and it does
#: so on its own LAN port, so the through-a-module test does not catch it.
#:
#: fwitten's second inverter is the case: without this the table says
#: `Battery: yes` while the *filename* of the same document says
#: `battery-none`. The filename's battery word (`diagnosis_document._battery_word`)
#: tests for all-zero, because "a zero decodes as a value and would otherwise
#: be read as evidence of a third-party pack"; this table has to agree.
#:
#: Unlike the dongle case there is no ambiguity to footnote. A battery reading
#: 0 V *and* 0% *and* 0 degrees is not a battery at nightfall; it is a device
#: telling you it has none. All three are required, so a real pack that
#: happens to sit at 0% keeps its yes.
ALL_ZERO_MEANS_ABSENT: dict[str, tuple[str, ...]] = {
    "Battery": ("battery level", "battery voltage", "battery temperature"),
}

#: What such a cell says instead. A footnote rather than a "no", because this
#: is not a reading of absence -- it is a reading that cannot distinguish.
UNTRUSTWORTHY = "yes?[^dongle]"


def _short_firmware(version: str) -> str:
    """Drop the hardware platform from a firmware string.

    `SAPPHIRE-H_B001.V000.P022` becomes `B001.V000.P022`. The platform is
    already implied by the model in the same row, and repeating it makes the
    cell wide enough to wrap.

    **Any platform, not a named one.** This matched one platform literally
    until the first non-RT diagnosis arrived: the SH20T of
    [#772](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/772)
    is a `PEARL-H` machine, and its version sailed through unshortened while
    every other row was trimmed -- which reads as a difference in the data
    rather than in this function.
    """
    prefix, separator, rest = version.partition("_")
    return rest if separator and prefix.isupper() else version


def _reports() -> list[tuple[str, dict]]:
    """Return (label, document) for every committed diagnosis."""
    documents = [
        (path.stem, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(DOCUMENTS.glob("*.json"))
    ]
    # A wallbox read at its own address has no `device` to put in a row.
    return [(stem, d) for stem, d in documents if d.get("document") != "wallbox"]


#: The SG blocks a user asks about, the column each becomes, and the fields
#: that answer it ("" for every field in the block).
SG_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("PV and AC", "sg_realtime", ""),
    ("Meter block", "sg_meter", ""),
    ("MPPT4 and up", "sg_trackers", "mppt"),
    ("Precise totals", "sg_precision", ""),
    ("Power limitation (read)", "sg_power_limit", ""),
)


def _sg_reports() -> list[tuple[str, dict]]:
    """Return (label, document) for every committed SG diagnosis."""
    return [
        (path.stem, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(SG_DOCUMENTS.glob("*.json"))
    ]


def _sg_mark(document: dict, component: str, prefix: str) -> str:
    """Return what one SG block did: answered, answered only zeros, or not.

    "0 only" is kept apart from "yes" because an SG answers 0 where the
    source promises the unavailable value (meter, trackers past its own), and
    a zero is not evidence of a capability.
    """
    section = document.get("string_inverter") or {}
    block = SG_COMPONENTS[component]
    fields = {
        name: field
        for name, field in block.declared_fields.items()
        if name.startswith(prefix)
    }
    words = (section.get("register_dump") or {}).get(block.register_space) or {}
    if any(
        words.get(str(field.address + i)) is None
        for field in fields.values()
        for i in range(field.count)
    ):
        return "no"
    readings = section.get("readings") or {}
    read = [
        readings[name.removesuffix("_raw")].get("value")
        for name in fields
        if name.removesuffix("_raw") in readings
    ]
    return "yes" if any(value != 0 for value in read) else "0 only"


def _sg_lines() -> list[str]:
    """Return the SG section: one row per diagnosis, then the models known."""
    reports = _sg_reports()
    lines = [
        "## String inverters (SG)",
        "",
        "An SG has a map of its own (`src/sungrow_modbus/string_inverter/`),",
        "read only. **0 only** means the block answered with nothing but zeros:",
        "an SG answers 0 where the source promises the unavailable value, so",
        "that is not evidence the machine has it.",
        "",
    ]
    if not reports:
        lines += ["_No diagnoses yet._", ""]
    else:
        header = [
            "Setup",
            "By",
            "Model",
            "Connection",
            "ARM firmware",
            "Phases",
            *(name for name, _, _ in SG_COLUMNS),
        ]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")
        for label, document in reports:
            device = document.get("device") or {}
            said = document.get("user_inputs") or {}
            row = [
                f"`{label}`",
                str(said.get("reporter") or "anonymous"),
                f"{device.get('device_type', 'unknown')} "
                f"(`{device.get('device_type_code', '—')}`)",
                _connection_cell(document.get("connection") or {}, said),
                f"`{(document.get('firmware') or {}).get('arm') or '—'}`",
                str(device.get("output_type") or "—"),
                *(
                    _sg_mark(document, component, prefix)
                    for _, component, prefix in SG_COLUMNS
                ),
            ]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    tested = {
        int(str(d.get("device", {}).get("device_type_code", "0x0")), 16)
        for _, d in reports
        if str(d.get("device", {}).get("device_type_code", "")).startswith("0x")
    }
    lines += [
        "Every SG model the source names, and whether anybody has tested one:",
        "",
        "| Code | Model | Tested |",
        "| --- | --- | --- |",
    ]
    for code in sorted(SG_MODELS):
        lines.append(
            f"| `0x{code:04X}` | {SG_MODELS[code]} | "
            f"{'**yes**' if code in tested else 'untested'} |"
        )
    lines.append("")
    return lines


def _model(document: dict) -> tuple[str, str]:
    """Return (model name, device type code) for one diagnosis."""
    raw = str(document.get("device", {}).get("device_type_code", ""))
    code = int(raw, 16) if raw.startswith("0x") else None
    return DEVICE_TYPES.get(code, "unknown"), raw or "—"


#: What has to be equal before two readings can be compared, and what is
#: then allowed to differ.
#:
#: Capability varies by **model, transport and firmware** at least, and this
#: project has measured all three mattering. So attributing a difference to
#: any one of them means holding the other two still -- otherwise "these two
#: documents disagree about MPPT3" says nothing about why.
#:
#: The transport is the claim rather than the verdict, deliberately: a
#: contributor who says `winet` and a measurement that agrees are the same
#: path, and the claim is what a reader of two documents compares.
def _comparable(document: dict) -> tuple[str, str, str]:
    """Return (model, transport, inverter firmware) for one reading."""
    firmware = (document.get("firmware") or {}).get("inverter")
    return (
        _model(document)[0],
        str((document.get("user_inputs") or {}).get("transport") or "unstated"),
        str(firmware) if firmware else "unknown",
    )


#: Probes that answer for what is fitted at a house -- a battery, a meter, a
#: wallbox, a second unit -- rather than for the inverter's firmware. A pair of
#: readings that differ on one of these differ in the installation, so the
#: firmware comparison leaves them out.
INSTALLATION_PROBES = frozenset(
    {
        "battery capacity (5639)",
        "battery level",
        "battery temperature",
        "battery voltage",
        "meter phase A current (5744)",
        "meter phase A voltage (5741)",
        "unit 2 SBR battery module block",
        "unit 2 inverter device type code",
        "unit 200 SBR battery module block",
        "unit 248 wallbox serial (direct)",
        "unit 3 wallbox serial",
    }
)


def _capability_marks(document: dict) -> dict[str, str]:
    """Return each curated probe's state, which is what varies."""
    probes = document.get("capability_probes") or {}
    return {
        name: str((entry or {}).get("state"))
        for name, entry in probes.items()
        if isinstance(entry, dict)
    }


def _attribution(reports: list[tuple[str, dict]]) -> list[str]:
    """Say which capabilities can be pinned on firmware, and which cannot.

    This is the question the whole exercise exists to answer -- *"collect as
    many diagnoses as possible to be able to identify firmware-related
    capabilities"* -- and answering it needs a **pair**: two readings that
    agree on model and transport and differ only in firmware. Anything less
    and a difference cannot be separated from the model.

    Generated rather than written, because the answer changes with every
    contribution and a hand-written paragraph would go stale silently. When
    no pair exists the section says so and names the reading that would
    create one, which is more use to somebody with hardware than a general
    plea for more data.
    """
    groups: dict[tuple[str, str], dict[str, list[str]]] = {}
    for label, document in reports:
        model, transport, firmware = _comparable(document)
        groups.setdefault((model, transport), {}).setdefault(firmware, []).append(label)

    pairs = {
        key: versions
        for key, versions in groups.items()
        if len([v for v in versions if v != "unknown"]) > 1
    }

    lines = [
        "## What can be attributed to firmware",
        "",
        "The question these diagnoses exist to answer: **which**",
        "capabilities move between firmware versions, as opposed to between",
        "models or between transports? Sungrow publishes no release notes, so",
        "the only way to know is to compare two readings that agree on model",
        "and transport and differ only in firmware.",
        "",
        "[firmware_support.md](firmware_support.md) asks the same question",
        "entity by entity, from each diagnosis's raw register dump, and pools",
        "every model on one firmware to ask whether they agree.",
        "",
    ]

    if not pairs:
        by_model = {
            model: sorted({fw for fw in versions if fw != "unknown"})
            for (model, _transport), versions in groups.items()
        }
        lines += [
            "**Nothing, yet — and that is a measurement rather than a gap in",
            "this page.** No two committed readings share a model and a",
            "transport while differing in firmware, so every capability",
            "difference between them is also a model difference and cannot be",
            "separated from it.",
            "",
            "What exists, and why none of it pairs up:",
            "",
            *_what_exists(groups),
            "",
            "So the reading that would unlock this is **not** a new model. It",
            "is a second reading of a model already here, on a different",
            "firmware -- which is worth saying plainly, because a wanted list",
            "otherwise reads as 'any hardware welcome' and the most valuable",
            "contribution is the least obvious one.",
            "",
        ]
        for model, versions in sorted(by_model.items()):
            if versions:
                lines.append(
                    f"- **{model}** is recorded on "
                    + ", ".join(_short_firmware(v) for v in versions)
                    + ". Any other firmware on one would make its capabilities"
                    " attributable."
                )
        lines.append("")
        return lines

    for (model, transport), versions in sorted(pairs.items()):
        known = {fw: labels for fw, labels in versions.items() if fw != "unknown"}
        marks = {
            fw: _capability_marks(dict(reports)[labels[0]])
            for fw, labels in known.items()
        }
        every = sorted({name for row in marks.values() for name in row})
        differing = [
            name
            for name in every
            if name not in INSTALLATION_PROBES
            and len({row.get(name) for row in marks.values()}) > 1
        ]
        lines += [
            f"### {model}, {transport}",
            "",
            "Same model, same transport, different firmware — so a difference",
            "here is the firmware's. What a house has fitted (battery, meter,",
            "wallbox) is left out.",
            "",
        ]
        if not differing:
            lines += [
                "**No capability differs.** Every curated probe answered the",
                "same way on "
                + " and ".join(sorted(_short_firmware(fw) for fw in known))
                + ", which is a result worth having: it says this firmware",
                "change moved nothing this project reads.",
                "",
            ]
            continue
        lines += ["| Capability | " + " | ".join(sorted(known)) + " |"]
        lines.append("| --- " * (len(known) + 1) + "|")
        for name in differing:
            row = " | ".join(marks[fw].get(name, "—") for fw in sorted(known))
            lines.append(f"| {name} | {row} |")
        lines.append("")
    lines += [
        "### Everything else",
        "",
        "Every reading by model and transport. A second firmware in any row",
        "that has only one would make the next pair.",
        "",
        *_what_exists(groups),
        "",
    ]
    return lines


def _what_exists(groups: dict[tuple[str, str], dict[str, list[str]]]) -> list[str]:
    """Tabulate model, transport and firmware, one row per firmware.

    Shown whether or not a pair exists. While none does it is the whole
    answer; once one does it is still what a contributor reads to see which
    reading would make the next one -- and it was dropped from the page the
    day the first pair appeared, which is when it became most useful.
    """
    rows = ["| Model | Transport | Inverter firmware |", "| --- | --- | --- |"]
    for (model, transport), versions in sorted(groups.items()):
        for firmware, labels in sorted(versions.items()):
            shown = _short_firmware(firmware)
            rows.append(
                f"| {model} | {transport} | {shown} "
                f"({len(labels)} reading{'s' if len(labels) > 1 else ''}) |"
            )
    return rows


def render() -> str:
    """Return the whole page."""
    reports = _reports()
    lines = [
        "# Compatibility",
        "",
        "**Generated — do not edit.** `scripts/generate/generate_compatibility.py` "
        "builds",
        "this from the diagnoses in",
        "[device-diagnosis/results/](../device-diagnosis/results/),"
        " and CI checks that it",
        "matches.",
        "",
        "Which parts of the register map a device answers varies by model, phase",
        "count, wiring, transport and firmware. The specification says what",
        "*exists*, not what a particular machine does with it — so every row",
        "below comes from a diagnosis taken off real hardware, and a model with",
        "no diagnosis is listed as **untested** rather than assumed to work.",
        "",
        "## Reported setups",
        "",
    ]

    if not reports:
        lines += ["_No diagnoses yet._", ""]
    else:
        header = [
            "Setup",
            "By",
            "Model",
            "Connection",
            "Battery (as reported)",
            "ARM firmware",
            *(name for name, _ in COLUMNS),
        ]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")
        for label, document in reports:
            model, code = _model(document)
            registers = document.get("capability_probes", document.get("registers", {}))
            device = document.get("device", {})
            # Schema 5 moved every contributed value into `user_inputs`; the
            # fallbacks read a document written before it.
            typed = document.get("user_inputs", {})
            row = [
                f"`{label}`",
                typed.get("reporter") or document.get("reporter") or "anonymous",
                f"{model} (`{code}`)",
                _connection_cell(document.get("connection", {}), typed),
                typed.get("battery") or device.get("battery_reported_by_hand") or "—",
                f"`{document.get('firmware', {}).get('arm') or '—'}`",
            ]
            through_module = "WiNet" in _connection_cell(
                document.get("connection", {}), typed
            ) or "Logger" in _connection_cell(document.get("connection", {}), typed)
            for name, register in COLUMNS:
                if name == "Phases":
                    row.append(str(device.get("output_type", "—")))
                    continue
                state = (registers.get(register) or {}).get("state")
                mark = MARKS.get(state, "—")
                if (
                    mark == "yes"
                    and through_module
                    and name in ZERO_MEANS_ABSENT_COLUMNS
                ):
                    mark = UNTRUSTWORTHY
                if mark == "yes" and name in ALL_ZERO_MEANS_ABSENT:
                    probes = [
                        (registers.get(probe) or {})
                        for probe in ALL_ZERO_MEANS_ABSENT[name]
                    ]
                    read = [
                        probe.get("values") for probe in probes if probe.get("values")
                    ]
                    if read and all(
                        all(word == 0 for word in values) for values in read
                    ):
                        mark = "no"
                row.append(mark)
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        lines += [
            "[^dongle]: Read through a WiNet-S or Logger, which answers **0**",
            '    where the inverter answers the specification\'s "unavailable"',
            "    — so a yes here may be a capability the machine does not",
            "    have. Measured on one SH8.0RT-V112 read both ways four",
            "    minutes apart: its own LAN port called MPPT3, MPPT4 and the",
            "    second meter channel unavailable, and its dongle reported",
            "    them as zero. The integration guards this in",
            "    [`capabilities.py`]"
            "(../src/sungrow_modbus/hybrid_inverter/capabilities.py);",
            "    the table cannot, so it says so.",
            "",
            "**Battery (as reported)** is free text, because no register",
            "reports a battery's brand. What Modbus can establish is whether",
            "the pack is a Sungrow one — the SBR/SBH per-module block at unit",
            "200 answers or it does not — and, when it is, *which* model: the",
            "capacity it reports matches one entry in the datasheet table, and",
            "the filename carries that model. For a third-party pack the make",
            "is whatever the person who sent the diagnosis wrote down.",
            "",
            "**By** is whoever provided it, and defaults to anonymous: a",
            "diagnosis is worth having either way, and nobody should have to",
            "attach their name to contribute one.",
            "",
            "Firmware is in the table because it decides more than the model",
            "does: which registers a device answers moves between versions, so",
            "two diagnoses are only comparable if both say which firmware",
            "they were taken on.",
            "",
            "**Connection** is marked _(reported)_ where the contributor told",
            "us. Registers 6100-6195 are documented as not forwarded by a",
            "WiNet-S/S2 or Logger, so their answering proves a direct path;",
            "register 13265 names the communication module when there is one,",
            "and only corroborates, because two measured dongles returned it",
            "empty. What no register reaches is the **medium**: a WiNet-S",
            "answers identically wired and over WiFi. One dongle read on both",
            "of its addresses returned identical documents — every probe, every",
            "field, even the TLS certificate — so only the person who plugged",
            "the cable in can say which was which, and that is what _(reported)_",
            "carries.",
            "**WiFi versus Ethernet on a WiNet-S is not determinable over",
            "Modbus** — nothing in the protocol reports it — so the diagnosis",
            "records what the contributor said and draws no conclusion.",
            "",
        ]

    lines += _attribution(reports)

    lines += [
        "## Models this library knows, and whether anybody has tested one",
        "",
        "Every model in Appendix 1 of the protocol document. **Untested** means",
        "nobody has sent a diagnosis — not that it does not work. What the",
        "library will do on an untested model is decided by its family, and the",
        "last column says what that rules out before anything is even read.",
        "",
    ]
    tested_codes = {
        int(str(d.get("device", {}).get("device_type_code", "0x0")), 16)
        for _, d in reports
        if str(d.get("device", {}).get("device_type_code", "")).startswith("0x")
    }
    lines.append("| Code | Model | Family | Tested | Known absent |")
    lines.append("| --- | --- | --- | --- | --- |")
    for code in sorted(DEVICE_TYPES):
        family = family_for(code)
        absent = sorted(c.value for c in known_absent(code))
        lines.append(
            f"| `0x{code:04X}` | {DEVICE_TYPES[code]} | "
            f"{family.value if family else '—'} | "
            f"{'**yes**' if code in tested_codes else 'untested'} | "
            f"{', '.join(absent) or '—'} |"
        )

    lines.append("")
    lines += _sg_lines()

    lines += [
        "## Sending one",
        "",
        "### First, get the file",
        "",
        "Either way produces a file with **no serial number, no host address and",
        "no timestamp**. That is deliberate: it is what lets you post it in",
        "public without any private channel needing to exist.",
        "",
        "1. **From the integration** — Settings → Devices & Services → Sungrow",
        "   Modbus → the three-dot menu → *Download diagnostics*.",
        "2. **Before installing anything** —",
        "   [`device-diagnosis/scripts/python/sungrow_diagnosis.py`]"
        "(../device-diagnosis/scripts/python/sungrow_diagnosis.py),",
        "   run from that folder, which needs nothing but Python.",
        "",
        "### Then send it",
        "",
        "- **[The diagnosis issue](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786)**:",
        "  attach the file as a comment, where every diagnosis is collected.",
        "- **A pull request** adding your file to",
        "  [device-diagnosis/results/](../device-diagnosis/results/),"
        " if you are comfortable",
        "  with git. This is the format the capability model already reads, so",
        "  it is the shortest path from your hardware to working code.",
        "",
        "The capability model in",
        "[`capabilities.py`](../src/sungrow_modbus/hybrid_inverter/capabilities.py)",
        "is built from these, so a diagnosis from an untested model is the",
        "single most useful thing anybody can contribute — including one that",
        "says everything works.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    """Write the page, or check the committed one is current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"{OUTPUT.relative_to(REPO)} is stale.\n"
                "Run scripts/generate/generate_compatibility.py and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT.relative_to(REPO)} matches the diagnoses")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO)}: {len(_reports())} diagnosis(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
