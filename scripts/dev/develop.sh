#!/usr/bin/env bash
# Boot a minimal Home Assistant with the Sungrow SHx integration loaded.
set -e

cd "$(dirname "$0")/../.."

# Which instance this is. The default is the one everybody means by "the dev
# instance": `config/` on :8123, against the simulator.
#
# `make dev-real` sets these to `config-real` and 8125, for an instance
# pointed at **real hardware**. Two instances rather than two config entries
# in one, because the point of the second is that it is disposable: its
# history, its entity ids and its registry are its own, so a day of talking
# to a real inverter leaves nothing to untangle from the simulator's.
#
# They must not run against the same directory at once -- Home Assistant
# rewrites `.storage` on change and the second one would lose the first's
# writes -- but on different ones they run side by side happily.
CONFIG_DIR="${SUNGROW_DEV_CONFIG:-config}"
PORT="${SUNGROW_DEV_PORT:-8123}"
CONFIG="${PWD}/${CONFIG_DIR}"

# Create the dev config on first run.
mkdir -p "${CONFIG}"
if [[ ! -f "${CONFIG}/.HA_VERSION" ]]; then
    hass --config "${CONFIG}" --script ensure_config
fi

# One configuration.yaml, copied rather than written: `config/configuration.yaml`
# is the tracked one and says why each component is there, and a second
# instance that drifted from it would debug differently from the first for
# reasons nobody would think to look for.
if [[ "${CONFIG_DIR}" != "config" && ! -f "${CONFIG}/configuration.yaml" ]]; then
    cp "${PWD}/config/configuration.yaml" "${CONFIG}/configuration.yaml"
fi

# Home Assistant looks for custom integrations in <config>/custom_components,
# so that is a symlink back to the repo. Never PYTHONPATH: the domain
# `sungrow_modbus` is also the library's import name, so putting
# custom_components/ on the path exposes the *integration* as top-level
# `sungrow_modbus` and it shadows the library. `from sungrow_modbus import
# TIERS` inside the integration then imports the integration from inside
# itself, and Home Assistant reports a circular import while loading the
# config flow.
#
# A real installation has config/custom_components/ as a directory and the
# library in site-packages, which is exactly what this reproduces. config/ is
# gitignored, so the link costs nothing.
ln -sfn "${PWD}/custom_components" "${CONFIG}/custom_components"

# `--forget` drops any Sungrow config entry this dev instance is holding, so
# the next boot starts at "Add integration" again.
#
# It exists because the host and unit id live in the **config entry**, not in
# this script and not in configuration.yaml, and Home Assistant remembers
# them. Point the devcontainer at a different network -- a VPN to somebody
# else's installation, say -- and the remembered address refuses, the entry
# fails to load, and it looks exactly as though something here hard-codes an
# address. Nothing does. This is how to forget it without hand-editing
# .storage.
if [[ "${1:-}" == "--forget" ]]; then
    SUNGROW_DEV_CONFIG_DIR="${CONFIG}" python - <<'PY'
import json
import os
from pathlib import Path

store = Path(os.environ["SUNGROW_DEV_CONFIG_DIR"]) / ".storage/core.config_entries"
if not store.exists():
    print("no config entries yet -- nothing to forget")
    raise SystemExit
document = json.loads(store.read_text(encoding="utf-8"))
entries = document["data"]["entries"]
keeping = [entry for entry in entries if entry["domain"] != "sungrow_modbus"]
dropped = len(entries) - len(keeping)
if not dropped:
    print("no Sungrow entry stored -- nothing to forget")
    raise SystemExit
document["data"]["entries"] = keeping
store.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
print(f"forgot {dropped} Sungrow config entry(ies) -- add the integration again")
PY
    # Forget and stop. Booting on from here is a surprise: `make forget`
    # reads as one action, and Home Assistant would then hold the
    # terminal for as long as it runs. Start it with `make dev`.
    exit 0
fi

# A second instance has to be told its port, and told it in `.storage/http`
# rather than in the YAML: `ha_http_port.py` says why in full -- the short of
# it is that a YAML port is a *pending* one Home Assistant reverts after five
# minutes with nobody to promote it, and it would then land on :8123 on top of
# the first instance. Harmless before the store exists; it says so and stops.
if [[ "${PORT}" != "8123" ]]; then
    python3 "${PWD}/scripts/dev/ha_http_port.py" "${CONFIG_DIR}" "${PORT}"
fi

# Onboarding, in the background, while Home Assistant starts in front of it.
# A fresh config/ -- or one whose .storage was cleared -- otherwise opens on
# `onboarding.html` and asks for the account that doc/development.yaml already
# publishes. Idempotent, so an instance that is already onboarded prints one
# line and stops.
(
    python3 "${PWD}/scripts/dev/ha_onboard.py" --url "http://127.0.0.1:${PORT}" \
        --username dev --password dev || true
) &

# Deliberately **without `--debug`**, which is not a logging flag.
#
# It sets `loop.set_debug(True)`, and an asyncio debug-mode loop is slow
# enough to break this integration's own network search: `async_sweep` opens
# 64 sockets at a time and rules an address out on a one-second wall-clock
# timeout, so loop overhead comes straight out of the budget for a connect
# that takes six milliseconds. Against a /24 holding two live inverters, a
# search with `--debug` finds nothing and one without it finds both.
#
# Nothing is lost. Log verbosity comes from the `logger:` block in
# config/configuration.yaml, which already sets this integration and the
# Modbus stack to debug; `--debug` adds only the loop mode and
# `hass.config.debug`. If you want it back for an asyncio bug, add it -- and
# expect the search to fail while it is on.
#
# `SETUP_PORT` covers the **first** boot, which `ha_http_port.py` cannot:
# there is no `.storage/http` to pin yet, and Home Assistant would create one
# on :8123 -- straight into the first instance's port, which is how this was
# found. It is `http`'s own default for an instance with no stored port
# (`default_server_port` in `homeassistant/components/http/config.py`), so
# from the second boot on the pinned store decides and this is ignored.
# `hacs_testbed.sh` does the same for the same reason.
SETUP_PORT="${PORT}" hass --config "${CONFIG}"
