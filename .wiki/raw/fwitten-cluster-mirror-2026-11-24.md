# fwitten's cluster: 13050 on the slave, and registers 33500-33502, 2026-11-24

fwitten's cluster, master SH10RT-V112 (`anon-86493117545`, unit 1) and slave SH10RT-V112
(`anon-33442450531`, unit 2), both SAPPHIRE-H_B001.V000.P023, over each one's own cable port.
Stand-ins proved before the write; nothing else was seen writing. Times CET. The maintainer gave
the go for the write. Battery 77.6 %, PV 0 W.

## 13050 on the slave while the master holds 2

One word written: master 13050 = 2, with 13051 left at 0xCC and 13052 at 0. Nothing was written
to the slave. Both inverters' 13050-13052 read about every two seconds.

| Time | Master 13050, 13051, 13052 | Slave 13050, 13051, 13052 | Battery, W | Meter, W |
| --- | --- | --- | --- | --- |
| 19:24:14, before | 0, 204, 0 | 0, 204, 0 | 508 | 14 |
| 19:24:14, the first sample after the write | 2, 204, 0 | 2, 204, 0 | 508 | -27 |
| 19:24:16-19:24:53, 22 more samples | 2, 204, 0 in all | 2, 204, 0 in all | 0 | 444-709 |
| 19:24:56, master put back to 0 at 19:24:55 | 0, 204, 0 | 0, 204, 0 | 0 | 484 |
| 19:25:00 | 0, 204, 0 | 0, 204, 0 | 1021 | -463 |

The slave stayed in Standby (13000 = 0x0008) throughout; the master read 0x0800 from 19:24:18.
Restored and read back by the script, then by a separate client: 13050 = 0 on both, master
13051 = 0xCC, 13052 = 0, 32998 = 2000 on both, 13000 = 0x0040 on the master.

Not tried: writing the slave's 13050, with the master at 2 or at 0.

## Holding 33500-33502

Register numbers; protocol addresses 33499-33501. Read only, after the run, one read per word.

| | 33500 | 33501 | 33502 |
| --- | --- | --- | --- |
| fwitten master, P023 | 170 (0xAA) | 160 | 2 |
| fwitten slave, P023 | 170 (0xAA) | 161 | 2 |
| the maintainer's single SH10RT (`0x0E03`), P020, own LAN port | 85 (0x55) | 160 | 2 |

`gerd-wallbox-inverter-control-2026-11-14.md` has protocol addresses 33500, 33501, 33502 = 160, 2, 65535 at a
single inverter, which is 33501 = 160 and 33502 = 2 again; its note's names are one register off.
