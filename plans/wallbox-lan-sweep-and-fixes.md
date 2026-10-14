# Wallbox over the LAN, then the issues found on 2026-10-14

**Status: 2026-10-14, 22:45. Part 1 measured: the wallbox answers directly over TLS (516, unit 248 only); a read must start on a data point's first register (full map in `Todo.md`); the integration's five wallbox reads comply and answer through the real library over TLS. Next: design the wallbox endpoint (a decision), correct CLAUDE.md and `doc/wallbox_registers.md`. Part 2 done and pushed (`411fb4c`).** Updated every ten
minutes, so another session can take over from here.

Consent: gerd allows any test, inverter and wallbox (maintainer,
2026-10-14). His Home Assistant is off. Addresses are in memory (*Sungrow
inverter dev connection*), never here; check the stand-in
(anon-00267885816) before trusting the subnet, which bar12 and the
maintainer's home share.

## Part 1: is the wallbox reachable over Modbus without the dongle?

The maintainer expects so. What is measured so far: the wallbox answers
unit 3 through the WiNet-S, and on the inverter's own LAN port units 3 and
248 do not answer (2026-10-13 and -14). The owner reports the wallbox has a
LAN cable of its own.

Plan:

1. Sweep the /24 for every host with any open TCP port (Modbus 502/503/
   1502/5020, TLS 516/802, web 80/443/8080, OCPP 9000/8887, SSH 22), slowly:
   VPN, 32 at a time, 3 s.
2. For every host found other than the inverter's two: is it the wallbox?
   Modbus on any open port, every unit 0-255, input 21200-21299.
3. The inverter's LAN port: every unit id 0-255 against the wallbox's
   input block (21200) and the inverter's own (4990), not only 3 and 248.
4. The same full unit sweep through the dongle, for completeness.

Results:

- **Sweep** (14 ports, 254 addresses, 5.5 min): 18 hosts. Modbus on 502
  only at the inverter's two addresses. Nothing on 503, 1502, 5020, 802,
  9000, 8887. One host with **only port 516 open**, no web interface,
  serving a Sungrow-signed certificate (issuer `OT.SUNGROW`, CN `sun`) --
  byte-identical (sha256 `84:50:5E:46:...:5B:5B`) to the WiNet-S's own at
  the same house. The rest are network gear (TP-Link, FRITZ!, devolo).
- **That host is the wallbox.** Modbus TCP inside TLS on 516: **unit 248**
  answers input 21216 (`model_name`) with `AC22E-01`; units 0-3, 200 and
  247 time out. Same wallbox as unit 3 through the dongle: firmware string,
  lifetime energy (input 21300-21301), control pilot and the rest of the
  live block agree word for word.
- **The direct path reads the whole firmware string** (`LE-01.1E1.001.
  901.25`), and **input 21267 reads 12372 directly where the dongle answers
  0** -- the dongle's habit of zeroing what it does not forward.
- So CLAUDE.md is wrong twice: unit 248 is not "only through a serial
  gateway" -- it is the wallbox's own LAN port, behind TLS -- and a wallbox
  is not "only reachable through an endpoint that already answered".
- **Unit sweep, 0-255 over TLS:** only 248 answers.
- **The stack can do it.** `modbus-connection` has `ModbusTlsParams` (`verify=False`
  for a self-signed device certificate), and Home Assistant's
  `modbus.async_get_unit` accepts it. So the integration could take the
  wallbox's own address as an endpoint -- which would also give gerd the
  wallbox and the cable's fuller inverter reading together, without a second
  entry for the inverter. Next: read it through the real library over TLS,
  once the dumps release the wallbox.
- Not yet known: plain Modbus TCP anywhere on the wallbox (no 502 open).
- **Wide dumps compared** (input and holding 20000-21999, blocks of 10;
  scratchpad `wb-direct.json`, `wb-dongle.json`, not published -- the
  serial is in them):
  - holding: the same 50 addresses both ways (21200-21239, 21300-21309);
    only 21228-21229 differ, the wallbox's clock between the two reads.
  - input, direct answers **more than the dongle shows** where both answer:
    21210-21213 an ASCII identity-like string (not published until
    understood), 21240-21249 a version string (`V1.0...`), 21331-21335
    0xFFFF, 21359 and 21362-21364 values -- all **0 through the dongle**.
  - input, the dongle answers blocks the direct path times out on
    (21220-21229, 21250-21269, 21290-21329). Re-read one by one on fresh
    connections: reproducible, and **it is the start address, not the
    content** -- 21295 x24 answers, 21296 x10 and 21300 x10 time out;
    21225 answers, 21220 does not. Over TLS the wallbox answers only reads
    that begin at certain addresses (so far 21200, 21210, 21225, 21240,
    21261, 21270, 21295, 21330). The dongle evidently reads it its own way
    and serves any start. The direct path is not a drop-in replacement:
    the integration's component reads would have to start at those
    addresses.
