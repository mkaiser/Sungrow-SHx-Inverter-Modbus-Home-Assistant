## Sungrow string inverters: power limitation registers (5006/5007)

### Registers (holding)

| Raw Modbus address (0-based, HA `address:`) | Register no. in Sungrow docs (1-based) | Name | Type | Unit / scale | Values |
|---|---|---|---|---|---|
| 5006 | 5007 | Power limitation switch | U16, holding (R/W) | — | `0xAA` (170) = enable, `0x55` (85) = disable |
| 5007 | 5008 | Power limitation setting | U16, holding (R/W) | 0.1 % | 0–1000 = 0–100.0% of rated (nominal) active power |

Related registers in the same block, with values read from the inverter:

| Raw address | Doc reg | Name | Type | Unit / scale | Observed |
|---|---|---|---|---|---|
| 5009 | 5010 | Export power limitation switch | U16 | — | 85 (`0x55`, disabled) |
| 5010 | 5011 | Export power limitation value | U16 | W | 500 |
| 5014 | 5015 | Export power limitation percentage | U16 | 0.1 % | 1000 (100%) |
| 5015 | 5016 | Installed PV power | U16 | 0.01 kW | — |
| 5038 | 5039 | Power limitation adjustment | U16 | kW, as configured | 5 |

### How I use it

I run two inverters, each on its own Modbus hub.

1. Write `170` to 5006 to enable limiting.
2. Wait 1–2 seconds.
3. Write the percentage × 10 to 5007. For example, 45% is written as `450`.
4. To turn limiting off, write `85` to 5006.

Both inverters (2 × SG5.0RS) accept the writes. On the inverter I read back, the values stick: 5006 reads `170` and 5007 reads `1000` (100%). The limit applies to the inverter's AC output, as a percentage of its rated output (5 kW). I adjust it about every 30 seconds while the feed-in price is negative.

```yaml
- action: modbus.write_register
  data:
    hub: SungrowSHx_inv2
    slave: 1
    address: 5006
    value: 170
- delay: 2
- action: modbus.write_register
  data:
    hub: SungrowSHx_inv2
    slave: 1
    address: 5007
    value: "{{ (states('input_number.power_limitation_percentage_2') | float * 10) | int }}"
```

Sensor definitions used to read the registers back:

```yaml
- name: Power Limitation Switch 2
  address: 5006 # doc reg 5007
  input_type: holding
  data_type: uint16
  scan_interval: 300

- name: Power Limitation Setting 2
  address: 5007 # doc reg 5008
  input_type: holding
  data_type: uint16
  unit_of_measurement: "%"
  scale: 0.1
  scan_interval: 300
```

### Environment

- Home Assistant 2026.10.4, built-in `modbus` integration, `modbus.write_register` action
- 2 × Sungrow SG5.0RS string inverters (5 kW), firmware `<FIRMWARE>`
- A separate hybrid inverter and battery on a third hub
