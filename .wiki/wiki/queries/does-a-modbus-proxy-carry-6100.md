---
type: query
title: "Does a Modbus proxy carry register 6100?"
tags: [proxy, transport, register-6100, mkaiser, open]
created: '2026-11-16'
query: "Through a modbus-proxy, does input 6100 answer for every session, or only for a short one of the reader's own?"
results_count: 6
---

# Does a Modbus proxy carry register 6100?

**Open, and narrowed: it is the address, not proxies.** Two houses' proxies carry 6100 for every
reader; one address at a third carries it for a short probe and not for a config entry.

**For it.** An anonymous SH10RT-V112 read through a modbus-proxy add-on
answered [register 6100](../entities/register-6100.md), so transport
detection saw the cable behind it
([the reading](../sources/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-summary.md)).
**Both of [swo14](../entities/installation-swo14.md)'s cluster inverters** answer it through a
proxy as well, each on a port of its own, and on the entry's ordinary polling connection rather
than a probe of its own -- which is the case mkaiser's entry could not get an answer for
([the host](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-summary.md),
[the slave](../sources/sh10rt-20-3p-sw14-anon-25617150722-battery-none-direct-lan-summary.md)).
Both answered again a week later, with evcc and the YAML package polling beside
([host](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3-summary.md), [slave](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-summary.md)).
At [mkaiser](../entities/installation-mkaiser.md) the config flow's own probe
of the proxy's address answered too, which is why the search labelled the
proxy "the inverter's own LAN port"
([the proxy reading](../sources/mkaiser-modbus-proxy-2026-11-16-summary.md)).

**Against it.** At the same house, in the same evening, a config entry
pointed at that proxy read 6100 as **neither answered nor refused** three
times -- at setup, after a reload and after a cold boot -- and its
*Connection* sensor stayed unknown. Moved to the inverter's own LAN port the
same entry read **direct** within a minute, and moved back it was unknown
again ([the proxy reading](../sources/mkaiser-modbus-proxy-2026-11-16-summary.md)).

**On 2026-11-21 the same proxy carried it to an entry.** An entry on the production
Home Assistant itself, pointed at the add-on's internal hostname with the YAML package
still polling through it, read 6100 as answered in its diagnosis (`winet_restricted_block_6100`,
and the capability probe present) -- yet its *Connection* sensor stayed unknown
([the production install](../sources/mkaiser-production-install-2026-11-21-summary.md)).
So the proxy does carry the block to an entry's connection, with another poller busy;
what does not get an answer is the entry's route probe. That weakens *the turn* below and
points at when and how the route probe reads.

So the address answers 6100 for one reader and not for another in the same
hour, while another house's proxy answers it for every reader. Two
explanations, neither measured:

- **The session.** The flow opens a short connection of its own; the entry
  reads through Home Assistant's shared `modbus` connection, which is also
  polling everything else. The proxy may carry 6100 on a fresh connection and
  not on a busy one.
- **The turn.** The production Home Assistant polls the inverter through the
  same proxy throughout, so the entry's probe may simply have lost its turn
  ([contention](../concepts/contention.md)). A failed read is not a refusal,
  and this is what that rule is for
  ([a failed read is not a refusal](../concepts/failed-read-is-not-refusal.md)).

## What the integration does meanwhile

**It keeps the entry's own answer, and shows unknown.** Decided 2026-11-16,
against two alternatives:

- **Carrying the flow's measurement into the entry** would print "the
  inverter's own LAN port" for a path this entry has never read. It is a
  measurement, so it is not a guess -- but it is one taken by another session,
  and storing it makes the entry state as fact what it could not confirm. The
  same objection as reading a capability off a datasheet instead of the wire.
- **Retrying the probe** would be the usual answer to a read that said
  nothing, and the evidence is against it here: three attempts, in three
  sessions over one evening, each got nothing from the proxy, and the same
  build read `direct` at the inverter's own LAN port in one. More reads of a
  register that did not answer three times buy a little load and no
  information.

Nothing is gated on the route: it names the path on the device page and feeds
the *Connection* sensor (`custom_components/sungrow_modbus/route.py`,
`custom_components/sungrow_modbus/sensor.py`). So unknown costs a line of
description, not a capability, and it is the true answer: this entry asked and
was not told.

What answers it: at the same house, with the production Home Assistant's
polling stopped, set an entry up through the proxy and read its *Connection*.
Direct there, with nothing else polling, is the turn; unknown is the session.
Then the same with the proxy in front of a dongle, where 6100 should be
refused rather than silent, which separates "the proxy does not carry the
block" from "the read did not get through".
