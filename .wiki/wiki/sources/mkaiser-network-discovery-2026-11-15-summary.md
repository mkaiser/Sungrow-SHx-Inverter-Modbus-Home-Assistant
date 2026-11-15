---
type: source
title: mkaiser-network-discovery-2026-11-15.md
source_path: raw/mkaiser-network-discovery-2026-11-15.md
ingested: '2026-11-15'
created: '2026-11-15'
tags:
  - discovery
  - mdns
  - dhcp
  - rak-module
  - mkaiser
---

# Discovery at the maintainer's house, 2026-11-15

Read through the production Home Assistant on 0.1.0a40 and from the dev container. Source:
`raw/mkaiser-network-discovery-2026-11-15.md`.

- **Zeroconf heard nothing from Sungrow** among 22 services: the house has no WiNet-S, and the
  inverter's own LAN port announces nothing.
- **A [RAK WiFi module](../entities/device-rak-wifi-module.md)** sits on the network: HTTP 401
  from `rak_mini_server` (Basic realm "RAK LOGIN"), DHCP hostname `rakmodule-` plus six hex
  digits, MAC prefix `AC:1F:09` (RAKwireless in the IEEE registry). The inverter names no
  communication module over Modbus.
- **`AC:19:9F` is Sungrow's one IEEE prefix**, the one peter_sm's inverter port carries
  ([twentieth reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18-summary.md)).
  The maintainer's inverter did not appear in Home Assistant's DHCP list.
- **The network search missed the inverter** twice while the YAML package polled it through the
  same Home Assistant, though it accepted every connect from the container; the manual step
  identified it at once. [Open](../queries/why-did-the-search-miss-mkaisers-inverter.md).
