# Discussion #546: site import power limit (register 32998)

Copied 2026-11-07 from GitHub discussion #546 ("Site import power limit") of
`mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant`, the comments that carry
a measurement. Handles as the authors posted them. The one address in the
thread (a host in `mbpoll` commands) is replaced by `<host>`; no serial
appears in it.

## Korsberg, 2025-06-25: the register found

SH10RT-V112. The owner set iSolarCloud's "Site import power limit" to a unique
value, polled holding registers in blocks of 100 with `mbpoll`, and found the
value at register 32998 (protocol address 32997). Their YAML reads it as
holding, `uint16`, `scale: 0.01`, unit kW, and writes it as
`kW * 100` through `modbus.write_register`.

## Korsberg, 2025-08-29: a readback

The template number and the Modbus sensor both show **9.5** (kW, through
`scale: 0.01`), with the slider's range 0-10 and step 0.01.

## ulfben, 2026-10-23

Runs SH10RT-V112 inverters with a 25 kWh battery; wants the limit to
coordinate grid charging of the home battery with an EV. Asks whether the
setting does what it claims.

## Jam3s97, 2026-11-01: a written and watched limit on an SH10RS

> Tested on **SH10RS**, via both WiNet-S and RS485 (Modbus TCP gateway). Same
> value and scaling on both paths.
>
> - Write: `mbpoll -m tcp -a 1 -r 32998 -t 4 <host> 1300` → accepted.
> - Read-back: `mbpoll -m tcp -a 1 -r 32998 -t 4 -c 1 -1 <host>` →
>   `[32998]: 1300` (13.00 kW).
>
> **Functional test** (meter active power, ~10 s samples, 2026-11-01):
> - Cap 12.00 kW, 43 min: median 11,977 W, mean 11,978 W.
> - Cap raised to 13.00 kW: import stepped up within one sample; 16 min at
>   median 12,924 W, mean 12,928 W.
> - Brief overshoots (max +563 W at 12 kW, +258 W at 13 kW) corrected on the
>   next sample.
>
> **Boundary test** the device enforces its own limit, not just iSolarCloud's
> UI:
> - Write 50.01 kW (`mbpoll ... 5001`) → rejected, Modbus exception ("Slave
>   device or server failure").
> - Write 50.00 kW (`mbpoll ... 5000`) → accepted.
> - Matches iSolarCloud's displayed range `[0.01, 50.00]` exactly on this
>   SH10RS.

`mbpoll -r` is 1-based by default, so `-r 32998` is protocol address 32997.
The owner scales import down when the grid voltage sags, on a long rural
supply.

## ulfben, 2026-11-01 to 2026-11-02: an SH10RT-V112 that ignores it

- 2026-11-01: a readback sensor and a control for register 32998 added to the
  YAML package; it "read back the existing 11.00 kW setting straight away".
- 2026-11-02: "My testing last evening indicates that my plant ignore this
  setting. It will happily charge at 'max charge power' and overload the main
  circuit no matter what the import limit is set to." The installer checked
  the plant setup and found nothing wrong.
- Firmware before and after an update the same day: inverters 95.13 → 95.14,
  battery 01.27 → 01.30, WiNet-S P040 → P045.
- iSolarCloud shows the range [0.01-50.00] kW on the SH10RT-V112 too; the
  upper boundary was not written.
- 2026-11-02, after the update: "Up-to-date firmware changed nothing. My plant
  keeps ignoring the site import limit setting when force charging."

The thread does not say how the forced charge was commanded (iSolarCloud, the
EMS mode registers, or a schedule), and gives no meter trace.
