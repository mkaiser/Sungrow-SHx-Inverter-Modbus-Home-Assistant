# Sungrow Modbus — Home Assistant integration

[![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2)

> ## ⚠️ Preview. Do not use this branch on a system you care about.
>
> This is the `proper-ha-integration` branch: a rewrite of this project as a
> real Home Assistant integration, released only as previews (`0.1.0aN`).
> Registers can move, entity IDs can change, and nothing here promises
> backwards compatibility yet.
>
> **If you are a normal user, you want [`main`](../../tree/main)** — the YAML
> package, evolved over five years, in use by thousands of people, and the only thing
> that is finished.

## Trying it

Install it through **HACS** from the preview channel,
`Sungrow-SHx-Inverter-Modbus-Home-Assistant-preview`: HACS reads a
repository's default branch, and this one's is the YAML package.
[doc/installing_a_preview.md](doc/installing_a_preview.md) has the steps;
[doc/integration_options.md](doc/integration_options.md) lists every option
under *Configure*.

**The preview sets up diagnostics only**: it identifies the inverter and runs
the survey, and creates no sensors for the readings. Everything below is
built and tested, and switched on in a later release.

## What this is

A Home Assistant integration on the Modbus architecture of Home Assistant
2026.9, meant to **replace** the YAML package. The hard requirement is that
existing users keep their recorder history, long-term statistics and
dashboards when they switch ([doc/integration_migration.md](doc/integration_migration.md)).

**What it does:**

- All 135 read entities of the YAML package, held to it by tests, with the
  unit and state class of every entry they replace; created **only where the
  hardware has them**.
- **Writes**, each read back at once: the state-of-charge limits, charge and
  discharge maxima, the export power limit, three mode flags, three
  selects, and the forced-charging schedule (two windows as times, with a
  target SoC each). Start and stop are **actions**, with who may call them yours to
  choose (administrators by default).
- **The SBR battery** and **the wallbox** (AC011E-01 / AC22E-01, read-only)
  as devices of their own, behind a WiNet-S or, for the wallbox, at its own
  address over TLS.
- **One shared connection per inverter**, so no external Modbus proxy.
- Setup by **searching the network**; model, unit id and a cluster slave's
  role come from what the devices answer.
- **Configurable poll intervals**, per group, from 5 seconds to never.
- **A generator the Sungrow cannot see**: a non-Sungrow inverter behind the
  same meter, added back into the house load.
- **Diagnostics** to attach to a bug report, serial and host removed.
- **The survey**, which reads what your installation answers, and the
  **control test**, which writes each control, checks the inverter acted on
  it and puts everything back
  ([device-survey/README.md](device-survey/README.md)).

**Not yet:** the iHomeManager and the Sungrow Logger (never measured; see
[devices-wanted.md](device-survey/devices-wanted.md)), SBH batteries, the
SBR's per-module entities, and writing to the wallbox.

[doc/architecture.md](doc/architecture.md) is how it is built and why,
[Todo.md](Todo.md) what is open, and
[doc/compatibility.md](doc/compatibility.md) which setups have been surveyed.

## Developing

Nothing here needs an inverter — there is a simulator.

```bash
scripts/dev/setup.sh       # devcontainer does this for you
scripts/dev/simulate.sh &  # a fake SH10RT on :5020
scripts/dev/develop.sh     # Home Assistant on :8123
```

Or `make setup`, `make sim-bg`, `make dev`. `make` on its own lists every
shortcut, and `make check` runs everything CI gates on.

Then *Settings → Devices & Services → Add integration → Sungrow Modbus*, and
point it at `127.0.0.1:5020`, unit id `1`.

[doc/development.yaml](doc/development.yaml) is the copy-paste runbook:
commands, the dev login, talking to real hardware, and getting the web UI onto
your LAN. [doc/development.md](doc/development.md) explains why things are the
way they are.

## The YAML package

It lives in [legacy/](legacy/) on this branch, and at the repository root on
`main`, which is where users should get it.

- [Installation / Configuration](legacy/doc/installation.md)
- [Migration from versions before 2026](legacy/doc/migration_guide.md)
- [Usage](legacy/doc/usage.md) · [FAQ](legacy/doc/faq.md) ·
  [Help / Troubleshooting](legacy/doc/help.md)
- [Changelog](legacy/doc/changelog.md)

## Register documentation

The mapping follows Sungrow's *Communication Protocol of Residential and Small
Industrial Hybrid Inverter*, **V1.1.16**, available from Sungrow support. If you
have a newer version, say so in the [discussions](../../discussions).

## Help and contributions

- [GitHub discussions](../../discussions) for questions, or
  [Discord](https://discord.gg/ZvYBejFkm2).
- [GitHub issues](../../issues) for bugs; attach a **diagnostics download**,
  which carries no serial and no address.
- **A survey of your installation** is the most useful contribution, one that
  says everything works included: send it to
  [the survey issue](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786).

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

The wallbox registers are nobody's official document, and two projects worked
theirs out by measurement:

- **[Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant](https://github.com/Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant)**,
  used here with its author's permission. Its charging-status enum is the one
  thing a single session cannot yield: watching a car finish charging shows
  the status settle on `6`, and only that table says `6` is *Completed*
  rather than idle.
- **[KevinD987/sungrow-ac011e](https://github.com/KevinD987/sungrow-ac011e)**
  (MIT), which publishes its register map with confidence marks and says
  plainly that nothing in it is manufacturer-confirmed. Its VERIFIED entry
  for the control-pilot voltage turned a hypothesis here into a second,
  independent measurement — on a different model.

[`doc/wallbox_registers.md`](doc/wallbox_registers.md) compares all three,
register by register, and says which of them holds each line.
