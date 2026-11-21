# The search run from the maintainer's production Home Assistant, with the proxy running, 2026-11-20

Raw note, transcribed from the maintainer's screenshot of the setup dialog's *Devices found* step
(taken 2026-11-20 14:34 local time). The screenshot itself carries a real serial and a hostname and is
not tracked; neither is in this note, nor any address.

## Conditions

- The production Home Assistant, after the maintainer reinstalled the integration from the preview
  channel: 0.1.0a45 or a preview build after it (a45 was released at 01:10 that day, a46 at 23:35).
  `src/sungrow_modbus/discovery.py` is unchanged between a40 and a45, and the flow's sweep with it.
- The YAML package running and polling the SH10RT through the modbus-proxy add-on on the same machine,
  as on 2026-11-15.
- The search ran on the house's /24, from that machine.

## What the dialog showed

- Summary: one Sungrow device found, one inverter, and two addresses listed below because one device
  can answer at more than one address.
- Row 1, pre-selected: SH10RT at the Home Assistant machine's own address, shown by its hostname --
  "the inverter's own LAN port -- Home Assistant's own address, so a Modbus proxy -- the same inverter
  as" the inverter's address, with the serial.
- Row 2: SH10RT at the inverter's own address -- "the inverter's own LAN port -- the same inverter as"
  the Home Assistant machine's address, given there as a number, with the same serial.
- Row 3: "None of these — let me choose".
- No row for the RAK WiFi module.

## Read off it

- **The inverter's own LAN port was found, from the machine whose sweeps missed it on 2026-11-15,
  with the proxy holding a session to it** and the YAML package polling through that session.
- Both rows read 6100 (route "the inverter's own LAN port"); the proxy was recognised as a proxy by
  being one of Home Assistant's own addresses, and counted as the same inverter by its serial.
- The summary sentence was **German** while the step's own text and the rows were **English**: the
  summary comes from `texts.py`, which takes `hass.config.language` (the system language), while the
  frontend renders the step description in the user's profile language and the row labels are built
  in English.
- Row 1 names the proxy by its hostname, row 2 refers to the same address by its number.
