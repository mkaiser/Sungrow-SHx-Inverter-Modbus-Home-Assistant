---
type: query
title: "Does a busy WiNet-S refuse with 0x04?"
tags: [winet-s, contention, answered]
created: '2026-10-29'
query: "Are the 0x04 refusals through firetribe's WiNet-S contention, or the dongle refusing?"
results_count: 2
---

# Does a busy WiNet-S refuse with 0x04?

**Answered: yes.** At [firetribe](../entities/installation-firetribe.md), through a
[WiNet-S](../entities/device-winet-s.md) that a wallbox and a second Home Assistant
also poll, three holding blocks answered in some rounds of the block read test and
were refused with an exception in others, every control write of leg B was refused
with 0x04, and so was one read of 13074 -- yet the forced charge command was written
and obeyed. [Source](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan-summary.md).

A refusal that comes and goes on the same register is not the register being
absent. If it is the dongle answering 0x04 when another client holds the inverter,
then on a WiNet-S 0x04 joins 0x06 as an
[answer that settles nothing](../concepts/failed-read-is-not-refusal.md), and a probe
must not read it as "not there".

Measured on [gerd](../entities/installation-gerd.md)'s WiNet-S on 2026-10-29, reads
only: holding 13002 x17, 13050 x51 and 33149 x2, six rounds each. One client: 18 of
18 answered. Three clients at once: 23 and then 25 of 54 refused with **0x04**, the
rest answered, twice over with a quiet minute between. So through a busy WiNet-S
0x04 says "busy", and the library retries it and never records it as "not there"
(`model.SETTLES_NOTHING`, with 0x06). A 0x04 to a **write** cannot be told apart
from an out-of-range refusal there, which matters to the
[13074](../entities/register-13074.md) write-scale probe.
