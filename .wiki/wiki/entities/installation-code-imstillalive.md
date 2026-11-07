---
type: entity
title: Installation code-imstillalive
tags: [installation, code-imstillalive, logger]
created: '2026-11-07'
---

# Installation code-imstillalive

An [SH25T](device-sh-t.md) and an [SH15T](device-sh-t.md), both on
[P067](firmware-pearl-h-b000-v000-p067.md), behind a Logger1000A
([Sungrow Logger](device-logger.md)), read on 2026-11-07 with the integration's diagnosis button,
four minutes apart. Read only. Issue #791.

- **The first inverters read through a Logger.** Each answered on the port the Logger forwards it
  on, and read like a [WiNet-S](device-winet-s.md): 6100, 2613, 2629 and the history blocks
  refused. The diagnosis's verdict is "through a communication module", which did not name itself.
- **How the Logger is set up, by the owner (issue #791):** SH25T on port 502 at unit 1, SH15T on
  503 at unit 2, a DTSU666-20 meter on 504 at unit 5, the Logger itself on 505 at unit 247, and
  each of four battery towers on a port of its own: two SBR256 on 507 and 509 (units 3, 4), two
  SBH200 on 506 and 508 (units 6, 7). The towers refuse the identity read (input 4951) with
  exception 2, and so does the Logger, so the integration's setup cannot add it. **The Logger
  itself was not read.**
- **[31211](register-31211.md) answers 0x55** on both; 33149 and 33150 answer 0xFFFF.
- **The inverters' meter reads 0**: the owner lists the meter as a device of the Logger.
- **Another Home Assistant polled every device throughout** (it runs the battery control). The
  SH15T's intermittent holding blocks are read as [contention](../concepts/contention.md).

## Diagnoses

- [SH25T, B000.V000.P067, code-imstillalive, through a Logger1000A](../sources/sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger-summary.md)
- [SH15T, B000.V000.P067, code-imstillalive, through a Logger1000A](../sources/sh15t-b000v000p067-3p-code-imstillalive-anon-07241574740-battery-unknown-meter-logger-summary.md)
