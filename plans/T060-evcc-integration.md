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
Modbus client, no races. While a capability test runs, our controls refuse: for the charger
evcc gets the error. For the **battery scripts it does not** (see *Battery*).
HA answers success for a call to a missing or `unavailable` entity
and only logs it, so an entity id has to be checked when configuring.
- Auth: in the evcc UI, *Home Assistant* integration → the HA login tab
  issues a token, and evcc renews it itself. If evcc runs as the HA app
  (`evcc-io/hassio-addon`, a community add-on), pick `http://supervisor/core` and
  the login step is skipped (docs.evcc.io/en/smarthome/home-assistant).
- The HACS integration `marq24/ha-evcc` brings evcc's state back into HA. This is optional.

**Meters → our entities (signs already match evcc: import +, battery discharge +).**
- grid: `power: sensor.meter_active_power` (>0 buy). Energy:
  `total_imported_energy` / `total_exported_energy` (`returnEnergy`).
- pv: `power: sensor.total_dc_power` (device-scoped: `total_pv_input_power`), energy: the total PV generation sensor.
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
  - `status`: a template sensor over *Car connected* and *Charging*, because the status
    code can read *idle* with a car plugged in
  - `power`, `energy`, `currentL1-3`, `voltageL1-3`: the wallbox sensors
  - Precondition: `select.…ev_charger_mode` is set **once** to user-defined and
    `switch.…ev_charger_grid_purchase` is set as wanted. evcc must never
    change the mode: a mode change ends the session (wiki
    `gerd-wallbox-night-2026-11-16-summary.md`).
  - **No `phaseswitch`**: a managed wallbox's phases are the inverter's to
    choose. evcc is configured `phases: 3`, with 6 A × 3 = 4.14 kW the minimum charge.
- For a standalone wallbox (its own entry, TLS 516), the entities are read-only.
  There is no control path today, so the doc says so and points at Todo § Wallbox 3.3.
- The HA controls passed with a car charging (wiki `gerd-wallbox-2026-11-24-summary.md`); evcc driving
  them is unwatched, so the doc is marked **experimental**. Plug&Play (21298) must be off.

**Battery → HA scripts.** The `homeassistant` meter has `modeNormal`,
`modeHold`, `modeCharge` (`modeNormal` is required once any other is set). The guide
ships three scripts over our entities:
- normal: `select.ems_mode` → `self_consumption`, and
  `select.battery_forced_charge_discharge` → `stop`
- hold: `ems_mode` → `self_consumption`, `stop`, and the maximum discharging power →
  10 W, as evcc's own template does: the battery may still charge from PV. Normal and
  charge put the limit back
- charge: `ems_mode` → `forced`, forced → `charge`,
  `number.battery_forced_charge_discharge_power` → a set value
- **A failed script is invisible to evcc.** evcc calls `script.turn_on`, which HA
  starts without waiting for it (`wait=False`), so a refused write inside it still
  answers 200. evcc then records the mode as applied and does not re-apply it until
  the mode changes. So each script has to check its result (wait for the select to
  read the wanted state, retry, then notify). The charge script sets the power **before** it
  starts the forced charge.
- Optional `modeDischarge` is left out: evcc does not need it, and it exports
  the battery.
- Verify with `evcc meter verifybatterymodes` (it cycles the modes and checks the
  battery power).
- Warning in the doc: a forced mode stays set if evcc dies. Add an HA automation
  that returns to normal when evcc goes unavailable: triggered by a REST
  sensor on evcc's `/api/state` (evcc has no health endpoint).

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

## Left to do

1. The meters are watched (the maintainer's); watch the charger's 33540/33545 with a car, at gerd's.
2. `evcc meter verifybatterymodes` on the maintainer's SH10RT.
3. Load the charger, vehicle and battery-mode YAML in evcc: only the meters and the forecast have been.
4. Then drop the *Experimental* box in `doc/evcc.md`.

## Status log

- 2026-11-26, 19:00 CET: `doc/evcc.md` has a section *A wallbox no inverter manages*: evcc's own `sungrow` charger
  over RS485 or a gateway (evcc has no TLS, so not port 516), phases set to automatic, the wallbox entry kept for
  reading with its capability test off while evcc drives. From a colleague's report of a standalone AC22E-01 switching
  1p/3p and evcc's source at `49b5a8d10` ([the source](../.wiki/wiki/sources/cross-reference-evcc-2026-11-26-summary.md),
  committed). Not watched here. Uncommitted with the rest of `doc/evcc.md`.

- 2026-11-25, 21:00 CET: normal and hold (no charge mode) with their watchdog are installed at the maintainer's; normal ran
  as a no-op, hold has not run, and evcc's discharge control is off. evcc switched hot water and heating to Komfort.
  Found: no `mode:` in a loadpoint's YAML (it resets the owner's choice at a restart); hold triggers for any loadpoint
  running in now, a heat pump included. The capacity is a fixed number in evcc (T098). `doc/evcc.md` has not got these yet.
- 2026-11-25, 16:00 CET: at the maintainer's, evcc also has the WARP2 and the heat pump (hot water and heating as
  Komfort/Eco switches), all in mode off. Hot water switched to Komfort and back from Home Assistant; evcc itself
  has not switched anything on yet. Battery scripts not installed.
- 2026-11-25, 15:30 CET: evcc 0.319.1 runs as the Home Assistant app at the maintainer's, meter-only
  (the integration's own ids through `http://supervisor/core`, no login step): grid, PV, battery, SoC
  and its limits read, with signs as documented, and the solar forecast loads. Nothing is written to the inverter.
  Scripts, watchdog and wallbox (a WARP2) are later. Uncommitted: `doc/evcc.md`, T060, T093, README,
  and this work's parts of `Todo.md`, the wiki index and `log.md`, which another session also edits.
- 2026-11-25: `doc/evcc.md` written. MQTT dropped (maintainer); EMHASS moved to
  [T093](T093-emhass.md) (maintainer). The device-scoped inverter ids were read off the
  simulator; the wallbox ids come from the entity names, as the simulator serves no
  wallbox. The scripts passed a throwaway harness test (a failed write, a stuck inverter,
  return to normal). evcc itself was not run, and the battery scripts were not run
  against the simulator.
