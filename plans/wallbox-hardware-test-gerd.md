# Testing the wallbox survey on gerd's hardware

Plan of record for the next wallbox reading. Gerd's is the only wallbox this
project has ever measured, so it is the only place the wallbox half of the
survey and of the integration can be tested for real.

## Why now

`plans/deduplication-part2.md` step 5a moves the wallbox decoder out of
`probe.py` into the library (`wallbox_registers.CONFIDENCE`, `readings()`,
`dump.WALLBOX_BANDS` / `WALLBOX_MASKED`). It also makes the integration's
`wallbox` fingerprint section the **same shape** as the survey's, with the
206-address dump included when `CONF_SURVEY_DUMP` is on. The offline golden
test (the committed 2026-09-08 dump decodes to its committed `readings`) shows
the code agrees with itself. It cannot show that:

- the published survey (uv, PyPI 0.1.0a12) still finds the wallbox at unit 3
  and dumps it, from a folder outside any checkout;
- the integration's new wallbox dump reads the same bands on real hardware,
  where 21281-21296 refuse and holding is scattered after 21248;
- the masked serial stays masked when the document comes from the device
  page rather than from the terminal.

The same session can also settle some of what `doc/wallbox_registers.md`
lists under "What is still open".

## The site

From the two committed documents (`doc/device-fingerprints/sh80rt-v112-
b001v000p022-3p-gerd-anon-00267885816-*`, both read 2026-09-08, schema 14):

| | |
| --- | --- |
| Inverter | SH8.0RT-V112, `0x0E0E`, firmware B001V000P022, three phase 3P4L |
| Battery | SBR096: unit 200 on the cable, unit 2 through the dongle |
| Wallbox | AC22E-01 (`0x3F80`), version fragment `LE-01.1E1.001.`, own LAN cable |
| Cable path | LAN cable in the inverter. 6100 answers. **No wallbox** at 3 or 248 |
| Dongle path | WiNet-S (`WINET-SV200.001.00.P043`) on WLAN. 6100 refuses. **Wallbox at unit 3** |
| Last reading | the car had finished: `charging_status` 6 *completed*, 0 W |

So the wallbox is reachable **only through the dongle's address**, which is
the one thing every step below depends on. The cable address is still worth
one run, because "no wallbox on the cable" is a finding the integration's
setup relies on (`_async_wallbox` in `__init__.py`) and it rests on one
reading.

## Before the session

1. **Consent.** Gerd agreed to the 2026-09 readings. Ask again before
   publishing new ones (CLAUDE.md, "a stand-in serial is not consent"), and
   ask whether `ip_address_last_two_octets` may be published again.
2. **Access.** Not recorded in this repository or in memory. Decide which
   route applies:
   - **A, gerd runs it.** Send the two folders (or a pull). Results land
     beside the launcher, and he sends the `.json` files and keeps the `.log`.
   - **B, the maintainer runs it over a VPN.** Record the addresses in
     `secrets.yaml` or in memory, never in this repository. Over a tunnel,
     slow the sweep (memory: *probe sweeps need slowing over VPN*) or give
     both hosts explicitly.
3. **Release first.** 0.1.0a12 is on PyPI and `make pin-check` is green
   (deduplication-part2 step 9). Route A runs on whatever PyPI has.
4. **Quiet link.** Gerd's Home Assistant is **stopped** for the whole
   session, as it was for both earlier readings. A Sungrow grants few sessions
   and needs about 90 s of quiet to reclaim them, and a wallbox behind a
   WiNet-S shares the dongle's. One tool at a time, with 90 s between tools.
5. **Two moments, if possible.** One run with the car **charging** is worth
   more than anything else here (21313, the 32-bit sign question and the
   session counters only move then). One run idle is the fallback. Agree a
   time with gerd when the car will be plugged in and charging.

Nothing in this plan writes to the wallbox or to the inverter. The control
test is not part of it.

## The session

### 1. The survey through the dongle (the main test)

    ./read_only_survey.sh <dongle-ip>          (route B, or gerd on Linux)
    read_only_survey.cmd <dongle-ip>           (gerd on Windows)

Run from a copy of the folder **outside a checkout**, so it is the install a
contributor gets. Answer the questions as the 2026-09-08 reading did:
transport `winet_wlan`, proxy `no`, reporter `gerd`.

Pass:

- the summary names a wallbox at **unit 3**, and the identification shows
  `unit 248 wallbox serial (direct)` with **no answer**;
- the run prints `wallbox dump  unit 3, 206 addresses...` and finishes it.
  Note the answered count: the earlier reading's bands answered fully apart
  from the documented holes;
