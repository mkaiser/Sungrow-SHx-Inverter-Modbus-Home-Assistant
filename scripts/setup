#!/usr/bin/env bash
# Install everything needed to develop the integration.
set -e

cd "$(dirname "$0")/.."

# Two passes: the first lets pip upgrade itself before the bulk install.
python3 -m pip install --upgrade pip
python3 -m pip install --requirement requirements_dev.txt
