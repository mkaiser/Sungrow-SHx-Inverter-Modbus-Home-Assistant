---
type: query
title: "What does an iHomeManager answer?"
tags: [ihomemanager, answered]
created: '2026-10-29'
query: "Which of the 53 mapped iHomeManager registers answer on a real unit, on which port?"
results_count: 1
---

# What does an iHomeManager answer?

**Answered for one unit**, on 2026-11-10: an iHomeManager on `SV930.001.00.P020`, at slave 247 on
port 503, answered **all 56 fields of the map**, the undocumented 4357-4362 and 8594-8774 among
its inputs, and holding 8024-8053
([the diagnosis](../sources/ihomemanager-ihomemanager-sv930-001-00-p020-anonymous-port503-summary.md)). 4359 and 4361 read 0
between the phase voltages, so whether 4358-4362 are U32 low word first or U16 with gaps is
still open, and a second unit on other firmware would say whether the answer is the device's or
this firmware's.

Two units elsewhere had answered 8028 (as 0x55/0xAA), 8031, 8155-8163, 8176-8179, 8559-8564 and
the undocumented 4358-4362 ([evcc cross-reference](../sources/cross-reference-evcc-summary.md));
the unit here answered all of those too. The map's sources are compared in the
[cross-reference](../sources/cross-reference-modbus-manager-summary.md). What is known about the
device is on [iHomeManager](../entities/device-ihomemanager.md).

A second question, still open: whether an iHomeManager silences the
inverter's meter phase registers 5741-5746 (issues #647, #651). Both of
ra1k-0's readings are through a WiNet-S, which refuses those registers anyway,
so only a reading of the inverter's own LAN port answers it.
