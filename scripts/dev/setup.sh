#!/usr/bin/env bash
# Install everything needed to develop the integration.
set -e

cd "$(dirname "$0")/../.."

# First, before anything reads a file: a clone made by Git for Windows and
# opened here can carry CRLF line endings, which break scripts and tests.
python3 scripts/dev/check_line_endings.py --fix

# Two passes: the first lets pip upgrade itself before the bulk install.
python3 -m pip install --upgrade pip
python3 -m pip install --requirement requirements_dev.txt

# A headless browser for the docs' screenshots (doc/development.md,
# "Screenshots for the docs"). Playwright gets a venv of its own, so its
# dependencies never meet Home Assistant's pins, and Chromium's headless shell
# its system libraries from apt (`--with-deps` runs apt through sudo).
SCREENSHOT_VENV="$HOME/.local/share/sungrow-screenshots"
python3 -m venv "$SCREENSHOT_VENV"
"$SCREENSHOT_VENV/bin/pip" install --quiet --upgrade pip playwright
"$SCREENSHOT_VENV/bin/playwright" install --with-deps chromium-headless-shell
