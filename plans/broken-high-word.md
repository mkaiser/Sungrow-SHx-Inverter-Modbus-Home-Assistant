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
