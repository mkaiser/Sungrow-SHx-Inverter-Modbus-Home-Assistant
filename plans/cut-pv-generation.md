# Cut PV generation (holding 31211): what is left

PR #738 (sebastian-tennant) adds a YAML switch that stops PV production by
writing 0xAA to holding register **31211** (0x55 lets PV run again). The
register is not in Sungrow's protocol document; theunknown86 found it in #554
by watching what iSolarCloud writes. The integration now carries it, gated by
firmware:

| What the device shows | Entity |
| --- | --- |
| 31211 reads 0xFFFF, 0, or anything but 0x55/0xAA | none |
| 31211 reads 0x55 or 0xAA | binary sensor **PV generation cut** |
| ...and its firmware is in `CONFIRMED_ON_FIRMWARE` | switch **Cut PV generation** |

`CONFIRMED_ON_FIRMWARE` holds **`SAPPHIRE-H_B001.V000.P022`** and
**`SAPPHIRE-H_B001.V000.P023`**: P023 confirmed on fwitten's SH10RT-V112 master
(1213 W, 0 W, 1199 W), P022 on gerd's SH8.0RT-V112 (2938 W, 0 W, 1913 W), both
over the inverter's own LAN port. A P022 or P023 inverter gets the switch.
Every other firmware waits for a run of its own.

A stop is judged by its bracket: 0 W between two windows of at least 500 W
(`STOP_BRACKET_W`) is `CONFIRMED` however far the sky moved them apart.

The cut is a ramp: DC power holds about 6 s after `0xAA` and reaches 0 W about
20 s after the write; after `0x55` it returns about 8 s later and is full
within about 20 s. `PV_CUT_SETTLE` (35 s) waits out the ramp before the window
that measures it.

## Why the switch waits

A read shows that the register is there, not what writing it does, and this
register is outside the specification. The only evidence of the write is its
effect: the PR author's SH10RT went from 1544 W of DC power to 0 within about
10 s, and came back 30-60 s after 0x55. That is one owner's report, on one
firmware they quoted as "95.12", and two inverters on 95.12 in the corpus
(mkaiser, bar12 before its update, both P020) answer the sentinel. So the
string that decides is 13250, not 2582, and the report does not say which
13250 build it was.

Where it answers, by the committed register dumps
(`tests/test_pv_generation_cut.py` asserts each one):

| 13250 (inverter firmware) | 31211 |
| --- | --- |
| SAPPHIRE-H_B001.V000.P020 | 0xFFFF |
| 13250 refused, 2582 = 01011.95.03 | 0xFFFF |
| SAPPHIRE-H_B001.V000.P022 | 0x55 |
| SAPPHIRE-H_B001.V000.P023 | 0x55 |
| PEARL-H_B000.V000.P071 | 0x55 |

fwitten's pair answers the sentinel on 95.03 and 0x55 on 95.14/P023: the same
two inverters, so the firmware decides it.

## Next

1. **Run the control test with the cut allowed** on a P071 SH-T over its own
   LAN port, in daylight with at least 500 W of PV: `survey.sh control <host>
   --cut-pv --enable-export-limit --restart` (with `SUNGROW_MODBUS_LIBRARY`
   until it is released), or the device page's button with **May it cut PV
   generation** on. The check writes 0xAA, needs DC power under 200 W,
   restores the snapshot's word and waits `PV_RECOVERY` (75 s) before the
   window after. The P071 SH-Ts in the corpus are surveyed only through a
   WiNet-S; 13018 already exists there, so the run also shows whether both
   registers act.
2. On a `CONFIRMED`, commit that survey and add its 13250 string to
   `CONFIRMED_ON_FIRMWARE[PV_GENERATION_CUT_CONTROL]`.
   `test_nothing_is_confirmed_without_a_document_that_shows_it` refuses an
   entry without such a document. A `--merge-into` replaces the document's
   whole `control_test` block, so run with the flags of the run it replaces.
3. Ask the PR author on #738 for their 13250 string, or a survey.
4. One evening's watch on a confirmed device: does a cut survive a night, or
   a restart, or does iSolarCloud rewrite it? The switch reports the register,
   so either way it shows the truth; a surprise belongs in its description.
5. Through a WiNet-S: the check judges by DC power, which the dongle forwards,
   so a run there answers whether the write is forwarded too.
6. Close #738 with a pointer to the release that ships the switch.
