#!/bin/sh
# Run the Sungrow survey: ./survey.sh [the survey's own arguments]
#
# The survey runs on the published `sungrow-modbus` library, pinned in the
# PEP 723 header of sungrow_survey.py. This finds a way to give it that:
#
#   1. uv, if it is installed -- it fetches a suitable Python and the pinned
#      library by itself, into a cache, and touches nothing else;
#   2. otherwise a Python 3.13+ that already has exactly that library;
#   3. otherwise it offers to install uv, and asks first.
#
# The survey reads, and writes only if its last question is answered yes:
# then it runs the control test after the reading. `control` as the first
# argument hands the rest to the control test itself (--dry-run, --restore
# <snapshot>, --start-only).
#
# Every argument is handed to the survey, and so is its exit code: 0 to 5
# each mean something -- 5 that the house was left changed -- and this
# script's own failures are 1.

set -u

# Relative paths in the environment and the arguments are the caller's, not
# this folder's; the script resolves its path arguments against this.
ORIGIN=$(pwd)
export SUNGROW_CALLER_DIR="$ORIGIN"
cd "$(dirname "$0")" || exit 1

SCRIPT=python/sungrow_survey.py

# The pin and the dependency list, read from the header so the version lives
# in one place.
# One quoted entry per line between `# dependencies = [` and `# ]`.
DEPENDENCIES=$(sed -n '/^# dependencies = \[/,/^# \]/s/^#[[:space:]]*\("[^"]*"\),\{0,1\}$/\1/p' "$SCRIPT" | tr '\n' ' ' | sed 's/ $//')
PIN=$(printf '%s\n' "$DEPENDENCIES" | sed -n 's/.*"sungrow-modbus==\([^"]*\)".*/\1/p')
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

# Whether this interpreter can run the survey as it is: 3.13 or newer, the
# pinned library exactly, and the Modbus backend the survey talks through.
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

To run the survey, install uv and run this again:

    https://docs.astral.sh/uv/getting-started/installation/

Or, with Python 3.13 or newer, install the library and run it directly:

    python3 -m pip install $DEPENDENCIES
    python3 $SCRIPT
EOF
}

# A library other than the published one, for trying a version that is not
# released yet: a wheel (`make wheel`), or a source folder with its
# pyproject.toml. uv installs the pin as usual and lays this over it. Unset --
# which is how a contributor runs this -- nothing here happens.
if [ -n "${SUNGROW_MODBUS_LIBRARY:-}" ]; then
    LIBRARY=$SUNGROW_MODBUS_LIBRARY
    case "$LIBRARY" in
        /*) ;;
        *) LIBRARY="$ORIGIN/$LIBRARY" ;;
    esac
    if [ -f "$LIBRARY" ] && [ "${LIBRARY%.whl}" != "$LIBRARY" ]; then
        WITH=--with
    elif [ -f "$LIBRARY/pyproject.toml" ]; then
        WITH=--with-editable
    else
        echo "SUNGROW_MODBUS_LIBRARY=$SUNGROW_MODBUS_LIBRARY is neither a .whl file nor a folder with a pyproject.toml." >&2
        exit 1
    fi
    if ! UV=$(find_uv); then
        echo "SUNGROW_MODBUS_LIBRARY needs uv, and uv is not here." >&2
        exit 1
    fi
    echo "Running on $LIBRARY, NOT the published sungrow-modbus $PIN." >&2
    exec "$UV" run "$WITH" "$LIBRARY" --script "$SCRIPT" "$@"
fi

while :; do
    if UV=$(find_uv); then
        exec "$UV" run --script "$SCRIPT" "$@"
    fi

    for candidate in python3 python python3.14 python3.13; do
        if command -v "$candidate" >/dev/null 2>&1 && ready "$candidate"; then
            exec "$candidate" "$SCRIPT" "$@"
        fi
    done

    echo "The survey needs uv, or a Python 3.13+ with sungrow-modbus $PIN, and"
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

    # Downloaded whole before anything runs: `download | sh` reports only
    # whether sh succeeded, and sh succeeds on an empty script, so a failed
    # download would go on as though uv had been installed.
    URL=https://astral.sh/uv/install.sh
    if command -v curl >/dev/null 2>&1; then
        installer=$(curl -LsSf "$URL") && [ -n "$installer" ] ||
            { echo "Could not download $URL." >&2; manual; exit 1; }
        printf '%s\n' "$installer" | sh || exit 1
    elif command -v wget >/dev/null 2>&1; then
        installer=$(wget -qO- "$URL") && [ -n "$installer" ] ||
            { echo "Could not download $URL." >&2; manual; exit 1; }
        printf '%s\n' "$installer" | sh || exit 1
    elif command -v python3 >/dev/null 2>&1; then
        # A slim container image has neither of the two above, and astral's
        # installer needs one of them itself. pip puts uv in ~/.local/bin.
        python3 -m pip install --user --quiet uv || { manual; exit 1; }
    else
        echo "Neither curl, wget nor python3 is here to install uv with." >&2
        manual
        exit 1
    fi
    if ! find_uv >/dev/null; then
        echo "uv was installed, but not where this looks for it." >&2
        manual
        exit 1
    fi
done
