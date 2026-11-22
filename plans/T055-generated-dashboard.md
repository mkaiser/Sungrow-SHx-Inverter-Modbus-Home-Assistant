# T055 - The integration's own dashboard

One dashboard for every house, built in the browser from the entities that
exist there. A user who wants more takes it over and edits it as their own.
Nothing to install from HACS.

## What it has to solve

- **Names differ per house.** An entity id may carry a room or a device
  prefix, the YAML package's legacy id, or a `_2` where an owner's own
  template sensor already holds the plain id. A dashboard written against
  entity ids fits one house.
- **Houses differ.** An entry can carry an inverter alone, or an inverter
  with a battery, a wallbox and an external generator; a wallbox entry carries
  neither. An entity exists only where its capability answered, so a dashboard
  written for the richest house reads *not available* everywhere else.
- **The controls write to the house.** The YAML package hid them behind a
  danger-mode switch; the integration's own guard today is per account and
  covers start, stop and the capability test only.

## The route: a dashboard strategy the integration serves

A dashboard strategy is a frontend module that returns a Lovelace config when
the dashboard is opened. The integration serves its own module, so it needs
nothing from HACS:

- `custom_components/sungrow_modbus/frontend/sungrow-modbus.js`, a plain ES
  module with no build step and no dependencies. It defines
  - `ll-strategy-dashboard-sungrow-modbus` (`static async generate(config, hass)`);
  - `sungrow-modbus-lock-card`, the hold-to-unlock wrapper (below);
  - entries in `window.customStrategies` and `window.customCards`, for the
    pickers.
- `custom_components/sungrow_modbus/frontend/layout.json`, the layout as
  data: views, sections, cards, and each card's entities named by
  `translation_key` (MPPTs and phases by pattern). Hand-written source.
- `async_setup` registers the static path once
  (`hass.http.async_register_static_paths`) and adds the module with
  `frontend.add_extra_js_url`, versioned by the manifest's version so an
  update reaches the browser. `frontend` joins the manifest's dependencies.

### Finding the entities

By what the integration owns, never by `entity_id`:

1. Inverters are the devices with a `sungrow_modbus` entity and no
   `via_device_id`. A battery or wallbox is the device whose `via_device_id`
   is that inverter; a wallbox-only entry is its own root. `device_id` in the
   strategy config pins one inverter; with several, each gets its own views.
2. A card slot resolves to the entity with `platform == "sungrow_modbus"`,
   that `device_id` and that `translation_key`; hidden and disabled entities
   are skipped.
3. A card that resolves nothing is dropped, and so is a section left empty.
   The condition is on the entity existing, not on its state: an offline
   device still shows *unavailable*, which is what its owner wants to see.
4. Names come from the integration's own translations
   (`component.sungrow_modbus.entity.<platform>.<key>.name`), so the dashboard
   speaks the user's language without a word typed into it. Headings come from
   a small en/de table in the module.

### Views

- **Overview**: now (PV, load, grid import and export, battery power, a
  state-of-charge gauge), today's counters, power over 24 hours, and daily
  energy as statistics bars over 30 days.
- **Battery**, where a battery device exists: a section per pack (health,
  temperature, voltage, current), cells, lifetime counters, charge and
  temperature over 48 hours.
- **Inverter**: state, alarm and fault, temperature, grid frequency; the
  MPPTs present; the phases present; firmware and lifetime totals; a link to
  the device page.
- **Wallbox**, where a wallbox device exists: status, power, session and total
  energy, phases, history.
- **Controls**: operation (EMS mode, forced charge or discharge and its
  power), limits (export, import), battery (minimum and maximum charge, backup
  reserve, charge and discharge power), schedules, wallbox control; above them
  a note that a change acts at once and is not undone. Start, stop and the
  capability test stay out: they are actions, under the entry's permissions.

### The controls lock

A strategy option picks it:

| `controls` | What the Controls view does |
| --- | --- |
| `hold` (default) | Visible to administrators only; each section is wrapped in `custom:sungrow-modbus-lock-card` |
| `admin` | Visible to administrators only, no lock |
| `hidden` | Not built |

The lock card wraps one card (`loadCardHelpers().createCardElement`) under an
overlay that takes every tap. Holding it 3 seconds and confirming unlocks it
for `unlock_seconds` (30 by default), then it locks again. The unlock lives in
that browser only, so one person's unlock does not open the controls on the
wall tablet. It is the same behaviour as HACS's `restriction-card` with
`action: hold`, which the maintainer's heat-pump dashboard uses, and it can be
used on its own in any dashboard while the integration is installed. That
makes it the replacement for the YAML package's danger-mode switch.

The view is restricted with `visible: [{user: ...}]`, which needs the
administrators' ids (`config/auth/list`, administrators only); for anyone
else the strategy leaves the view out.

### How a user adapts it

1. **Add it**: Settings → Dashboards → Add dashboard → *Sungrow Modbus*, or
   two lines in the raw configuration editor.
2. **Options**, in the raw configuration editor:

   ```yaml
   strategy:
     type: custom:sungrow-modbus
     device_id: <optional, one inverter>
     controls: hold        # hold | admin | hidden
     unlock_seconds: 30
     views: [overview, battery, inverter, wallbox, controls]
   ```

3. **Take control** (the dashboard's menu): Home Assistant writes out the
   generated config with the house's real entity ids, to edit card by card.
   A dashboard taken over no longer follows a capability that appears later;
   the docs say so.

## Steps

1. **Read the frontend first**, at the minimum Home Assistant version
   (`doc/architecture.md`): the custom dashboard strategy API and `generate`'s
   signature; whether `window.customStrategies` reaches the add-dashboard
   picker; that `hass.entities` carries `translation_key`, `platform` and
   `device_id`; that *Take control* works on a custom strategy. What does not
   hold changes this plan before any code.
2. Serve the module (`__init__.py`, `manifest.json`); a test that the path is
   registered once across two entries; `make hassfest`.
3. `layout.json`, and a test that every `translation_key` in it is one the
   description modules define and `translations/en.json` names, so a renamed
   key fails CI instead of emptying a card.
4. The strategy, then the lock card.
5. `doc/dashboard.md` (the three levels, the options, the lock card on its
   own, screenshots); links from the README and the install guide;
   `doc/integration_migration.md`'s danger-mode row and paragraph point at
   the lock card; `doc/architecture.md`'s "danger-mode toggle ... not ported"
   becomes the lock decision; `dashboard/wallbox/dashboard.yaml` goes, its
   view now built.
6. `make quick`, then `make check`.

## Verification

- The dev instance on the simulator: each view, English and German, each
  `controls` mode as an administrator and as a plain user; the lock ignores a
  tap, opens after a 3-second hold and a confirm, and locks again after its
  time.
- A wallbox-only entry and a house without a battery leave no empty section.
- *Take control* produces the real ids and still renders after a reload.
- The container has no node, so the module is checked by hand on the dev
  instance; the test of step 3 guards the data.
- gerd: save the live inverter and wallbox dashboards first, add this one
  beside them, compare, and replace them only on the maintainer's word.
