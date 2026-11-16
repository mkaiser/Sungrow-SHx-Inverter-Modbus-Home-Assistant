---
type: entity
title: RAK WiFi module
tags: [rak-module, dongle, discovery]
created: '2026-11-15'
---

# RAK WiFi module

An older WiFi stick built on a RAKwireless module, found beside the maintainer's inverter
([mkaiser](installation-mkaiser.md); [the reading](../sources/mkaiser-network-discovery-2026-11-15-summary.md)).

- **Not a Modbus device**: it accepts a connection on port 502, and the integration's
  identification gets no Sungrow answer from it.
- **A web page on port 80**, behind HTTP Basic authentication (realm "RAK LOGIN", server
  `rak_mini_server`).
- **Named to the router** as `rakmodule-` plus the MAC's last three octets, with RAKwireless's
  vendor prefix `AC:1F:09`. **It announces nothing over mDNS**: it was not among the 44 service
  instances a 15-second browse heard from a machine on its own segment
  ([the browse](../sources/mkaiser-mdns-2026-11-16-summary.md)).
- **The inverter does not report it**: the maintainer's P020 names no communication module, so
  which inverter carries one only its owner can say.

The integration matches its DHCP hostname and asks the owner which inverter it belongs to; the
linked module then shows under that inverter with a link to its page
(`custom_components/sungrow_modbus/wifi_module.py`). Unknown: which inverters shipped with it,
whether it forwards Modbus to the inverter at all, and whether the `rakmodule-` name is used by
other makers' sticks.
