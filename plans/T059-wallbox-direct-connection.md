# T059 - The wallbox: the direct connection first

A wallbox with an address of its own is an entry of its own and the only one
that writes to it; an inverter entry leaves it out by its serial (decided and
built 2026-11-12: `doc/architecture.md`, wiki `device-wallbox.md`). Left:

1. **The search's result says it.** Where the search finds an inverter
behind a WiNet-S and a wallbox on 516, the list could say that the
wallbox will be read on its own and not through the inverter. Today the
inverter entry simply gives it up once the wallbox entry is added.
2. **On hardware at gerd's**: his inverter entry (WiNet-S) and his wallbox
entry side by side, to see the inverter entry give the wallbox up after a
reload, and take it back when the wallbox entry is deleted.
3. **The options screenshot** (`HA-settings-configure-capability-test.png`)
still shows the two wallbox fields an inverter entry no longer has;
retake it (`doc/development.md`, *Screenshots for the docs*).

Open, unchanged: Modbus over TLS on a **WiNet-S's** own 516 for the
inverter. Worth building only if 516 is a *separate* session pool from 502:
hold 502 until it refuses, then try 516. The certificate is settled (wiki:
`device-winet-s.md`): one certificate is built into the firmware, its key is
on every unit, and verifying it gains nothing.
