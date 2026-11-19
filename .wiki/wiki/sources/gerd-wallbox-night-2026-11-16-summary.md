---
type: source
title: gerd-wallbox-night-2026-11-16.md
source_path: raw/gerd-wallbox-night-2026-11-16.md
ingested: '2026-11-17'
created: '2026-11-17'
tags:
  - wallbox
  - ac22e-01
  - gerd
  - capability-test
  - ems
  - winet-s
---

# gerd's wallbox, the night of 2026-11-16/17

Over a VPN to [gerd](../entities/installation-gerd.md)'s site, with a car charging (three phase,
at most 16.2 A a phase) and the owner's consent: the first run of the
[managed capability test](../concepts/capability-test.md) on hardware, then single writes to the
inverter's EV charger block, then a watch that ran until morning. The inverter at unit 1 on its LAN
cable, the [wallbox](../entities/device-wallbox.md) over TLS on 516, one client per path. Source:
`raw/gerd-wallbox-night-2026-11-16.md` (the working notes as written, and the four test logs).
Register numbers here; the raw note gives protocol addresses, one lower.

## What was measured

| Fact | Evidence |
| --- | --- |
| **The managed capability test passed on its first run on hardware**: user current 6, 8 and 10 A followed (the car drew 5.6, 7.5 and 9.5 A after 7-10 s), 5 A refused with 0x04, stop seen after 4 s, charging again after 10 s | the 21:33 run: `device-diagnosis/scripts/python/sungrow_managed_wallbox_test.py` with `--leave --start-stop`, exit 0 |
| **Writing charging on (33540 = 0xAA) while it is on does nothing**: 60 s watched, no dip, the session kept going | test 1, 00:15 |
| **Writing the mode it already has (33541 = 160 in fast) does not end the session** | test 2, 00:18 |
| **A change to user defined (163) while charging ends the session**, in under 6 s (status `completed`, the inverter's own word then reads off); 163 to 160 does too. Charging on written afterwards restarts the car in about 6 s and it is at full power in about 40 s | test 3, 00:21; test 4, 02:02 |
| **163 entered with charging off turns charging on by itself**; the car starts at 6 A and ramps about 1.4 A per 5 s to the user current | test 4, 02:00-02:01 |
| **In user-defined mode 21203 is the user current exactly, 0.1 A per count**: 16.0 A at 16.0 A set, 10.0 A within 5 s of writing 10.0 A; the car then draws about 0.7 A less | test 4, 02:01-02:02 |
| **In fast mode 21203 reads 24-28 A while the car draws 15.4-16.2 A**: it is the inverter's offer, above what a 16 A-a-phase car takes, not the car's current. It wandered with no trend all night | the watch, 21:21 to 02:17 |
| **The managed test's restore declared the house back while its own mode change was ending the session**: the checks ran in user-defined mode, so the restore wrote the mode back to fast (163 to 160, which ends a session, as tests 3 and 4 measured), read the block on/fast/16.0 A at once and saw the car charging; 28 s later the wallbox read `completed` and the inverter's word off. The owner's car app said the charge was done at 47 % (the target was 100 %). One charging on from that state held | the run's report (`restored_block` on, fast, 16.0 A; `restored` true), reads at 21:33:33 and 21:34:35 |
| **The inverter does not stop a fast charge at the home battery's minimum**: the battery sat at 13023 = 0.5 to 0.2 % with no PV and the car drew 10.6 kW for hours | 21:21 to 02:17 |
| **The inverter ramps the offer down by itself for a spell**: two dips, to 5.7-6.0 A (21:57) and 7.4-7.8 A (22:02), with the block unchanged, back to full within 2 min | the watch, 21:55-22:04 |
| **A car can suspend a charge for hours with the inverter and the wallbox willing**: from 02:19 the status read `suspended by the vehicle` (0 A, 0 W) with the inverter's word on, fast, 16.0 A; three attempts of about 2 min (02:32, 02:46, 02:53, 100-180 W), nothing since. At 03:50 the inverter's own word went off by itself; one charging on at 03:51 was accepted and the offer ramped to 19.8 A, and the car still declined until the watch ended at 06:05 | the watch and the 03:51 write |
| **The time pair 33546-33549 is a date pair**: two Unix times at UTC midnight, a day apart; both moved one day when the session restarted after midnight | the watch, 00:25 |
| **The wallbox's phases stayed three** the whole night (21204 0, 21225 3, 21270 0, 21272 4140 W) | the watch |
| **One ISP reconnect, 02:49-02:53 (about 3.5 min)**; a WireGuard tunnel to the site was up again by itself within the watchdog's two tries; the car's state could not be seen in the gap | the watch's ERR rows, the VPN watchdog |
| **The wallbox's TLS port refused a connection once in a quiet moment** (03:28) and a read timed out once (03:27); both clean on the next round | the watch |

## What did not answer

- **Why the car suspended its charge at 02:19**, and why the inverter then switched the charge off at 03:50.
  The reason is in the car's app, which the owner had not read when the watch ended
  ([the query](../queries/why-does-a-managed-wallbox-stop-charging.md)).
- **What 33538 (85) and 33539 (161) are**: they did not move in any state.
- **Whether a mode change from the app ends the session too** (the app was not used).
- **The 21203 offer's ceiling in fast mode**: it reached 27.9 A on a 16 A car; whether it would go to the
  rating (32 A) with a car that takes more is not seen.

## What changed in the code and plans

Nothing in `src/` or `custom_components/` yet. The managed test's restore (`src/sungrow_modbus/wallbox/managed_test.py`) needs to wait for the inverter to settle after a mode change and check the car again after that, or it reports a house back that is not. For the inverter's EV charger controls
(`src/sungrow_modbus/hybrid_inverter/ev_charger.py`): a *Wallbox charge mode* change to or from user defined
ends a charging session, and charging on has to follow it, as the select already writes. `Todo.md` (Wallbox
item 3) and `plans/T003-T004-wallbox_tests.md` are updated with what is left.
