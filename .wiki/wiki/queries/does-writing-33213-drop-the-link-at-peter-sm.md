---
type: query
title: "Does writing 33213 drop the link at peter-sm?"
tags: [contention, charge-window, peter-sm, sapphire-h-b001-v000-p023, open]
created: '2026-11-02'
query: "Is the connection lost on the charge window's write of 33213 at peter-sm the register's doing or the link's?"
results_count: 3
---

# Does writing 33213 drop the link at peter-sm?

**Open.** Both control tests at [peter-sm](../entities/installation-peter-sm.md) on 2026-11-02,
13 minutes apart over the inverter's own LAN port on
[P023](../entities/firmware-sapphire-h-b001-v000-p023.md), lost the connection on the same write:
window 1's end minute, register 33213, after the start hour, start minute and end hour
(33210-33212) had been written and before the enable. The check reported "could not tell", and
the restore put every word back
([sixth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-5-summary.md),
[seventh](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-6-summary.md)).
A third run, on 2026-11-07 with integration 0.1.0a27, lost it on the same write again, with
word 36, and restored every word
([tenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan-summary.md)).

Against the register: the same window, 33213 included, was written over the cable on P023 at
[fwitten](../entities/installation-fwitten.md), and the window did as it was told
([the survey](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2-summary.md)).
For it: the same write three times, on two days, where [contention](../concepts/contention.md) dies a little
further into a run each time.

What answers it: a third run at peter-sm with only the charge window check
(`--charge-window`), and one single write of 33213's own held value; a loss on that write alone
is the register.
