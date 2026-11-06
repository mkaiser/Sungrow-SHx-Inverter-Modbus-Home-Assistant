#!/usr/bin/env bash
# Run hassfest on this integration, the way CI's `home-assistant/actions/hassfest`
# does, before tagging.
#
# Current core's hassfest is built against current core: it imports symbols
# Home Assistant 2026.10 does not have (`LORAWAN_SCHEMA`), so it cannot run in
# the dev environment, which is held at the version the test plugin supports.
# It runs in `.venv-marketplace/` instead, the Home Assistant 2026.11 venv that
# `make marketplace` also uses, created here when missing. Its two extra
# dependencies, tqdm and ruff, go into that venv, never into the dev one.
#
# What it needs from core is read from the reference clone (`make refs`):
# hassfest itself, the `packages/hassfest` library, and the strings that say
# which `categories` and `connectivity` values exist. Without those strings an
# unknown value is not reported at all, so a clone lacking them says nothing.
#
#     scripts/dev/hassfest.sh
#
# Exits 1 on an error; warnings are printed and do not fail, as in CI.
set -euo pipefail

cd "$(dirname "$0")/../.."

VENV="${PWD}/.venv-marketplace"
CORE="${PWD}/.reference/core"

if [[ ! -d "${CORE}/script/hassfest" ]]; then
    echo "no reference clone of core; run make refs first" >&2
    exit 2
fi
if [[ ! -x "${VENV}/bin/python" ]]; then
    echo "creating ${VENV} with homeassistant==2026.11.* -- a few minutes, once"
    python3 -m venv "${VENV}"
    "${VENV}/bin/pip" install --quiet --upgrade pip
    "${VENV}/bin/pip" install --quiet "homeassistant==2026.11.*"
fi
"${VENV}/bin/python" -c "import tqdm, ruff" 2>/dev/null \
    || "${VENV}/bin/pip" install --quiet tqdm ruff

# Appended, not prepended: the clone's `homeassistant` is a partial tree, and
# the installed one has to win.
exec "${VENV}/bin/python" -c "
import sys
sys.path.append('${CORE}/packages/hassfest')
sys.path.append('${CORE}')
sys.argv = ['hassfest', '--core-path', '${CORE}',
            '--integration-path', 'custom_components/sungrow_modbus',
            '--action', 'validate']
from script.hassfest.__main__ import main
raise SystemExit(main())
" | grep -v '^Validating '
