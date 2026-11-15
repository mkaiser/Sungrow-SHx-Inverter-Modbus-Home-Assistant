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

# wg and wg-quick, for a WireGuard tunnel to another owner's inverter from
# inside the container (runArgs in devcontainer.json grants NET_ADMIN).
# poppler-utils (pdftotext, pdftoppm), to read manufacturers' manuals and
# datasheets: Claude Code's PDF reading renders pages with pdftoppm.
#
# The last three are Home Assistant's, not this integration's, and they are
# here to keep a boot log readable. `config/configuration.yaml` leaves
# `default_config:` out, but onboarding creates entries of its own -- Google
# Translate text-to-speech among them -- which pull in `ffmpeg` and `camera`
# anyway, and each then logs a traceback about a missing system library on
# every boot. Twenty lines of noise that mean nothing is how a real error
# gets missed.
#
#   ffmpeg         the tts entry onboarding creates
#   libturbojpeg0  camera's snapshot path, which tts drags in
#   libpcap0.8     scapy, under Home Assistant's `dhcp` -- which this
#                  integration *does* use (`dhcp` in `manifest.json`), so
#                  without it the DHCP discovery of an inverter cannot be
#                  tried in this container at all
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    wireguard-tools poppler-utils ffmpeg libturbojpeg0 libpcap0.8
