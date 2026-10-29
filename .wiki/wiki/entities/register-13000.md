---
type: entity
title: Register 13000 (running state)
tags: [register, input, running-state]
created: '2026-10-29'
---

# Register 13000 (running state)

Input register 13000, the inverter's running state. The whole map is
`derived.RUNNING_STATES` (`src/sungrow_modbus/inverter/derived.py`), and the
running and stopped sets are derived from its labels.

- **`0x0000` is "Running", not off.**
- **A [WiNet-S](device-winet-s.md) re-encodes it**: cable 0x0040 becomes
  0x0000, and 0x0080 becomes 0x8100. So a code seen only through a dongle says
  nothing about what the inverter sends, and the duplicates in the map are
  the dongle's.
- **`0x0020 Starting`** is most of the wait after a Modbus start.
  `is_starting` recognises it.
- **A start can take several `0xCF` commands** before the state moves, so
  `async_ensure_running` re-sends while the state still reads stopped, and
  every control-test driver calls it on the way out. See the
  [control test](../concepts/control-test.md).
