---
type: entity
title: SUNSTONE-H_B000.V001.P068
tags: [firmware, sunstone-h-b000-v001-p068]
created: '2026-10-31'
---

# SUNSTONE-H_B000.V001.P068

[SH-RS](device-sh-rs.md) firmware. Only read through a [WiNet-S](device-winet-s.md).

- [Register 31211](register-31211.md) answers 0x55.
- The battery firmware string (13280) carries bytes after its NUL terminator, which the library
  now drops.
- Writes are unmeasured: no control test on this firmware.

## Surveys

- [SH6.0RS, B000.V001.P068, anonymous, a WiNet-S](../sources/sh60rs-b000v001p068-1p-anonymous-anon-17579213881-battery-sbr192-winet-summary.md)
