#!/usr/bin/env bash
# Boot a second Home Assistant that installs this integration the way a user
# does: through HACS, from the preview channel.
#
# ## Why this is not the dev instance
#
# `scripts/develop.sh` makes `config/custom_components` a **symlink** to the
# repository, so the instance runs the working tree. That is what you want
# while writing code and exactly wrong for testing an install:
#
# - HACS downloads into `<config>/custom_components/<domain>`. Through that
#   symlink it would write *into the repository*, over tracked files, and drop
#   its own `hacs/` directory next to the integration where hassfest and the
#   test suite would then find it.
# - The preview channel ships the same domain, `sungrow_modbus`. Two copies at
#   one path is the conflict `doc/installing_a_preview.md` warns users about,
#   not an upgrade.
#
# So this is a separate config directory, on a separate port, holding a
# separate Home Assistant. Nothing here symlinks anything: whatever runs in it
# arrived the way a stranger's copy arrives.
#
#     scripts/hacs_testbed.sh                # set up if needed, then boot
#     scripts/hacs_testbed.sh --update       # re-download HACS first
#     scripts/hacs_testbed.sh --setup-only   # prepare it, do not boot
#     scripts/hacs_testbed.sh --reset        # delete the testbed and start over
#     PORT=8125 scripts/hacs_testbed.sh      # somewhere else
#
# The parts that cannot be scripted are printed before it boots: Home
# Assistant's own onboarding, and HACS asking GitHub to authorise this
# instance through a device code.
set -euo pipefail

cd "$(dirname "$0")/.."

CONFIG="${PWD}/config-hacs"
PORT="${PORT:-8124}"
HACS_URL="https://github.com/hacs/integration/releases/latest/download/hacs.zip"
PREVIEW="https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant-preview"

update=false
boot=true
for argument in "$@"; do
    case "${argument}" in
        --update) update=true ;;
        --setup-only) boot=false ;;
        --reset)
            # Deliberately not `rm -rf $CONFIG` from a variable that could be
            # empty: an unset CONFIG would make that `rm -rf /`. The path is
            # spelled out, and checked first.
            if [[ -d "${PWD}/config-hacs" ]]; then
                rm -rf "${PWD}/config-hacs"
                echo "deleted config-hacs/ -- the next run starts from nothing"
            else
                echo "config-hacs/ does not exist; nothing to reset"
            fi
            exit 0
            ;;
        *)
            echo "unknown option: ${argument}" >&2
            echo "usage: $0 [--update] [--setup-only] [--reset]" >&2
            exit 2
            ;;
    esac
done

mkdir -p "${CONFIG}"

if [[ ! -f "${CONFIG}/.HA_VERSION" ]]; then
    hass --config "${CONFIG}" --script ensure_config
fi

# `default_config:` rather than a hand-picked list. HACS depends on http,
# websocket_api, frontend, persistent_notification, lovelace and repairs, and
# this instance exists to behave like somebody's real one -- so it gets the
# same bundle a real one has. The first boot is therefore slow: Home
# Assistant pip-installs each component's requirements, and the UI 404s until
# it is done. The next boot is quick.
if [[ ! -f "${CONFIG}/configuration.yaml" ]] || ! grep -q "hacs_testbed" "${CONFIG}/configuration.yaml"; then
    cat > "${CONFIG}/configuration.yaml" <<YAML
# Written by scripts/hacs_testbed.sh -- an instance for testing the HACS
# install of this integration. Delete the directory to start over.
# hacs_testbed
default_config:

http:
  server_port: ${PORT}

logger:
  default: info
  logs:
    custom_components.hacs: debug
    custom_components.sungrow_modbus: debug
    sungrow_modbus: debug
YAML
    echo "wrote ${CONFIG}/configuration.yaml"
fi

# HACS is itself a custom integration, and it is not in HACS -- it is the one
# thing you install by hand. Its release asset unpacks flat, so it goes into a
# directory of its own.
if [[ ! -f "${CONFIG}/custom_components/hacs/manifest.json" ]] || [[ "${update}" == true ]]; then
    echo "downloading HACS from ${HACS_URL}"
    rm -rf "${CONFIG}/custom_components/hacs"
    mkdir -p "${CONFIG}/custom_components/hacs"
    scratch="$(mktemp -d)"
    trap 'rm -rf "${scratch}"' EXIT
    curl -fsSL -o "${scratch}/hacs.zip" "${HACS_URL}"
    python3 -c "
import sys, zipfile
zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])
" "${scratch}/hacs.zip" "${CONFIG}/custom_components/hacs"
    version="$(python3 -c "
import json, pathlib, sys
print(json.loads(pathlib.Path(sys.argv[1]).read_text())['version'])
" "${CONFIG}/custom_components/hacs/manifest.json")"
    echo "HACS ${version} unpacked into config-hacs/custom_components/hacs"
fi

# Nothing is symlinked here. Said out loud because every other script in this
# repository does the opposite, and because a symlink at this path would let
# HACS write into tracked files.
if [[ -L "${CONFIG}/custom_components" ]]; then
    echo "error: ${CONFIG}/custom_components is a symlink." >&2
    echo "This testbed must hold real directories, or HACS writes into the repository." >&2
    exit 1
fi

installed="not installed yet"
if [[ -f "${CONFIG}/custom_components/sungrow_modbus/manifest.json" ]]; then
    installed="$(python3 -c "
import json, pathlib, sys
print(json.loads(pathlib.Path(sys.argv[1]).read_text())['version'])
" "${CONFIG}/custom_components/sungrow_modbus/manifest.json")"
fi

cat <<NEXT

========================================================================
A Home Assistant for testing the HACS install
config-hacs/                                       http://localhost:${PORT}
========================================================================

  This integration here:  ${installed}
  HACS:                   $(python3 -c "
import json, pathlib
print(json.loads(pathlib.Path('${CONFIG}/custom_components/hacs/manifest.json').read_text())['version'])
")

  What this script cannot do for you

  1  Onboarding. Create any account -- it is local to config-hacs/ and
     holds nothing. dev / dev is fine; this instance talks to the
     simulator unless you point it somewhere else.

  2  Settings -> Devices & services -> Add integration -> HACS.
     It asks you to authorise a GitHub account by typing a code at
     https://github.com/login/device. That is HACS talking to GitHub, not
     to this project, and it cannot be automated from here.

  3  HACS -> three dots -> Custom repositories. Add
     ${PREVIEW}
     with category Integration. Then open it and Download.

  4  Restart Home Assistant. The library comes from PyPI on the way up,
     which is the step that surprises people -- it needs working internet
     and it makes that one boot slower.

  5  Settings -> Devices & services -> Add integration ->
     Sungrow Modbus (preview).

  What to watch for, because this is the install a user gets

  - The version HACS shows is a **commit hash**, not 0.1.0aN. The preview
    channel publishes no releases of its own, so that hash is what a bug
    report should quote.
  - The library is pip-installed from PyPI against the pin in
    manifest.json. If that fails, setup fails with RequirementsNotFound
    and the integration never appears -- which is what
    scripts/check_pinned_library.py exists to catch before a user does.
  - Nothing in this directory is the working tree. A change you make in
    the repository does **not** appear here until it reaches the preview
    channel. Use \`make dev\` for the other thing.

  First boot downloads component requirements and logs setup errors while
  it does; the UI 404s until it settles. Not a bug.

========================================================================

NEXT

if [[ "${boot}" == false ]]; then
    echo "--setup-only: not booting. \`make hacs\` when you want it."
    exit 0
fi

exec hass --config "${CONFIG}" --debug
