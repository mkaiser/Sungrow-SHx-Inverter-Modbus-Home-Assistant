---
type: source
title: mkaiser-range-checks-2026-11-17.md
source_path: raw/mkaiser-range-checks-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags: [capability-test, range-checks, battery, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# Which write bounds the inverter enforces, mkaiser, 2026-11-17

`.wiki/raw/mkaiser-range-checks-2026-11-17.md` records the upper-bound checks from run 3 of
*Extended test (auto repeat)* at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), over the cable, with the battery at
about 22 %. Each writes one value just above the maximum the integration offers and reads the
register back raw.

| Claim | Evidence | Status |
| --- | --- | --- |
| The state-of-charge maximum is enforced by the device | 13057 refused 101 % with exception 0x04 | one run |
| `battery_max_charge_power`'s bound is not enforced | 7374 W written and stored, maximum 7274 W | one run |
| `battery_max_discharge_power`'s bound is not enforced | 7374 W written and stored, maximum 7274 W | one run |
| `battery_charging_start_power`'s bound is not enforced | 1010 W written and stored, maximum 1000 W | one run |
| `battery_discharging_start_power`'s bound is not enforced | 1010 W written and stored, maximum 1000 W | one run |
| `battery_forced_charge_discharge_power`'s bound is **also** not enforced | 7374 W written, 7370 W stored -- a 10 W quantisation, and still above the 7274 W maximum | one run |
| The pack's own limit moves during a check | the manufactured discharge asked 4823 W and the pack accepted 4820 W, "its own limit moved" | one run |

So on this firmware **only the SoC bound is the device's**; every battery *power* bound is the
integration's own, and the entity's maximum is the only guard there is. That is the measured form
of the claim behind the range-check work, and it matches the five settings this house once stored
above their maximum.

## A verdict that overstates the evidence

The forced charge/discharge power was recorded as "the device clamped it". The rule in
`src/sungrow_modbus/capability_test/writepath.py` makes any readback word below the written word
a clamp, without asking whether the stored value is inside the bound, and `CLAMPED` maps to
established in `src/sungrow_modbus/capability_test/ledger.py`. A register that rounds to its own
step is therefore recorded as enforcing a maximum it does not enforce, and the check is never
asked again. A clamp should require the stored value to be at or below the bound.

## What each unrun check was waiting for

Worth keeping, because they say what a day's testing needs: the **charge ceiling** wants the
battery charging above 55 %; the **charging and discharging start thresholds** want battery power
between 200 and 800 W (it was ±4282 W); the **`battery_min_soc` upper bound** wants a floor well
below the battery's level; and the **export power limit** could not be attributed because the
house moved 2126 W during the check.
