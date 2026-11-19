# T008 - The search missed the maintainer's inverter

**The search missed the maintainer's inverter** (2026-11-15, 0.1.0a40,
production Home Assistant): two sweeps of the home /24 found port 502
open only on the old RAK WiFi module (which accepts and echoes, not
Modbus) and never on the SH10RT, which the YAML package was polling
through the same Home Assistant; from the dev container the SH10RT
accepted six of six connects in under 10 ms. The manual step identified it at once. Not retried slowly
(that happens only when nothing answers). A sweep from the dev container,
which holds no session, found and identified it in one round, so the port
is not deaf to a sweep: what it does under a sweep from the address
already polling it was the question. **Answered 2026-11-17, and the
hypothesis is wrong**: with the dev container's own Home Assistant polling
the inverter without a break, 12 of 12 connects from that same container
were accepted in 7.6-21.8 ms and both full /24 sweeps found it, costing the
poller no lost connection (wiki: why did the search miss the maintainer's
inverter, the run). So contention does not explain the miss, and nothing
needs to count an already-connected host as a candidate.

**What is left is one measurement**: the production Home Assistant reaches
this inverter through a **modbus-proxy on its own machine**, so the session
held from that address is the proxy's, not Home Assistant's. Run the same
sweep from the production machine with the proxy running. If it finds the
inverter there too, the miss was never about sessions and the sweep's own
behaviour on that host is what to look at.
