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
  vendor prefix `AC:1F:09`.
- **It advertises over mDNS**, under a service type of its own: instance
  `rak475_service_` plus the same six hex digits, type `_rak47x._tcp`, port 5000, with `VER`
  `1.9.0.10.12-2.13.4`, a `TEST` field reading `Let's go`, and a `MAC` field giving the whole
  address in clear ([the firewall runs](../sources/mkaiser-mdns-firewall-2026-11-16-summary.md)).
  It is **intermittent**: heard in one browse and missed in two others the same afternoon, all
  three of which counted 44 instances
  ([an mDNS browse is a floor](../concepts/mdns-browse-is-a-floor.md)). Two earlier readings
  recorded that it announced nothing ([2026-11-15](../sources/mkaiser-network-discovery-2026-11-15-summary.md),
  [the first browse](../sources/mkaiser-mdns-2026-11-16-summary.md)); both were browses that
  missed it, not devices that were silent.
- **The inverter does not report it**: the maintainer's P020 names no communication module, so
  which inverter carries one only its owner can say.

The integration matches its DHCP hostname and asks the owner which inverter it belongs to; the
linked module then shows under that inverter with a link to its page
(`custom_components/sungrow_modbus/wifi_module.py`). Unknown: which inverters shipped with it,
whether it forwards Modbus to the inverter at all, and whether the `rakmodule-` name is used by
other makers' sticks.
