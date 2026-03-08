#!/bin/bash
#
# Create and activate Python virtual environment with pymodbus
#
# IMPORTANT: This script must be sourced, not executed!
# Usage:
#   source ./createVenv.sh
#   . ./createVenv.sh

# Check if script is being sourced (not executed)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "ERROR: This script must be sourced, not executed!"
    echo ""
    echo "Usage:"
    echo "  source ./createVenv.sh"
    echo "  OR"
    echo "  . ./createVenv.sh"
    echo ""
    echo "Reason: The virtual environment activation needs to affect your current shell."
    exit 1
fi

echo "Creating virtual environment in .venv..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing pymodbus..."
pip install pymodbus

echo ""
echo "✓ Virtual environment activated!"
echo -e "\033[38;5;214mTo deactivate the python virtual environment, run: deactivate\033[0m"
echo ""
echo "You can now run the modbus access script:"
echo "  ./modbus_regAccess.py -h        # Show help"
echo "  ./modbus_regAccess.py INPUT 5214    # Read a register"