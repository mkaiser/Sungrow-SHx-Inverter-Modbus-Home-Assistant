#!/usr/bin/env bash
# Boot a second Home Assistant that installs this integration the way a user
# does: through HACS, from the preview channel.
#
# ## Why this is not the dev instance
#
# `scripts/dev/develop.sh` makes `config/custom_components` a **symlink** to the
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
#     scripts/dev/hacs_testbed.sh                # set up if needed, then boot
#     scripts/dev/hacs_testbed.sh --update       # re-download HACS first
#     scripts/dev/hacs_testbed.sh --setup-only   # prepare it, do not boot
#     scripts/dev/hacs_testbed.sh --reset        # delete the testbed and start over
#     PORT=8125 scripts/dev/hacs_testbed.sh      # somewhere else
#
# ## The Marketplace, from Home Assistant 2026.11
#
# 2026.11 builds HACS in, as Settings -> Marketplace, and the HACS installer
# stops there. `--marketplace` boots that instead: Home Assistant 2026.11 from
# a venv of its own (`.venv-marketplace/`, created on first use, so a
# testbed's installs never reach the dev environment), against
# `config-marketplace/` on :8126, with nothing downloaded. Add the preview
# channel there with Add from link.
#
#     scripts/dev/hacs_testbed.sh --marketplace              # 2026.11, fresh
#     scripts/dev/hacs_testbed.sh --marketplace --adopt-hacs # from a copy of config-hacs/
#     scripts/dev/hacs_testbed.sh --marketplace --reset      # delete config-marketplace/
#
# `--adopt-hacs` starts it from a copy of `config-hacs/`, HACS and its
# installed preview included: the upgrade a HACS user makes. `config-hacs/`
# itself is not touched.
#
# The parts that cannot be scripted are printed before it boots: Home
# Assistant's own onboarding, and HACS asking GitHub to authorise this
# instance through a device code.
set -euo pipefail

cd "$(dirname "$0")/../.."

marketplace=false
adopt=false
for argument in "$@"; do
    case "${argument}" in
        --marketplace) marketplace=true ;;
        --adopt-hacs) adopt=true ;;
    esac
done
if [[ "${adopt}" == true && "${marketplace}" == false ]]; then
    echo "--adopt-hacs only makes sense with --marketplace" >&2
    exit 2
fi

if [[ "${marketplace}" == true ]]; then
    NAME="config-marketplace"
    PORT="${PORT:-8126}"
    VENV="${PWD}/.venv-marketplace"
    HASS="${VENV}/bin/hass"
    HA_PIN="homeassistant==2026.11.*"
else
    NAME="config-hacs"
    PORT="${PORT:-8124}"
    HASS="hass"
fi
CONFIG="${PWD}/${NAME}"
HACS_URL="https://github.com/hacs/integration/releases/latest/download/hacs.zip"
PREVIEW="https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant-preview"

# Is an instance already serving this directory?
#
# Home Assistant 2026.9 takes an advisory `flock` on `<config>/.ha_run.lock`
# and writes its pid there, and it deliberately does not unlink the file on
# exit -- so the file's presence means nothing and the pid in it means
# everything. Checked here rather than left to Home Assistant, for two
# reasons: its own refusal arrives after this script has printed a banner
# promising an instance it is not going to start, and everything below this
# point *writes* to the directory. `scripts/dev/ha_http_port.py` in particular
# edits a store that a running instance holds in memory and rewrites on
# change, which would lose one of the two writes.
running_pid() {
    local lock="${CONFIG}/.ha_run.lock"
    [[ -f "${lock}" ]] || return 1
    python3 - "${lock}" <<'PYTHON'
import json, os, sys

try:
    pid = json.load(open(sys.argv[1]))["pid"]
except (OSError, ValueError, KeyError):
    raise SystemExit(1)
try:
    os.kill(pid, 0)          # signal 0 asks "is it there", and sends nothing
except ProcessLookupError:
    raise SystemExit(1)      # a stale file, which Home Assistant copes with
except PermissionError:
    pass                     # somebody else's process, so it is running
print(pid)
PYTHON
}

update=false
boot=true
for argument in "$@"; do
    case "${argument}" in
        --update) update=true ;;
        --setup-only) boot=false ;;
        --marketplace | --adopt-hacs) ;;
        --reset)
            if pid="$(running_pid)"; then
                echo "${NAME} is being served right now by pid ${pid}." >&2
                echo "Stop it first (kill ${pid}), then reset." >&2
                exit 2
            fi
            # Deliberately not `rm -rf $CONFIG` from a variable that could be
            # empty: an unset CONFIG would make that `rm -rf /`. Each path is
            # spelled out, and checked first.
            if [[ "${marketplace}" == true ]]; then
                target="${PWD}/config-marketplace"
            else
                target="${PWD}/config-hacs"
            fi
            if [[ -d "${target}" ]]; then
                rm -rf "${target}"
                echo "deleted ${NAME}/ -- the next run starts from nothing"
            else
                echo "${NAME}/ does not exist; nothing to reset"
            fi
            exit 0
            ;;
        *)
            echo "unknown option: ${argument}" >&2
            echo "usage: $0 [--marketplace [--adopt-hacs]] [--update] [--setup-only] [--reset]" >&2
            exit 2
            ;;
    esac
