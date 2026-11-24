"""The cards the integration's dashboard shows, shipped in the wheel.

`power-flow-card-plus` and `energy-flow-card-plus` by flixlix (MIT) are not
committed here: the release fetches the pinned versions, checks their SHA-256
and puts them, with their licences, beside this file
(`scripts/release/fetch_cards.py`). A source checkout that has not run that has
no bundles, and the dashboard shows tiles instead.
"""

from __future__ import annotations

from pathlib import Path

DIRECTORY = Path(__file__).parent
#: The power flow, and the energy flow of the day.
BUNDLES = ("power-flow.js", "energy-flow.js")
LICENCES = ("LICENSE.power-flow-card-plus", "LICENSE.energy-flow-card-plus")


def present() -> list[str]:
    """Return the bundles that are here. Reads the disk."""
    return [name for name in BUNDLES if (DIRECTORY / name).is_file()]
