# gerd's battery: the inverter's battery level against the pack's own SoC, 2026-11-14

Read only, over the WireGuard tunnel, from the development container, through gerd's WiNet-S
(the inverter at unit 1, the SBR096 at unit 2). Nothing was written.

## Readings

| Time (local) | Pack SoC, input 10744 (unit 2) | Inverter battery level, input 13023 (unit 1) | Min SoC, holding 13059 | Max SoC, holding 13058 | Backup reserve, holding 13100 |
| --- | --- | --- | --- | --- | --- |
| about 08:50 | not read | 14 (1.4 %) | 100 (10 %) | 1000 (100 %) | 0 |
| about 09:05 | 114 (11.4 %) | 15 (1.5 %) | 100 (10 %) | 1000 (100 %) | not read |
| 09:15 | 123 (12.3 %) | 25 (2.5 %) | 100 (10 %) | not read | not read |

At about 09:05 the inverter's block 13020-13025 read raw 1920, 65527, 187, 15, 970, 180, and the
pack's 10741-10745 read 1928, 65526, 183, 114, 97. iSolarCloud's battery page at 09:01 (the owner's
screenshot) showed: state of charge 11.1 %, current -1.10 A, voltage 192.6 V, temperature 18 °C,
health 97 %. Voltage, current, temperature and health agree on all three; only the charge level
differs.

The battery had discharged all night (input 5214 +300 to +600 W, positive is discharge), stopped at
about 08:00, and charged from PV after about 09:00.

## The maintainer's statement

The maintainer (mkaiser), 2026-11-14: one reading is the battery's absolute charge, the other is
relative to the usable charge, the window between the minimum and maximum SoC.

The readings fit: (11.4 - 10) / (100 - 10) = 1.6 % against 1.5 % read; (12.3 - 10) / 90 = 2.6 %
against 2.5 %. A plain offset (SoC - minimum) gives 1.4 % and 2.3 %.

## Also seen

Max SoC (13058) reads 100 %. gerd's diagnoses of 2026-10-30 to 2026-11-03 read 90 %. Who changed
it, and when, is not known.
