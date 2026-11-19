# T055 - A generated dashboard

Nothing generates one yet. Open: generate a Lovelace dashboard (asking
first), or rely on entity metadata and document the auto-generated view.

**The question to settle first: one default dashboard over houses that
differ.** An entry can carry an inverter alone, or an inverter with an SBR,
a wallbox and an external generator; a wallbox or an iHomeManager entry
carries neither. An entity exists only where its capability answered
(`Capability`, measured at setup), so a dashboard written for the richest
house reads *not available* on every other one, and one written for the
poorest shows almost nothing. The routes, none chosen:

- **Generated per entry, from the capabilities that answered.** One
  dashboard, built for the house it is built in, with no empty card by
  construction. It has to be rebuilt when a capability appears later (a
  battery added, a wallbox found), which wants a repair or an action rather
  than a silent rewrite, and it must never overwrite what the owner has
  edited since.
- **One shipped dashboard of conditional cards.** A card per device behind a
  condition on an entity of that device, so a device that is not there
  leaves no gap. Nothing to generate and nothing to keep per house, but a
  condition on `unavailable` also hides a device that is merely offline,
  which is the state an owner most wants to see; the condition has to be on
  the capability (the entity existing at all), not on its state.
- **A dashboard per device, linked from one view.** Follows the device
  pages, so nothing is ever empty, but it is several dashboards and not the
  one asked for.
- **Nothing of our own**: document Home Assistant's auto-generated view,
  which is what an install gets today.

Whatever is chosen is asked for and never installed by itself: a dashboard
that appears unbidden is a change to the owner's sidebar.
`legacy/doc/dashboard.md` is the YAML package's, and the material to port
(T051); `doc/energy_dashboard.md` stays what it is, the Energy
dashboard being core's and not ours.
