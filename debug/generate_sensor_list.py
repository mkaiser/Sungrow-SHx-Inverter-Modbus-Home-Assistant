#!/usr/bin/env python3

# Warning: This code is 99% vibe-coded. Don't expect much 
# Usage:  
# cd debug 
# ./generate_sensor_list.py ../modbus_sungrow.yaml -o sensor_list_for_ha_template_editor.txt

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except Exception:
    print("Requires PyYAML. Install with: pip install pyyaml", file=sys.stderr)
    raise

# allow !secret to be parsed as its scalar name/value
def _secret_constructor(loader, node):
    return loader.construct_scalar(node)

yaml.SafeLoader.add_constructor('!secret', _secret_constructor)

def sanitize_entity(name: str) -> str:
    s = name.lower()
    # replace any non-alnum with underscore
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    return s

def collect_modbus_sensors(cfg):
    names = []
    for m in cfg.get("modbus", []) or []:
        for s in (m.get("sensors") or []):
            n = s.get("name")
            if n:
                names.append(n)
    return names

def collect_template_sensors(cfg):
    names = []
    for item in cfg.get("template", []) or []:
        if not isinstance(item, dict):
            continue
        # look for explicit "sensor" blocks inside template (list of sensors)
        sensors = item.get("sensor")
        if isinstance(sensors, list):
            for s in sensors:
                if isinstance(s, dict):
                    n = s.get("name")
                    if n:
                        names.append(n)
    return names

def collect_top_level_sensors(cfg):
    names = []
    for item in cfg.get("sensor", []) or []:
        # some top-level sensor entries are dicts with 'platform' and 'name'
        if isinstance(item, dict):
            n = item.get("name")
            if n:
                names.append(n)
            # nested list (e.g. platform: template with 'sensors' list)
            for v in item.values():
                if isinstance(v, list):
                    for sub in v:
                        if isinstance(sub, dict) and "name" in sub:
                            names.append(sub.get("name"))
    return names

def main():
    p = argparse.ArgumentParser(description="Generate sensor list from modbus_sungrow.yaml")
    p.add_argument("yaml", nargs="?", default="modbus_sungrow.yaml")
    p.add_argument("--out", "-o", help="Write output to file (default stdout)")
    args = p.parse_args()

    path = Path(args.yaml)
    if not path.exists():
        print("Input file not found:", path, file=sys.stderr)
        sys.exit(2)

    with path.open("r", encoding="utf-8") as fh:
        content = yaml.safe_load(fh)

    names = []
    names.extend(collect_modbus_sensors(content))
    names.extend(collect_template_sensors(content))
    names.extend(collect_top_level_sensors(content))

    # remove duplicates while preserving order
    seen = set()
    uniq = []
    for n in names:
        if n not in seen:
            seen.add(n)
            uniq.append(n)

    # sort alphabetically, case-insensitive
    uniq = sorted(uniq, key=lambda s: s.lower())

    out_lines = []
    for name in uniq:
        eid = sanitize_entity(name)
        out_lines.append(f"{name}={{{{states('sensor.{eid}')}}}}")

    output = "\n".join(out_lines) + "\n"

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print("Wrote", args.out)
    else:
        print(output, end="")

if __name__ == "__main__":
    main()