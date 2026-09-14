#!/usr/bin/env python3
"""Pin a Home Assistant instance's port where 2026.9 actually keeps it.

`http:` in `configuration.yaml` no longer decides the port, and finding that
out the slow way costs an afternoon. Home Assistant 2026.9 stores the HTTP
config in `<config>/.storage/http` as two configs -- `stable` and `pending`
-- and:

- YAML becomes **pending**, never stable. Once the store records
  `yaml_migration_done`, the YAML is ignored outright and a repair issue says
  so ("breaks in 2027.2").
- A boot uses pending only while its `error` is null, and arms a **five
  minute auto-revert**. Promotion to stable is an explicit websocket command
  (`http/config/promote`) that a person sends *after checking the new config
  works*, because stable is what recovery mode falls back to.
- When nobody promotes it, `http/config.py` writes
  `error: "not_promoted"` and restarts onto stable.

Measured here, and it is not a corner case: the HACS testbed served :8124
for five minutes, reverted itself to the default :8123, collided with the dev
instance already on that port, and came up with `http` dead -- so no API, no
frontend, and an onboarding script waiting forever for a port nothing was
listening on.

A scripted instance has nobody to promote anything, so this writes `stable`
directly and clears `pending`. That is the state a promotion would have left
behind, reached without a websocket client, and it leaves no revert timer
armed.

    python scripts/ha_http_port.py config-hacs 8124

**Only ever run this against a stopped instance**, and only on a dev one:
Home Assistant loads this store at startup and rewrites it on change, so
editing it underneath a running instance loses one of the two writes.

It refuses to touch a store whose schema it does not recognise, because a
mangled `.storage/http` is a Home Assistant that cannot serve anything.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

#: The store version this script understands. Home Assistant migrates its own
#: stores; a bump here means the shape changed and the assumptions below need
#: re-reading rather than forcing.
VERSION = 2
MINOR_VERSION = 2

#: What `http` writes for an unconfigured instance, which is what the fields
#: beside the port have to look like.
DEFAULTS: dict[str, object] = {
    "cors_allowed_origins": ["https://cast.home-assistant.io"],
    "login_attempts_threshold": -1,
    "ip_ban_enabled": True,
    "ssl_profile": "modern",
    "use_x_frame_options": True,
}


def build(port: int, previous: dict[str, object] | None = None) -> dict[str, object]:
    """Return a `stable` config for one port, keeping any other settings."""
    config = dict(DEFAULTS)
    if previous:
        # Whatever else somebody set stays set; only the port and the
        # promotion state are this script's business.
        config.update(
            {
                key: value
                for key, value in previous.items()
                if key not in ("server_port", "created_at", "error", "error_message")
            }
        )
    config["server_port"] = port
    config["created_at"] = datetime.now(UTC).isoformat()
    config["error"] = None
    config["error_message"] = None
    return config


def pin(config_dir: Path, port: int) -> int:
    """Write the port into the instance's HTTP store. Returns an exit code."""
    store = config_dir / ".storage" / "http"

    if not store.exists():
        # A first boot has not happened yet, so there is nothing to correct
        # and nothing whose shape can be checked. Writing a store from
        # scratch here would be guessing at a schema; Home Assistant will
        # create it, and the next run pins it.
        print(f"{store} does not exist yet -- run this after the first boot")
        return 0

    document = json.loads(store.read_text(encoding="utf-8"))
    if (document.get("version"), document.get("minor_version")) != (
        VERSION,
        MINOR_VERSION,
    ):
        print(
            f"refusing to edit {store}: it is version "
            f"{document.get('version')}.{document.get('minor_version')}, and this "
            f"script knows {VERSION}.{MINOR_VERSION}. Read "
            "homeassistant/components/http/config.py before changing it.",
            file=sys.stderr,
        )
        return 2

    data = document.setdefault("data", {})
    stable = data.get("stable") or {}
    if stable.get("server_port") == port and data.get("pending") is None:
        print(f"{config_dir.name} is already pinned to :{port}")
        return 0

    was = stable.get("server_port")
    data["stable"] = build(port, stable)
    # Cleared deliberately: a pending config is what arms the five-minute
    # revert, and a promoted one leaves nothing behind.
    data["pending"] = None
    # The YAML is ignored once this is set, which is why the port has to live
    # here. Said in the store as well as in the comment above.
    data["yaml_migration_done"] = True

    store.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"{config_dir.name}: stable port {was} -> {port}, pending cleared")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Pin the port of the instance whose config directory is named."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "config_dir", type=Path, help="a Home Assistant config directory"
    )
    parser.add_argument("port", type=int)
    args = parser.parse_args(argv)

    if not args.config_dir.is_dir():
        print(f"no such directory: {args.config_dir}", file=sys.stderr)
        return 2
    if not 1 <= args.port <= 65535:
        print(f"not a port: {args.port}", file=sys.stderr)
        return 2

    return pin(args.config_dir, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
