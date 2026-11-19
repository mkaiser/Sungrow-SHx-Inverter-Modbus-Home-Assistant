# evcc on top of the Sungrow integration — investigation and user guide

## Context

`Todo.md` § *EVCC connection* asks whether evcc can take its inverter and wallbox
readings from us instead of opening its own Modbus session. A Sungrow accepts few
sessions (wiki `concepts/contention.md`), and the maintainer wants no Modbus proxy
and no second writer racing the integration. Scope chosen: **meters + wallbox +
battery control**, delivered as a **user guide** (`doc/evcc.md`) plus Todo/wiki updates.
No integration code changes.

## Findings (researched 2026-11-17)

**Licence / cost.** evcc is open source (MIT) and free to run. A sponsor token
($4/month or $150 once on GitHub Sponsors; €50/year or €150 once direct) is
needed only for many commercial chargers. The **`homeassistant` charger template
says "No sponsor token required"**, and meters never need one. evcc's own
Sungrow AC011E-01/AC22E-01 template is token-free too, but it talks Modbus
directly, so we don't use it. A trial token is published (currently valid to
2026-11-23).
Sources: docs.evcc.io/en/sponsorship, /en/chargers/home-assistant-charger,
/en/chargers/sungrow-ac22e-01.

**The route: evcc's `homeassistant` templates.** evcc then reads and writes only
HA entities over HA's REST API, never Modbus. Each write lands in our
integration, so it takes the shared serialized connection, `PARALLEL_UPDATES = 1`
and the `write_owner.py` interlock. This meets the requirement: no proxy, one
Modbus client, no races. While a capability test runs, our controls refuse and
evcc just logs an error.
- Auth: in the evcc UI, *Home Assistant* integration → the HA login tab
  issues a token, and evcc renews it itself. If evcc runs as the HA app
  (`evcc-io/hassio-addon`, a community add-on), pick `http://supervisor/core` and
  the login step is skipped (docs.evcc.io/en/smarthome/home-assistant).
- The HACS integration `marq24/ha-evcc` brings evcc's state back into HA. This is optional.

**Meters → our entities (signs already match evcc: import +, battery discharge +).**
- grid: `power: sensor.meter_active_power` (5600: >0 buy). Energy:
  `total_imported_energy` / `total_exported_energy` (`returnEnergy`).
- pv: `power: sensor.total_dc_power`, energy: the total PV generation sensor.
- battery: `power: sensor.battery_power` (5214: + discharging, − charging,
  legacy YAML l.370), `soc: sensor.battery_level`, `capacity`, and
  `minSocEntity`/`maxSocEntity` → `number.battery_min_soc` / `number.battery_max_soc`.
  Entity ids are verified against a running instance (`make dev` + `make sim`)
  before they go into the doc.

**Wallbox → `homeassistant` charger.**
- For a wallbox the inverter manages (gerd's case): the inverter overwrites
  21203 and ignores 21204 (wiki `concepts/managed-wallbox-phases.md`). So evcc
  steers through the inverter's EV-charger block on the inverter entry:
  - `enable`: `switch.…ev_charger_charging` (33540)
  - `setMaxCurrent`: `number.…ev_charger_user_current` (33545, 6 A up)
  - `enabled`: the same switch
  - `status`: `sensor.…wallbox_charging_status`, with `statusA: idle`,
    `statusB`: standby / suspended by the charge point / suspended by the
    vehicle / completed, and `statusC: charging`
  - `power`, `energy`, `currentL1-3`, `voltageL1-3`: the wallbox sensors
  - Precondition: `select.…ev_charger_mode` is set **once** to user-defined and
    `switch.…ev_charger_grid_purchase` is set as wanted. evcc must never
    change the mode: a mode change ends the session (wiki
    `gerd-wallbox-night-2026-11-16-summary.md`).
  - **No `phaseswitch`**: a managed wallbox's phases are the inverter's to
    choose. evcc is configured `phases: 3`, with 6 A × 3 = 4.14 kW the minimum charge.
- For a standalone wallbox (its own entry, TLS 516), the entities are read-only.
  There is no control path today, so the doc says so and points at Todo § Wallbox 3.3.
- Caveat: the HA controls with a car charging are still open (Todo § Wallbox 3.1).
  The doc marks the wallbox part **experimental** until that is watched.

**Battery → HA scripts.** The `homeassistant` meter has `modeNormal`,
`modeHold`, `modeCharge` (`modeNormal` is required once any other is set). The guide
ships three scripts over our entities:
- normal: `select.ems_mode` → `self_consumption`, and
  `select.battery_forced_charge_discharge` → `stop`
- hold: `ems_mode` → `forced`, forced charge/discharge → `stop` (the battery
  idles, the PV still serves the house; verify on hardware what *stop* does to
  PV-to-battery)
- charge: `ems_mode` → `forced`, forced → `charge`,
  `number.battery_forced_charge_discharge_power` → a set value
- Optional `modeDischarge` is left out: evcc does not need it, and it exports
  the battery.
- Verify with `evcc meter verifybatterymodes` (it cycles the modes and checks the
  battery power).
- Warning in the doc: a forced mode stays set if evcc dies. Add an HA automation
  that returns to normal when evcc goes unavailable (through the ha-evcc
  integration's state).

**Solar forecast and car SoC: both live in HA; evcc reads them (same principle as Modbus).**
- *Forecast.* evcc's `tariffs: solar: template: homeassistant` (token-free) reads
  the forecast(s) selected in HA's **Energy dashboard** (Forecast.Solar, Solcast,
  …), summed, hourly (docs.evcc.io/en/tariffs/home-assistant). evcc uses the forecast
  for charge plans and battery control. Why HA: one fetcher per site keeps the
  free tiers' tight quotas (Solcast hobbyist ≈10 calls/day; Forecast.Solar
  rate-limits per IP) from being spent twice. HA's dashboard and automations
  need the forecast anyway. Cost: hourly resolution only, and evcc's
  forecast is not documented as exposed back to HA.
