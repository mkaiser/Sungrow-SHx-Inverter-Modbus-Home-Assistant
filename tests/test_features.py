"""The feature report: each feature set, and how far a diagnosis tested it.

It summarises evidence the document already holds, so what these tests pin is
that it never claims more than that evidence: a dongle's readback confirms
nothing, a simulator settles nothing, a finding outranks a match, and a read
alone is only *readable*.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sungrow_modbus import features
from sungrow_modbus.capability_test import procedure
from sungrow_modbus.capability_test.coverage import EFFECT_FIELDS, WATCHED, WRITTEN
from sungrow_modbus.diagnosis_document import SCHEMA, attach_capability_test

REPO = Path(__file__).resolve().parent.parent
DOCUMENTS = sorted((REPO / "device-diagnosis" / "results" / "inverter").glob("*.json"))


def _state(document: dict[str, Any], key: str) -> str:
    rows = {row["feature"]: row for row in features.feature_report(document)}
    return str(rows[key]["state"])


def _document(**block: Any) -> dict[str, Any]:
    conditions = {"direct_connection": True, **block.pop("conditions", {})}
    return {
        "schema": SCHEMA,
        "readings": {"values": block.pop("values", {})},
        "capability_test": {"conditions": conditions, **block},
    }


def test_every_check_and_every_written_field_belongs_to_a_feature_set() -> None:
    """A check the procedure runs that no set claims would vanish from the report."""
    checks = {check for feature in features.FEATURE_SETS for check in feature.checks}
    fields = {field for feature in features.FEATURE_SETS for field in feature.fields}
    assert set(EFFECT_FIELDS) <= checks
    assert fields >= WRITTEN
    assert fields >= WATCHED


def test_a_cable_readback_confirms_and_a_dongle_readback_does_not() -> None:
    row = {"field": "battery_min_soc", "verdict": procedure.MATCH}
    cable = _document(readback=[row])
    dongle = _document(readback=[row], conditions={"direct_connection": False})

    assert _state(cable, "battery_soc_limits") == features.CONFIRMED
    assert _state(dongle, "battery_soc_limits") == features.INCONCLUSIVE


def test_a_finding_outranks_a_match() -> None:
    document = _document(
        readback=[
            {"field": "battery_min_soc", "verdict": procedure.MATCH},
            {"field": "battery_max_soc", "verdict": procedure.SCALED},
        ]
    )
    assert _state(document, "battery_soc_limits") == features.WRONG_SCALE


def test_a_refusal_holds_through_a_dongle() -> None:
    """An exception is the device answering, whatever is in the path."""
    document = _document(
        readback=[{"field": "export_power_limit", "verdict": procedure.REFUSED}],
        conditions={"direct_connection": False},
    )
    assert _state(document, "export_limit") == features.REFUSED


def test_a_watched_effect_confirms_through_a_dongle() -> None:
    document = _document(
        effects=[{"check": "PV generation cut", "verdict": procedure.CONFIRMED}],
        conditions={"direct_connection": False},
    )
    assert _state(document, "pv_cut") == features.CONFIRMED


def test_a_simulated_run_settles_nothing() -> None:
    document = _document(
        readback=[{"field": "battery_min_soc", "verdict": procedure.MATCH}],
        conditions={"simulated": True},
        values={"battery_min_soc": 10.0},
    )
    assert _state(document, "battery_soc_limits") == features.READABLE


def test_a_capability_the_integration_withholds_is_not_available() -> None:
    document = _document(conditions={"capabilities": ["battery"]})
    assert _state(document, "pv_cut") == features.NOT_AVAILABLE
    assert _state(document, "backup_mode") == features.NOT_READ


def test_a_value_that_did_not_read_is_not_readable() -> None:
    """None is no answer, and no answer is not a capability."""
    document = {"schema": SCHEMA, "readings": {"values": {"backup_mode_raw": None}}}
    assert _state(document, "backup_mode") == features.NOT_READ
    document["readings"]["values"]["backup_mode_raw"] = 0xAA
    assert _state(document, "backup_mode") == features.READABLE


def test_attaching_a_block_recomputes_the_report() -> None:
    document: dict[str, Any] = {"schema": SCHEMA, "readings": {"values": {}}}
    block = {
        "conditions": {"direct_connection": True},
        "restart": {"verdict": procedure.CONFIRMED},
    }
    attach_capability_test(document, block, serial="A123456789")

    rows = {row["feature"]: row for row in document["features"]}
    assert rows["start_stop"]["state"] == features.CONFIRMED


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: p.stem)
def test_every_committed_document_gets_a_report(path: Path) -> None:
    """Schema 24 and before keep their block under `control_test`."""
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = features.feature_report(document)

    assert [row["feature"] for row in rows] == [f.key for f in features.FEATURE_SETS]
    assert all(row["state"] in features.STATES for row in rows)
    restart = (document.get("control_test") or {}).get("restart") or {}
    if restart.get("verdict") == procedure.CONFIRMED:
        assert {r["feature"]: r for r in rows}["start_stop"]["state"] == (
            features.CONFIRMED
        )