done

if pid="$(running_pid)"; then
    cat <<ALREADY
A Home Assistant is already serving ${NAME}/, as pid ${pid}.

  Open it:   http://localhost:${PORT}   (log in as dev / dev)
  Stop it:   kill ${pid}
  Or stop both instances and the simulator:   make stop

Nothing was changed. Home Assistant would have refused to start a second
one anyway -- this says so before setting anything up, because the steps
below write to that directory while it is in use.
ALREADY
    exit 0
fi

if [[ "${marketplace}" == true ]]; then
    if [[ ! -x "${HASS}" ]]; then
        echo "creating ${VENV} with ${HA_PIN} -- a few minutes, once"
        python3 -m venv "${VENV}"
        "${VENV}/bin/pip" install --quiet --upgrade pip
        "${VENV}/bin/pip" install --quiet "${HA_PIN}"
    fi
    if [[ "${adopt}" == true ]]; then
        if [[ -e "${CONFIG}" ]]; then
            echo "${NAME}/ exists already; --reset it first to adopt config-hacs/ afresh." >&2
            exit 2
        fi
        if [[ ! -f "${PWD}/config-hacs/custom_components/hacs/manifest.json" ]]; then
            echo "config-hacs/ has no HACS install to adopt; run make hacs first." >&2
            exit 2
        fi
        cp -a "${PWD}/config-hacs" "${CONFIG}"
        rm -f "${CONFIG}/.ha_run.lock"
        echo "copied config-hacs/ to ${NAME}/ -- 2026.11 takes HACS over on its first boot"
    fi
fi

mkdir -p "${CONFIG}"

if [[ ! -f "${CONFIG}/.HA_VERSION" ]]; then
    "${HASS}" --config "${CONFIG}" --script ensure_config
fi

# No `default_config:`, and the reason is worth keeping.
#
# That bundle depends on `go2rtc`, whose binary ships only inside Home
# Assistant's container images -- a pip install cannot find it, so `go2rtc`
# fails to initialise and takes `default_config` down with it. Three ERROR
# lines on every boot, for a WebRTC camera proxy this instance will never
# use.
#
# Nothing here needs the bundle. `homeassistant/bootstrap.py`'s
# DEFAULT_INTEGRATIONS already sets up frontend, analytics, person, backup
# and the helpers unless recovery mode is on; HACS's manifest declares http,
# websocket_api, lovelace, repairs and persistent_notification, and Home
# Assistant sets a config entry's dependencies up when it loads. So the list
# below is only what somebody looking at this instance would otherwise miss.
if [[ ! -f "${CONFIG}/configuration.yaml" ]] || ! grep -q "hacs_testbed v3" "${CONFIG}/configuration.yaml"; then
    cat > "${CONFIG}/configuration.yaml" <<YAML
# Written by scripts/dev/hacs_testbed.sh -- an instance for testing the HACS
# install of this integration. Delete the directory to start over.
# hacs_testbed v3
#
# No \`http:\` block, deliberately. Home Assistant 2026.9 keeps the HTTP
# config in .storage/http and ignores this file once it has migrated it --
# raising a repair issue to say so. A port set here becomes a *pending*
# config that reverts itself after five minutes, onto :8123 and into the dev
# instance's port.
# scripts/dev/ha_http_port.py writes the port where it is actually read.
#
# No \`default_config:\` either: it depends on go2rtc, whose binary exists
# only in Home Assistant's container images, and its failure takes the whole
# bundle with it. What this instance needs, Home Assistant loads on its own.

# A recorder, so an entity has a graph behind it.
history:

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
if [[ "${marketplace}" == false ]] && { [[ ! -f "${CONFIG}/custom_components/hacs/manifest.json" ]] || [[ "${update}" == true ]]; }; then
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

# The port, written where 2026.9 reads it. Not in configuration.yaml: see
# scripts/dev/ha_http_port.py, which has the whole mechanism. Harmless before the
# first boot, when the store does not exist yet -- it says so and moves on.
python3 "${PWD}/scripts/dev/ha_http_port.py" "${CONFIG}" "${PORT}"

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

