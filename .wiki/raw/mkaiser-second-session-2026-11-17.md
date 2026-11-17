# The maintainer's SH10RT: a sweep from the address already polling it, 2026-11-17

The question [why did the search miss the maintainer's inverter](../wiki/queries/why-did-the-search-miss-mkaisers-inverter.md)
left one explanation unmeasured: that the inverter's own LAN port refuses or stalls a second TCP
connection from an address that already holds one. This is that measurement.

Run at 06:35 local from the repository's dev container, on `anon-37323352958`
(SAPPHIRE-H_B001.V000.P020), against the inverter's own LAN port. The container's **own** Home
Assistant (`config-real`, this checkout's integration) had been polling the inverter without a
break since 21:13 the previous evening -- confirmed from its log, a coordinator fetch every few
seconds through the whole sweep, the last one 7 seconds before it. So every connect below came
from an address that already held a live Modbus session to the same device.

The script is `discovery.async_port_open` and `discovery.async_sweep`, the integration's own, at
their shipped settings (concurrency 64, per-address timeout 1.0 s).

## What happened

| Step | Result |
| --- | --- |
| 6 sequential connects before the sweep | 6/6 accepted, 7.6 to 21.8 ms |
| full /24 sweep, port 502 | 4.0 s, three addresses with 502 open, **the inverter among them** |
| 6 sequential connects after the sweep | 6/6 accepted, 9.5 to 11.4 ms |
| a second full /24 sweep | 4.0 s, the same three, the inverter again |

Twelve of twelve connects accepted, both sweeps found it, and the polling Home Assistant kept
fetching throughout -- no lost connection in its log attributable to the sweeps.

## What it settles

**The inverter's own LAN port does not refuse a second TCP session from an address that already
holds one.** The explanation the query page carried is wrong, at least for a poller connected
directly to the inverter.

What it does not settle: the production Home Assistant polls this inverter **through a
modbus-proxy on its own machine**, not directly, so the session from that address is the proxy's.
This run used a directly polling Home Assistant instead. If the miss is about the proxy's machine
specifically, this does not touch it.

## Also seen

Three addresses on the segment answer on port 502, where earlier readings from this container
named two (the inverter and the proxy). The third was not identified; nothing was read from it
beyond the open port.
