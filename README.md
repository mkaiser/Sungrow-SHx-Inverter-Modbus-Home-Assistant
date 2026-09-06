# Sungrow Modbus — Home Assistant integration

[![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2)

> ## ⚠️ Experimental. Do not use this branch on a system you care about.
>
> This is the `proper-ha-integration` branch: a rewrite of this project as a
> real Home Assistant integration. It is **unreleased, unversioned in any
> meaningful sense, and not on HACS.** Registers can move, entity IDs can
> change, and nothing here promises backwards compatibility yet.
>
> **If you are a normal user, you want [`main`](../../tree/main)** — the YAML
> package, five years old, in use by thousands of people, and the only thing
> that is finished.

## What this is

A Home Assistant integration built on the Modbus architecture that arrived in
Home Assistant 2026.9. It sets up through the UI, shares one serialized
connection per inverter, and keeps its register knowledge in a plain Python
library that tests without Home Assistant and without hardware.

It is intended to **replace** the YAML package rather than sit beside it, so
the hard requirement is that existing users keep their recorder history, their
long-term statistics and their dashboards when they switch.

## Where it has got to

**Works:**

- All 127 read entities of the YAML package, generated from it so they cannot
  drift, with the unit and state class of every entry they replace.
- Setup through the UI: search the network for inverters, or type an address.
  The model is detected from the device itself.
- Entities are created **only where the hardware has them** — a two-tracker
  inverter gets no MPPT3 sensors, a single-phase one gets no phase B or C.
- A migration that keeps your entity IDs, so history and dashboards continue.
  You are asked at setup; either answer works. See
  [doc/integration_migration.md](doc/integration_migration.md).
- Diagnostics you can download and attach to a bug report.
- One naming convention, enforced by a test.

**Not there yet:**

- **Writes.** Every `number`, `select`, `switch` and `button` the YAML package
  has. This integration is read-only today.
- Battery modules (SBR/SBH), the wallbox, the iHomeManager.
- A release. The library is not on PyPI, so a HACS install would fail.

[doc/integration_plan.md](doc/integration_plan.md) is the plan of record and
says what is decided, what is open, and why.

## Trying it

Nothing here needs an inverter — there is a simulator.

```bash
scripts/setup       # devcontainer does this for you
scripts/simulate &  # a fake SH10RT on :5020
scripts/develop     # Home Assistant on :8123
```

Then *Settings → Devices & Services → Add integration → Sungrow Modbus*, and
point it at `127.0.0.1:5020`, unit id `1`.

[doc/development.yaml](doc/development.yaml) is the copy-paste runbook:
commands, the dev login, talking to real hardware, and getting the web UI onto
your LAN. [doc/development.md](doc/development.md) explains why things are the
way they are.

## The YAML package

It lives in [legacy/](legacy/) on this branch, and at the repository root on
`main`, which is where users should get it. Nothing about it changes until
this integration reaches parity.

- [Installation / Configuration](legacy/doc/installation.md)
- [Migration from versions before 2026](legacy/doc/migration_guide.md)
- [Usage](legacy/doc/usage.md) · [FAQ](legacy/doc/faq.md) ·
  [Help / Troubleshooting](legacy/doc/help.md)
- [Changelog](legacy/doc/changelog.md)

## Register documentation

The mapping comes from Sungrow's official *Modbus communication protocol
specification*, available from Sungrow support and updated only sporadically.
If you have a newer version, say so in the
[discussions](../../discussions).

```
TI_20251119_Communication_Protocol_of_Residential_Hybrid_Inverter_V1.1.11_EN.pdf
TI_20230117_Communication.Protocol.of.Residential.and.Commerical.PV.Grid-connected.Inverter_V1.1.53_EN.pdf
```

## Help and contributions

- [GitHub discussions](../../discussions) for questions.
- [Discord](https://discord.gg/ZvYBejFkm2) — the lowest-threshold way to ask.
- [GitHub issues](../../issues) for bugs and pull requests.

A diagnostics download from the integration answers most of the first round of
questions on a bug report, so attach one if you have it.

## Related work

- **[HA Modbus Manager](https://github.com/TCzerny/ha-modbus-manager)**
- **[Sungrow Wallbox](https://github.com/Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant)**
- **[Sungrow Logger 1000a](https://github.com/RafAustralia/Sungrow-Logger1000a-Modbus)**
- **[Chint DTSU666 Modbus](https://github.com/RafAustralia/Chint-DTSU666-20-modbus/)**
- **[EVCC](https://github.com/Hoellenwesen/home-assistant-configurations)**
- Sungrow document collections
  [by bohdan-s](https://github.com/bohdan-s/Sungrow-Inverter) and
  [by Gnarfoz](https://github.com/Gnarfoz/Sungrow-Inverter)

## Acknowledgements

Five years of this project is the work of many people — everyone who filed a
register correction, tested a firmware, or answered a question in the
discussions. The YAML package's history is theirs.
