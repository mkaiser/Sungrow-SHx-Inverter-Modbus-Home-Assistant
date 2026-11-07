---
type: source
title: mkaiser-discharge-window-2026-11-04.md
source_path: raw/mkaiser-discharge-window-2026-11-04.md
ingested: '2026-11-04'
created: '2026-11-04'
tags: [capability-test, discharge-window, mkaiser, sapphire-h-b001-v000-p020]
---

# The maintainer's SH10RT: the discharge window check

`.wiki/raw/mkaiser-discharge-window-2026-11-04.md`: two evening runs of the capability test with
`--discharge-window` at [mkaiser](../entities/installation-mkaiser.md), on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), over the inverter's own LAN port,
no PV, a third-party battery at 28 %.

| Fact | Evidence |
| --- | --- |
| **Moving every discharge window away from now stops the discharge** | 722.5 W before, 0 W ±0 during, 719 W after: "did as it was told" |
| **It comes back when the words are put back** | 719 W after the restore, 3.5 W from the start |
| The schedule is at the SH-RT layout and is **always on in the snapshot** | weekday and weekend windows 1 and 2 each 00:00 to 24:00 |
| The check refuses a battery under 500 W | run 1 discharged 495 W and skipped it, naming the floor |
| Forced discharge and charge both obey on P020 | 1251 W against 1250 W, and 1250 W, with the pack's own limits at 3300 W and 4500 W |
| Restore is whole | every schedule word and every other touched word read back original; no snapshot left |

The second run on hardware, after [gerd](../entities/installation-gerd.md)'s cable run
(3799, 0, 3800 W on P022, in the
[third reading](sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md)),
and the first on P020, on a third-party battery and at night. See
[the capability test](../concepts/capability-test.md).
