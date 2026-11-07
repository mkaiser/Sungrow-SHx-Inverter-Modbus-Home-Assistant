"""Button descriptions, generated from the write table.

Do not edit by hand: `scripts/generate/descriptions.py buttons` writes this
file from `scripts/generate/tables/writes.py`, and CI checks that it matches.

Each is a command register: a press writes one word, and there is no state to
show, because a command does not read back what was sent.
"""

from __future__ import annotations

from .entity import SungrowButtonDescription

BUTTON_DESCRIPTIONS: tuple[SungrowButtonDescription, ...] = ()
