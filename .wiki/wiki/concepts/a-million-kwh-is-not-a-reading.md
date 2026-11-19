---
type: concept
title: A million kWh is not a reading
tags: [decoding, counters, recorder, firmware]
created: '2026-11-19'
---

# A million kWh is not a reading

A sentinel is a value the specification declares. A **broken word** is not
declared by anybody, and it reads as a number.

[SUNSTONE-H_B000.V002.P067](../entities/firmware-sunstone-h-b000-v002-p067.md)
is the measured case: 13042, the high word of `total_battery_charge`, is wrong
on all three machines read, and at
[Maximo101](../entities/installation-maximo101.md)'s it holds `0xFFFF` while
13041 below it keeps counting correctly. The double word is therefore not
`0xFFFFFFFF`, so a `nan=` sentinel cannot catch it, and the sensor published
**429,494,295.3 kWh** and then rose plausibly from there — into the recorder's
long-term statistics, where it stays until somebody deletes it by hand
(`doc/integration_migration.md`).

So the library refuses a reading for its **size**:

- **A lifetime energy counter above 1,000,000 kWh decodes as None.**
  `CeilingField` and `energy_counter()` in `src/sungrow_modbus/model.py`, used
  by all 74 energy registers wider than one word, across every device map:
  the inverter's, the SG's, the SBR's, the iHomeManager's, the wallbox's and
  the Logger's. `tests/test_energy_ceiling.py` holds the maps to it, so a
  counter added later cannot go back to publishing a broken word.
- **The ceiling is a property of the field, not a rule in the sensor
  platform.** Everything that reads these maps has to agree about it: Home
  Assistant's sensors, the readings a diagnosis publishes, the plausibility
  checks. A rule in one of them leaves the others publishing a number the
  first has already refused.
- **It is far from anything real, on purpose.** The largest honest lifetime
  counter in the whole corpus is 79,459.6 kWh, at
  [robbensonmio](../entities/installation-robbensonmio.md)'s; the ceiling
  stands twelve times above it and four hundred times below the broken
  reading. It decides nothing a measurement could decide.
- **A one-word counter needs none.** At 0.1 kWh a `U16` cannot pass 6,553.6
  kWh, which is a lifetime a house can have, and its sentinel is `0xFFFF`.

## What the ceiling cannot see, and what does

A high word that is merely **one wrap short** reads perfectly plausibly:
14,844.2 kWh at [bigz2012](../entities/installation-bigz2012.md)'s, 6,374.1 at
[brendan](../entities/installation-brendan.md)'s. Nothing in either reading
says anything is wrong. Standing it beside a counter it has to contain does:

- `total_battery_charge` >= `total_battery_charge_from_pv`, charging from PV
  being a part of charging;
- `total_battery_charge` >= `total_battery_discharge`, a battery not being
  able to give out more than it took in.

`lifetime battery counters contain each other` in
`src/sungrow_modbus/capability_test/plausibility.py` is that check. It costs
no Modbus read, and it is judged on **one poll** rather than over days,
because it is arithmetic between registers read in the same block — which is
what lets a single diagnosis settle it for a house nobody can visit.

**Its margin is measured, not chosen: 10 %, with a floor of 100 kWh.** Sungrow
counters cross each other honestly by a little — by 0.03 % at
anonymous-33472554127's, 0.70 % at [sisu70](../entities/installation-sisu70.md)'s,
2.06 % at [icefest](../entities/installation-icefest.md)'s, and by 4.17 % at
[biergitkraft](../entities/installation-biergitkraft.md)'s, whose counters have
barely started. The broken ones are out by 32.4 % and 40.6 % (bigz2012) and
97.3 % and 99.4 % (brendan). Over all 89 inverter documents the check matches
81, finds 2 and leaves 6 without a verdict.

## Containments Sungrow's counters do **not** honour

Measured over the same corpus, and recorded here so nobody adds them. Three
read like relations and are not:

- `total_pv_generation_battery_discharge` >= `total_pv_generation`: **54
  violations**, up to 46 % ([ra1k-0](../entities/installation-ra1k-0.md)'s).
- `total_exported_energy` >= `total_exported_energy_from_pv`: **23**, one of
  them a 0.0 against 16,758.3 kWh.
- `total_pv_generation` >= `total_exported_energy_from_pv`: 20 % out at
  [fwitten](../entities/installation-fwitten.md)'s.

Two more do hold over the whole corpus, with 40 % of headroom --
`total_pv_generation` >= `total_battery_charge_from_pv` and >=
`total_direct_energy_consumption` -- and are still not worth checking: a lost
wrap makes the **whole** smaller, never the part bigger, so neither can catch
the fault this exists for.

## The two of them divide the fault, and neither does both halves

Maximo101's reading **passes** the containment, because 429 million kWh is
larger than everything it is compared with: a containment sees a whole that
has fallen below its part, and that machine's whole has gone up. No upper
bound would help — [bleughb](../entities/installation-bleughb.md)'s honest
machine reads 9,290 kWh charged against 0.0 from PV, and
anonymous-17579213881's reads 5.6 times its own discharge.

So: **the ceiling is the defence** and catches only the reading that is
absurd; **the containment is the detector** and catches only the one that is
not. Where the ceiling has refused a reading, the field decodes as None, and
the containment check drops out of the summary rather than reporting on a
house — the ceiling has already spoken, in a log line that names the field and
the value.
