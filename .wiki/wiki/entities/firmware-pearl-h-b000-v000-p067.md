---
type: entity
title: PEARL-H_B000.V000.P067
tags: [firmware, pearl-h-b000-v000-p067]
created: '2026-11-07'
---

# PEARL-H_B000.V000.P067

[SH-T](device-sh-t.md) firmware, a build number below [P071](firmware-pearl-h-b000-v000-p071.md). Read on
an SH25T and an SH15T at [code-imstillalive](installation-code-imstillalive.md), through a
[Logger](device-logger.md); read only. Version 1 is `PEARL-H_01011.95.41` on the SH25T and
`PEARL-H_01011.94.41` on the SH15T.

- [Register 31211](register-31211.md) answers 0x55 on both, so P067 is in `ANSWERING`
  (`tests/test_pv_generation_cut.py`). The cut is not watched here, so P067 is **not** in
  `CONFIRMED_ON_FIRMWARE`.
- 33149 and 33150 (battery start power) answer 0xFFFF on both, which decodes as unavailable.
- 13018 answers 85 on both (the SH15T's probe had no answer; its dump read it).
- The write scale of [register 13074](register-13074.md) is not measured.

## Diagnoses

- [SH25T, B000.V000.P067, code-imstillalive, through a Logger1000A](../sources/sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger-summary.md)
- [SH15T, B000.V000.P067, code-imstillalive, through a Logger1000A](../sources/sh15t-b000v000p067-3p-code-imstillalive-anon-07241574740-battery-unknown-meter-logger-summary.md)
