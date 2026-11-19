# T018 - Should `mppt3 / mppt4 carries a string` ask for the current?

**Should `mppt3 / mppt4 carries a string` ask for the current?**
It grants the tracker on a voltage above `TRACKER_LIVE_V`, 50 V, in
daylight (`src/sungrow_modbus/capability_test/plausibility.py`), and at
[Maximo101](.wiki/wiki/entities/installation-maximo101.md)'s SH10RS that
is wrong: `mppt4` reads 39.5 V to 53.6 V with **0.0 A** in every download,
at 3.8 kW of PV and at 10.5 kW alike, while the other three trackers
account for `total_dc_power` to within 1 %. An unloaded input drifts past
50 V, so the check says *matched* for a tracker with nothing on it -- the
one thing `doc/capability_tests.md` says it catches.

`mppt4_current` answers 0.0 A on that model, in the same block, so the
discriminator is there. What has to be decided is the other case: a model
that reports no tracker current at all should not turn a *matched* into an
*inconclusive* for everyone. A verdict that reads "a voltage, and current
with it" where the current answers, and the present rule where it does
not, is the shape to weigh.

**What it owes is settled, and it is cheap**: a readings check carries a
revision of its own since the clock fix, in
`plausibility.CHECK_REVISIONS`. So a verdict change raises
`mppt3 / mppt4 carries a string` to 2 **in the same commit**, and every
house drops what that check gathered under the old rule and keeps
everything else. No `plausibility.SCHEMA` bump, no clearing, and nothing
for an owner to press: ordinary polling fills the row again.
