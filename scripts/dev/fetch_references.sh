#!/usr/bin/env bash
# Clone the upstream sources this integration is written against into
# .reference/ (gitignored), so their real code can be read and grepped
# instead of relying on documentation that may lag behind.
#
# Home Assistant core is cloned blobless + sparse, which keeps it to a few
# MB: the components this integration mirrors, core's recorder and sensor
# tests, and `script/` -- which holds hassfest, run from here before tagging
# (AGENTS.md has the command). The sparse set is applied on every run, so an
# older clone gains what was added to it.
set -e

cd "$(dirname "$0")/../.."
mkdir -p .reference

if [[ ! -d .reference/core ]]; then
    git clone --filter=blob:none --sparse --depth 1 \
        https://github.com/home-assistant/core.git .reference/core
else
    git -C .reference/core pull --depth 1 --ff-only
fi
git -C .reference/core sparse-checkout set \
    homeassistant/components/modbus \
    homeassistant/components/sofar \
    homeassistant/components/fronius \
    tests/components/recorder \
    tests/components/sensor \
    script

for repo in home-assistant-libs/modbus-connection pymodbus-dev/pymodbus; do
    name="${repo##*/}"
    if [[ ! -d ".reference/${name}" ]]; then
        git clone --depth 1 "https://github.com/${repo}.git" ".reference/${name}"
    else
        git -C ".reference/${name}" pull --depth 1 --ff-only
    fi
done

echo "Reference sources in .reference/"
