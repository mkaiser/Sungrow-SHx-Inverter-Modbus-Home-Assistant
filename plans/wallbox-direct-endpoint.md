# The wallbox's own address: integration and survey

**Status: 2026-10-15, 07:18. Steps 1-6 done and pushed (851f2de). Releasing
0.1.0a14 now, together with the `direct-lan` filename word (the survey names
files through the library, so both ride one release). Then step 7: gerd's
wallbox document from the launcher on PyPI 0.1.0a14.** Updated at least every ten minutes while work runs, so another
session can take over from here.

Approved by the maintainer on 2026-10-14: both halves, the integration and
the survey. The measurements behind this are in `Todo.md`, "Wall box
integration": the wallbox answers Modbus TCP inside TLS on port 516, unit
248, at its own LAN address; a read must start on a data point's first
register; the integration's five wallbox reads already do.

## Design

**An option on the inverter's entry, not an entry of its own.** Every
wallbox entity's unique id is the inverter's serial plus a suffix, and the
device is `<inverter serial>-wallbox`. As an option, a wallbox that moves
from the dongle to its own address keeps its device, its entity ids and its
history; every platform is reused; `via_device_id` still hangs it off the
inverter. A separate entry would have needed a new identity (the wallbox's
own stand-in) and broken that history. It also settles gerd's case: one
entry on the inverter's cable, plus the wallbox's address.

- Option `CONF_WALLBOX_HOST` (empty: none), in the options flow's
  "advanced" section. Port 516 and unit 248 are constants, not options:
  they are the only values measured.
- Validated when saved: the options flow reads the wallbox's model name
  over TLS at unit 248 and refuses an address where none answers.
- Setup (`_async_wallbox`): with the option set, the wallbox is reached
  through `ModbusTlsParams(host, port=516, verify=False,
  check_hostname=False)`, unit 248, and the endpoint is not probed for one
  (a dongle entry would otherwise find the same wallbox a second time).
  Without it, nothing changes.
- `verify=False`: the certificate is Sungrow-signed and identical across
  devices; there is nothing to verify it against.
- The device-page survey: its wallbox dump must start every read on a valid
  start over TLS. A second band set, `dump.WALLBOX_TLS_BANDS`, cut at
  measured starts; the document says which path (`"path": "tls"` or
  `"dongle"`).

**The terminal survey.** Today `probe.py sweep` reports port 516 "found,
not readable".

- On a host with 516 open, try unit 248 over TLS for the wallbox's model
  name. A wallbox there becomes a found device of its own.
- It is surveyed as a wallbox: identity, readings, and a dump with the TLS
  bands, written as a document of its own (the inverter documents are
  inverter-centric; a wallbox-only document needs `label_for` to name it
  from the wallbox).
- The survey runs on the published library: anything new in the library
  reaches it only with a release (0.1.0a14).

## Steps

1. [x] Integration: `CONF_WALLBOX_HOST`, TLS unit in `_async_wallbox`,
       options-flow field and validation, strings; tests with a mock unit.
2. [x] Library: `WALLBOX_TLS_BANDS` aligned to the measured starts, and a
       test that every band read starts on one.
3. [x] Integration survey: dump with the TLS bands on the direct path,
       `path` in the wallbox section.
4. [x] Terminal survey: find a wallbox on 516, survey it, write its
       document; `label_for` for a wallbox-only document.
5. [x] Hardware: gerd's cable entry + the wallbox's address in the dev
       instance; the survey against the wallbox's address.
6. [x] Docs (CLAUDE.md, `doc/wallbox_registers.md`, the survey README),
       `make check`, commit. Release 0.1.0a14: asked, not done.
7. [ ] After the release: survey gerd's wallbox with the launcher (PyPI
       0.1.0a14) and publish it under `doc/device-fingerprints/wallbox/`,
       with the corpus checks that folder needs.

## Log

