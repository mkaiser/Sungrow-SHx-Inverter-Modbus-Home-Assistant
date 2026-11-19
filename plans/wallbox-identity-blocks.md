# T040 - A second wallbox's diagnosis: which blocks identify a unit

**A second wallbox's diagnosis.** Settles whether 21211-21214 identify
the unit. Three registers wait on it: input 21201-21206 (the serial as
Sungrow's portal shows it -- gerd's hashes to his published stand-in, so
this block is that serial; use it as the device identity?), input
21211-21214 (a short code, masked) and holding 21250-21259 (twenty
constant ASCII digits, masked). Whichever differ between two wallboxes
identify a unit and stay masked; whichever match are a model constant
and can be unmasked. A second AC22E-01 arrived 2026-11-10 (anonymous,
#786), but both documents publish these blocks as `null` with no
stand-in per block, so they cannot be compared: settling it needs the
masking to publish a stand-in for each masked block (a hash compares
without revealing), and a third reading. The AC011E-01 at unit 4
arrived on 2026-11-16 (#786) and is ingested, but as a Home Assistant
diagnostics download, whose wallbox section carries none of the three
blocks: 21211 and 21212 appear in it as the charger's enable and
start/stop, not as the short code. So this still waits on the masking
change plus a reading that carries the blocks -- a terminal diagnosis of
that wallbox would do it.
