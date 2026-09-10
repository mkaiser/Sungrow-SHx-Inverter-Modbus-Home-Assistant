#!/usr/bin/env python3
"""Artefacts for InfluxDB and Grafana users whose entity ids are changing.

Home Assistant's recorder follows a renamed entity. **Nothing outside it
does.** The InfluxDB integration tags every point with `entity_id` set to the
*object id*, writes forward only, and never rewrites history — so an id change
starts a new series and every Grafana panel goes on rendering data that stops.
The same is true of Prometheus, MQTT statestream and Node-RED.

So this exists, and its limits are the point:

* it **never connects to anything**. It reads the entity map in this
  repository and prints text;
* what it prints is **for review**, not for piping into a shell. Rewriting
  someone's time-series database is not a thing to do on the strength of a
  script that has never seen their data;
* the **delete step is commented out**, always. Nobody has ever regretted
  keeping the old series a week longer.

The cheapest fix is the first one: a Grafana regex matching both names costs
nothing and needs no rewrite at all.

    python scripts/influx_migration.py --device SH10RT
    python scripts/influx_migration.py --device SH10RT --format flux
    python scripts/influx_migration.py --device SH10RT --format influxql
    python scripts/influx_migration.py --device SH10RT --reverse
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from naming import modern_name

from homeassistant.util import slugify

REPO = Path(__file__).resolve().parent.parent


def pairs(device: str) -> list[tuple[str, str, str]]:
    """Return (key, legacy object id, modern object id) for every entity.

    Object ids, not entity ids: that is what the InfluxDB integration puts in
    the `entity_id` tag, and getting it wrong would produce a regex that
    matches nothing.
    """
    from custom_components.sungrow_modbus.derived_descriptions import (
        DERIVED_BINARY_SENSORS,
        DERIVED_SENSORS,
    )
    from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS

    rows: list[tuple[str, str, str]] = []
    for description in (
        *SENSOR_DESCRIPTIONS,
        *DERIVED_SENSORS,
        *DERIVED_BINARY_SENSORS,
    ):
        if not description.legacy_name:
            continue
        legacy = slugify(description.legacy_name)
        modern = slugify(
            f"{device} {modern_name(description.key, description.legacy_name)}"
        )
        rows.append((description.key, legacy, modern))
    return sorted(rows, key=lambda row: row[1])


def _direction(row: tuple[str, str, str], reverse: bool) -> tuple[str, str]:
    """Return (from, to) object ids for the direction being migrated."""
    _, legacy, modern = row
    return (modern, legacy) if reverse else (legacy, modern)


def grafana(rows: list[tuple[str, str, str]], reverse: bool) -> str:
    """Return regexes that match a series under either name.

    This is the whole fix for most people. A Grafana panel filtering
    `entity_id = 'total_dc_power'` keeps working across the change if it
    filters `entity_id =~ /^(total_dc_power|sh10rt_total_dc_power)$/` instead,
    and nothing in the database has to move.
    """
    lines = [
        "# Grafana: replace the entity_id filter in each panel.",
        "#",
        "#   before:  \"entity_id\" = 'total_dc_power'",
        '#   after:   "entity_id" =~ /^(total_dc_power|sh10rt_total_dc_power)$/',
        "#",
        "# No data moves, both halves of the series render, and it keeps working",
        "# whichever way you migrate later.",
        "",
    ]
    for row in rows:
        source, target = _direction(row, reverse)
        lines.append(f"/^({source}|{target})$/    # {row[0]}")
    return "\n".join(lines)


def flux(rows: list[tuple[str, str, str]], reverse: bool, bucket: str) -> str:
    """Return Flux that copies each series to the new tag value (InfluxDB 2.x)."""
    lines = [
        "// InfluxDB 2.x. Run one at a time, in the Data Explorer, and check the",
        "// row count before and after. These COPY: the old series is untouched.",
        "//",
        f"// Bucket assumed to be {bucket!r}; change it if yours differs.",
        "",
    ]
    for row in rows:
        source, target = _direction(row, reverse)
        lines.append(
            f"// {row[0]}\n"
            f'from(bucket: "{bucket}")\n'
            f"  |> range(start: 0)\n"
            f'  |> filter(fn: (r) => r["entity_id"] == "{source}")\n'
            f'  |> set(key: "entity_id", value: "{target}")\n'
            f'  |> to(bucket: "{bucket}")\n'
        )
    lines.append(
        "// Deleting the old series is deliberately not written out here. Keep it\n"
        "// until you have looked at a dashboard covering the seam, then remove it\n"
        "// by hand with the delete API."
    )
    return "\n".join(lines)


def influxql(rows: list[tuple[str, str, str]], reverse: bool, database: str) -> str:
    """Return the export/rewrite/import recipe for InfluxDB 1.x.

    InfluxQL cannot change a tag value: tags are part of the series key, so
    `SELECT INTO` carries the old key with it. The only route is out to line
    protocol, rewrite the text, and back in — which is why this prints a recipe
    to read rather than commands to run.
    """
    lines = [
        "# InfluxDB 1.x. A tag is part of the series key, so InfluxQL cannot",
        "# rewrite one -- SELECT INTO carries the old key with it. The route is",
        "# out to line protocol, rewrite the text, and back in.",
        "#",
        "# 1. Export. Do this on the InfluxDB host, with the service running.",
        f"influx_inspect export -database {database} \\",
        "  -datadir /var/lib/influxdb/data -waldir /var/lib/influxdb/wal \\",
        "  -out /tmp/ha-export.lp -compress=false",
        "",
        "# 2. Rewrite the entity_id tag. Anchored on the tag, so a value that is a",
        "#    prefix of another entity's cannot be caught by mistake.",
    ]
    for row in rows:
        source, target = _direction(row, reverse)
        lines.append(
            f"sed -i 's/,entity_id={source},/,entity_id={target},/g' /tmp/ha-export.lp"
            f"    # {row[0]}"
        )
    lines += [
        "",
        "# 3. Import into a NEW database, then compare before switching Grafana.",
        "influx -import -path=/tmp/ha-export.lp -precision=ns \\",
        f"  -database={database}_migrated",
        "",
        "# 4. Deleting the old database is deliberately left commented out.",
        f"# DROP DATABASE {database}",
    ]
    return "\n".join(lines)


def main() -> int:
    """Print the artefacts. Nothing is connected to and nothing is executed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device",
        required=True,
        help="the device name Home Assistant shows, e.g. SH10RT -- modern object "
        "ids are slugified from it",
    )
    parser.add_argument(
        "--format",
        choices=("grafana", "flux", "influxql", "table"),
        default="grafana",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="migrating back: modern ids to legacy ones",
    )
    parser.add_argument("--bucket", default="homeassistant", help="InfluxDB 2.x bucket")
    parser.add_argument(
        "--database", default="homeassistant", help="InfluxDB 1.x database"
    )
    args = parser.parse_args()

    rows = pairs(args.device)
    if args.format == "table":
        width = max(len(legacy) for _, legacy, _ in rows)
        for row in rows:
            source, target = _direction(row, args.reverse)
            print(f"{source:<{width}}  ->  {target}")
    elif args.format == "grafana":
        print(grafana(rows, args.reverse))
    elif args.format == "flux":
        print(flux(rows, args.reverse, args.bucket))
    else:
        print(influxql(rows, args.reverse, args.database))

    print(f"\n# {len(rows)} entities.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
