# T019 - A lifetime counter with a broken high word reaches the recorder

**A lifetime counter with a broken high word reaches the recorder.**
`total_battery_charge` is 13041 and 13042, low word first. On all three
[P067](.wiki/wiki/entities/firmware-sunstone-h-b000-v002-p067.md) machines
in the corpus the high word is wrong, and at
[Maximo101](.wiki/wiki/entities/installation-maximo101.md)'s it reads
`0xFFFF` -- the specification's *unavailable* -- so the sensor publishes
**429,494,295.3 kWh** and then rises plausibly from there. The `nan=`
sentinel the fault words carry
(`src/sungrow_modbus/hybrid_inverter/registers.py`) does not catch it,
because the whole double word is not 0xFFFFFFFF: the low word is alive.

Two defences, and they are not alternatives:

- **A ceiling on the energy counters.** A house does not reach a million
  kWh, and a reading above one is a word that is not a measurement; the
  sensor is better unavailable than wrong. It has to be a property of the
  field, not a rule in the sensor platform, so the library's own readers
  and the diagnosis publish the same.
- **A readings check for a relation that cannot fail honestly**:
  `total_battery_charge` >= `total_battery_charge_from_pv`, the second
  being a part of the first, and >= `total_battery_discharge`. It costs no
  Modbus read and it catches all three machines from a single poll, which
  is what tells a broken register from an unusual house.

Note what neither fixes: a recorder that has already taken 429 million kWh
keeps that statistic until somebody deletes it by hand, so for the houses
affected the integration's own answer is only half the repair. Whether to
say so in `doc/integration_migration.md` is part of this.

## Status log

Newest first.

### 2026-11-19 -- tests, and four counters the test caught that I had missed

`tests/test_energy_ceiling.py` enumerates the maps rather than listing the
fields by hand, and it earned that on the first run: `total_yield`,
`monthly_yield` and `annual_yield` on the Logger are **64-bit** (four words)
and the iHomeManager's `total_rated_battery_capacity` is a rating rather than
a counter, so all four had been left behind by a sweep for 32-bit lifetime
totals. All four carry the ceiling now, and the helper takes a `count`. The
rule the test states has **no exceptions to remember**: every energy register
wider than one word, in every map, counters and ratings alike -- the ceiling
is a statement about kilowatt-hours, not about accumulation.

Tests, 206 passing in the two files, 1058 in the register maps around them:

- `tests/test_energy_ceiling.py`: every multi-word energy field carries the
  ceiling its unit asks for; the field refuses Maximo101's two words
  (`0x9F6D`, `0xFFFF`) and reads the same low word under a sound high word; a
  refused value is logged once per value; an unknown unit is refused rather
  than given the kWh ceiling; and **every one of the 96 committed documents**
  is checked against the ceiling, with Maximo101's `total_battery_charge` the
  only reading above it anywhere.
- `tests/test_plausibility.py`: the synthetic house still matches every check,
  a whole cut by a sixth is a finding, one cut by 5 % is not, a house under
  the floor leaves the row waiting rather than failing, three polls settle it
  -- and a corpus section that runs the check over all 89 inverter documents
  and asserts it finds **exactly** bigz2012's and brendan's, matches
  Maximo101's, and matches 81 houses.

Next: `Todo.md`, then the gate.

### 2026-11-19 -- the plan's last question, answered: yes, and in its own section

**`doc/integration_migration.md` now says it**, under *A reading the
integration now refuses, that your history may still hold*, between
*Afterwards* and *What the entities look like now*. Why it belongs in the
migration guide and not only in a release note: the migration is **what
carries the bad statistic forward**. A house answering *Start fresh* gets new
entity ids and a clean series; a house answering *Migrate my existing
entities* keeps the id, and the recorder keeps writing to the same
long-term statistics the 429 million kWh is already in. That is a
consequence of the choice this document exists to explain.

Written to the **symptom**, not to the firmware: a reader cannot tell what
their inverter runs without looking, but anybody who has had this has seen an
Energy dashboard bar in the hundreds of millions.

The repair is the owner's and the document says so plainly. Verified against
the installed Home Assistant rather than from memory:

- `recorder.purge_entities` removes **states and events only**
  (`homeassistant/components/recorder/purge.py:purge_entity_data`), so it is
  not the tool, and the document says why.
- **Developer tools -> Statistics** is, and its three actions are named as its
  own translations name them: *Delete statistics in a time range* (the one
  to use, `recorder/clear_statistics` with a start and an end), *Adjust sum*
  (`recorder/adjust_sum_statistics`, for a single hour) and *Delete selected
  statistics* (the whole series).