if [[ "${marketplace}" == true ]]; then
cat <<NEXT

========================================================================
Home Assistant $("${HASS}" --version) with the built-in Marketplace
${NAME}/                                  http://localhost:${PORT}
========================================================================

  This integration here:  ${installed}

  Onboarding is done for you, in the background: log in as dev / dev.

  What this script cannot do for you

  1  Settings -> Marketplace. Connect GitHub (a device code at
     https://github.com/login/device): adding a custom repository and
     keeping it up to date need it, browsing does not.

  2  Add from link:
     ${PREVIEW}
     type Integration. Then open it and Download, and restart.

  3  Settings -> Devices & services -> Add integration ->
     Sungrow Modbus (preview).

  What is still to find out (Todo.md, Release item 6), once main
  carries the integration

  - Do the five steps from the preview to the main repository keep the
    entity ids and their history on a migrated install?
  - Does a commit-tracked install switch to versions once the mirror
    publishes a release?

========================================================================

NEXT
else
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

  Onboarding is done for you, in the background, as soon as this
  instance is serving: log in as dev / dev. Those credentials are
  deliberately public and only ever acceptable because this directory is
  gitignored and holds fabricated data.

  What this script cannot do for you

  1  Settings -> Devices & services -> Add integration -> HACS.
     It asks you to authorise a GitHub account by typing a code at
     https://github.com/login/device. That is HACS talking to GitHub, not
     to this project, and it cannot be automated from here.

  2  HACS -> three dots -> Custom repositories. Add
     ${PREVIEW}
     with category Integration. Then open it and Download.

  3  Restart Home Assistant. The library comes from PyPI on the way up,
     which is the step that surprises people -- it needs working internet
     and it makes that one boot slower.

  4  Settings -> Devices & services -> Add integration ->
     Sungrow Modbus (preview).

  What to watch for, because this is the install a user gets

  - The version HACS shows is a **commit hash**, not 0.1.0aN. The preview
    channel publishes no releases of its own, so that hash is what a bug
    report should quote.
  - The library is pip-installed from PyPI against the pin in
    manifest.json. If that fails, setup fails with RequirementsNotFound
    and the integration never appears -- which is what
    scripts/release/check_pinned_library.py exists to catch before a user does.
  - Nothing in this directory is the working tree. A change you make in
    the repository does **not** appear here until it reaches the preview
    channel. Use \`make dev\` for the other thing.

  First boot downloads component requirements and logs setup errors while
  it does; the UI 404s until it settles. Not a bug.

========================================================================

NEXT
fi

if [[ "${boot}" == false ]]; then
    echo "--setup-only: not booting. \`make hacs\` when you want it."
    exit 0
fi

# Onboarding, in the background, while Home Assistant starts in front of it.
#
# A fresh instance opens on `onboarding.html` and asks for an account before
# it shows anything, which is friction with no payoff here: the account is
# local to a gitignored directory, it guards fabricated data, and it is the
# same dev / dev the other instance uses. So this asks the API instead.
#
# It has to be concurrent, because the endpoint only exists once the instance
# is serving -- and it is idempotent, so a second boot prints one line and
# stops. Its output interleaves with the log, which is why it says what it
# did rather than being silent.
(
    python3 "${PWD}/scripts/dev/ha_onboard.py" --url "http://127.0.0.1:${PORT}" \
        --username dev --password dev || true
) &

# Without `--debug`, for the reason spelled out in scripts/dev/develop.sh: it is
# a loop mode rather than a logging flag, and an asyncio debug loop makes this
# integration's network search report an empty network. This testbed exists to
# see what a user gets, and a user does not run with it.
#
# `SETUP_PORT` covers the first boot, which `ha_http_port.py` cannot: there is
# no `.storage/http` to pin yet, and Home Assistant would create one on :8123,
# into the dev instance's port. It is `http`'s own default for an instance with
# no stored port (`default_server_port` in `homeassistant/components/http/
# config.py`), so on every later boot the pinned store decides and this is
# ignored.
#
# A loop rather than `exec`, because *Restart* in the UI is Home Assistant
# exiting with 100 (`RESTART_EXIT_CODE`) and leaving the start to whatever
# launched it -- the Supervisor, or here this script. Any other exit, a stop or
# Ctrl-C included, ends the testbed.
while true; do
    status=0
    SETUP_PORT="${PORT}" "${HASS}" --config "${CONFIG}" || status=$?
    if [[ "${status}" -ne 100 ]]; then
        exit "${status}"
    fi
    echo "Home Assistant asked for a restart (exit 100); starting it again"
    # The store exists by now, and nothing holds it between the two runs.
    python3 "${PWD}/scripts/dev/ha_http_port.py" "${CONFIG}" "${PORT}"
done
