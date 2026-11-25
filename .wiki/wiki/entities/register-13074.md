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
| every B001 measured: [P020](firmware-sapphire-h-b001-v000-p020.md), [P022](firmware-sapphire-h-b001-v000-p022.md), [P023](firmware-sapphire-h-b001-v000-p023.md) | **multiplied by ten** before the range check | [mkaiser](installation-mkaiser.md), [bar12](installation-bar12.md), [gerd](installation-gerd.md), [peter-sm](installation-peter-sm.md), [fwitten](installation-fwitten.md) since P023; [firetribe](installation-firetribe.md)'s **6 kW** SH6.0RT-V112 ([readback](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-2-summary.md)) |
| [P023](firmware-sapphire-h-b001-v000-p023.md), a 5 kW SH5.0RT-V112 on `.95.14` | **multiplied** by an unknown factor: the probe's write was refused, which ten and 0.1 % of the 5000 W rating both give | [mahagon](installation-mahagon.md), cable |
| [PEARL-H_B000.V000.P071](firmware-pearl-h-b000-v000-p071.md) (SH-T) | stored as handed, by the watched limit alone: word 125 held 106.5 W | [GalKar](installation-galkar.md), through a WiNet-S |
| [01011.95.03](firmware-sapphire-h-01011-95-03.md) | stored as handed | [fwitten](installation-fwitten.md) before P023 |
| [SUNSTONE-H_B000.V002.P065](firmware-sunstone-h-b000-v002-p065.md) (SH-RS) | stored as handed | [Jam3s97](installation-jam3s97.md), through a WiNet-S: the probe's acceptance |
| [SUNSTONE-H_B000.V002.P057](firmware-sunstone-h-b000-v002-p057.md) (SH-RS) | stored as handed | [bleughb](installation-bleughb.md), through a WiNet-S: the probe's acceptance |
| [SUNSTONE-H_B000.V001.P066](firmware-sunstone-h-b000-v001-p066.md) (SH-RS) | stored as handed | [icefest](installation-icefest.md), over RS485 and through a WiNet-S: the probe's acceptance |

On the times-ten firmware, a plain write sets ten times what was asked, or
it is refused with 0x04 when ten times the value is out of range. fwitten's
SH10RT-V112 pair answered 1:1 on 01011.95.03, and times ten on P023, cable
and dongle alike. So it is the firmware, not the model -- and swo14's two
**SH10RT-20s** on 01011.95.03 answer 1:1 as well, which is the same version on
a different model, through a Modbus proxy. On the SH-RS, P065 stores as handed;
[P068](firmware-sunstone-h-b000-v001-p068.md) is unmeasured, so the integration's per-device
probe, not a family rule, is what keeps an RS right.

**Ten watts, not 0.1 % of the rating**: at firetribe, 6000 W rated, word 60 read back 600 W, where 0.1 % would read 360
([second reading](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-2-summary.md)). gerd's 8 kW
on P022 reads 600 for the same word too ([readback](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-4-summary.md)). At 10 kW the two coincide.

**swo14 answered 1:1 again on 2026-11-24**, both inverters ([host](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3-summary.md),
[slave](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-summary.md)). A later run there skipped the established readback, so it did not lift the
mode, asked no scale and divided by ten: its export check wrote 125 for 1250 W, and that verdict says
nothing about the register. The test now lifts the mode for the probe alone ([host](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4-summary.md)).
No house has run that yet. Through a WiNet-S the probe may still read 13087 as off from the dongle's cache
after the lift and decline, which leaves the division by ten; unmeasured, and the ordinary readback shares it.

**Two cluster masters do not hold the limit under a manufactured discharge**:
[fwitten](installation-fwitten.md) on P023 and swo14 here, where the single inverters did
([bar12](installation-bar12.md), [peter-sm](installation-peter-sm.md)). Whether the cluster is why is not measured;
swo14's PV export was held in the first run.

**Only while feed-in limitation (13087) is on.** With it off, the register
ignores writes on B001: no exception, no change. That is most houses.

**A second dongle echoes a forwarded word, so an echo is not a measurement.** At
[bigz2012](installation-bigz2012.md)'s SH10RS on
[P067](firmware-sunstone-h-b000-v002-p067.md) the capability test wrote word 60 for 600 W with
feed-in limitation off, and the WiNet-S2 reported 60 back -- the same pattern that was kept open
below as possible evidence that P071 stores the word as handed
([the diagnosis](../sources/sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan-summary.md)).
Two dongles, two firmware families, one behaviour: a cache answering with the word it forwarded
explains both, where "the register took it" would have to be true of both firmwares at once. An
echo therefore says nothing about P071, whose watched limit (below) does. On P067 itself the write
scale is **unmeasured**: the owner reports 1:1 in watts, which is a report, and a probe needs the
mode on.

