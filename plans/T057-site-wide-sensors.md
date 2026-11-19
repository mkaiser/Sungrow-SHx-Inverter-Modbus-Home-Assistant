# T057 - Site-wide sensors for several inverters

Each inverter is its own config entry, so nothing adds them up, and the
answer today is documented helpers: `doc/energy_dashboard.md` (*Several
inverters*) says what to sum, what to take from the master only and what
never to sum.

Open: entities of the integration's own, **only if users ask**. They need
something above the one-entry-per-inverter rule (`doc/architecture.md`): the
entry that is the cluster's master owns a "Site" device, found by the roles
the diagnosis already measures (*measured* or *inferred*), and the sensors
are unavailable, not 0, when a member is. `total_site_pv_power` already
exists for the inverter that has a second one on its supply, so the Site
wording has a precedent.

Names, in the existing convention (sentence case, the device name added by
Home Assistant, the ids in English). **Agreed by the maintainer
2026-11-12**; they go into `scripts/generate/tables/naming.py` when the
entities are built:

| Entity | Name | Id (device "Site") |
| --- | --- | --- |
| Summed PV power | Site PV power | `sensor.site_pv_power` |
| Summed AC output | Site AC output power | `sensor.site_ac_output_power` |
| Summed daily PV energy | Site daily PV generation | `sensor.site_daily_pv_generation` |
| Summed total PV energy | Site total PV generation | `sensor.site_total_pv_generation` |
| Summed battery charge / discharge power | Site battery power | `sensor.site_battery_power` |
| The meter's own values, taken from the master | Grid power, as on the master | no new entity |
| Inverters in the sum | Site inverters counted | `sensor.site_inverters_counted` (diagnostic) |

The device: "Sungrow site" (or the system name the owner gives in setup),
with each inverter keeping its own "SH10RT" or name. German: "Anlage" for
site ("Anlage PV-Leistung", "Anlage Tagesertrag PV"). A user who wants other
words renames the helper, not the integration.
