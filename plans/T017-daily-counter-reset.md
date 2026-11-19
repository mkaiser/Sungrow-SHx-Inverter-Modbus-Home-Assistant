# T017 - Does the inverter reset its daily counters in one step?

**Does the inverter reset its daily counters in one step?**
Open, and now measurable. `daily_consumed_energy` adds five daily counters
together, so if the inverter zeroes its eight over several polls, one poll
reads some of today against some of yesterday -- which is what the YAML
package put in the history as a nightly negative spike
([#708](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/708),
[#797](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/797)).

`daily counters reset at midnight` now names **every** counter that fell in
the poll, with before and after, and every one still standing, and it says
so on a pass as well as on a failure (`EventCheck.notes`). So the answer
arrives at mkaiser's too, where the row is red on the clock of T016 --
the nightly failure sentence carries it.

**What is needed is one more night of auto repeat.** The two nights already
observed named only `daily_pv_generation`, so neither answer is established.
Then: if the reset is atomic, the clamp in `_consumed` is belt and braces
and the device page can say the counters reset together; if it is
staggered, that is a device finding worth a page, and the clamp is what
makes the sensor correct.

The sum itself is settled either way: `daily_consumed_energy` and
`total_consumed_energy` are held at zero as a floor
(`src/sungrow_modbus/hybrid_inverter/derived.py`), which no longer leaves a
user-visible defect waiting on the measurement.
