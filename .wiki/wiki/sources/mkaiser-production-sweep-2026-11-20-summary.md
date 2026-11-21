---
type: source
title: mkaiser-production-sweep-2026-11-20.md
source_path: raw/mkaiser-production-sweep-2026-11-20.md
ingested: '2026-11-21'
created: '2026-11-21'
tags:
  - mkaiser
  - discovery
  - modbus-proxy
  - config-flow
---

# The search from the maintainer's production Home Assistant, proxy running, 2026-11-20

[mkaiser](../entities/installation-mkaiser.md)'s production Home Assistant, after reinstalling the
integration (0.1.0a45 or a preview build after it), ran the setup search on the house's /24 while the
YAML package polled the SH10RT through the modbus-proxy add-on on the same machine -- the conditions
under which two sweeps on 0.1.0a40 had missed the inverter. Source: the maintainer's screenshot of
*Devices found*, transcribed in `raw/mkaiser-production-sweep-2026-11-20.md` (the image carries a
serial and is not tracked).

| Fact | Evidence |
| --- | --- |
| **The search found the inverter's own LAN port from the production machine, with the proxy holding a session to it** | row 2 of the dialog |
| It found the proxy too, called it a Modbus proxy (Home Assistant's own address) and counted both as one inverter by serial | row 1, the summary "1 inverter, 2 addresses" |
| Both addresses read 6100 as answered (route: the inverter's own LAN port) | both rows' route note |
| The sweep code is the one that missed on 2026-11-15: `discovery.py` unchanged from a40 to a45 | `git diff` of the release commits |
| The summary sentence was in the system language (German), the rest of the step in English | the dialog; `texts.py` takes `hass.config.language` |

## What it means

- The 2026-11-15 miss is **not reproduced** by the same sweep from the same machine beside the same
  proxy, after contention was ruled out from the dev container
  ([the query](../queries/why-did-the-search-miss-mkaisers-inverter.md)). Nothing in the search needs
  to change for it.
- Separately, a flow sentence built in the backend follows the system language, not the viewer's:
  a house whose profile language differs from the system's gets a mixed-language dialog.