- 23:02 Step 1. `const.py`: `CONF_WALLBOX_HOST`, `WALLBOX_TLS_PORT` 516,
  `WALLBOX_TLS_UNIT` 248 (in the integration, not the library, so no release
  is needed for it). `links.py`: `wallbox_tls_params(host)`
  (`ModbusTlsParams`, `verify=False`, `check_hostname=False`), imported by
  setup and the config flow. `__init__._async_wallbox`: with the option set,
  only unit 248 over TLS is probed and the endpoint is not asked (no second
  copy through a dongle); a TLS address that answers nothing logs a warning
  and leaves the entry loaded. Options flow: the field in the "advanced"
  section (renamed "Battery, wallbox and diagnostics"), checked on save by
  `_async_wallbox_answers` (temporary unit, model name at unit 248),
  `wallbox_not_found` otherwise; the check runs before the other-inverter
  and promotion detours. Tests: `test_wallbox_entities.py` (TLS at 248,
  endpoint not asked, unique ids and device unchanged, a silent address
  does not fail the entry), new `test_wallbox_direct.py` (saved, refused,
  cleared without probing, the probe's params, a link failure).
- 23:07 Steps 2-3. Measured on the wallbox first: from every valid start a
  read up to the next start answers (scratchpad `wb-lengths.json`), so only
  the start matters. `dump.WALLBOX_TLS_BANDS`: twelve reads, each on a
  measured start, none longer than `BLOCK` (32); all twelve answered live.
  Holding 21249-21312 answers directly -- never reached through the dongle.
  Tests: every band starts on a start in `TLS_READ_STARTS`, and the bands
  cover every field the integration decodes. Integration:
  `fingerprint.wallbox_bands(direct)`, `wallbox_is_direct(coordinator)` (the
  entry's `CONF_WALLBOX_HOST`), `planned_steps(wallbox_direct=)`, and
  `"path": "tls" | "dongle"` in the wallbox section. Tests: the dongle path
  says `dongle`; the direct path dumps exactly the TLS bands at unit 248.
- 23:13 Step 4. New `scripts/sungrow_read_only_survey/wallbox_direct.py`:
  `async_identify(host)` (model name at unit 248 over TLS), `async_survey`
  (stand-in, `WALLBOX_TLS_BANDS` dump, masked, readings) writing a
  **wallbox document** (`"document": "wallbox"`, no `device`, filename
  `<model>-<reporter>-<stand-in>-wallbox-tls.json`); nothing read -> exit 1,
  no file. `sungrow_survey.py`: a swept 516 host that is a wallbox is
  surveyed (a WiNet-S's 516 stays "reported only"); a host given by address
  is checked for a wallbox on 516 first and not asked as an inverter when its
  502 is closed; three questions (address consent, reporter, comment); its
  exit code joins the inverters'. Smoke test on gerd's wallbox: 32 readings,
  **293** answered raw addresses (200 through the dongle), the full firmware
  string, the same stand-in as the dongle's document. **Mask widened**:
  `WALLBOX_MASKED` adds input 21210-21213, a short code only the direct path
  answers -- unknown whether it identifies a unit, so treated like the serial
  until a second wallbox is read. Tests: `test_wallbox_direct_survey.py`.
- 23:16 Step 5, on gerd's hardware. Terminal survey from the checkout
  (`python3 sungrow_survey.py <wallbox>`): found the AC22E-01 on 516, three
  questions, exit 0, 32 readings, 289 raw addresses answered (293 less the
  four newly masked), document `ac22e01-gerd-anon-41346964423-wallbox-tls`.
  Integration (dev instance, `DEVICES_MODE_OFFERED` flipped for the test and
  reverted): an entry on the inverter's **cable**, then the option -- the
  inverter's own address refused with `wallbox_not_found`, the wallbox's
  accepted. After the reload: SH8.0RT-V112 138 entities, SBR096 17, and
  **AC22E-01 21, via the inverter, read over TLS at unit 248**, every value
  as through the dongle, firmware string whole. `run_survey` with the dump:
  `path: tls`, unit 248, the same stand-in, 289 answered, both masks.
- 23:25 Step 6. CLAUDE.md (the option, the survey's wallbox document),
  `doc/wallbox_registers.md` (holding 21249-21312, the 21210-21213 mask),
  the survey README, probe.py's sweep help. `make check` 2859 passed.
  Committed locally, not pushed -- see the status line.
- 07:18 (2026-10-15) Found 851f2de already on origin. Folded the naming
  decision into the release: `TRANSPORT_WORDS["direct_lan"]` and probe.py's
  `REPORTED_TRANSPORTS` say `direct-lan`, and a measured direct verdict does
  too; the five cable documents renamed (`...-meter-direct-lan`,
  `...-battery-none-direct-lan`), README and compatibility.md updated. The
  wallbox document keeps `-wallbox-tls`: it names the wallbox's path, not an
  inverter's.
