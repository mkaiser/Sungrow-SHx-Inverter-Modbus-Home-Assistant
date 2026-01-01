#!/usr/bin/env python3
# PROMPT TO RECREATE THIS SCRIPT (verbatim requirements)
#
# Create a Python script that:
# - is run from subdirectory scripts
# - is called "generate_second_inverter_config" and has the .py extension
# - takes a number as input parameter, e.g. '1' or '2'
# - takes the modbus_sungrow.yaml file from one directory level above and creates the file
#   "modbus_sungrow_multiple_inverters_%number%" (output should have a .yaml extension)
# - adds a suffix to all "- name" entries
#   - there should be a space before the number
#   - rename suffix to " inv 1" (i.e. " inv <n>")
# - also add this suffix to all used sensors in the automations, templates etc.
#   Example: sensor.battery_max_discharge_power --> sensor.battery_max_discharge_power_inv_1
# - use secrets with suffix:
#   - sungrow_modbus_device_address_inv_1 (or inv_2)
#   - also change host and port to use suffix (sungrow_modbus_host_ip_inv_<n>, sungrow_modbus_port_inv_<n>)
# - remove unintended extra line breaks introduced by the script.

"""Generate a multi-inverter config by suffixing list-item `- name:` entries.

Usage (run from this directory):
  python3 ./generate_second_inverter_config.py 2

This will:
- read:  ../modbus_sungrow.yaml
- write: ../modbus_sungrow_multiple_inverters_2.yaml

It performs conservative, line-based transformations to preserve formatting.
Only single-line scalars on the same line as `- name:` are modified.

Rules:
- `- name: X` becomes `- name: X inv <n>`
- Entity references are rewritten to match the new entity_ids, e.g.
    `sensor.battery_max_discharge_power` -> `sensor.battery_max_discharge_power_inv_<n>`
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


_NAME_LINE_RE = re.compile(
    r"^(?P<prefix>\s*-\s*name\s*:\s*)(?P<value>[^#\n]*?)(?P<comment>\s*(#.*)?)$"
)

_ENTITY_ID_RE = re.compile(
    r"\b(?P<domain>sensor|binary_sensor|switch|number|select|button|scene)\.(?P<object_id>[a-z0-9_]+)\b"
)

_SUNGROW_SECRET_RE = re.compile(
    r"!secret\s+(?P<name>sungrow_modbus_host_ip|sungrow_modbus_port|sungrow_modbus_device_address|sungrow_modbus_battery_max_power)\b"
)


def _append_suffix_preserving_quotes(raw: str, suffix: str) -> str:
    original = raw
    s = raw.strip()
    if not s:
        return original

    leading = original[: len(original) - len(original.lstrip(" \t"))]
    trailing = original[len(original.rstrip(" \t")) :]

    if (len(s) >= 2) and ((s[0] == s[-1]) and s[0] in {'"', "'"}):
        quote = s[0]
        inner = s[1:-1]
        return f"{leading}{quote}{inner}{suffix}{quote}{trailing}"

    return f"{leading}{s}{suffix}{trailing}"


def transform_text(text: str, suffix: str) -> tuple[str, int]:
    out_lines: list[str] = []
    replacements = 0

    for line in text.splitlines(keepends=True):
        # Keep line endings intact but match only on the content without EOL.
        eol = ""
        if line.endswith("\r\n"):
            eol = "\r\n"
        elif line.endswith("\n"):
            eol = "\n"

        content = line[: -len(eol)] if eol else line

        m = _NAME_LINE_RE.match(content)
        if not m:
            out_lines.append(line)
            continue

        value = m.group("value")

        # Avoid risky transformations on complex YAML scalars.
        if value.strip() in {"|", ">"}:
            out_lines.append(line)
            continue
        if value.lstrip().startswith(("&", "*")):
            out_lines.append(line)
            continue

        new_value = _append_suffix_preserving_quotes(value, suffix)
        if new_value != value:
            replacements += 1

        out_lines.append(f"{m.group('prefix')}{new_value}{m.group('comment')}{eol}")

    return "".join(out_lines), replacements


def suffix_entity_ids(text: str, *, inv_number: str) -> tuple[str, int]:
    """Append or normalize `_inv_<n>` suffix for entity ids in the text."""

    def repl(match: re.Match[str]) -> str:
        domain = match.group("domain")
        object_id = match.group("object_id")

        desired = f"_inv_{inv_number}"
        if object_id.endswith(desired):
            return f"{domain}.{object_id}"

        # If an inv suffix already exists, normalize it.
        object_id = re.sub(r"_inv_\d+$", desired, object_id)
        if not object_id.endswith(desired):
            object_id = f"{object_id}{desired}"

        return f"{domain}.{object_id}"

    updated, count = _ENTITY_ID_RE.subn(repl, text)
    return updated, count


def suffix_sungrow_secrets(text: str, *, inv_number: str) -> tuple[str, int]:
    def repl(match: re.Match[str]) -> str:
        name = match.group("name")
        return f"!secret {name}_inv_{inv_number}"

    updated, count = _SUNGROW_SECRET_RE.subn(repl, text)
    return updated, count


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in {"-h", "--help"}:
        print(
            "Usage: generate_second_inverter_config.py <number>\n"
            "Run from the 'scripts' directory; reads ../modbus_sungrow.yaml and writes ../modbus_sungrow_multiple_inverters_<number>.yaml."
        )
        return 2

    number = argv[1]
    if not number.isdigit():
        print(f"Error: <number> must be digits, got: {number!r}")
        return 2

    scripts_dir = Path.cwd()
    source = scripts_dir.parent / "modbus_sungrow.yaml"
    if not source.exists():
        print(
            "Error: expected source file not found: "
            f"{source}\n"
            "Make sure you run this script from the 'scripts' directory directly under the folder containing modbus_sungrow.yaml."
        )
        return 2

    dest = scripts_dir.parent / f"modbus_sungrow_multiple_inverters_{number}.yaml"

    original = source.read_text(encoding="utf-8")
    name_suffix = f" inv {number}"
    updated, name_replacements = transform_text(original, suffix=name_suffix)
    updated, entity_replacements = suffix_entity_ids(updated, inv_number=number)
    updated, secret_replacements = suffix_sungrow_secrets(updated, inv_number=number)

    dest.write_text(updated, encoding="utf-8")

    print(
        f"Wrote {dest} ({name_replacements} '- name:' entr(y/ies) updated, {entity_replacements} entity_id reference(s) updated, {secret_replacements} secret reference(s) updated)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
