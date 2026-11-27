# T093: EMHASS beside evcc, for the battery

Split off from [T060](T060-evcc-integration.md) by the maintainer, 2026-11-25. Researched
2026-11-17; nothing is built or measured. The question: is EMHASS instead of, or beside,
evcc better for a Sungrow house?

## Findings

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
battery.** evcc ([T060](T060-evcc-integration.md), `doc/evcc.md`) stays the core: real-time surplus charging, vehicle and SoC
handling, plans, a UI. Add EMHASS only if the site has a **dynamic tariff** where
arbitrage pays. Then follow EMHASS's documented split:
- **EMHASS owns the battery**: drop evcc's `modeNormal/Hold/Charge` scripts and keep
  evcc's battery meter read-only.
- **evcc owns the car**: EMHASS sets the loadpoint mode (`now`/`off`/`smart`; check the names against the evcc version in use) through
  evcc's API or the ha-evcc entities.
- **Never let both control the battery.** This is the same single-writer rule the integration enforces.
- One HA forecast feeds both (EMHASS can take `pv_power_forecast` at runtime from HA).
- Also note: a managed wallbox's inverter already does PV-surplus charging itself (EV
  charger mode *PV surplus*). evcc's added value there is SoC targets, plans and the
  UI, not the surplus regulation.

## Steps

1. Find a house with a dynamic tariff whose owner wants this.
2. Write the automations that turn `p_batt_forecast` into `ems_mode` and the forced
   charge/discharge power, with the result checks the scripts in `doc/evcc.md` have, and
   a return to self consumption when EMHASS stops publishing.
3. Try them against the simulator, then at that house.
4. Write an owner's guide, linked from `doc/evcc.md`, saying who owns the battery.

## Status log

- 2026-11-25: split from T060. Not started.
