"""The pin in manifest.json is a promise about a published wheel.

`scripts/check_pinned_library.py` is the only thing in this repository that
tests that promise, because everything else runs against the editable install
from `src/`, which satisfies whatever the source tree can satisfy. So these
tests are about the *check*, not about the library: they build wheels by hand,
with and without the module in question, and assert it says so.

No network. The published-wheel mode is exercised only through `provided()`,
which takes a path.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "check_pinned_library.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_pinned_library", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


check = _load()


def _wheel(path: Path, modules: dict[str, str]) -> Path:
    """Build a wheel-shaped zip holding exactly the given `module -> source`."""
    wheel = path / "sungrow_modbus-9.9.9-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, source in modules.items():
            member = name.replace(".", "/")
            if name == "sungrow_modbus":
                member = f"{member}/__init__.py"
            else:
                member = f"{member}.py"
            archive.writestr(member, source)
        archive.writestr(
            "sungrow_modbus-9.9.9.dist-info/METADATA", "Name: sungrow-modbus\n"
        )
    return wheel


def test_the_pin_is_read_out_of_the_manifest():
    manifest = json.loads(
        (REPO / "custom_components" / "sungrow_modbus" / "manifest.json").read_text()
    )
    assert f"sungrow-modbus=={check.pinned_version()}" in manifest["requirements"]


def test_every_library_import_in_the_integration_is_collected():
    wanted = check.required()
    # Not an exhaustive list -- the point is that both import shapes land.
    assert "sungrow_modbus" in wanted
    assert "sungrow_modbus.fingerprint" in wanted
    assert "COMPONENTS" in wanted["sungrow_modbus"]


def test_a_name_defined_at_module_level_counts():
    names = check.public_names(
        "X = 1\ndef f(): pass\nclass C: pass\nfrom os import path\nY: int = 2\n", "x.py"
    )
    assert names == {"X", "f", "C", "path", "Y"}


def test_a_missing_module_is_reported(tmp_path, capsys):
    wheel = _wheel(tmp_path, {"sungrow_modbus": "TIERS = ()\n"})
    assert check.report(wheel, "test") == check.BROKEN
    out = capsys.readouterr().out
    assert "is not in the wheel" in out


def test_a_wheel_that_has_everything_passes(tmp_path, capsys):
    # Mirror the real imports: every module the integration names, each
    # exporting every name it asks for.
    modules = {}
    for module, names in check.required().items():
        source = "".join(f"{name} = None\n" for name in sorted(names))
        modules[module] = source or "\n"
    wheel = _wheel(tmp_path, modules)
    assert check.report(wheel, "test") == check.OK
    assert "every import resolves" in capsys.readouterr().out


def test_a_submodule_import_is_not_a_missing_symbol(tmp_path, capsys):
    """`from sungrow_modbus import fingerprint` resolves without `__init__` help.

    The first version of the script called this a missing symbol and failed on
    a correct tree, which is the one way a guard like this does harm: it gets
    switched off.
    """
    wheel = _wheel(
        tmp_path,
        {"sungrow_modbus": "\n", "sungrow_modbus.fingerprint": "SCHEMA = 17\n"},
    )
    gaps = check.provided(wheel)[0]
    assert "sungrow_modbus.fingerprint" in gaps
    assert check.report(wheel, "test") == check.BROKEN  # other modules are absent
    assert "does not provide fingerprint" not in capsys.readouterr().out


def test_a_wheel_that_is_not_there_is_undetermined_not_broken(tmp_path):
    """Report an unreadable wheel as undetermined, never as a promise that holds."""
    assert check.main(["--wheel", str(tmp_path / "nothing.whl")]) == check.UNDETERMINED


@pytest.mark.parametrize("code", [check.OK, check.BROKEN, check.UNDETERMINED])
def test_the_three_outcomes_are_distinct(code):
    assert {check.OK, check.BROKEN, check.UNDETERMINED} == {0, 1, 2}
