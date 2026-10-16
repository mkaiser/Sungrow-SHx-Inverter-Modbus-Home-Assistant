"""The committed documents in `device-fingerprints/`, split by kind.

Inverter and wallbox documents sit side by side. A wallbox read at its own
address is a document of its own (`"document": "wallbox"`, no `device`), so
every check written for an inverter document takes `INVERTER_DOCUMENTS`, and
`tests/test_wallbox_documents.py` takes `WALLBOX_DOCUMENTS`. Split by what
the file says it is, not by its name.
"""

from __future__ import annotations

import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "device-fingerprints"


def _is_wallbox(path: Path) -> bool:
    return json.loads(path.read_text(encoding="utf-8")).get("document") == "wallbox"


ALL_DOCUMENTS = sorted(
    [*(FOLDER / "inverter").glob("*.json"), *(FOLDER / "wallbox").glob("*.json")]
)
WALLBOX_DOCUMENTS = [path for path in ALL_DOCUMENTS if _is_wallbox(path)]
INVERTER_DOCUMENTS = [path for path in ALL_DOCUMENTS if not _is_wallbox(path)]
