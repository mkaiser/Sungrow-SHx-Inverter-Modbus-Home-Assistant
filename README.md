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
> package, evolved over five years, in use by thousands of people, and the only thing
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
- **Writes.** The state-of-charge limits, the charge and discharge maxima, the
  export power limit, the three mode flags and the three selects. Starting and
  stopping the inverter are **actions** rather than buttons, deliberately:
  Home Assistant has no confirmation dialog for a button press.
- **The SBR battery as its own device** — all forty registers, seventeen
  entities. Which Modbus unit it answers on is worked out rather than asked,
  because it moves with the transport.
- **The wallbox as its own device** — AC011E-01 / AC22E-01, twenty-one
  entities, read-only. Found by asking the inverter's endpoint, since a
  wallbox has no Modbus endpoint of its own even with its own LAN cable.
- Setup through the UI: search the network for inverters, or type an address.
  The model, the Modbus unit id and a cluster slave's role are detected from
  the devices themselves; where two inverters need telling apart you are asked
  what to call them, once.
- Entities are created **only where the hardware has them** — a two-tracker
  inverter gets no MPPT3 sensors, a single-phase one gets no phase B or C.
- A migration that keeps your entity IDs, so history and dashboards continue.
  You are asked at setup; either answer works. See
  [doc/integration_migration.md](doc/integration_migration.md).
- Diagnostics you can download and attach to a bug report.
- One naming convention, enforced by a test.
- **A one-command survey** you can run against your own installation, which is
  how the capability model gets its evidence — see
  [contributing a fingerprint](doc/device-fingerprints/README.md#contributing-one).
  It reads and never writes.

**Not there yet:**

- **A release, and a HACS install.** `v0.1.0a1` is tagged but nothing is
  published yet, and HACS needs more than a release: it resolves a repository
  to the latest **stable** release or else to the **default branch**, and this
  one's default branch is `main`, which has no `custom_components/`. So HACS
  cannot install this branch until the integration reaches `main` or a stable
  release exists — see [doc/integration_plan.md](doc/integration_plan.md#what-is-next).
  Copying `custom_components/sungrow_modbus/` into your own `config/` works
  today and needs no HACS. The first releases are **preview** releases,
  labelled as such in the version, the integration's name and a repair
  notice.
- The **iHomeManager** and the **Sungrow Logger**. Both are documented by
  Sungrow and neither has ever been measured by this project — if you have
  one, [doc/device-fingerprints/devices-wanted.md](doc/device-fingerprints/devices-wanted.md)
  says what would help.
- **SBH** batteries, which need a register document nobody has, and the SBR's
  per-module cell entities, which need one more pack size measured before the
  module count can be trusted.
- Writing to the wallbox. Its registers are undocumented by Sungrow and known
  from three independent measurements, which is not a basis for starting
  somebody's car charging from an automation.

## What it can do that the YAML package cannot

Not a list of everything — a list of the things that are *only* possible
because it is an integration.

- **One shared connection per inverter.** Everything pointed at the same
  host and port serialises behind one socket. A Sungrow accepts very few
  Modbus sessions, so this is what removes the external Modbus proxy that
  wallbox and iHomeManager users are told to run today.
- **Entities exist only where the hardware has them.** A two-tracker inverter
  gets no MPPT3 sensors and a single-phase one gets no phase B or C, decided
  from what the device answers rather than from a comment in a YAML file.
- **Per-user access control.** Home Assistant enforces permissions per entity,
  so a household member in the read-only group sees every reading and can
  change nothing. And **starting or stopping the inverter is an action rather
  than a button**, so who may do it is yours to choose — administrators only
  by default, or anyone who can already control the inverter, per inverter. A
  YAML button can be pressed by any normal user from any dashboard, and has no
  confirmation. The ladder is [asserted in
  tests](tests/test_permissions.py), not just described.
- **Configurable poll intervals**, per group, from 5 seconds to never. The
  scarce resource is connections, not bandwidth, so being able to stop reading
  data nobody looks at is the cheapest fix for the dropouts people report.
- **Write, then read back, at once.** The YAML needs a `template number`, a
  `modbus.write_register` action *and* a `homeassistant.update_entity` call to
  show what the inverter actually accepted. One entity does all of it.
- **Diagnostics you can attach to a bug report** — model, which capabilities
  the inverter confirmed, which registers reported themselves unavailable, why
  any entity was not created. Serial number and host removed.
- **Setup without knowing your inverter's IP.** It searches the network, and
  identifies devices by what answers rather than by unit id.
- **Migration that keeps your history.** You are asked at setup; either answer
  works, and it is reversible.

[doc/architecture.md](doc/architecture.md) sketches how the pieces fit
together — the integration, the device library, and which layer owns the
connection. [doc/integration_plan.md](doc/integration_plan.md) is the plan of
record and says what is decided, what is open, and why.
[doc/compatibility.md](doc/compatibility.md) says which setups anybody has
actually tested.

## Trying it

Nothing here needs an inverter — there is a simulator.

```bash
scripts/setup.sh       # devcontainer does this for you
scripts/simulate.sh &  # a fake SH10RT on :5020
scripts/develop.sh     # Home Assistant on :8123
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

**A diagnostics download answers most of the first round of questions on a bug
report**, so attach one. It carries no serial number, no host address and no
timestamp, which is why it can go straight into a public issue.

**Reporting a setup that works is worth as much as reporting one that does
not.** Which parts of the register map a device answers varies by model, phase
count, wiring, transport and firmware, and Sungrow's specification says what
*exists*, not what your machine does with it — so the capability model is
built from fingerprints off real hardware. If your model is listed as
untested in [doc/compatibility.md](doc/compatibility.md), a compatibility
report is the single most useful thing you can contribute — including one that
says everything works.

**No GitHub account needed.** [Discord](https://discord.gg/ZvYBejFkm2) is the
shortest route: drop the diagnostics file in and say what your setup is. If you
do have an account, the
[compatibility report form](../../issues/new?template=compatibility_report.yml)
asks the questions that turn out to matter, so nothing has to be asked
afterwards.

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
