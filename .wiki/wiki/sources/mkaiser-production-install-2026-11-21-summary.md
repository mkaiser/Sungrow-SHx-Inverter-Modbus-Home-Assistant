---
type: source
title: mkaiser-production-install-2026-11-21.md
source_path: raw/mkaiser-production-install-2026-11-21.md
ingested: '2026-11-21'
created: '2026-11-21'
tags:
  - mkaiser
  - modbus-proxy
  - import-limit
  - capability-test
  - home-assistant
---

# The maintainer's production Home Assistant, 2026-11-21: the integration beside the YAML package

[mkaiser](../entities/installation-mkaiser.md)'s SH10RT on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), the integration (0.1.0a46, from the preview
channel) set up on the production Home Assistant **while the YAML package keeps running**, both reading
through one modbus-proxy add-on in front of the inverter's own LAN port. Then two extended tests and a
watched import-limit run in daylight. Source: `raw/mkaiser-production-install-2026-11-21.md`.

| Fact | Evidence |
| --- | --- |
| **The integration and the YAML package poll side by side through one proxy** without either losing reads: the package's entities kept updating every few seconds through both extended tests and the restart | the package's entity timestamps; no timeouts logged |
| With the package running, the setup dialog counted 150 of its ids held and offered only *new* ids | the setup dialog |
| A re-added entry got back its device's area and the diagnosis entities' last states from an earlier, deleted entry | the device page |
| First extended test: 21/54 passed, 0 failed, every readback matched; restart in daylight ~3 min | the entry's diagnosis |
| **Site import limit with PV below the load** (PV ~1.05 kW, load ~2.09 kW): cap 1830 W, import 2439 -> 1876.5 -> 2323 W, ratio 1.03 | the capability test's effect |
| 32998 refused 0 and 5001 (0x04), took 5000; `export_scale` x10, as before | the capability test's conditions |
| **The engine's import-limit check cannot run with PV above the load**: its fixed 1250 W forced charge drew only 582 W from the grid, and it declined | the second run's note |
| **Site import limit with PV above the load, by hand** (forced charge 4500 W, PV 2.6-3.6 kW, load 2.0-2.2 kW): a 2190 W cap took median import from 4386 W to 1933 W, the charge cut to 2.4-3.0 kW; single samples overshot to ~4 kW for ~10 s where PV dipped; no clean after-bracket under passing clouds | the watched run's samples |
| **Through the proxy the entry's diagnosis read 6100 as answered**, while the entry's *Connection* sensor stayed unknown | the diagnostics, the sensor |
| *Inverter self consumption (estimated)* while working, 5.5 h: median 248 W, hourly medians 143-365 W (highest at ~8.4 kW PV), 10th-90th percentile 104-416 W, single readings down to -178 W | the recorder's series of the entity |

## What it means

- Running both is safe behind a proxy; the remaining cost of doing so is a doubled Energy dashboard if
  both sets of sensors are put into it, and two writers if both are used to control.
- The cap counting PV now has a run with PV above the load, which the earlier ones lacked
  ([register 32998](../entities/register-32998.md)); a steady-light bracket is still wanted.
- The open question about proxies and 6100 narrows from "the proxy" to "the route probe"
  ([the query](../queries/does-a-modbus-proxy-carry-6100.md)).
