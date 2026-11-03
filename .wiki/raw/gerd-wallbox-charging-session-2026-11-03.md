# gerd's wallbox through a charging session, 2026-11-03

Logged by the maintainer over a VPN with gerd's Home Assistant stopped: one Modbus TLS session to the
wallbox's own address (unit 248), a read of four blocks every 30 s, from 11:55:44 to 15:07:18 UTC
(372 rows, 3 failed reads: a timeout each, nothing refused). A car charged at about 10.7 kW on three phases from before the first row; the wallbox
stopped charging at 14:50:42 UTC. The reads are 21267, 21300-21322, 21360-21366 and holding 21312-21313.
Values are the raw words; `u32` joins low word first. No serial, no address.

| UTC | 21308 W | 21310 Wh | CP 21312 | 21313 | 21314 | 21315 | 21317 | 21267 | 21365 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 11:55:44 | 10668 | 8612 | 5.93 V | 527 | 3 | 0 | 3 | 7826 | -70 |
| 12:06:59 | 10698 | 10614 | 5.94 V | 527 | 3 | 0 | 3 | 7916 | -69 |
| 12:18:08 | 10653 | 12600 | 5.94 V | 526 | 3 | 0 | 3 | 8050 | -69 |
| 12:28:19 | 10647 | 14409 | 5.94 V | 527 | 3 | 0 | 3 | 8127 | -68 |
| 12:38:34 | 10689 | 16232 | 5.94 V | 509 | 3 | 0 | 3 | 8211 | -70 |
| 12:48:47 | 10690 | 18051 | 5.94 V | 506 | 3 | 0 | 3 | 8353 | -70 |
| 12:58:58 | 10747 | 19874 | 5.93 V | 504 | 3 | 0 | 3 | 8544 | -63 |
| 13:09:11 | 10728 | 21701 | 5.93 V | 489 | 3 | 0 | 3 | 8682 | -65 |
| 13:19:25 | 10736 | 23532 | 5.94 V | 514 | 3 | 0 | 3 | 8819 | -66 |
| 13:29:41 | 10727 | 25370 | 5.93 V | 527 | 3 | 0 | 3 | 8951 | -67 |
| 13:39:52 | 10737 | 27190 | 5.93 V | 521 | 3 | 0 | 3 | 9084 | -67 |
| 13:50:07 | 10735 | 29025 | 5.93 V | 516 | 3 | 0 | 3 | 9196 | -66 |
| 14:00:16 | 10749 | 30841 | 5.94 V | 527 | 3 | 0 | 3 | 9281 | -66 |
| 14:10:27 | 10741 | 32663 | 5.94 V | 494 | 3 | 0 | 3 | 9401 | -67 |
| 14:20:38 | 10713 | 34481 | 5.93 V | 499 | 3 | 0 | 3 | 9537 | -71 |
| 14:31:57 | 10697 | 36502 | 5.94 V | 462 | 3 | 0 | 3 | 9671 | -69 |
| 14:42:25 | 10683 | 38361 | 5.94 V | 476 | 3 | 0 | 3 | 9776 | -70 |
| 14:48:36 | 10688 | 39462 | 5.94 V | 454 | 3 | 0 | 3 | 9841 | -66 |
| 14:49:06 | 10682 | 39552 | 5.93 V | 454 | 3 | 0 | 3 | 9847 | -67 |
| 14:49:37 | 10676 | 39642 | 5.94 V | 454 | 3 | 0 | 3 | 9854 | -67 |
| 14:50:07 | 10678 | 39740 | 5.94 V | 456 | 3 | 0 | 3 | 9856 | -68 |
| 14:50:42 | 0 | 39814 | 8.97 V | 456 | 3 | 1 | 5 | 9863 | -68 |
| 14:51:12 | 0 | 39814 | 8.96 V | 456 | 3 | 1 | 5 | 9868 | -70 |
| 14:51:43 | 0 | 39814 | 8.96 V | 458 | 3 | 1 | 5 | 9873 | -70 |
| 14:52:16 | 0 | 39814 | 9.02 V | 0 | 3 | 0 | 6 | 9878 | -70 |
| 14:52:46 | 0 | 39814 | 9.02 V | 0 | 3 | 0 | 6 | 9881 | -70 |
| 14:53:17 | 0 | 39814 | 9.02 V | 0 | 3 | 0 | 6 | 9884 | -70 |
| 14:53:49 | 0 | 39814 | 8.91 V | 0 | 3 | 0 | 6 | 9887 | -70 |
| 14:54:21 | 0 | 39814 | 8.92 V | 0 | 3 | 0 | 6 | 9889 | -68 |
| 14:54:51 | 0 | 39814 | 9.02 V | 0 | 3 | 0 | 6 | 9892 | -68 |
| 14:55:22 | 0 | 39814 | 9.01 V | 0 | 3 | 0 | 6 | 9895 | -68 |
| 15:07:18 | 0 | 39814 | 8.92 V | 0 | 3 | 0 | 6 | 9957 | -70 |

Register numbers in the header; the words come from the logger's blocks, 21308 and 21310 as u32.

## What it shows

- **21313** read 297-527 for three hours at a steady 10.6-10.8 kW; it follows nothing that moves with power. It held 454-458 until the stop, and read **0 from 14:52:16**, 94 s after the power fell to 0, on the poll where the status reached 6.
- **21308/21310 signedness:** the high words read 0 in every row, and power never left 10634-10760 W, so no value could tell a signed word from an unsigned one. A negative reading would be needed (a car feeding back), or more than 32767.
- **21310** kept the session's energy after the end: 39814 Wh from 14:50:42 to the last row. 21300 stopped counting with it.
- **The stop, in order:** power and currents to 0 and control pilot 5.94 V -> 8.97 V (state B, vehicle connected, not charging) with the status at 5 and 21315 at 1; about 90 s later status 6, 21315 back to 0 and 21313 at 0. Start mode 21314 read 3 throughout, charging or not.
- **21267** rose from 7826 to 9957 in 11534 s, 0.185 a second (one in about 5.4 s), through the stop. It is not a write counter and does not follow charging; the shape of uptime.
- **21365** read between -71 and -63 throughout and did not move at the stop; holding 21312/21313 read 2 and 220 in every row.
