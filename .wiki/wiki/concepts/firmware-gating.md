---
type: concept
title: Firmware gating
tags: [firmware, capabilities, writes]
created: '2026-10-29'
---

# Firmware gating

The firmware decides what is read at all and what may be written, so it is
**read before anything decides on it**. Setup reads 2582 and then 13250
(`async_update_firmware`) before the first poll.

- `ABSENT_ON_FIRMWARE` comes from what the device **refused**.
- `CONFIRMED_ON_FIRMWARE` comes from a [control test](control-test.md) that
  **watched a write work**, never from a register merely answering.
  `test_nothing_is_confirmed_without_a_document_that_shows_it` refuses an
  entry without such a document.
- Both match either string exactly.
- A string that changes while polling reloads the entry. One that appears
  after reading empty does not.
- The firmware moves under an entry, so a per-device measurement such as
  [13074's write scale](../entities/register-13074.md) is stored together
  with the firmware it was measured on.

Example: [register 31211](../entities/register-31211.md), where a read gives
the binary sensor and only a confirmed firmware gives the switch.
