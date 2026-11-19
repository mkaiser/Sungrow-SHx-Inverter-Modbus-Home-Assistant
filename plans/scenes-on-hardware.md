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
