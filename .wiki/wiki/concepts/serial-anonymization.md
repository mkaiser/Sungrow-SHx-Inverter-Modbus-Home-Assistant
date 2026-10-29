---
type: concept
title: Serial anonymization
tags: [privacy, serial, survey]
created: '2026-10-29'
---

# Serial anonymization

**No real device serial goes into anything this repository tracks**,
including this wiki. A serial is a device's identity: Sungrow's support uses
it to identify an installation, it is printed on the case, and it is the one
field in a survey that could tie a published reading to a household.
The rule is in `AGENTS.md`; this page is how it is carried out.

- **Every published document carries a stand-in**, in a field named for what
  it is: `serial_anonymized_hashed`. It is derived by hash, so one device
  always maps to one stand-in and files stay diffable. The shape is preserved,
  so the string decoder stays under test. The wiki names devices by these
  stand-ins (`anon-...`).
- **The real serial and the full address reach only the transcript**, which
  is written beside the script and gitignored there by name.
  `tests/test_survey_dependencies.py` holds every name a run writes to that.
  No un-redacted copy of the document is written, so `--save
  device-survey` cannot put a real serial there whatever it is asked.
  **A transcript is never a wiki source.**
- `NEVER_PUBLISH = ("serial",)` filters anything whose *name* mentions a
  serial, both values and key lists.
- **A wallbox's serial** (input 21201-21206) sits just below the model name, so
  `wallbox.probe_units` reads the name. At the publishing boundary the serial
  words are masked, and `wallbox.serial_anonymized_hashed`, from the same
  `stand_in` as the inverter's, is published in their place.
- **The tree is checked.** `tests/test_no_real_serials.py` matches the
  *shape* of a serial over every tracked file, `.wiki/` included. Each hit
  must be on a list of strings known to be invented.
- **Register words can hide a serial** where the shape test does not look:
  a fixture that carries one as Modbus words.

In tests, use an obviously fake serial: `A123456789`, or `A987654321` where
two must differ. **Addresses** are handled the same way. A document carries
`ip_address_last_two_octets` only with its owner's agreement, and this wiki
carries none.
