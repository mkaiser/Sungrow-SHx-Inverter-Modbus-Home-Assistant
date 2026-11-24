---
type: source
title: sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3.json
source_path: ../device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3.json
ingested: '2026-11-24'
created: '2026-11-24'
tags:
  - diagnosis
  - sh10rt-20
  - sapphire-h-01011-95-03
  - swo14
  - direct_lan
  - proxy
  - capability-test
  - third-party-battery
---

# SH10RT-20 on 01011.95.03, swo14's host, battery full, no car charging

Read 2026-11-24 at 13:38 UTC from a Home Assistant diagnostics download on integration 0.1.0a54 (schema 29; the `diagnosis` section, committed unchanged, with no register dump or block read test). Posted to issue #786. Source: `device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3.json`.

**The comment reads "this is the slave/client" and that is the form's**: the document is the host's
(stand-in, pack and meter). The slave's document of the same minute is
[here](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-summary.md). The owner names "YAML package (mkaiser), evcc" as other pollers.

| | |
| --- | --- |
| Installation | [swo14](../entities/installation-swo14.md), host, unit 1 on the proxy's port 502 |
| Model | [SH10RT-20](../entities/device-sh-rt.md), type code `0x0E13` |
| Stand-in serial | `anon-00541024454` |
| Firmware | [`SAPPHIRE-H_01011.95.03`](../entities/firmware-sapphire-h-01011-95-03.md) (as before; the 13250 block is refused) |
| Battery | BYD HVM 11 kWh, 100 % |
| Transport | direct LAN through the Modbus proxy; [6100](../entities/register-6100.md) answered |
| WiNet-S | **fitted**: both inverters' dongles answer the mDNS browse, each with its inverter's record (`1;3603;...;1;516;SH10RT-20;1;4` and `...;2;4`) |
| At the time | PV 2429 W, load 317 W, export 2140 W, battery idle |

## The capability test (one run, ended 10:58 UTC, outcome 3)

Nothing left changed. Nine of nine readbacks matched, the two the first reading could not do
(`battery_min_soc`, `battery_reserved_soc_for_backup`) included.

- [13074](../entities/register-13074.md): the held 10000 W written back and accepted, **stored as handed**.
- **Forced discharge did as it was told**: 1251 W for 1250 W.
- **Export limit at 1250 W: 7641.5 W before, 1162 W during (MAD 15 W), 6117 W after.** "Could not tell",
  because the after-window drifted by 1524 W; the fall to the commanded figure is in the record. That
  export came from PV, of both inverters: the host's own PV was about 6.2 kW.
- Upper bounds: 13059 refuses 51 % and 13058 refuses 101 %, exception 0x04; 33047, 33048, 13052, 33149
  and 33150 store a value above their maximum, as on 2026-11-17.
- EMS modes 2, 3 and 4 taken; the write paths each took their own words.
- Not checked: forced charge, charge window, charge ceiling and
  [32998](../entities/register-32998.md) (battery too full); restart not asked for.

## A host's load power leaves the slave out

At the run's start (its `readings_changed`, in the [car-charging document](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4-summary.md))
[13007's load power](../entities/installation-swo14.md) read **-1650 W**, with 2926 W of AC power and
4600 W of export: AC minus export is -1674 W. The slave was making 2450 W
([its own](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-2-summary.md)), and -1650 + 2450 = 800 W is a plausible house. So **load power on
the host is its own output minus export, and the slave's output is missing from it**.
