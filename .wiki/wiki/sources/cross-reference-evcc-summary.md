---
type: source
title: cross-reference-evcc.md
source_path: raw/cross-reference-evcc.md
ingested: '2026-11-05'
created: '2026-11-05'
tags: [cross-reference, ihomemanager, wallbox, licences]
---

# Cross-reference: evcc

`raw/cross-reference-evcc.md` compares this project's registers with every
Sungrow template and driver in evcc, at commit `bcea759cd9`, and with the
evcc issues in which users read registers off real devices.

| Device | Agrees | Differs, or adds |
| --- | --- | --- |
| SH hybrid | all 25 template registers | battery power: evcc signs unsigned 13022 by 13001's bits, this project reads signed 5214 |
| SG string inverter | 5007/5008, 0xAA/0x55 and 0.1 % | the inverter resets 5008 to 110 % while the switch is off |
| [iHomeManager](../entities/device-ihomemanager.md) | 8145, 8155-8163, 8176, 8178, 8559-8564, 8031 | **8028 reads 0x55/0xAA**, not V1.0.2's 0/1; phase voltages at input **4358, 4360, 4362**, undocumented |
| [Wallbox](../entities/device-wallbox.md) | all 16 driver registers, codes 1-9, 21203 at 0.1 A in its code | 21263 read as a work mode; a 60 s idle timeout |

- **Licences.** The templates are MIT, as evcc is. The wallbox driver,
  `charger/sungrow.go`, reserves all rights in its own header: a cross-check,
  never a source.
- **The iHomeManager readings are the first from real units** this project
  has: firmware `iHomeManager-SV930.001.00.P015`, build B003, behind two
  SH10RT-20 (evcc #33775), and a second unit's raw voltage block
  (evcc #34169). They are someone else's measurement, held as `field` in
  `src/sungrow_modbus/ihomemanager/registers.py`.
- **evcc's wallbox map derives from Louisbertelsmann's**, so it does not
  raise a register's confidence in `doc/wallbox_registers.md`.
- **Sungrow's wallbox document exists** (`AC011E-01_Modbus_Protocol_V1.0.16_EN_Confidential.pdf`)
  and is confidential; the wallbox's names stay this project's own.
