# The maintainer's SH10RT: which write bounds the inverter enforces, 2026-11-17

From run 3 of *Extended test (auto repeat)* at `anon-37323352958`
(SAPPHIRE-H_B001.V000.P020, third-party battery), over the inverter's own LAN port, started by
auto repeat itself at 09:39 local with the battery at about 22 % after a forced charge. The run's
own record is the capability ledger's third block (`outcome 3`, "ran, but checks were skipped or
inconclusive").

Each upper-bound check writes one value just above the maximum the integration offers, reads the
register back raw over a confirmed cable, and puts the original back.

| Control | Maximum offered | Written | Read back | Verdict recorded |
| --- | --- | --- | --- | --- |
| `battery_max_soc` | 100 % | 101 % | -- | **refused**: exception 0x04 on `write_register(13057, 1010)` |
| `battery_max_charge_power` | 7274 W | 7374 W | 7374 W | the bound is not enforced |
| `battery_max_discharge_power` | 7274 W | 7374 W | 7374 W | the bound is not enforced |
| `battery_forced_charge_discharge_power` | 7274 W | 7374 W | **7370 W** | "the device clamped it" |
| `battery_charging_start_power` | 1000 W | 1010 W | 1010 W | the bound is not enforced |
| `battery_discharging_start_power` | 1000 W | 1010 W | 1010 W | the bound is not enforced |

## What it says about the inverter

**Only the state-of-charge bound is enforced.** 13057 refuses 101 % with an exception, which is
the device answering. Every battery *power* bound is the integration's own: the inverter stores
whatever it is given, so the entity's maximum is the only guard there is.

The forced charge/discharge power is **not** an exception to that. It read back 7370 W against a
written 7374 W, which is the register quantising to 10 W -- and 7370 W is still **above** the
7274 W maximum. The bound is not enforced there either.

## What it says about the capability test

The check recorded "the device clamped it" for that register. The rule it uses is in
`src/sungrow_modbus/capability_test/writepath.py`:

```text
if raw is not None and raw < word:
    return [row(check, CLAMPED, f"took {value:g} {probe.unit} and stored the word {raw}", ...)]
```

Any readback word below the written word counts as a clamp, whether or not the stored value is
inside the bound. A register that merely rounds to its own step is then recorded as enforcing a
maximum it does not enforce, and `CLAMPED` maps to `ESTABLISHED` in
`src/sungrow_modbus/capability_test/ledger.py`, so the check is marked settled and never asked
again. A clamp should require the stored value to be at or below the bound; otherwise the right
verdict is the "not enforced" one the other four got.

## Other conditions the same run reported

Reasons checks could not run, each naming what it needs -- useful for planning a day's testing:

- **charge ceiling**: the battery charging, above 55 %; at ~22 % "the battery is too low for the
  ceiling to be put under it".
- **charging start threshold**: needs battery charge power between 200 and 800 W; it was -4282 W.
- **discharging start threshold**: same window; it was 4282 W.
- **upper bound of `battery_min_soc`**: "51 % is not well below the battery's level", at ~22 %.
- **export power limit**: "not measured -- the house was 2126 W different afterwards, so the
  change cannot be attributed", and separately "the export limit's write scale was not
  determined, so it was written divided by ten: feed-in limitation is off".

**The pack's own limit moves while a check runs**: the manufactured discharge asked for 4823 W
and the pack accepted 4820 W, "its own limit moved", which is the same live BMS limit that makes
the derived ceiling drift with state of charge.

## What passed

In the same run, all reported "the inverter did as it was told": forced discharge, the
forced-charging window, discharge windows away from now, the site import limit, the backup mode
write path, the load control write path, the weekend discharge enable write path, forced-charging
window 2 encoding, the upper bound of `battery_max_soc`, and the EMS mode options. The ledger went
from 15 of 52 established to **34 of 54**.
