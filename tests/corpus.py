"""The committed documents in `device-survey/results/`, split by kind.

Inverter, wallbox, iHomeManager and SG documents sit side by side. A wallbox
read at its own address is a document of its own (`"document": "wallbox"`,
no `device`), and so is an iHomeManager's (`"document": "ihomemanager"`), so
every check written for an inverter document takes `INVERTER_DOCUMENTS`,
`tests/test_wallbox_documents.py` takes `WALLBOX_DOCUMENTS` and
`tests/test_ihomemanager.py` takes `IHOMEMANAGER_DOCUMENTS`. Split by what
the file says it is, not by its name. An SG's is
`"document": "string_inverter"`, with a `device` of its own shape.
"""

from __future__ import annotations

import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "device-survey" / "results"


def _kind(path: Path) -> str | None:
    return json.loads(path.read_text(encoding="utf-8")).get("document")


ALL_DOCUMENTS = sorted(
    path
    for folder in ("inverter", "wallbox", "ihomemanager", "logger", "string_inverter")
    for path in (FOLDER / folder).glob("*.json")
)
WALLBOX_DOCUMENTS = [path for path in ALL_DOCUMENTS if _kind(path) == "wallbox"]
IHOMEMANAGER_DOCUMENTS = [
    path for path in ALL_DOCUMENTS if _kind(path) == "ihomemanager"
]
LOGGER_DOCUMENTS = [path for path in ALL_DOCUMENTS if _kind(path) == "logger"]
STRING_INVERTER_DOCUMENTS = [
    path for path in ALL_DOCUMENTS if _kind(path) == "string_inverter"
]
INVERTER_DOCUMENTS = [path for path in ALL_DOCUMENTS if _kind(path) is None]
