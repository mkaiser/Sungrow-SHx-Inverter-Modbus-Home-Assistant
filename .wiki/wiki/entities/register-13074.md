---
type: entity
title: Register 13074 (export power limit)
tags: [register, holding, export-limit, write-scale]
created: '2026-10-29'
---

# Register 13074 (export power limit)

Holding register 13074, the export power limit. It **reads** in watts, which
agrees with its 10000 W maximum from register 5623. **Its write scale is per
device**, because it follows the firmware, and the firmware moves under an
entry.

## The two behaviours

| Firmware | A written word is | Measured at |
| --- | --- | --- |
| every B001 measured: [P020](firmware-sapphire-h-b001-v000-p020.md), [P022](firmware-sapphire-h-b001-v000-p022.md), [P023](firmware-sapphire-h-b001-v000-p023.md) | **multiplied by ten** before the range check | [mkaiser](installation-mkaiser.md), [bar12](installation-bar12.md), [gerd](installation-gerd.md), [anonymous](installation-anonymous.md), [fwitten](installation-fwitten.md) since P023 |
| [01011.95.03](firmware-sapphire-h-01011-95-03.md) | stored as handed | [fwitten](installation-fwitten.md) before P023 |

On the times-ten firmware, a plain write sets ten times what was asked, or
it is refused with 0x04 when ten times the value is out of range. fwitten's
SH10RT-V112 pair answered 1:1 on 01011.95.03, and times ten on P023, cable
and dongle alike. So it is the firmware, not the model.

**Only while feed-in limitation (13087) is on.** With it off, the register
ignores writes: no exception, no change. That is most houses.

## How the code carries it

- `registers.AsymmetricNumberField` holds the common case:
  `write_units_per_count=10`, and `scale` 1 because that is what the register
  contains. It cannot live in `modbus-connection`, whose `NumberField`
  shares one scale by design. The difference from the YAML is declared in
  `tests/test_writes.py`.
- **`sungrow_modbus.inverter.export_scale` asks the inverter** with one
  write that changes nothing on either firmware. It writes the held word back
  when ten times that word would be out of range, or a tenth of it when that
  tenth is below the minimum. The answer is the **refusal**, which survives a
  dongle's stale readback. Where no such word exists, it declines. With
  feed-in limitation off, it needs leave to lift the mode.
  `tests/test_export_scale.py` sweeps both firmwares and asserts that the
  register never moves. From a terminal,
  `device-survey/scripts/python/sungrow_control_test.py --export-scale`
  asks it and does nothing else. With `--merge-into <document>` it adds the
  `export_scale` block to a survey, and a full control test run then
  writes 13074 at the factor the probe answered.
- `number.SungrowExportLimitNumber` probes on the first write. It stores the
  factor in entry data (`CONF_EXPORT_WRITE_SCALE`) together with the firmware
  it was measured on, re-measures after a firmware change, and writes the raw
  word itself. An unanswered probe falls back to ten and is not stored. The
  update listener skips the reload when that key is all that changed
  (`_built_from`).
- In the [control test](../concepts/control-test.md), leg B on 13074 needs
  the mode lifted. `_lift_export_mode` switches it on for that probe alone,
  and back to the snapshot's word the moment the register is restored.
  It does so only with `--enable-export-limit`, because it curtails a real
  house.
- The export limit's behavioural check can only catch a decade that is too
  small. A cap ten times too large leaves the export where it was, so leg B
  is the only way to catch that direction.

## Evidence

The `export_scale` blocks in the fwitten and gerd surveys (indexed under
Sources), and the control-test readbacks.
