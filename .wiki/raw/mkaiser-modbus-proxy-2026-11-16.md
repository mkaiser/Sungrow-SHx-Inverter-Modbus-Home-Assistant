# A Modbus proxy at the maintainer's house, 2026-11-16

Taken by the maintainer's session from the dev container (Docker Desktop on
Windows, on the container bridge, so not on the house's segment), with a
development Home Assistant 2026.11 of its own and the integration from the
working tree at 0.1.0a42 plus two uncommitted changes. The house's /24 is
called "the home network"; no address here. Read only, but for the config
flow and the two moves the maintainer asked for. Nothing was written to the
inverter.

The house: the SH10RT on P020 (`anon-37323352958`), its own LAN port, and the
production Home Assistant, which polls the inverter **through a modbus-proxy
running on its own machine**. The proxy was polling throughout; nothing about
the house was changed for this. Night, the inverter in low-SoC Standby.

## What the search found

*Add integration → Search my network*, the home network's /24:

| | |
| --- | --- |
| addresses checked | 1270 |
| answered the port scan | 3 |
| identified as a Sungrow | 2 |

The two are **one inverter at two addresses**: the inverter's own LAN port,
and the proxy on the production Home Assistant's machine, which answers every
identity read with the inverter's own answers -- one serial, one model.

**Both cards carried the same route note**, "the inverter's own LAN port".
The flow's own probe of register 6100
**answered through the proxy**, so the flow read the proxy's path as a cable.

**Neither card was named a proxy.** The two signals that would have named one
both said nothing, each for its own reason:

- Home Assistant's own addresses (`_async_local_addresses`) hold only the dev
  container's, because the proxy runs beside the *production* Home Assistant,
  on another machine. This is not the container's doing: a proxy is named only
  where the searching Home Assistant is itself the proxy's host.
- The MAC vendor prefix was **none**: an ARP entry exists only on the same
  segment, and the container is behind a bridge.

The offer order then fell through to the host string, which sorts `.125`
before `.35` and put the proxy first -- the better address, for the wrong
reason. Fixed since in `custom_components/sungrow_modbus/config_flow_schemas.py`
(`_address_order`, `tests/test_config_flow_proxy.py`).

## What the entry read, by address

The entry was created through the proxy, then moved to the inverter's own LAN
port and back, with *Reconfigure*. Each move kept the entry, its entities and
its history (`connection_moved`).

| Entry points at | `sensor.connection` |
| --- | --- |
| the proxy, at setup | unknown |
| the proxy, after a reload | unknown |
| the proxy, after a cold boot | unknown |
| **the inverter's own LAN port** | **direct**, within a minute |
| the proxy again | unknown |

`unknown` is the integration's third answer: 6100 neither answered nor
refused (`custom_components/sungrow_modbus/route.py`, measured once at setup in
`custom_components/sungrow_modbus/__init__.py`). So **the entry's 6100 probe
does not get an answer through this proxy, while the config flow's probe of
the same address did.** The difference between the two is the session: the
flow opens a short connection of its own, the entry reads through Home
Assistant's shared `modbus` connection.

Not settled by this: whether the proxy itself does not carry 6100 for the
entry's session, or whether the read lost its turn to the production Home
Assistant's own polling through the same proxy. One house, one proxy, one
evening.

## What the entry carried

Set up through the proxy, on an ordinary entry (no diagnostics-only mode):
**195 entities on one device page** -- 112 primary, 58 diagnostic (17 of them
the diagnosis and capability test), 25 config -- with live readings, the mode
select offering all three modes at *Read only*, and *Diagnosis: start*
unavailable there. 15 entities read unknown or unavailable, each explained:
the buttons until pressed, the diagnosis counters until a run, the battery and
communication-module firmware versions (no battery, no module in the path),
PV power limitation at night, and `sensor.connection` above. No errors in the
log.

## The move dialog

Moving off the proxy and back onto it, the dialog's proxy sentence was
**empty both ways** -- the same blind spot, in the place it was written to
speak.