**SH-T on [P071](firmware-pearl-h-b000-v000-p071.md): stored as handed, on one watched limit.** At
[GalKar](installation-galkar.md), exporting 2539 W, the run asked for 1250 W, could not ask the probe (the
read of 13074 was refused), wrote word 125, and export held at 106.5 W (MAD 36.5) and came back to
2528 W ([second reading](../sources/sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan-2-summary.md)). What the inverter did is the evidence a dongle cannot spoil. Not settled: the
register was not read back, and 13088 read 0.5 % of 15000 W (75 W), where 125 W is 0.8 %; times ten would
read 8.3 % and hold 1250 W. A second house would confirm it. **The consequence**: where the probe cannot
answer, the integration divides by ten, so on an SH-T it sets **a tenth** of the limit asked; and at
GalKar's, holding 0 W, the probe has no word to ask with. The fallback stays ten (the
maintainer, 2026-11-24): a wrong one would set ten times the limit, a wrong ten only a tenth. P071 alone gets one
once a second watched run confirms it (T080). Before this, at
[ra1k-0](installation-ra1k-0.md) the register held 20000 W, its maximum, and
ten times that wraps to 3392 W in sixteen bits, inside the bounds, so the
probe had no word that changes nothing on both firmwares. The capability test then
wrote word 60 for 600 W with feed-in limitation off, and the WiNet-S reported
60 back, where B001 would have kept its old value. **This contradicts "ignores
writes" for P071 if the register really took it**, and would mean P071 stores
the word as handed, which the watched
limit above now agrees with, though a dongle may equally report the word it forwarded.

## How the code carries it

- `registers.AsymmetricNumberField` holds the common case:
  `write_units_per_count=10`, and `scale` 1 because that is what the register
  contains. It cannot live in `modbus-connection`, whose `NumberField`
  shares one scale by design. The difference from the YAML is declared on
  the field, in `src/sungrow_modbus/hybrid_inverter/registers.py`.
- **`sungrow_modbus.hybrid_inverter.export_scale` asks the inverter** with one
  write that changes nothing on either firmware. It writes the held word back
  when ten times that word would be out of range, or a tenth of it when that
  tenth is below the minimum. The answer is the **refusal**, which survives a
  dongle's stale readback -- but a WiNet-S other clients poll also answers
  0x04 when busy ([measured](../queries/does-a-busy-winet-s-refuse-with-0x04.md)),
  so a refusal is believed only after three asks, each followed by a read
  that answers; an acceptance is believed at once. Where no such word
  exists, it declines. With
  feed-in limitation off, it needs leave to lift the mode.
  `tests/test_export_scale.py` sweeps both firmwares and asserts that the
  register never moves. From a terminal,
  `device-diagnosis/scripts/python/sungrow_capability_test.py --export-scale`
  asks it and does nothing else. With `--merge-into <document>` it adds the
  `export_scale` block to a diagnosis, and a full capability test run then
  writes 13074 at the factor the probe answered.
- `number.SungrowExportLimitNumber` probes on the first write. It stores the
  factor in entry data (`CONF_EXPORT_WRITE_SCALE`) together with the firmware
  it was measured on, re-measures after a firmware change, and writes the raw
  word itself, and keeps the probe's publishable record beside them
  (`CONF_EXPORT_WRITE_SCALE_PROBE`), which the integration's diagnosis document
  carries as its `export_scale` block. An unanswered probe falls back to ten
  and is not stored. The
  update listener skips the reload when that key is all that changed
  (`_built_from`).
- In the [capability test](../concepts/capability-test.md), leg B on 13074 needs
  the mode lifted. `_lift_export_mode` switches it on for that probe alone,
  and back to the snapshot's word the moment the register is restored.
  It does so only with `--enable-export-limit`, because it curtails a real
  house.
- The export limit's behavioural check can only catch a decade that is too
  small. A cap ten times too large leaves the export where it was, so leg B
  is the only way to catch that direction.

## Evidence

The `export_scale` blocks in the fwitten and gerd diagnoses (indexed under
Sources), and the capability-test readbacks.
