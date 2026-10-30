# gerd's AC22E-01: the manufacturer's portal beside a direct read, 2026-10-30

Two readings of one wallbox, a few minutes apart, taken to cross-check the
register map against something Sungrow itself displays.

**The plant name and the serial number the portal shows are left out**: the
first names the owner's family, the second is the device's real serial.
What is kept about the serial is the one fact it was checked for (below).

## 1. iSolarCloud, the owner's device page

Passed on by the maintainer. Device model AC22E-01, "Data update time:
30/Oct/2026 14:15" (local time).

| Portal field | Value |
| --- | --- |
| Charging power | 0 W |
| Total delivered energy | 635.28 kWh |
| Energy charged until now | 0.28 kWh |
| Phase A / B / C charging voltage | 227.6 V / 0.0 V / 0.0 V |
| Phase A / B / C charging current | 6.10 A / 0.00 A / 0.00 A |
| Charging status | `--` |
| Current status | Normal |
| Commissioning date | 09/Jun/2026 |

**The serial number it shows** is 11 characters long. Hashed with
`survey_document.stand_in`, it gives `anon-41346964423`, the stand-in the
wallbox document derives from input 21201-21206.

## 2. Direct read, unit 248 over TLS on port 516

Read-only (function code 4), one session, 2026-10-30T13:20:31Z, about five
minutes after the portal's update time. Identity proven before reading
anything else: model name AC22E-01 at input 21216, and the stand-in of the
serial words equal to `anon-41346964423`.

| Register | Raw | Decoded |
| --- | --- | --- |
| 21300-21301 | u32, low word first | 635310 |
| 21302-21307 | phase voltages and currents | all 0 |
| 21308-21309 | charging power | 0 |
| 21310-21311 | session energy | 279 |
| 21312 | control pilot | 893 |
| 21313 | open register | 0 |
| 21314 | start mode | 1 |
| 21317 | charging status | 6 |
| 21322 | available current | 161 |
