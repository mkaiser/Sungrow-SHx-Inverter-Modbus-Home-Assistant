# Discovery at the maintainer's house, 2026-11-15

Taken by the maintainer's session from the dev container and through the
production Home Assistant (2026.11.1, integration 0.1.0a40, Home Assistant OS
on the house LAN), read only but for the config flow the maintainer asked for.
No address here; the house's /24 is called "the home network".

## What Home Assistant's zeroconf hears

`zeroconf/subscribe_discovery` listed 22 services (printers, a receiver, TVs,
ESPHome nodes, Matter, a NAS, a wallbox of another make). **Nothing from
Sungrow**: no `WiNet-WebServer`, no `SUNGROW*` instance. Unicast mDNS questions
from the container (PTR `_http._tcp.local`, from a random port and from 5353)
to the inverter's address and to the RAK module's went unanswered.

## The RAK WiFi module

A second device beside the inverter answers TCP 502 and 80:

- **HTTP on 80**: `401 Unauthorized`, `Server: rak_mini_server`,
  `WWW-Authenticate: Basic realm="RAK LOGIN"`. No credentials were tried.
- **Home Assistant's DHCP watcher** (`dhcp/subscribe_discovery`) lists it with
  hostname `rakmodule-` and six hex digits (the MAC's last three octets), MAC
  vendor prefix `AC:1F:09`, which the IEEE registry assigns to "shenzhen
  RAKwireless technology Co.,Ltd" (standards-oui.ieee.org/oui/oui.txt, read
  2026-11-15).
- On 502 it accepts a connection; the integration's identification got no
  Sungrow answer from it (below). An earlier sweep found it echoing what it is
  sent (`sungrow_modbus.discovery`'s docstring).

The inverter (SH10RT, P020, its own LAN port) names no communication module in
any of its diagnoses, so nothing over Modbus ties the module to it.

## Sungrow's vendor prefix

The IEEE registry lists one prefix for "SUNGROW POWER SUPPLY CO.,LTD.":
`AC:19:9F` (same file, same day). peter_sm's twentieth reading records it as
the MAC vendor prefix of that inverter's own LAN port. The maintainer's inverter
is not in Home Assistant's DHCP list nor in the router integration's six
tracked devices (probably a fixed address), so its MAC was not read.

## The network search missed the inverter

The config flow's search (*Add integration → diagnosis → search*), twice, of
the home network: on port 502 only the RAK module answered the connect; 503,
504, 505 and 516 nothing; identification found 0 of 1 candidates Sungrow
(debug log, `custom_components.sungrow_modbus.config_flow`). The inverter was
being polled by the YAML package through the same Home Assistant at the time.
From the dev container the inverter accepted six of six TCP connects in 4-10 ms
right after. Entering its address in the manual step identified it at once
(SH10RT, 6100 answered: its own LAN port).
