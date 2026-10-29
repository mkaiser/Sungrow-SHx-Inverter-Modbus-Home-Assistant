---
type: concept
title: The legacy slot of a second inverter
tags: [migration, history, multi-inverter]
created: '2026-10-29'
---

# The legacy slot of a second inverter

The YAML ids are global and unprefixed, so only one device can hold them.
`legacy/modbus_sungrow_multiple_inverters_<n>.yaml` appends ` inv <n>` to every
name and `_inv_<n>` to every unique_id. Which physical inverter was `inv 2` is
something only the house knows, so the integration **measures it rather
than asking**. That file's `sensor.sungrow_inverter_serial_inv_<n>` holds its
inverter's serial as its *state*, and an entry already knows the serial it
is talking to.

`migration.async_resolve_legacy_slot` matches them: the live state first,
then the states the recorder kept. It returns `""` only when no numbered
slot (`_inv_<n>`) ever existed in the registry or the recorder.

Each of these rules, if broken, loses somebody's history:

- **`None` is not `""`.** No match means the question could not be answered.
  Reading it as the unsuffixed slot would silently hand a second inverter the
  first one's years of readings, and no later guess undoes that. So `None` is
  stored as `None`, `stored_legacy_slot` returns it, and a `None` entry
  claims no legacy ids. An absent key is the unsuffixed slot of an entry that
  predates the slot.
- **The slot is stored in `data` under `CONF_LEGACY_SLOT`**, because detection
  needs the YAML package installed, or its serial still in the recorder, and
  the migration's next instruction is to remove it. The claim at setup reads
  the stored slot and never re-derives it. Only the options flow measures
  again, for a slot stored as `None`.
- **The suffix goes on the name, not the id.** The YAML names the entity
  `Total DC power inv 2`, and Home Assistant slugifies that. Appending
  `_inv_2` to the finished id agrees today, and stops agreeing the first time
  a name contains something `slugify` treats differently.
- **The lookup uses platform `modbus`**, not `sensor`. The YAML reads the
  serial over Modbus, so `modbus` is what registered it. Getting this wrong
  costs nothing visible: it simply never matches, and a two-inverter house
  migrates as though it had one.

See [adopting the legacy entity ids](legacy-id-adoption.md).
