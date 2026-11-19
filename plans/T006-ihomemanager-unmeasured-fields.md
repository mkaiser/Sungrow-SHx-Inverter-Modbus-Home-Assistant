# T006 - The iHomeManager fields left out of its entities

Each is read and kept in the diagnosis and gets no entity until a second
unit is measured (Todo blocker T042; wiki: the iHomeManager source page).

- **8554, the output type**: reads 0, "single phase", on a three-phase
  site (three phase voltages, three phase powers).
- **8047 (start/stop) and 8048 (charger mode)**: read 0 and 0xA7, codes
  no document lists.
- **8051-8052, the active power limitation and its ratio**: 8051 reads
  0, not a code of the 0xAA/0x55 pair; 8052 reads 0x7FFF, an unset value.
- **Channel 2 (8565-8574), the PROD.CT**: all zeros on a unit with no
  CT there.
- **8029, the feed-in limit in kW**: only in a third-party template, in
  no Sungrow document.
A second unit, ideally single phase, on other firmware or with a
PROD.CT, decides each: a field whose reading then makes sense gets its
entity in `ihomemanager_descriptions.py`.
