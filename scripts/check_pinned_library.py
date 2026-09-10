#!/usr/bin/env python3
"""Check that the pinned library provides what the integration imports.

`manifest.json` pins `sungrow-modbus==X.Y.Z`, and Home Assistant pip-installs
that exact version on the first start after somebody copies the integration
in. So the integration's `from sungrow_modbus... import ...` lines are a
promise about a **published artefact**, and nothing in this repository tested
that promise: every test, and the whole dev container, runs against the
editable install from `src/`, which satisfies any import the source tree can
satisfy.

That gap shipped. Between `v0.1.0a1` and `v0.1.0a2` the integration began
importing `sungrow_modbus.fingerprint`, a module added after the a1 wheel was
built, while the manifest still pinned a1. Every test passed, `ruff` passed,
hassfest passed, the release was green -- and a copy of the branch could not
start, with an `ImportError` at the moment a user clicked *Add integration*.
It was found by unzipping the wheel by hand. This is that, as a command.

    python scripts/check_pinned_library.py --wheel dist/*.whl   # a local build
    python scripts/check_pinned_library.py                      # what is on PyPI

**Only the first mode is a CI gate**, and the distinction is the point:

- `--wheel` asks whether the wheel built from *this tree* serves *this*
  integration. That is answerable offline, and true whenever the tree is
  consistent, so `make check` can gate on it. It catches a module the build
  configuration does not pick up -- invisible to every other check, because an
  editable install has no build configuration.
- Without `--wheel` it downloads the version the manifest pins and asks the
  same question of it. On a development branch that is legitimately red: the
  integration moves ahead of the last release, which is why
  `doc/installing_a_preview.md` says to install a tag and not the branch. Run
  it before telling anyone to install something, and after a release.

Nothing here executes the downloaded wheel. Modules and their public names are
read with `ast`, so a wheel is inspected, never trusted.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parent.parent
INTEGRATION = REPO / "custom_components" / "sungrow_modbus"
MANIFEST = INTEGRATION / "manifest.json"
LIBRARY = "sungrow_modbus"
DISTRIBUTION = "sungrow-modbus"
PYPI = "https://pypi.org/pypi/{name}/{version}/json"

# Exit codes, so a caller can tell "the promise is broken" from "I could not
# find out". A release must never treat the second as the first.
OK = 0
BROKEN = 1
UNDETERMINED = 2


def pinned_version() -> str:
    """Read the version manifest.json promises, straight out of `requirements`."""
    manifest = json.loads(MANIFEST.read_text())
    for requirement in manifest.get("requirements", []):
        name, _, version = requirement.partition("==")
        if name.strip() == DISTRIBUTION and version:
            return version.strip()
    raise SystemExit(f"{MANIFEST} has no {DISTRIBUTION}== pin in its requirements")


def required() -> dict[str, set[str]]:
    """Collect what the integration imports from the library: module -> names.

    The empty module name is the package itself, so `from sungrow_modbus
    import TIERS` is recorded against `sungrow_modbus`.
    """
    wanted: dict[str, set[str]] = {}
    for source in sorted(INTEGRATION.glob("*.py")):
        tree = ast.parse(source.read_text(), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == LIBRARY or module.startswith(f"{LIBRARY}."):
                    names = {alias.name for alias in node.names}
                    wanted.setdefault(module, set()).update(names)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == LIBRARY or alias.name.startswith(f"{LIBRARY}."):
                        wanted.setdefault(alias.name, set())
    return wanted


def public_names(source: str, filename: str) -> set[str]:
    """Collect the module-level names a source file defines or imports.

    Read rather than executed, and deliberately generous: a name assigned
    inside `if TYPE_CHECKING` or under a `try` still counts, because the
    question here is "would this import resolve", not "is this good API".
    """
    names: set[str] = set()
    tree = ast.parse(source, filename=filename)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom | ast.Import):
            names.update(
                alias.asname or alias.name.split(".")[0] for alias in node.names
            )
    return names


def provided(wheel: Path) -> tuple[dict[str, set[str]], list[str]]:
    """Collect what a wheel provides: per module its names, plus the file list."""
    modules: dict[str, set[str]] = {}
    with zipfile.ZipFile(wheel) as archive:
        members = archive.namelist()
        for member in members:
            if not member.endswith(".py"):
                continue
            parts = member.split("/")
            if not parts or parts[0] != LIBRARY:
                continue
            source = archive.read(member).decode("utf-8")
            stem = member[: -len(".py")].replace("/", ".")
            if stem.endswith(".__init__"):
                stem = stem[: -len(".__init__")]
            modules[stem] = public_names(source, member)
    return modules, sorted(m for m in members if m.endswith(".py"))


def download(version: str, into: Path) -> Path:
    """Fetch the wheel for one published version. Raises on anything unclear."""
    url = PYPI.format(name=DISTRIBUTION, version=version)
    try:
        with urllib.request.urlopen(url, timeout=30) as answer:
            release = json.load(answer)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise LookupError(f"{DISTRIBUTION} {version} is not on PyPI") from error
        raise LookupError(f"PyPI answered {error.code} for {version}") from error
    except OSError as error:  # no network, DNS, TLS
        raise LookupError(f"could not reach PyPI: {error}") from error

    wheels = [f for f in release.get("urls", []) if f["filename"].endswith(".whl")]
    if not wheels:
        raise LookupError(f"{DISTRIBUTION} {version} has no wheel on PyPI")
    wheel = wheels[0]
    target = into / wheel["filename"]
    try:
        with urllib.request.urlopen(wheel["url"], timeout=60) as answer:
            target.write_bytes(answer.read())
    except OSError as error:
        raise LookupError(f"could not download {wheel['filename']}: {error}") from error
    return target


def report(wheel: Path, label: str) -> int:
    """Print the comparison, and return the exit code that describes it."""
    modules, files = provided(wheel)
    wanted = required()

    gaps: list[str] = []
    for module in sorted(wanted):
        if module not in modules:
            gaps.append(f"module {module} is not in the wheel")
            continue
        for name in sorted(wanted[module] - modules[module]):
            # `from sungrow_modbus import fingerprint` names a *submodule*,
            # which resolves at runtime without appearing anywhere in the
            # package's `__init__.py`. Checking only module-level names calls
            # that a missing symbol -- and it is how this integration reaches
            # the survey tables, so getting it wrong would have made the
            # script cry wolf on a correct tree.
            if f"{module}.{name}" in modules:
                continue
            gaps.append(f"{module} does not provide {name}")

    print(f"integration  {len(wanted)} library modules imported")
    print(f"wheel        {wheel.name} -- {len(files)} modules ({label})")
    if not gaps:
        print(f"verdict      every import resolves against {DISTRIBUTION} {label}")
        return OK

    print("verdict      the pin does not provide what the integration imports")
    for gap in gaps:
        print(f"  {gap}")
    print()
    print("A copy of this integration installed against that version will fail")
    print("to start. Either release a version that has it, or do not import it")
    print("yet: `python scripts/sync_version.py --set X.Y.Z` moves both halves.")
    return BROKEN


def main(argv: list[str] | None = None) -> int:
    """Run the check against a local wheel, or against the pinned release."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--wheel",
        type=Path,
        help="a locally built wheel to check instead of the published one",
    )
    args = parser.parse_args(argv)

    if args.wheel:
        if not args.wheel.is_file():
            print(f"no such wheel: {args.wheel}", file=sys.stderr)
            return UNDETERMINED
        return report(args.wheel, "built here")

    version = pinned_version()
    with tempfile.TemporaryDirectory() as scratch:
        try:
            wheel = download(version, Path(scratch))
        except LookupError as error:
            print(f"undetermined  {error}", file=sys.stderr)
            print(
                "              nothing is proven either way; a release must not "
                "read this as success",
                file=sys.stderr,
            )
            return UNDETERMINED
        return report(wheel, f"PyPI {version}, the version manifest.json pins")


if __name__ == "__main__":
    raise SystemExit(main())
