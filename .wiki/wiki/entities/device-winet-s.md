---
type: entity
title: WiNet-S communication module
tags: [dongle, winet-s, transport]
created: '2026-10-29'
---

# WiNet-S communication module

Sungrow's WiFi/Ethernet dongle. It plugs into the inverter, forwards Modbus
TCP on port 502, and serves the same Modbus inside TLS on **port 516**. Much of
what a diagnosis sees through it is the dongle's doing, not the inverter's.

## What it changes

| Behaviour | Consequence | Page |
| --- | --- | --- |
| Refuses input **6100** (0x02) | the measurement of transport | [register 6100](register-6100.md) |
| Refuses inputs **6196-6198**, the start of the daily PV yields (V1.1.16 6196~6226), where every cable reading answers | the history registers (daily, monthly, yearly yields from 6196 on) are cable-only | this page, below |
| Does not forward inputs **2612** and **2628** (sub-controller and battery firmware) | capability gating by transport, not a `layout.ISOLATE` case | [transport detection](../concepts/transport-detection.md) |
| Answers **an empty string** where the inverter refuses (13249, 13264, 13279) | "the block answered" is not evidence | [zero means absent](../concepts/zero-means-absent.md) |
| Answers **0** where the inverter answers 0xFFFF | invents MPPT3, MPPT4, a second meter channel | [zero means absent](../concepts/zero-means-absent.md) |
| Re-encodes **13000** (cable 0x0040 → 0x0000, 0x0080 → 0x8100) | duplicate running-state codes | [register 13000](register-13000.md) |
| Forwards a write and **reads it back stale**, indefinitely | legs A and B of the capability test are not evidence; only leg C survives | [capability test](../concepts/capability-test.md) |
| Under a polling Home Assistant, **stops answering mid-run**, and a write that timed out can still land; it also reports a stale sample after timeouts and a sample of all zeros ([gerd](installation-gerd.md)) | a restore through a dongle retries without deadline and reads the result over the other path where there is one | [the run](../sources/gerd-import-limit-2026-11-08-summary.md) |
| At [gerd](installation-gerd.md) on P022 it read the schedule's switch **33208** back current, but its window words **33210-33214** as 0 throughout, though the window took effect | the same register block, two behaviours; the cable confirmed the restore | [the schedule run](../sources/gerd-import-limit-schedule-2026-11-08-summary.md) |
| Not always: at [bar12](installation-bar12.md) on P023, writes of **13017** and **32998** through the dongle read back current at once, and the cable agreed | one dongle, one night; the rule above stands for the capability test | [forced startup](../sources/bar12-forced-startup-2026-11-07-summary.md), [import limit](../sources/bar12-import-limit-2026-11-07-summary.md) |
| Answers **0x04** to reads it answers alone, while other clients poll it ([firetribe](installation-firetribe.md), and reproduced at [gerd](installation-gerd.md)) | 0x04 through a dongle settles nothing, like 0x06 | [busy WiNet-S](../queries/does-a-busy-winet-s-refuse-with-0x04.md) |
| Refuses the SBR's cells and modules blocks | fewer pack fields | [SBR battery](device-sbr-battery.md) |
| Faults when the wallbox behind it is polled faster than every 10 s, by an ioBroker user's account ([shcshc76](../sources/cross-reference-shcshc76-summary.md)); not measured here | the wallbox's poll stays at 10 s or slower | [wallbox](device-wallbox.md) |
| Carries a [wallbox](device-wallbox.md) at unit **3** | moving to a cable loses it unless `wallbox_host` is set | [identify by what answers](../concepts/identify-by-what-answers.md) |

A dongle forwards about 1020 of 1510 dumped addresses, where a cable forwards
1461.

## What cannot be learned through it

- **WiFi or Ethernet.** Not determinable over Modbus. `user_inputs.transport`
  in a diagnosis is the only source.
- **Round-trip time** times the path from the reader, usually a VPN. It says
  nothing about the inverter and is not recorded.

## Port 516

