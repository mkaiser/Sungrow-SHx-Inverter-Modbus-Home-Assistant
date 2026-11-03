"""The inverter: its register map, its device object, and what follows from them.

One map for every model (`registers`, with the identity and control blocks in
`components`); what a given machine answers of it is decided in
`capabilities`, and the values the YAML package computed with templates are
in `derived` and `smoothing`. `faults` names the bits of the fault and alarm
words, `layout` records which registers must be read on their own, and
`export_scale` asks a firmware how it writes 13074.
"""

from .device import SungrowInverter

__all__ = ["SungrowInverter"]