- the document's `wallbox` section has `unit`, `readings` and
  `register_dump`. `readings` has the **same 32 keys** as the 2026-09-08
  document, each with `register` and `held` matching it, and `model_name`
  `AC22E-01`;
- the six serial words `dump.WALLBOX_MASKED` names (input, from 21200) are
  masked in `register_dump`, and the wallbox's real
  serial (from the `.log`, which only the person who ran it holds) appears
  nowhere in the `.json`: `grep -c <serial> <document>.json` gives 0;
- the document and the transcript are **beside the launcher**, and nothing
  else was written;
- exit code 0, or 3 with a stated reason.

### 2. The survey through the cable

    ./read_only_survey.sh <cable-ip>

Ninety seconds after step 1. Pass: `unit 3 wallbox serial` and `unit 248
wallbox serial (direct)` both **no answer**, and no `wallbox` section. If a
wallbox does answer here, that is a finding against `_async_wallbox`'s
docstring and against CLAUDE.md ("a wallbox answers 3 only through the
dongle"). Record it, don't explain it away.

### 3. The integration, from the device page

Either gerd's own Home Assistant with the preview channel at 0.1.0a12
(route A), or the dev instance pointed at the dongle (route B). Either way,
**only one** Home Assistant talks to the inverter.

1. Add the integration on the **dongle** endpoint. Pass: a wallbox device
   appears, hung off the inverter (`via_device`), with model AC22E-01 and the
   21 read-only entities. Nothing on it is writable.
2. With *Include a raw register dump* **off**, press *Run capability survey*
   and download the document. Pass: `wallbox` is `{"unit": 3, "readings":
   {...}}` with the same keys and per-field shape as step 1, and no
   `register_dump`.
3. Turn the option **on**, run it again. Pass: `wallbox` also carries
   `register_dump`. Its answered addresses match step 1's, minus whatever
   changed between the two moments, and it is masked the same way.
4. Add a second entry on the **cable** endpoint (with the first one disabled,
   or Home Assistant restarted in between). Pass: no wallbox device.

### 4. If the car is charging: the open questions

While a session runs, take two survey runs about five minutes apart (step 1
twice, 90 s quiet before each). From the two dumps:

- **21313**: does it still track power roughly at 1:13, and does it go to 0
  when charging stops? Plot it against 21308.
- **21308 / 21310 sign**: only a value above 2^31 would settle it, so expect
  nothing. Note it as still open.
- **Holding 21263**: answered or refused this time.
- **Input 21263**: still 320, or changed with the mode.
- **Version string 21226-21235**: still the fragment `LE-01.1E1.001.`?
- **The clock**: compare `charging_started` / `charging_ended` `local_time`
  with the wall clock at the run. The claim is local time, not UTC.

## After the session

1. **Publish** (with consent): copy the new dongle document into
   `doc/device-fingerprints/` under the filename the survey chose, and the
   cable one if it differs in substance from the committed one. Replace the
   2026-09-08 documents only if the new ones carry everything they did. Then
   `make gen` (compatibility table) and `make check`.
   `tests/test_no_real_serials.py` must pass with no new allow-list entry.
2. **Golden, both decoders.** Decode the new `register_dump` offline with the
   library's `readings()` **and** with 0.1.0a11's `probe._wallbox_readings`
   (`git show v0.1.0a11:scripts/sungrow_read_only_survey/probe.py`). They
   must agree field for field. That proves the move in step 5a changed
   nothing on a reading the old code never saw. Then add the new document to
   the golden test beside the 2026-09-08 one.
3. **Integration against survey.** Compare step 3.3's `wallbox` section with
   step 1's: same `readings` keys, same `held`, values within what five
   minutes can move. A difference in **shape** is a bug in step 5a.
4. **Docs.** Update `doc/wallbox_registers.md`: the sources table ("one
   firmware, one session" becomes two), "What is still open", and any `held`
   mark a second reading earns. If a mark changes, change
   `wallbox_registers.CONFIDENCE` with it. The golden test will insist.
5. **Memory.** Record how gerd's site is reached (not the addresses) beside
   the other setups in *Sungrow inverter dev connection*.

## Done when

- [ ] steps 1 and 2 pass from a folder outside a checkout, on PyPI 0.1.0a12
- [ ] step 3 passes, with the dump option off and on
- [ ] the new dump decodes identically through 0.1.0a11's decoder and the
      library's
- [ ] the new document is committed (with consent) and in the golden test
- [ ] `doc/wallbox_registers.md` says what the second reading settled, and
      what it did not
