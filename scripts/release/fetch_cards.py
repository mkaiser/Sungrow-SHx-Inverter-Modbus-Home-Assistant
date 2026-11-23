#!/usr/bin/env python3
"""Fetch the two cards that ship in the library's wheel.

    python scripts/release/fetch_cards.py                  # fetch, verify, patch
    python scripts/release/fetch_cards.py --check dist/*   # are they in what was built?

`power-flow-card-plus` and `energy-flow-card-plus` are flixlix's, under MIT, and
are not committed here. Each is pinned by version and SHA-256, so a changed
upstream file fails the build rather than shipping. The element is renamed on
the way, so it cannot clash with a copy the user has from HACS, and it no longer
lists itself in the card picker. A patch whose text is not there exactly once
fails too: upstream moved, and somebody has to look.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import tarfile
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[2]
CARDS = REPO / "src" / "sungrow_modbus" / "cards"
LICENCE = "LICENSE.power-flow-card-plus"
#: Both cards carry this text, from the same author's repositories.
LICENCE_DIGEST = "91efab740137d92f5a21ab8196b10973aaf417a0b3fbce4c15535ca61baa01cd"

UPSTREAM = "https://github.com/flixlix"
RAW = "https://raw.githubusercontent.com/flixlix"


class Card:
    """One upstream card: where it comes from, and what it is called here."""

    def __init__(
        self, bundle: str, repo: str, version: str, digest: str, picker: str
    ) -> None:
        """Name a card; `picker` is the code that lists it in the card picker."""
        declared, _, picker = picker.partition(";")
        self.bundle = bundle
        self.repo = repo
        self.version = version
        self.digest = digest
        self.tag = f"sungrow-modbus-{bundle.removesuffix('.js')}"
        self.url = f"{UPSTREAM}/{repo}/releases/download/{version}/{repo}.js"
        self.patches = (
            (f"(`{repo}-editor`)", f"(`{self.tag}-editor`)"),
            (f"(`{repo}`)],", f"(`{self.tag}`)],"),
            # Not in the card picker: `Sungrow power flow` is.
            (
                f"{declared};{picker}({{type:`{repo}`,",
                f"{declared};0&&{picker}({{type:`{self.tag}`,",
            ),
        )

    def patched(self, bundle: str) -> str:
        """Return the bundle under its own element name."""
        for old, new in self.patches:
            if bundle.count(old) != 1:
                raise SystemExit(f"{self.repo}: expected exactly one {old!r}")
            bundle = bundle.replace(old, new)
        header = (
            f"// {self.repo} {self.version} by flixlix, MIT "
            f"({UPSTREAM}/{self.repo}); renamed."
        )
        return f"{header}\n{bundle}"


POWER = Card(
    "power-flow.js",
    "power-flow-card-plus",
    "v0.6.1",
    "1061bea717a788520a73f08ac7c233d711600dc7efbed2b2d4a39e2dbee32c04",
    "var pd;Xo",
)
ENERGY = Card(
    "energy-flow.js",
    "energy-flow-card-plus",
    "v0.5.1",
    "a5d312a20a2d79842c734f764912822eacfe705ddd55f867eca405c5e56f1d74",
    "var Fd;vs",
)
CARDS_BY_BUNDLE = {card.bundle: card for card in (POWER, ENERGY)}


def _download(url: str, digest: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        raw: bytes = response.read()
    found = hashlib.sha256(raw).hexdigest()
    if found != digest:
        raise SystemExit(f"{url}: SHA-256 {found}, expected {digest}")
    return raw


def fetch() -> None:
    """Download, verify and write the cards and the licence."""
    for card in CARDS_BY_BUNDLE.values():
        text = _download(card.url, card.digest).decode("utf-8")
        (CARDS / card.bundle).write_text(card.patched(text), encoding="utf-8")
        print(f"{card.bundle}: {card.url}")
    url = f"{RAW}/{POWER.repo}/{POWER.version}/LICENSE"
    (CARDS / LICENCE).write_bytes(_download(url, LICENCE_DIGEST))
    print(f"{LICENCE}: {url}")


def check(archives: list[Path]) -> None:
    """Fail unless every archive carries both cards and the licence."""
    for archive in archives:
        if archive.suffix == ".whl":
            with zipfile.ZipFile(archive) as built:
                names = built.namelist()
        else:
            with tarfile.open(archive) as packed:
                names = packed.getnames()
        for name in (*CARDS_BY_BUNDLE, LICENCE):
            wanted = f"sungrow_modbus/cards/{name}"
            if not any(member.endswith(wanted) for member in names):
                raise SystemExit(f"{archive.name} has no cards/{name}")
        print(f"{archive.name}: carries both cards")


def main() -> int:
    """Run."""
    parser = argparse.ArgumentParser(description="Fetch the power and energy cards")
    parser.add_argument("--check", nargs="+", type=Path, metavar="ARCHIVE")
    args = parser.parse_args()
    if args.check:
        check(args.check)
    else:
        fetch()
    return 0


if __name__ == "__main__":
    sys.exit(main())
