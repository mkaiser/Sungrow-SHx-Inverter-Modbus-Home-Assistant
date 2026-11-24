# T055 - The integration's own dashboard

One dashboard for every house, built in the browser from the entities that
exist there. A user who wants more takes it over and edits it as their own.
Nothing to install from HACS.

## Status log

- **2026-11-24, 01 CET**: **0.1.0a53 is released** (PyPI, GitHub, the preview mirror pinned; 0.1.0a52 stopped in CI at a test
  importing a Home Assistant component CI does not install, and was never published). It carries the power flow and, under
  Home's *Today*, the day's energy flow (`energy-flow-card-plus`, from long-term statistics; its figures are **not seen on real
  values**, the simulator's daily sensors are constant), the Diagnosis view's Settings, one tab for a wallbox entry, and the
  lock at 2 s / 60 s. Left: the maintainer's look, then gerd's (where the doubled tabs were seen), and a check that *Today*'s
  circles show the day's figures once statistics exist.

- **2026-11-23, 23 CET**: gerd's house showed Home and Diagnosis twice (0.1.0a51), because his wallbox is an entry of
  its own and so a family of its own: the Home *Car* section alone filled a Home. Fixed: with one inverter, a wallbox
  entry lends its entities to the inverter's Home and Controls and its Diagnosis is a part of the inverter's; inverters
  come first; with several inverters a wallbox keeps its own tabs but no Home. The lock opens after 2 s and stays open
  60 s. Checked in Chromium on synthetic houses (inverter alone, wallbox alone, both, on the bus and beside it, two
  inverters, two wallboxes), not on gerd's registry. Not released.
  Then the power flow card in the wheel and the
  diagnosis's settings in the Diagnosis view, checked on a scratch instance on the simulator: the flow draws, an answer
  saves, an allowed test refuses a tap while locked and saves once held. Not seen: a wallbox entry's settings, a save
  refused during a run in the browser (the server's refusal is tested).

- **2026-11-23**, done over, after the maintainer's four items and their looking at it; released
  as 0.1.0a51 (PyPI, GitHub, the preview mirror). What it is now is *The second layout* below; where that differs from the older sections, it
  holds. Checked in Chromium on a demo house: German and English, desktop and phone, dark; the lock (tap and Tab reach
  nothing, a hold opens); taking over, then a newer revision: add beside, replace (the backup equals the copy),
  dismiss; Stop outside the lock; and, in the strategy alone, a plain user, no battery, two inverters, an SG, a
  wallbox on its own, diagnostics only. **Not checked**: gerd's registry (unreachable that evening), a live run
  in the Diagnosis view, the results of a wallbox entry.

- **2026-11-22 evening**, released: 0.1.0a50 is on PyPI, the GitHub release and the preview
  mirror (pin check green). The maintainer's own Home Assistant and gerd's run the same code as
  a hand-installed `0.1.0a50+g5390594`; a Marketplace update to 0.1.0a50 replaces it with the
  release. Left: the maintainer's verdict on the dashboard at both houses, and at gerd's whether
  it replaces the two hand-made dashboards.

- **2026-11-22**, built and checked (`bf6d52f`, `3aa6b6c`, `3aee981`): steps 1-4
  below are done, the gate green (8758 passed). Release **0.1.0a50** carries it,
  committed and tagged `v0.1.0a50` (`5390594`) but **not pushed**: the maintainer
  said not yet. Pushing is `git push --follow-tags origin proper-ha-integration`,
  then the release skill's steps 5-6. The same code runs at gerd's as
  `0.1.0a50+g5390594` (file-URL wheel; the previous build kept as
  `/config/sungrow_modbus_42d3adc_backup`), where the maintainer tries the
  dashboard themselves. The restart for it ended auto repeat on both entries.

## The second layout

- **Views**: Home, Energy, Battery, Inverter, Wallbox, Controls, Diagnosis. An option that says `overview` is read as
  `home`. Tiles carry short names of the layout's own; the lists keep `{type: entity}`.
- **Battery power is charge and discharge**, never signed (maintainer).
- **Controls by device**, everything about the battery in one section, in groups side by side; no question
  headings (maintainer). The lock leaves values readable: the wrap is `inert` under an invisible overlay.
- **A setting outside the lock opens no dialog**, since the dialog would change it past the lock; the layout
  test holds that, and that Stop is never locked and what writes is for administrators.
- **Power flow: in the library's wheel** (maintainer, 2026-11-23), and the day's energy flow beside it
  (`energy-flow-card-plus`, which reads long-term statistics of the day's sensors and needs no Energy dashboard; on Home's
  *Today*, where it replaces the six tiles it shows). `scripts/release/fetch_cards.py` fetches the pinned
  `power-flow-card-plus`, checks its SHA-256, renames its element and drops its card picker entry; the wheel carries it
  with its licence, and `dashboard.py` serves the one file. Tiles where it is missing (a source checkout) or fails to
  load. The energy flow is core's `energy-distribution`, where the Energy dashboard has sources.
- **The diagnosis's settings** are the entry's options (`diagnosis_settings.py`), read and saved over the websocket by
  administrators, with Configure's texts. Saving does not reload (`_built_from` leaves `RUN_OPTIONS` out), since a
  reload would end a collection; the server refuses a save during a run, and an allowed test through the unlocked part.
- **Results**: `sungrow_modbus/diagnosis/results` (`websocket.py`, administrators, the host taken out), built by
  `capability_test/results.py`; a person's name for every check in `capability_test/labels.py`, the ledger's names
  unchanged. What a check waits for, and verdicts, are still English (T007's item 4.3).
- **Logs**: each run's notes come with the results; the live log is the recorded history of *Diagnosis: current
  step*, read by the card (`logLines` in `frontend/tests.js`), so nothing new is recorded.
- **Revisions**: a change to `layout.json`'s views raises `revision` and adds to `changes`, which a digest in the test
  enforces; `sungrow-modbus-update-card` sits on the first view. Copies from 0.1.0a50 carry none.

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
4. Every tile and entities row carries `name: {type: entity}`: the entity's
   own translated name without the device name in front. A plain row repeats
   the device ("Carport AC22E-01 Phase mode"), which is why gerd's wallbox
   dashboard was given hand-typed short names. Nothing is typed in, so the
   dashboard speaks the user's language, and so does a copy taken over.
   Headings come from a small en/de table in the module.

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

## What the frontend offers

Read in the frontend that Home Assistant 2026.11, the minimum, pins
(`home-assistant-frontend` 20261028.6):

- **A custom dashboard strategy** is the element `ll-strategy-dashboard-<name>`
  with `static async generate(config, hass)`, referred to as
  `strategy: {type: custom:<name>}` (`src/panels/lovelace/strategies/get-strategy.ts`).
  An optional `shouldRegenerate(config, oldHass, newHass)` decides when it is
  built again; without it, a registry change rebuilds it.
- **The add-dashboard dialog lists custom strategies** registered in
  `window.customStrategies` (`{type, strategyType: "dashboard", name,
  description, documentationURL}`), beside Home Assistant's own
  (`src/data/lovelace_custom_strategies.ts`, `dialog-new-dashboard.ts`).
- **`hass.entities` carries `platform`, `translation_key` and `device_id`**
  (`EntityRegistryDisplayEntry`, `src/data/entity/entity_registry.ts`).
- **Take control works on a custom strategy.** *Edit dashboard* opens the
  strategy editor dialog: its YAML mode edits the options, and its *Take
  control* saves the generated config as an ordinary dashboard
  (`hui-root.ts`). The module sets no `noEditor`, which would skip straight to
  taking control and hide the options.
- **Names without the device**: tiles and entities rows take `name` as
  `{type: entity}` (`EntityNameItem`, `src/common/entity/entity_name_config.ts`).
- **A view or section is limited to users** by the `user` visibility
  condition (`users: [...]`).

## Steps

1. **Done.** `dashboard.py` serves `frontend/` at `/sungrow_modbus_frontend`
   and adds the module with `?v=` a hash of the files (a development build
   carries the release's version with other code). `frontend` is an
   after-dependency, not a dependency: every real Home Assistant runs it, and
   without it setup goes on with no dashboard (`tests/test_dashboard.py`).
2. **Done.** `frontend/layout.json` names each entity as
   `<domain>.<translation_key>`. `a|b` takes the first that exists (the hybrid
   and the string inverter name the same reading differently), a leading `~`
   resolves anywhere in the integration if unique and never keeps a card on
   its own (the wallbox history's PV and load), and `{n}` expands over a
   card's `repeat`. `tests/test_dashboard_layout.py` holds every key to
   `translations/en.json`, every text to English and German, and the views to
   the strategy's list. It caught the MPPTs: a hybrid has `mppt1..4`, a string
   inverter `sg_mppt1..12`, so they are two cards, not one with alternatives.
3. **Done.** `frontend/sungrow-modbus.js`: the strategy and the lock card,
   no build step, no dependency. What the build settled:
   - **Families.** An inverter and every device whose `via_device_id` leads
     to it; a wallbox entry of its own is its own family, and each family
     builds the views it can fill, but a wallbox entry beside one inverter joins its Home, Controls and
     Diagnosis (`guests`). gerd's separate wallbox entry gives one
     Wallbox view, its history drawing the inverter's PV and load through `~`.
     With two inverters every view is built per inverter, suffixed with the
     device name, and the ambiguous `~` lines drop out.
   - **Names.** `{type: entity}` shows the entity's name in Home Assistant's
     **system** language: the frontend takes entity names from the server,
     not the viewer's profile. Headings and the lock follow the viewer.
   - **The lock** is a hold alone, without a confirm dialog: a held press is
     already deliberate, and a browser `confirm()` is not reliable in the
     companion apps' web views. Its cards share a `group` (`controls`), so one
     hold opens the whole view; the unlock lives in that browser tab. The
     unlocked note sits below the card, so the last row stays reachable.
   - **The Controls view** is left out for a plain user, and carries the
     administrators as `visible` users, for a copy that is taken over.
   - `registryDependencies = ["entities", "devices"]`: rebuilt on a registry
     change, not on every state change.
   - Checked in V8 against gerd's real registry (legacy ids,
     `total_consumed_energy_2`, `sh8_0rt_v112_` prefixes all resolve) and
     against an empty house, a pinned wallbox, both languages, each
     `controls` mode and two inverters; then in Chromium on a scratch instance
     on the simulator: every view renders without a console error, a tap
     leaves the lock shut, a hold opens the group, *Lock* shuts it,
     the add-dashboard dialog lists *Sungrow Modbus* under *Community
     dashboards*, the edit dialog edits the options in YAML, and *Take
     control* saves the real ids with the lock cards kept.
4. **Done.** `doc/dashboard.md` (adding it, the views, the lock, the
   options, taking control, the lock card on its own, coming from the YAML
   package), with three screenshots in `doc/images/` that
   `scripts/dev/screenshot.py` retakes (`dashboard-add`, `dashboard-home`,
   `dashboard-controls`). Linked from the README; the migration guide's
   danger-mode row and paragraph now point at the lock; `doc/architecture.md`
   records the decision; `doc/development.md` says how the module is checked;
   the merge step in `plans/T047-T053-release.md` names its documentation
   link; `dashboard/wallbox/dashboard.yaml` is gone.
5. `make quick`, then `make check`.

## Verification

- The dev instance on the simulator: each view, English and German, each
  `controls` mode as an administrator and as a plain user; the lock ignores a
  tap, opens after a 3-second hold and a confirm, and locks again after its
  time.
- A wallbox-only entry and a house without a battery leave no empty section.
- *Take control* produces the real ids and still renders after a reload.
- The container has no node, so the module is checked by hand on the dev
  instance; the test of step 3 guards the data.
- gerd: the live inverter and wallbox dashboards are saved (gitignored
  `tmp/gerd-backup-ha/live_2026-11-22_*.json`; the wallbox one carries
  hand-typed short names, the device-name problem `{type: entity}` solves).
  The build is installed there; left: the maintainer adds the dashboard
  beside them, compares, and decides whether it replaces them.
