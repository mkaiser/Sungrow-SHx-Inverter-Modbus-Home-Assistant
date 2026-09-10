#!/usr/bin/env python3
"""Build the zip a contributor is handed, and check that it actually runs.

    python scripts/make_scan_zip.py              # write sungrow_scan.zip
    python scripts/make_scan_zip.py --verify     # and prove it runs unpacked

`scripts/sungrow_scan/` is written to be shippable, and "shippable" is a
claim that decays quietly: one convenient `from sungrow_modbus import ...` at
the top of a file and every contributor's copy stops working, while
everything here keeps passing because the library is installed.

`tests/test_scan_is_standalone.py` guards that boundary by reading the
imports. This does the other half -- it unpacks the built zip somewhere else
and runs it with a Python that has nothing installed, which is the only test
of the claim that cannot be fooled.

Everything in the directory goes in, including `README.txt`, which is the
first thing whoever opens it will read, and `scan_plan.json`, without which
there is nothing to read from the inverter.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "scripts" / "sungrow_scan"
OUTPUT = REPO / "sungrow_scan.zip"

#: What not to ship. Everything else in the directory is shipped on purpose:
#: a file worth keeping out is worth deleting rather than filtering.
SKIP = ("__pycache__", ".pyc")


def _files() -> list[Path]:
    """Return the files to ship, sorted so two builds are identical."""
    return sorted(
        path
        for path in SOURCE.rglob("*")
        if path.is_file() and not any(part in str(path) for part in SKIP)
    )


def build(output: Path) -> Path:
    """Write the zip, with everything under one `sungrow_scan/` directory.

    One directory inside, so unpacking it in a downloads folder produces a
    folder rather than five loose files among whatever else is there.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in _files():
            archive.write(path, Path("sungrow_scan") / path.relative_to(SOURCE))
    return output


def verify(output: Path, port: int) -> int:
    """Unpack the zip where nothing is installed and run it.

    Two independent things are being proved, and both have failed in
    practice: that the files are enough on their own -- a missing
    `scan_plan.json` would only show up here -- and that no module reaches
    for the device library at import time.

    A venv rather than the current interpreter, because `sungrow_modbus` and
    `modbus-connection` are both installed in this container. Running the
    unpacked copy with this Python would prove nothing at all.
    """
    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        with zipfile.ZipFile(output) as archive:
            archive.extractall(root)
        unpacked = root / "sungrow_scan"

        environment = root / "venv"
        venv.create(environment, with_pip=False)
        python = environment / "bin" / "python"
        if not python.exists():  # pragma: no cover - Windows layout
            python = environment / "Scripts" / "python.exe"

        installed = subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.util as u;"
                "print([n for n in ('modbus_connection','sungrow_modbus')"
                " if u.find_spec(n)])",
            ],
            capture_output=True,
            text=True,
            check=True,
            # `env` cleared of PYTHONPATH: this container puts the repo on it,
            # which would hand the venv the very library being hidden.
            env={"PATH": "/usr/bin:/bin"},
        )
        if installed.stdout.strip() != "[]":
            print(f"  the check venv is not bare: {installed.stdout.strip()}")
            return 1
        print(f"  unpacked to {unpacked}")
        print(f"  python      {installed.stdout.strip()} -- nothing installed")

        # Import every module, which is where a module-level library import
        # would fail, and then run the entry point far enough to prove it
        # starts: `--help` exercises the imports and the argument parser
        # without needing an inverter.
        for module in sorted(path.stem for path in unpacked.glob("*.py")):
            result = subprocess.run(
                [str(python), "-c", f"import {module}"],
                cwd=unpacked,
                capture_output=True,
                text=True,
                env={"PATH": "/usr/bin:/bin"},
            )
            state = "ok" if result.returncode == 0 else "FAILED"
            print(f"  import {module:<12} {state}")
            if result.returncode != 0:
                print(result.stderr.strip()[-800:])
                return 1

        result = subprocess.run(
            [str(python), "collect.py", "--help"],
            cwd=unpacked,
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin"},
        )
        print(f"  collect.py --help  {'ok' if result.returncode == 0 else 'FAILED'}")
        if result.returncode != 0:
            print(result.stderr.strip()[-800:])
            return 1

        if port:
            # The whole survey, against whatever is on that port. Not the
            # default, because it needs `scripts/simulate.sh` running and this
            # script is also run in CI, where nothing is.
            answers = "n\n1\n6\n2\nn\n1\nzip-verify\nbuilt by make_scan_zip.py\n"
            run = subprocess.run(
                [str(python), "collect.py", "127.0.0.1", "--port", str(port)],
                cwd=unpacked,
                input=answers,
                capture_output=True,
                text=True,
                env={"PATH": "/usr/bin:/bin"},
            )
            last = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""
            print(f"  full survey        {last or 'no output'}")
            if run.returncode not in (0, 3, 4):
                print(run.stdout.strip()[-2000:])
                return 1
    return 0


def main() -> int:
    """Build the zip, and verify it if asked."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="unpack it into a temporary directory and run it with a bare "
        "Python, which is the only real test of the zip",
    )
    parser.add_argument(
        "--against",
        type=int,
        default=0,
        metavar="PORT",
        help="with --verify, also run the whole survey against a device on "
        "127.0.0.1 at this port -- 5020 is `scripts/simulate.sh`",
    )
    args = parser.parse_args()

    output = build(args.output)
    size = output.stat().st_size
    print(f"Wrote {output.relative_to(REPO) if REPO in output.parents else output}")
    print(f"  {len(_files())} files, {size / 1024:.0f} kB")
    if not args.verify:
        return 0
    if shutil.which("python3") is None:  # pragma: no cover - defensive
        print("  cannot verify without a python3 on PATH")
        return 1
    print("Verifying, with nothing installed:")
    return verify(output, args.against)


if __name__ == "__main__":
    sys.exit(main())
