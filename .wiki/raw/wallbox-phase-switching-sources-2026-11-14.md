# Phase switching on a Sungrow AC wallbox: what the documents and others say, read 2026-11-14

Read to answer one question: can the phases of an AC22E-01 or AC011E-01 that a Sungrow hybrid
inverter manages be chosen by hand, and if not, when does the system switch them? The downloads
stay in the maintainer's gitignored `tmp/wallbox-sources/`; this note keeps what they say about
the question, with where each one is. Quotes are short; the rest is paraphrase.

## 1. Sungrow's documents

| Document | Where | What it says about phases and modes |
| --- | --- | --- |
| AC22E-01 datasheet, Version 6 (file dated 2025-07-22) | info-support.sungrowpower.com/application/pdf/2025/08/04/DS_20250722_AC22E-01_Datasheet_V6_EN.pdf | "Automatic phase switching: Yes". 22 kW or 11 kW at three phase (configurable), 7.4 kW at a single-phase connection. Footnote on the charging modes: "Only available with Sungrow SHRT hybrid inverter in direct connection. For Sungrow SHT hybrid inverter and other Sungrow inverters, the Sungrow iHomeManager is required." |
| AC22E-01 user manual, AC22E-01-UEN-Ver18-202509 (53 pages) | info-support.sungrowpower.com/product-materials/77d88c6d-f17c-427f-a94e-8a63b4041eef.pdf | Technical data: automatic phase switching yes; charging mode "OCPP / EMS by iEnergyCharge" and "Eco charging / Fast Charging / Scheduled charging / Customized charging by iSolarCloud". In EMS mode it is commissioned in iSolarCloud and, without an iHomeManager, must be on the inverter's RS485; with one, on WLAN or LAN. iEnergyCharge is needed "only if the charger is used standalone". **No phase setting, no condition for the switch, no register table.** |
| SH5.0-10RT / -20 user manual, Ver24-202503 (134 pages) | info-support.sungrowpower.com/application/pdf/2025/07/17/SHRT%20User%20Manual.pdf | §3.5: supported chargers AC011E-01 from firmware V1.2.469, AC22E-01 from LE-01.1E1.001.101.32. §6.10: the charger's RS485 A/B to the inverter's A1/B1. A charger on one hybrid of several is not supported. **Nothing on charging modes or phases.** |
| iSolarCloud user manual, iSolarCloud-V146-UCN-Ver28-202610 (223 pages) | info-support.sungrowpower.com/cms/af994f1d-bb0d-408a-b310-6ad732402c99/... (the long name ends `_compressed.pdf`) | Charger settings (European server): Plug&Play, charging mode for all chargers of the plant: **ECO** (with *Energy purchase* on/off and *Battery discharge cut-off SOC*), **Fast charging**, **Scheduled charging**, **Customized** (by time with current or power, or by tariff threshold); control strategy across up to 3 chargers; mileage per kWh. Logger settings: in *ECO & economic*, "if the surplus falls below the charger's minimum charging power, the system will either ensure the minimum charging power for the charger or stop charging, depending on whether drawing power from the grid is allowed". **No phase setting anywhere in it.** |
| Sungrow EV Power Guide (2023, AC011E-01 and SH-RT) | cleanpowersweden.com/wp-content/uploads/2023/05/EN_Sungrow_EV_PowerGuide-1.pdf | Green Power mode: "If PV surplus falls below the minimum charging power of 4.14 kW, power is provided from the grid and/or battery storage." Customized mode 6-16 A, 4.14 kW at 6 A to 11 kW at 16 A. A PHEV limited to 3.7 kW: "the Sungrow Wallbox AC011E-01 charges with single phase". **No one-phase surplus charging for the AC011E-01 here.** |
| iHomeManager manual (ManualsLib 3715764) | manualslib.com/manual/3715764/Sungrow-Ihomemanager.html | **Not read**: ManualsLib answered with a bot check. Its 1.38-4.14 kW single-phase rule is known only from a web search's summary (`plans/wallbox_tests.md`). |

## 2. TCzerny/ha-modbus-manager's wallbox pages (main, read 2026-11-14)

`docs/README_sungrow_ac011e_wallbox.md` and `docs/README_sungrow_wallbox_connection.md`, at
github.com/TCzerny/ha-modbus-manager. Register numbers below are this repository's; that project
writes protocol addresses, one lower.

- Its AC011E template (AC007-00, AC011E-01, AC22E-01) offers a **Phase Mode** select (three /
  single) on the wallbox's own 21204, a **Working Mode** select (Network, Plug and Play, EMS) and a
  *Phase Switching Status* sensor; it is based on Louisbertelsmann's project.
