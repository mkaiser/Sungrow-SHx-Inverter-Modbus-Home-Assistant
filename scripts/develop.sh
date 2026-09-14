#!/usr/bin/env bash
# Boot a minimal Home Assistant with the Sungrow SHx integration loaded.
set -e

cd "$(dirname "$0")/.."

# Create the dev config on first run.
if [[ ! -d "${PWD}/config" ]]; then
    mkdir -p "${PWD}/config"
fi
if [[ ! -f "${PWD}/config/.HA_VERSION" ]]; then
    hass --config "${PWD}/config" --script ensure_config
fi

# Home Assistant looks for custom integrations in <config>/custom_components,
# so that is a symlink back to the repo. It used to be PYTHONPATH instead,
# which broke the moment the domain was renamed to `sungrow_modbus`: that is
# also the library's import name, so putting custom_components/ on the path
# exposes the *integration* as top-level `sungrow_modbus` and it shadows the
# library. `from sungrow_modbus import TIERS` inside the integration then
# imports the integration from inside itself, and Home Assistant reports a
# circular import while loading the config flow.
#
# A real installation has config/custom_components/ as a directory and the
# library in site-packages, which is exactly what this reproduces. config/ is
# gitignored, so the link costs nothing.
mkdir -p "${PWD}/config"
ln -sfn "${PWD}/custom_components" "${PWD}/config/custom_components"

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
    python - <<'PY'
import json
from pathlib import Path

store = Path("config/.storage/core.config_entries")
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

# Onboarding, in the background, while Home Assistant starts in front of it.
# A fresh config/ -- or one whose .storage was cleared -- otherwise opens on
# `onboarding.html` and asks for the account that doc/development.yaml already
# publishes. Idempotent, so an instance that is already onboarded prints one
# line and stops.
(
    python3 "${PWD}/scripts/ha_onboard.py" --url http://127.0.0.1:8123 \
        --username dev --password dev || true
) &

# Deliberately **without `--debug`**, which is not a logging flag.
#
# It sets `loop.set_debug(True)`, and an asyncio debug-mode loop is slow
# enough to break this integration's own network search: `async_sweep` opens
# 64 sockets at a time and rules an address out on a one-second wall-clock
# timeout, so loop overhead comes straight out of the budget for a connect
# that takes six milliseconds. Measured on this machine against a /24 holding
# two live inverters -- three runs out of three found **nothing** with
# `--debug`, and three out of three found both without it. It cost a real
# debugging session, on a search the maintainer ran against his own house.
#
# Nothing is lost. Log verbosity comes from the `logger:` block in
# config/configuration.yaml, which already sets this integration and the
# Modbus stack to debug; `--debug` adds only the loop mode and
# `hass.config.debug`. If you want it back for an asyncio bug, add it -- and
# expect the search to fail while it is on.
hass --config "${PWD}/config"
