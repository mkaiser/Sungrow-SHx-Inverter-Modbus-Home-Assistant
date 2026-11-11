---
type: query
title: "Is battery power firmware dependent?"
tags: [battery, register-5214, register-13022, firmware, open]
created: '2026-11-11'
query: "Do 5214 and 13022 read battery power the same way on every firmware, and does 5214 answer on every one?"
results_count: 35
---

# Is battery power firmware dependent?

**Open.** On every firmware measured: **no for how it reads, unknown for whether it answers.**

Two registers carry battery power. 5214-5215 is S32 and the one the integration shows; 13022 is
U16 with no direction, which Sungrow's V1.1.17 keeps beside it while recommending 5214-5215
([V1.1.17](../sources/hybrid-protocol-v1-1-17-summary.md)). evcc signs 13022 by 13001's
charging (0x02) and discharging (0x04) bits
([evcc](../sources/cross-reference-evcc-summary.md)), and so does the integration's self
consumption where 5214 is refused.

## How it reads: the same on ten firmwares

35 readings whose dump holds 5214, 13022 and 13001 together, on P020, P022 and P023 (SH-RT),
P059, P065, P067 and P068 (SH-RS), P067 and P071 (SH-T), and B001.V001.P038 (SH10T), over the
cable, through a WiNet-S and through a Logger. In all 35:

- **5214 is negative with the charging bit and positive with the discharging bit**, near 0 with
  neither. For example gerd's SH8.0RT-V112 on P022, -2047 W charging
  ([cable](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md)),
  robbensonmio's SH10RT on P020, 2259 W discharging
  ([cable](../sources/sh10rt-b001v000p020-3p-robbensonmio-anon-21004123443-battery-sbr256-direct-lan-summary.md)),
  an SH25T on P067, -9249 W charging
  ([Logger](../sources/sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger-summary.md)).
- **13022 holds the same magnitude, never signed**: 2089 beside -2047, 9279 beside -9249, 3800
  beside 3800 ([gerd, third reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md)).
  The two are read in different blocks, so they differ by what the battery did in between.
- **With no battery, 13022 reads 65535**, the unavailable word: fwitten's slave
  ([cable](../sources/sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan-summary.md)).

## Whether 5214 answers: unknown for older firmware

- **No committed diagnosis refuses it.** 60 answered it in the block read test. Two answered
  intermittently, mahagon's SH5.0RT-V112 on P023 over the cable
  ([cable](../sources/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-meter-direct-lan-summary.md))
  and an SH6.0RS on P068 through a WiNet-S
  ([WiNet-S](../sources/sh60rs-b000v001p068-1p-anonymous-anon-17579213881-battery-sbr192-winet-summary.md)),
  where other readings on the same firmware answered every round: the link, not the firmware.
- **Users report it failing**: on an SH8.0RS through a WiNet-S on WLAN, every poll, firmware not
  recorded (#655); and no battery power sensor with a third-party battery emulating a BYD (#770)
  ([user findings](../sources/github-issues-user-findings-summary.md)).
- **No diagnosis reads SAPPHIRE 51.0x**, the older firmware on which other newer registers
  (13249, 13264, 13279) time out (#660, #673, same source). Whether 5214 exists there is not
  known.

What answers it: a diagnosis of #655's SH8.0RS with its firmware, or of any inverter on
SAPPHIRE 51.0x or with a third-party battery.