- The inverter's own LAN port shows only the inverter's mirror of the charger (its 33540-33550
  block), never the wallbox's 21xxx; those come through a WiNet-S's forwarding (unit 2 or 3) or at
  the wallbox's own address over TLS on 516, unit 248. With an iHomeManager the iHomeManager holds
  516 and is polled instead.
- The iHomeManager's map has **no phase word**: "Not on iHM (charger `21xxx` only): setpoint
  current, phase switch, remote start/stop".
- "Set working mode to **EMS** for Modbus/EMS control." Whether a write to the wallbox's 21xxx
  collides with the inverter's management "is **not settled**. Prefer read-only first."
- SH-T and larger hybrids with an AC22E-01 need an iHomeManager; RS485 to an SH-T is unsupported.

## 3. Photovoltaikforum, "SUNGROW Sammelthread Ladestation AC22E-01" (thread 206089)

88 pages, 873 posts, 2023-06-19 to 2026-11-14, read in full as text; 55 mention phases. Each
post at `https://www.photovoltaikforum.com/thread/206089-sungrow-sammelthread-ladestation-ac22e-01/?postID=<id>#post<id>`.
Owners' reports, not measurements.

| Post | Date | Setup | Report |
| --- | --- | --- | --- |
| 3225674 | 2023-06-19 | Sungrow's product team | The AC22E-01 announced with automatic 1/3-phase switching. |
| 4398552 | 2025-07-27 | AC22E-01 | Charged three phase but no longer single phase on LE-01.1E1.001.101.38; after 001.901.12 three phase only at 4 kW. |
| 4454227 | 2025-09-10 | SH10RT-20, AC22E-01 MID | "Dynamic phase switching" does not work: three phase from 4.3 kW or nothing; Sungrow support could not help. |
| 4455869 | 2025-09-11 | the same | Has installer access to wallbox and inverter, asks how to activate phase switching. |
| 4583196 | 2025-12-27 | AC22E-01 | Asks whether automatic phase switching in PV surplus can be turned off: a Renault ZOE fails without a simulated unplug. |
| 4583263 | 2025-12-27 | AC011E-01 | On the AC011E-01 the 1/3-phase switch is available only over Modbus RTU (not OCPP). |
| 4754686-4755583 | 2026-05-11/12 | inverter, no iHomeManager, AC22E-01 | Stayed single phase in every mode; cause was a car with one phase. With an iHomeManager an installer finds *System parameters, item 4: charger power supply, 1 or 3 phase* (4754737); **without one that item is not there** (4755326, 4755356); the wallbox's own app had three phase set. |
| 4756920 | 2026-05-13 | SH10RT, SBR128, AC22E-01 | In PV surplus at about 3 kW of PV the charge never fell below 4 kW and the battery emptied. |
| 4766620 | 2026-05-23 | AC22E-01 on LAN, 4.5+4.5 kWp | Surplus without grid: single phase only, even at 5.5 kW of PV; with grid: three phase, but only 4.1 kW. |
| 4784646 | 2026-06-09 | — | Automatic phase switching does not work over OCPP. |
| 4791286 | 2026-06-16 | installer, customers' AC22E-01 | One customer's stays at 1.4 kW in surplus only; another, 5+5 kWp, at most 3.4 kW single phase. |
| 4867251 | 2026-09-02 | AC22E-01 | 2.4 kW surplus: interrupted (household limit, delay, low ESS SoC); with grid allowed, 4.1 kW at 6 A on three phases; nothing to set as owner or installer. |
| 4889688 | 2026-09-28 | AC22E-01, iHomeManager | PV surplus **with** grid purchase: always three phase, at least 4 kW, empties the house battery. **Without**: switches between one and three phases, which trips his breaker. |
| 4894024 | 2026-10-02 | the same | Scheduled charging also switches between one and three phase. |
| 4897792 | 2026-10-06 | the same | No local access to the wallbox since it was set to EMS; everything through iSolarCloud. |
| 4901132 | 2026-10-10 | the same | With full installer rights: **automatic phase switching cannot be disabled**. |
| 4901435 | 2026-10-10 | the same | The breaker tripped at a phase change while set to 22 kW; the installer set 11 kW in iEnergyCharge, with an installer account only. |
| 4935414 | 2026-11-13 | the same | "Why must it charge three phase with grid purchase, while without it goes single phase?" |

## 4. What follows, for a wallbox an inverter manages

- No Sungrow document names a setting to choose the phases; the switch is automatic.
- By the owners' reports the switch to one phase happens in **PV surplus (ECO) with energy purchase
  off** (and in scheduled charging); with energy purchase on, or in fast charging, the charge stays
  at three phase and at least 4.1 kW. Several owners with an SH-RT report it never switching.
- With an iHomeManager an installer parameter chooses 1 or 3 phase supply; without one there is
  none.
- Choosing the phases by hand is documented only on the wallbox's own 21204, for a wallbox nobody
  else manages (evcc, ha-modbus-manager).