- **Inverter's LAN port, every unit 0-255** at input 21215 x5: nothing
  answers. The link was alive (unit 1 device type 0x0E0E); the inverter
  is silent on those addresses rather than refusing.

## Part 2: fix the issues found

From `Todo.md`, in this order:

1. The survey-dump option's two defaults (form `True`, code `False`).
2. The wallbox firmware string cut short when decoded from a dump.
3. `via_device` deprecated (`via_device_id`), before HA 2027.8.
4. The survey's three link-failure bugs: timeouts labelled "refused", a run
   that read nothing exiting 3, a lost link deciding the transport.
5. A control test's dry run claiming "every planned check ran".
6. The restart deadline at night (381 s measured against 420 s).
7. `test_no_real_serials.py` decoding serials stored as register words.
8. One entry per inverter -- a design decision for the maintainer, not
   fixed here.

Done (working tree, not committed; `make check` not yet run on the whole):

1. **Survey-dump default**: one constant, `const.DEFAULT_SURVEY_DUMP = True`,
   read by the form, `survey.py` and `fingerprint.py`. On, because the
   option's own description says "On, and worth turning off if you are in a
   hurry". `test_survey_register_dump.py`: never saved -> dumps; saved off ->
   does not.
2. **Firmware string cut by the dump**: `dump.WALLBOX_BANDS`'s first band is
   split at input 21225 so the 10-register string is one read. Library
   change -- the survey gets it with the next release.
   `test_no_dump_block_splits_a_wallbox_string` fails on the old bands
   (`version_string (21225-21234) is split`), passes now.
3. **`via_device` -> `via_device_id`**: `_async_register_inverter` puts the
   inverter in the device registry before any platform runs (core `sofar`'s
   pattern); `SungrowRuntimeData.inverter_device_id`; the sub-device
   coordinator links with it. The wallbox device test asserts the
   deprecation is not logged (fails before, passes after) and no longer
   claims a wallbox has no address of its own.

4. **The survey's link failures**, three-valued throughout:
   - a) timeouts: `blocks.py` raises `TimedOut` for a `ModbusTimeoutError`
     and labels it `timed out`; only a Modbus exception response stays
     `refused with an exception`; any other library error is a drop. The
     library's `block_test` gains the same `TIMED_OUT` (it said `dropped the
     connection`). A test that faked a refusal with a bare `ModbusError` now
     raises the real `IllegalDataAddressError`.
   - b) a run that read nothing (no decoded value, no answered dump address)
     exits **1**, with an action saying the file is not worth sending;
     a test holds every published document to not counting as empty.
   - c) `probe.failure_state()` publishes `refused` only for an exception
     response and `no answer` otherwise (the library's `State` words, as the
     integration already did), for every capability probe and for 6100. A
     6100 with no answer gives the verdict `TRANSPORT_NOT_DETERMINED`, which
     claims no route: no transport question, no word in the filename.
     `Transport.state_6100` replaces the bool.
5. **Dry run**: a dry run's 0 now says "dry run: the plan resolved, and
   nothing was written" -- in the result file (library
   `control_test.DRY_RUN_MEANS`, used by `document()`) and in the CLI's
   headline and last line (its own copy, since it runs on the published
   library; a test holds the two equal). The code stays 0.
6. **Restart deadline** 420 -> **600 s**: the night restarts took 381 and
   369 s. Comment, CLAUDE.md, the CLI's help and the restart option's text
   say "over 6 at night"; the test holds the deadline to 1.5x the slowest
   measured.
7. **Serials as register words**: `test_no_real_serials.py` decodes every
   run of 4-5 digit integers as two ASCII characters per word (keys skipped,
   runs broken by anything but a list/dict separator) and holds the result
   to the same shape and FABRICATED list. Checked against the leaked
   `b3d0e70` versions of both test files: caught in both; the tree is clean.
