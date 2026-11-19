# T009, T013 - The scenes on hardware

**The new scenes on hardware.** `doc/scenes.md` has the YAML package's
seven rewritten against the integration's option keys, with the two
automations that need a limit reading it from the entity
(`state_attr(..., 'max')`) instead of from a secrets file, and
`tests/test_scenes_doc.py` holds every id, option and range in it to the
descriptions. Nothing in it has been activated on a device. Left:
- **Press one, at the maintainer's SH10RT.** **Done 2026-11-17**:
 *Battery Forced Charge*, installed from `doc/scenes.md` into the dev
 instance's `scenes.yaml`, set **both selects** -- EMS mode to forced and
 the battery command to charge -- and the inverter reported "Running in
 compulsory (forced) mode". The rewrite does what a pasted scene could
 not. What it did **not** do is move any energy: see *Beyond the one press* below.
- **Watch what `max` reads.** **Done 2026-11-17.** The attribute is there
 on hardware (*Feed-in limit* `max` = 10000.0 W, the battery numbers from
 `battery.ceiling`), and the automation itself ran: activating
 *Self-Consumption Mode (max battery discharge)* had
 `state_attr(number..., 'max')` render **7420.0 W** and write it, not
 `None` and not 0. The pattern in `doc/scenes.md` works.

 Worth keeping: **the ceiling moves with the battery's state** -- the same
 `max` read 7148 W with the pack empty, 7420 W at ~25 % and 7318 W a
 minute later, because the pack's limit falls back to what the BMS will
 take at that moment (`src/sungrow_modbus/battery/power.py`). That is the
 argument for the automation over a figure stored in the scene, and it
 belongs in `doc/scenes.md` where it tells a reader why the automation
 exists (wiki: the charge).

## T013 - Beyond the one press

**The new scenes, on hardware beyond the one press.** `doc/scenes.md`'s
three faults are fixed (2026-11-17): the newer entity ids are given as a
table rather than promised as "one substitution" -- three of them are
named differently, not just prefixed; every scene state is quoted, since
Home Assistant drops a whole scene whose state is a bare number, which
cost two of the seven on a real instance; and the two forced scenes now
carry a power, without which the inverter reports forced mode and moves
nothing. `tests/test_scenes_doc.py` holds all three to the descriptions.

Left: the scenes other than *Battery Forced Charge* have still never been
activated on a device. *Zero Export Power* and *Max Export Power* need a
house that is exporting, so they wait for sun with a battery that is not
empty; *Battery Bypass* and *Battery Forced Discharge* need a battery with
something in it. None of them is urgent, and the forced-charge press
already proved the mechanism the rewrite was for.

## Status log

### 2026-11-19 -- done: all seven scenes, and both automations, on hardware

Everything this plan waited for ran at the maintainer's SH10RT between 12:35
and 13:11 CET
(`.wiki/wiki/sources/mkaiser-scenes-2026-11-19-summary.md`). The pack was
empty, so a forced charge made the battery scenes testable -- 0.0 % to 8.7 %
in 14 minutes at -4502 W -- and the export scenes came with it, because
bypass sends the PV the battery was absorbing to the grid.

**T009's last need is met**: why the automations read the maximum instead of
storing it is now in `doc/scenes.md`, with the three readings that show the
ceiling moving with the pack.

**T013 is done**, and found three things worth more than the presses:

- the `number..._power` line is what makes a forced scene move, and the
  discharge scene overwrites what the charge left;
- *Max Export Power* is half a thing without its automation, which was not
  installed here -- so the document now names the automation at the scene;
- **a scene is not atomic**: three of seven presses did nothing first time,
  one logging a lost connection mid-write, on a link carrying two Home
  Assistants. Both registers of the failing scene were written singly
  between the failures and both took.

Nothing of `doc/scenes.md` is untested now. What is unmeasured is what any
scene does over time: every reading here is within two minutes of a press.
