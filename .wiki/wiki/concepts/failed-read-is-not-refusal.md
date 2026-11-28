---
type: concept
title: A failed read is not a refusal
tags: [modbus, probes, evidence]
created: '2026-10-29'
---

# A failed read is not a refusal

An exception **response** is the device answering: it is there, and it
declined. That is evidence. A connection lost, a timeout or a desync is the
link failing to carry the question, and it says nothing about the register.

In `modbus_connection`:

| Type | Means |
| --- | --- |
| `ModbusExceptionError` and subclasses | an answer |
| `ServerDeviceBusyError` (0x06) | an answer that settles nothing |
| `ServerDeviceFailureError` (0x04) | the same, through a busy WiNet-S ([measured](../queries/does-a-busy-winet-s-refuse-with-0x04.md)); `model.SETTLES_NOTHING` holds both |
| `ModbusConnectionError`, `ModbusTimeoutError`, `ModbusProtocolError` | not an answer |

Consequences:

- **Probes are three-valued**: yes, no, undetermined. `None` must never read
  as `False`.
- **A probe that decides something published gets retries.**
- **The CLI exits 1 on a link failure** and prints the exit codes last,
  because a pasted transcript loses `$?`.
- **A test fixture that fakes a refusal with a bare `ModbusError` cannot see
  any of this.** Raise the real type.
- **A refusal can arrive as a 10 s timeout** over a slow link, instead of
  exception 0x02. `blocks.NARROW_BUDGET` bounds the narrowing of failing
  blocks and marks what it did not reach. Over a slow link, check for
  `not narrowed` before believing a range. Never put a timeout-only finding
  in `layout.py`.

Related: [contention](contention.md), which looks like refusal and is not.

## Where the code still reads a non-answer as an answer

Found by the code review of 2026-11-28, from the source; each is a task in `Todo.md`:

- `src/sungrow_modbus/wallbox/managed_test.py` takes any `ModbusExceptionError` as a refusal, a busy
  WiNet-S's 0x04 or 0x06 included, and `scripts/dev/managed_wallbox_field.py scan` does the same and stops
  at its first timeout (T104).
- `src/sungrow_modbus/battery/discovery.py` reads a timeout on the device type read at unit 2 as "no type
  code, a pack" (T112, which waits on a read of what a pack at unit 2 answers through a WiNet-S).
