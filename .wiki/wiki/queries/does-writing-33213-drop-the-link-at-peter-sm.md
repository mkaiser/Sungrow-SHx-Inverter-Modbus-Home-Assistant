---
type: query
title: "Does writing 33213 drop the link at peter-sm?"
tags: [contention, charge-window, peter-sm, sapphire-h-b001-v000-p023, open]
created: '2026-11-02'
query: "Is the connection lost on the charge window's write of 33213 at peter-sm the register's doing or the link's?"
results_count: 10
---

# Does writing 33213 drop the link at peter-sm?

**Open.** Both capability tests at [peter-sm](../entities/installation-peter-sm.md) on 2026-11-02,
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
Three more runs, on 2026-11-08 and 2026-11-09 with integrations up to 0.1.0a32, lost it on the
same write (words 59, 21 and 18), each with this entry's polling held off, and restored every word
([twelfth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-10-summary.md),
[thirteenth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-11-summary.md),
[fifteenth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-13-summary.md) readings).
Three more, on 2026-11-09 and 2026-11-10 with integrations 0.1.0a33 to 0.1.0a36, lost it on the
same write (words 3, 30 and 19) and restored every word
([sixteenth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14-summary.md),
[seventeenth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-15-summary.md),
[eighteenth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-16-summary.md) readings).
Nine of nine attempts, morning, afternoon and evening. A fourteenth-reading run did not try it:
the owner's own charge schedule was on.

**Those three runs also lost the connection elsewhere**, where the earlier ones had not: the
write of 13059 once, EMS mode 3's write of 13050 twice, and a write of 33047 above its bound
twice, among the write-path checks that 0.1.0a33 added. Each time the discharge-window write
that follows 33213 dropped too (33154 or 33155), which says only that the link was not back.

The same write lost the connection once at [mkaiser](../entities/installation-mkaiser.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), and went through on the next run
that evening, among losses at three other addresses ([third reading](../sources/sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter-summary.md)).

Against the register: the same window, 33213 included, was written over the cable on P023 at
[fwitten](../entities/installation-fwitten.md), and the window did as it was told
([the diagnosis](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2-summary.md)).
For it: the same write nine times, on five days, where [contention](../concepts/contention.md) loses
the connection at a different address each time. Against it, since 0.1.0a33: this house now loses
the connection at other addresses too, so a link that drops on writes is in play; but only 33213
has dropped in every run that wrote it, and 13050 and 33047 went through in one run of three.

What answers it: a third run at peter-sm with only the charge window check
(`--charge-window`), and one single write of 33213's own held value; a loss on that write alone
is the register.