Real Modbus behind TLS 1.2. It refuses the same registers as 502, and it
exhausts under rapid reconnects the same way. The certificate is
Sungrow-signed (issuer `OT.SUNGROW`, CN `sun`, serial number 1, RSA-2048, valid
2024-10-24 to 2054-10-17) and byte-identical to the wallbox's at the same house,
SHA-256 `84505e46778f2611df26ed1ad8a4e872945f7eb33e050e617c96a73add005b5b`
([gerd's certificate](../sources/gerd-tls-certificate-2026-11-06-summary.md)), and the same
at another house ([bar12's](../sources/bar12-tls-certificate-2026-11-06-summary.md)): one
certificate built into the firmware, its private key on every unit, so this TLS
authenticates nothing and verifying it gains nothing.
`sungrow_diagnosis.py` reports a WiNet-S's 516 without reading it, after asking it for a wallbox at unit 248 and a Logger at unit 247.

## mDNS and its web page

At [gerd](installation-gerd.md) it answers mDNS with one service, `_http._tcp`, instance
`WiNet-WebServer`, on a host named `SUNGROW` and its serial. Its TXT record lists **every device
behind it with its serial**: the inverter (unit, device type code 4999, model), the battery
(unit through the dongle and over the cable, model) and the dongle itself
([the reading](../sources/gerd-mdns-2026-11-11-summary.md)). Anyone on the LAN can read them.
Whether a multicast browse sees the same, and on other firmware, is
[open](../queries/does-a-winet-s-advertise-over-mdns.md).

Its web page is **HTTPS on port 443** under a self-signed Sungrow certificate; port 80, which
its own mDNS record names, refuses ([gerd](../sources/gerd-mdns-2026-11-11-summary.md); 443
also answers at [bar12](../sources/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan-summary.md)).
The device page's *Visit* link opens `https://` and the entry's host
(`custom_components/sungrow_modbus/route.py`).

## The history registers

V1.1.16's inputs from 6196 hold PV, direct-consumption and export history:
daily, monthly and yearly yields. Inputs 6196-6198 answer on every cable reading in the corpus, on P020, P022, P023
and firmware the document did not report, and are refused on every dongle
reading, SH-RT, SH-T and SH-RS alike, for example
[gerd on the cable](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-summary.md)
against [gerd through the dongle](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-summary.md).
V1.1.16 says the same of the whole block, registers 6100-6826: "WiNet-S/S2
and Logger is not supported", "Applicable types: SH5.0-10.0RT". That is why
the YAML package dropped its monthly and yearly sensors: most of its users
read through a dongle. From 0.1.0a23 the diagnosis's dump reads the whole block
(`src/sungrow_modbus/dump.py`). Over the cable at
[peter-sm](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-3-summary.md)
every address of it answered, and the monthly PV generation (6227-6238), direct consumption
(6417-6428) and export (6596-6607) hold values up to October and 0 for the months to come.

The same dump places the yearly registers, which V1.1.16 gives as twenty U32 slots "valid for
15 years" without naming the first year. For all three quantities the slot at 6272, 6451 and
6630 holds exactly the sum of that quantity's monthly values (PV 8410.4 kWh, direct
consumption 2350.6, export 3777.8), so each slot is U32 low word first at 0.1 kWh, the first
slot (6250, 6429, 6608) is 2015, and 2015-2029 are the fifteen; the five slots after 2029
read 0xFFFF. November and December read 0 while 2025 holds 8541.9 kWh of PV, so the monthly
registers hold the current calendar year only and are cleared at the new year. One house.

Through [ra1k-0](installation-ra1k-0.md)'s WiNet-S on P071 the monthly PV generation (6227) and
export (6596) blocks are refused, but the monthly direct consumption (6417) answers, **all 0**,
beside a daily direct consumption of 118.1 kWh: a dongle's zero, not the inverter's history
([the reading](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-3-summary.md)).

The integration reads the block over the cable as six sensors, this month and this year per
quantity, gated on `Capability.ENERGY_HISTORY` (`src/sungrow_modbus/hybrid_inverter/capabilities.py`).

