# The maintainer's SH10RT: eight daily counters reset in one poll, 2026-11-20

Read at 00:25 CET (23:25 UTC) on 2026-11-20 out of the development instance's plausibility store,
written by *Extended test (auto repeat)* at `anon-37323352958` (SAPPHIRE-H_B001.V000.P020), over
the inverter's own LAN port, on 0.1.0a44 (`e8f1c84`). The third night of observing, and the first
on the corrected check: `daily counters reset at midnight` at **revision 2**, which judges the
fall on the inverter's own clock.

The collection was re-armed at 21:30 CET on 2026-11-19 after Home Assistant was restarted to load
the corrected check. The restart dropped this check's stored state, revision 1 against revision 2,
and left every other row standing: `Plausibility.from_dict` in
`src/sungrow_modbus/capability_test/plausibility.py`.

## The reset

```text
daily counters reset at midnight
  {"passes": 1,
   "failures": [],
   "notes": ["pv_generation 4.9->0, imported_energy 12->0, exported_energy 0.2->0,
              battery_charge 1.8->0, battery_discharge 1.6->0,
              exported_energy_from_pv 0.2->0, battery_charge_from_pv 1.5->0,
              direct_energy_consumption 3.2->0 reset at 00:09 by the inverter's
              clock, where Home Assistant read 23:09, the rest at zero"],
   "revision": 2}
```

| | |
| --- | --- |
| Counters that fell in that one poll | **eight**: `daily_pv_generation` 4.9, `daily_imported_energy` 12, `daily_exported_energy` 0.2, `daily_battery_charge` 1.8, `daily_battery_discharge` 1.6, `daily_exported_energy_from_pv` 0.2, `daily_battery_charge_from_pv` 1.5, `daily_direct_energy_consumption` 3.2 -- each to 0 |
| Counters still standing after it | none: "the rest at zero" |
| The inverter's clock | 00:09 |
| Home Assistant's clock | 23:09 (the instance is on UTC) |
| Verdict | pass, 1 of 1 event needed |

**The reset is atomic on this device.** Eight counters went to zero in the same one-minute poll,
and the sentence names every one that fell with its before and after, so a poll that caught some
reset and some standing would have read as a shorter list with the rest named as standing. None
was. Three nights of observing have now produced no such poll here.

What makes this night the one that answers it: the two earlier nights' sentences named only
`daily_pv_generation`, because the house had no other non-zero daily counter to fall from. The
day of 2026-11-19 put 12 kWh through the meter and 1.8 kWh into the battery, so eight counters had
something to lose.

**The clock reads an hour apart and the sentence says so**, two measured times rather than a
derived offset: the inverter keeps CET, this Home Assistant keeps UTC. The same fall judged by the
old rule was a failure at 23:04, 23:03 and 23:02 on the three previous nights
(`.wiki/raw/mkaiser-midnight-reset-2026-11-17.md`,
`.wiki/raw/mkaiser-midnight-reset-night-2-2026-11-18.md`).

## The rest of the store at the same reading

4337 observations, 2026-11-16T17:27:44Z to 2026-11-19T23:24:18Z.

| Check | State |
| --- | --- |
| `daily counters reset at midnight` | **1 pass**, no failure, the note above |
| `lifetime battery counters contain each other` | **175 passes**, no failure -- established here for the first time |
| `lifetime counters never fall` | 4330 passes, no failure |
| `running states` | 0x0008 Standby 2772, 0x0040 Running 1524, 0x0800 26, 0x8000 Stop 8, 0x0020 7 -- every code in the decode table |
| the collection | **37 of 55 established, 0 failed**, 11 runs kept |

`lifetime battery counters contain each other` became applicable on this boot: its first field was
read here for the first time, which is why the house's total moved from 54 to 55 checks.

## Zero runs, for the second night running

`continuous_runs_started` stayed 0 from 21:30 CET to 00:25 CET. The battery sat at 0 % and the
inverter in low-SoC Standby throughout, and *Diagnosis: current step* read *waiting for changed
test conditions: waiting for the inverter to run*. *Diagnosis: next attempt* stayed `unknown`,
with the reason only in its `waiting_for` attribute, because what it waits on is a condition and
not a slot.

Nine write-side rows are still waiting here, each wanting a charged battery: `export power limit`,
`charge ceiling`, `upper bound of battery_min_soc`, and six `upper bound of ...` rows whose
evidence was measured with an older revision of the test.

## Not evidence of

- Any other model or firmware. One device, one reset, on P020.
- Anything about a staggered reset elsewhere: this says the behaviour was not seen here, not that
  no device has it.
- The clamp in `derived.py` being unnecessary. It is the floor under a sum of five of these
  counters at **every** house, including the ones nobody has observed.
