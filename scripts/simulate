#!/usr/bin/env bash
# Regenerate the register seed and serve it over Modbus TCP on :5020.
set -e

cd "$(dirname "$0")/.."

python3 scripts/gen_simulator_registers.py
exec python3 scripts/simulator.py "$@"