Not done by the integration on its own, and this is the decision: it does not
delete or adjust anybody's statistics. An upgrade that silently removes years
of recorded data is worse than the wrong number, which is visible and which
the owner can judge.

Next: the wiki ingest and `Todo.md`, then the gate.

### 2026-11-19 -- both built, and the corpus corrects the plan above

**The relation catches two of the three, not all three.** Run over all 89
inverter documents, `lifetime battery counters contain each other` finds
bigz2012 and brendan and **matches Maximo101**, because 429,494,295.3 kWh is
*larger* than every counter it is compared with: a containment catches a whole
that has fallen below its part, and that machine's whole has gone up. The
ceiling is the only thing that sees it. Nothing can be done about this by
widening the relation -- there is no honest upper bound on the pair either
(bleughb reads 9,290 kWh charged against 0.0 from PV, and
anonymous-17579213881 reads 5.6x its own discharge), so an upper ratio would
fire on honest houses. The two defences divide the fault between them exactly,
and the sentence in the plan above is the one thing in it the corpus does not
support.

The sweep's whole result: **81 matched, 2 found, 6 without a verdict** (houses
with no battery, or under the 100 kWh floor). No honest machine is touched.

Built:

- `CeilingField` and `energy_counter()` in `src/sungrow_modbus/model.py`, with
  `ENERGY_CEILING_KWH` = 1,000,000 and `ENERGY_CEILING_WH` beside it. `scale`
  is a required argument and the ceiling is taken from `unit`: a defaulted
  scale would have quietly re-scaled the four counters that hold whole units,
  and a kWh ceiling on the wallbox's watt-hours would have refused any car
  that has charged a megawatt-hour. Refused values are logged when the value
  changes, not every poll.
- Every energy counter wider than one word in all six maps now declares it:
  the inverter's nine lifetime totals and its 45 yearly history slots, the
  SBR's two, the SG's nine, the iHomeManager's two, the wallbox's two and the
  Logger's daily yield.
- `lifetime battery counters contain each other` in
  `src/sungrow_modbus/capability_test/plausibility.py`, judged on one poll so
  a diagnosis settles it from one run.

Next: the tests, then the `doc/integration_migration.md` question.

### 2026-11-19 -- decided: both, because the corpus says each misses what the other catches

Measured over every committed diagnosis
(`device-diagnosis/results/*/*.json`: 96 documents, 89 of them an inverter's):

- **Above a million kWh: only Maximo101's two readings** (429,494,295.3 and
  429,494,257.3). The largest honest lifetime counter anywhere in the corpus
  is `total_pv_generation_battery_discharge` at **79,459.6 kWh**
  (robbensonmio's). A ceiling of 1,000,000 kWh therefore stands 12x above the
  largest real reading and four hundred times below the broken one. It is the
  only defence that stops a number reaching the recorder -- but it catches
  **one** of the three machines.
- **The two others read plausibly.** bigz2012's 14,844.2 kWh and brendan's
  6,374.1 kWh are numbers a house can have; no ceiling can see them. The
  relation catches both: against their own `total_battery_discharge` they are
  short by 40.6 % and 99.4 %.
- **The relation can fail honestly, by a little.** Three machines read
  `total_battery_charge_from_pv` above `total_battery_charge` --
  anonymous-33472554127 by 0.03 %, sisu70 by 0.70 %, icefest by **2.06 %** --
  and biergitkraft reads 5.0 kWh discharged against 4.8 kWh charged, 4.17 %
  of a counter that has barely started. The two broken machines that read
  plausibly are out by **32.4 % and 40.6 %** (bigz2012) and **97.3 % and
  99.4 %** (brendan). So the check needs a margin, not a bare `>=`: **10 %**
  sits five times above the worst honest reading and three times below the
  smallest broken one, with a floor of 100 kWh so that a house in its first
  weeks cannot trip it.

So: both, and neither alone. The ceiling is the defence (it keeps the number
out of the recorder); the relation is the detector (it is the only one that
sees a high word that is merely one wrap short).

**Weighed and not built: the wider relations.** The same sweep tested five
more containments. `total_pv_generation >= total_battery_charge_from_pv` and
`>= total_direct_energy_consumption` hold over the whole corpus with 40 %
headroom, but they cannot catch a lost wrap (it makes the whole smaller, never
the part bigger), so they would add two rows to every house's ledger and find
nothing. Three others are **not relations at all** and would have fired on
honest machines: `total_pv_generation_battery_discharge >= total_pv_generation`
(54 violations, up to 46 %), `total_exported_energy >=
total_exported_energy_from_pv` (23, including a 0 against 16,758.3), and
`total_pv_generation >= total_exported_energy_from_pv` (fwitten's, 20 %).
Recorded here so the next session does not re-run the sweep.

Next: the ceiling as a field property in the library.
