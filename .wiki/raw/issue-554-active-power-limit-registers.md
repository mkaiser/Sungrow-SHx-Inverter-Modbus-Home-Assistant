# Issue #554: the active power limit registers iSolarCloud writes

Frozen copy of the findings in
<https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/554>
(a feature request for limiting the inverter's active power), as read on
2026-11-05. Handles as the issue shows them; quotations verbatim.

## The request

The issue asks for a way to stop PV production, for negative prices: theunknown86
writes "we want no PV production at all... All house loads & battery charge
should come from the grid even when solar is available", and notes that the
export limit alone "will still charge & power loads".

## What the documented registers did

Gnarfoz (collaborator) pointed at holding 13089 (active power limit on/off)
and 13090 (active power limit ratio), new in the V1.1.9 protocol document, and
reported: "my inverter reports 0xFFFF for holding registers 13089 and 13090,
regardless of if I switch active power limit on or off via iSolarCloud. ... It
might indicate that these registers are not available in my firmware version
(95.01)." theunknown86: "13089 and 13090 return 0xFFFF for me also on both my
SH15T."

## What iSolarCloud writes (theunknown86)

> ok, little more time with it. Since the value is changeable via iSolarCloud
> these are the registers it uses.
>
> 31204 = Active Power Limitation
> 0x00 AA [170] = On
> 0x00 55 [85] = Off
>
> 31205 = Active Power Limitation Ratio (%)
> uint16
> scale 0.1
> unit %

> Another that goes with it... I was playing with setting Active Power to 0%
> and my inverter shut down... WTF
>
> That's another setting
>
> 31213 = Shutdown at active power limit ratio of 0%
> 0x00 AA [170] = On
> 0x00 55 [85] = Off
>
> Probably worth mentioning... the Active Power Gradient Control makes it
> really slow to respond to setting the limit. Just give it a few minutes to
> take effect. We can add those registers also in time

Their final automation: "Slider controls all associated registers, 100% turns
off the limiter, shutdown at 0% is forced off, the max value is dynamically
pulled from the inverter, and the wattage slider is translated to the ratio of
the inverter register."

The inverter models: theunknown86 has two SH15T. The firmware of the inverter
that shut down is not stated.
