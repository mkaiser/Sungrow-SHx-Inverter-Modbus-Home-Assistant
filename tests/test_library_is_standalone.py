"""The device library must not depend on Home Assistant.

This is the architectural boundary the two-package split exists to create:
`src/sungrow_modbus` knows registers and decoding, `custom_components/` knows
Home Assistant, and the library can therefore be tested without Home
Assistant, used from any Python program, and released on its own.

Nothing but discipline enforced that until this test. A single convenient
`from homeassistant...` import would dissolve the boundary silently, and the
suite would keep passing because Home Assistant is installed here anyway.
"""

from __future__ import annotations

import ast
from pathlib import Path
import tomllib

LIBRARY = Path(__file__).resolve().parent.parent / "src" / "sungrow_modbus"
PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

#: Anything the library importing would break the boundary.
FORBIDDEN_ROOTS = {"homeassistant", "custom_components", "voluptuous"}


def _imported_roots(path: Path) -> set[str]:
    """Return the top-level module names imported by one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_library_imports_nothing_from_home_assistant() -> None:
    offenders: dict[str, set[str]] = {}
    for path in sorted(LIBRARY.rglob("*.py")):
        bad = _imported_roots(path) & FORBIDDEN_ROOTS
        if bad:
            offenders[str(path.relative_to(LIBRARY.parent.parent))] = bad
    assert not offenders, (
        f"the device library must stay Home Assistant free, but: {offenders}"
    )


def test_library_declares_no_home_assistant_dependency() -> None:
    dependencies = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"][
        "dependencies"
    ]
    roots = {
        d.split()[0].split(">")[0].split("=")[0].split("[")[0] for d in dependencies
    }
    assert "homeassistant" not in roots, dependencies
