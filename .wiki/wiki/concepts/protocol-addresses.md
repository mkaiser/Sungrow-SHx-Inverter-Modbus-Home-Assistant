---
type: concept
title: Protocol addresses and register numbers
tags: [addresses, registers, convention]
created: '2026-10-29'
---

# Protocol addresses and register numbers

**Addresses are protocol addresses**, one below the register number in
Sungrow's document and in the YAML comments (`address: 4989 # reg 4990`).

- **The register maps are written in the document's numbers**, through
  `addresses.reg()`: `power_flow_status = integer(reg(13001))`.
- **No register is read by a literal address.** A mapped field is looked up
  with `addresses.field_address(name, device)`. The few registers that no
  component maps are named constants in `addresses.py` (`DIRECT_ONLY_PROBE`,
  ...), and `Address.register` gives the document's number beside the
  protocol one. The survey scripts import the same names.
- `tests/test_addresses.py` fails on a field declared any other way, and on
  a new literal. **Tests are exempt on purpose**: a fixture carries the
  specification's numbers, not the code's.
- **`swap: word` in the YAML means `word_order="little"`.** Sungrow sends
  32-bit values low word first.

Every page in this wiki gives **register numbers** unless it says
"protocol".
