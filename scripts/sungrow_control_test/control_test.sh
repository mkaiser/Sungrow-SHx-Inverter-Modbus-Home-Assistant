#!/bin/sh
# Run the Sungrow control test: ./control_test.sh <host> --dry-run
#
# **The control test writes to your inverter.** Start with --dry-run, which
# writes nothing. This launcher only finds a Python for it; what the test does
# and when it asks is in sungrow_control_test.py.
#
# The test runs on the published `sungrow-modbus` library, pinned in the
# PEP 723 header of sungrow_control_test.py. This finds a way to give it that:
#
#   1. uv, if it is installed -- it fetches a suitable Python and the pinned
#      library by itself, into a cache, and touches nothing else;
#   2. otherwise a Python 3.13+ that already has exactly that library;
#   3. otherwise it offers to install uv, and asks first.
#
# Every argument is handed to the test, and so is its exit code: 0 to 5 each
# mean something -- 5 that the house was left changed -- and this script's own
# failures are 1.

set -u

cd "$(dirname "$0")" || exit 1

SCRIPT=sungrow_control_test.py

# The pin and the dependency list, read from the header so the version lives
# in one place.
PIN=$(sed -n 's/^#[[:space:]]*dependencies = \[.*"sungrow-modbus==\([^"]*\)".*/\1/p' "$SCRIPT" | head -n 1)
DEPENDENCIES=$(sed -n 's/^#[[:space:]]*dependencies = \[\(.*\)\]$/\1/p' "$SCRIPT" | head -n 1 | sed 's/, / /g')
if [ -z "$PIN" ]; then
    echo "$SCRIPT names no sungrow-modbus version in its header; this copy is damaged." >&2
    exit 1
fi

find_uv() {
    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return 0
    fi
    # Where the installer puts it, which a shell started before the install
    # does not have on its PATH yet.
    if [ -x "$HOME/.local/bin/uv" ]; then
        echo "$HOME/.local/bin/uv"
        return 0
    fi
    return 1
}

# Whether this interpreter can run the test as it is: 3.13 or newer, the
# pinned library exactly, and the Modbus backend the test talks through.
ready() {
    "$1" - "$PIN" >/dev/null 2>&1 <<'EOF'
import sys
from importlib.metadata import version

if sys.version_info < (3, 13):
    raise SystemExit(1)
if version("sungrow-modbus") != sys.argv[1]:
    raise SystemExit(1)
import modbus_connection.tmodbus  # noqa: F401
EOF
}

manual() {
    cat >&2 <<EOF

To run the control test, install uv and run this again:

    https://docs.astral.sh/uv/getting-started/installation/

Or, with Python 3.13 or newer, install the library and run it directly:

    python3 -m pip install $DEPENDENCIES
    python3 $SCRIPT <host> --dry-run
EOF
}

while :; do
    if UV=$(find_uv); then
        exec "$UV" run --script "$SCRIPT" "$@"
    fi

    for candidate in python3 python python3.14 python3.13; do
        if command -v "$candidate" >/dev/null 2>&1 && ready "$candidate"; then
            exec "$candidate" "$SCRIPT" "$@"
        fi
    done

    echo "The control test needs uv, or a Python 3.13+ with sungrow-modbus $PIN, and"
    echo "neither is here."
    if [ ! -t 0 ]; then
        # Nobody to ask: piped, or started from something that is not a
        # terminal. Installing software unasked is not an option.
        manual
        exit 1
    fi
    printf "Install uv (from astral.sh)? [y/N] "
    read -r answer || answer=""
    case "$answer" in
        [yY]*) ;;
        *)
            manual
            exit 1
            ;;
    esac

    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh || exit 1
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh || exit 1
    else
        echo "Neither curl nor wget is here to download the installer with." >&2
        manual
        exit 1
    fi
    if ! find_uv >/dev/null; then
        echo "uv was installed, but not where this looks for it." >&2
        manual
        exit 1
    fi
done