- *Car SoC.* evcc's `vehicles: template: homeassistant` takes `soc`, `range`,
  `status`, `limitSoc`, `capacity`, and optional `start_charging`/`stop_charging`/`wakeup`
  (docs.evcc.io/en/vehicles/home-assistant). Why HA: one cloud client per car account.
  Two clients polling the maker's API wake the car, hit rate limits and get
  accounts locked, the same "few sessions" problem as the inverter. HA keeps
  the SoC history. Set `autodetectdisabled` and make the car the loadpoint's
  default vehicle. Check the HA vehicle page for a sponsor badge before
  writing the doc (none seen on the index).
- *Exception:* if the car has no HA integration but evcc has a template, use
  evcc's and mirror it back with `marq24/ha-evcc`. Without any SoC (e.g. gerd's car
  had no Internet on 2026-11-17), evcc plans by **kWh** for the current session
  only; percent targets and repeating plans need SoC + capacity (docs.evcc.io/en/features/plans).

## EMHASS instead of, or beside, evcc?

EMHASS (Energy Management for Home Assistant, MIT, HA app or docker, v0.18.9 on
2026-11-14, actively maintained) is a **planner**, not a charge controller.
- It solves an LP/MILP over PV forecast, load forecast and tariffs, day-ahead or
  as MPC every ~5 min. It publishes HA sensors (`sensor.p_batt_forecast`,
  `sensor.soc_batt_forecast`, `sensor.p_deferrableX`, `sensor.p_grid_forecast`, …).
  **It never writes to a device**: HA automations apply its plan
  (emhass.readthedocs.io/en/latest/publish_data.html, /automations.html). Like
  evcc via HA, it opens no Modbus session.
- It treats an EV as a *deferrable load*: a fixed amount of energy before a deadline, on/off at
  nominal power **per timestep** (30 min, or 5 min in MPC). There is no seconds-level
  PV-surplus current regulation and no SoC target, which you convert to kWh
  yourself. Its own EV recipe hands real-time charging to evcc
  (emhass.readthedocs.io/en/latest/cookbook/ev_evcc_executor.html).
- Its strength is **cost-optimal battery dispatch** under dynamic tariffs
  (Tibber, Nordpool, …) and scheduling other loads (heat pump, water heater). It has its
  own PV (Open-Meteo/PVLib, Solcast, Forecast.Solar) and ML load forecasts.
- Cost: more setup (a model of the system, tuning, automations that turn
  `p_batt_forecast` into `ems_mode`/forced-power writes), and no EV UI or vehicle integration.

**Verdict: not a better option for the car; a possible later addition for the
battery.** evcc stays the plan's core: real-time surplus charging, vehicle and SoC
handling, plans, a UI. Add EMHASS only if the site has a **dynamic tariff** where
arbitrage pays. Then follow EMHASS's documented split:
- **EMHASS owns the battery**: drop evcc's `modeNormal/Hold/Charge` scripts and keep
  evcc's battery meter read-only.
- **evcc owns the car**: EMHASS sets the loadpoint mode (`now`/`off`/`pv`) through
  evcc's API or the ha-evcc entities.
- **Never let both control the battery.** This is the same single-writer rule the integration enforces.
- One HA forecast feeds both (EMHASS can take `pv_power_forecast` at runtime from HA).
- Also note: a managed wallbox's inverter already does PV-surplus charging itself (EV
  charger mode *PV surplus*). evcc's added value there is SoC targets, plans and the
  UI, not the surplus regulation.

## Changes

1. **New `doc/evcc.md`** (for owners). It covers why to go through HA (sessions,
   the write interlock), cost, connecting evcc to HA, a full `evcc.yaml` (meters
   grid/pv/battery, charger, vehicle via HA, the solar forecast via HA, a loadpoint with
   `phases: 3`, `mincurrent: 6`, and site), the
   three battery scripts plus the fail-safe automation, the precondition on the wallbox
   mode, the limits (no phase switching, standalone wallbox read-only, wallbox control
   experimental), how to verify, and a short "with EMHASS" section (who owns
   the battery, who owns the car). Link it from `README.md` / `doc/integration_migration.md`
   wherever the docs list user guides.
2. **`Todo.md` § EVCC connection**: replace the question with the answer and what
   is left (watch evcc driving 33540/33545 with a car at gerd's; test the battery
   scripts with `verifybatterymodes` on the maintainer's SH10RT; what *stop* in
   forced mode does). Follow the multi-writer rule: `git status`/`git diff
   Todo.md` first, re-read, make a targeted edit.
3. **Wiki**: a source page for the evcc docs read today (save a raw note in
   `.wiki/raw/evcc-homeassistant-templates-2026-11-17.md`), a query page
   `queries/can-evcc-drive-a-managed-wallbox-through-ha.md` for the unwatched claims,
   and updates to `index.md` and `log.md`, following `.wiki/AGENTS.md`. No real serials or addresses.

## Verification

- `make dev` + `make sim`: confirm every entity id in the example exists and
  the selects accept the scripted options. Run the scripts in HA against the
  simulator.
- Optional: start evcc (docker) against the dev HA. `evcc --demo` is not enough;
  use the YAML with the `homeassistant` templates and check that evcc's UI shows grid/PV/battery
  and the loadpoint. Then run `evcc meter verifybatterymodes` (against the
  simulator it checks only the wiring; the evidence comes from hardware).
- `make check` (wiki lint, the no-serials test, gen-check).
- Commit only the files named above, and only when asked. No push without asking.
