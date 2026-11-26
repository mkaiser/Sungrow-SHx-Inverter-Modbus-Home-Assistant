---
type: concept
title: Zero and empty mean absent
tags: [capabilities, winet-s, decoding]
created: '2026-10-29'
---

# Zero and empty mean absent

"The block answered" is not evidence that the thing exists.

- **Numbers.** A [WiNet-S](../entities/device-winet-s.md) answers 0 where the
  inverter answers 0xFFFF, which would invent MPPT3, MPPT4 and a second meter
  channel. `ZERO_MEANS_ABSENT` in `src/sungrow_modbus/hybrid_inverter/capabilities.py`
  is the guard.
- **Strings.** Sungrow fills a UTF-8 field it cannot answer with 0x00, which
  decodes to `""`. `present()` in `model.py` maps that to None. Otherwise an
  absent battery's firmware string would count as evidence of a battery.
- **Firmware strings through a dongle.** Inputs 13249, 13264 and 13279 can
  time out on the inverter's own LAN port. The inverter then closes the
  session, so `_async_update_components` retries a lost connection once per
  component. Through the dongle, the same inputs answer with every character
  0x00.
- **A capacity of 0.** Register 5639 is the inverter's report of its pack's
  size. Every house with a pack reads non-zero there, every SBR and SBH and
  two BYD packs (1110 and 1020); 0 comes only from inverters without one and
  from the [maintainer's](../entities/installation-mkaiser.md) Pylontech
  Force H1, whose capacity the inverter does not report
  ([seventh reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-6-summary.md)).
  So 5639 declares 0 as no reading (`NAN_BEYOND_YAML`). Nothing on Modbus can
  set it, being an input register, so the owner can enter one in the options.
- **Sentinels.** An SH10RT returns 0xFFFF for MPPT3/4, and battery blocks are
  absent without storage. A poll losing one block is normal; that is what
  `UpdateReport` is for.

Capabilities are re-probed every poll, and the entry reloads when they
**grow**, since nothing ever removes an entity.
