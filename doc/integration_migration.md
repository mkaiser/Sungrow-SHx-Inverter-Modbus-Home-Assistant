# Moving from the YAML package to the integration

> **Not in the preview releases yet.** The preview releases set an entry up
> for diagnostics only: it identifies the inverter and runs the survey, and
> creates no readings, so nothing described below happens and your YAML
> package keeps running untouched. This guide describes the ordinary setup,
> which comes in a later release.

The integration is meant to replace `modbus_sungrow.yaml`. Your recorder
history, your long-term statistics and every dashboard card are stored against
**entity IDs**, so the only thing that decides whether they survive the switch
is which IDs the new entities claim.

You are asked once, during setup, and either answer is a real answer:

| | Migrate my existing entities | Start fresh |
| --- | --- | --- |
| Entity IDs | `sensor.total_dc_power` | `sensor.sh10rt_total_dc_power` |
| Recorder history | continues, uninterrupted | old history stays under the old IDs |
| Energy dashboard | keeps its statistics | needs the new sensors selected |
| Your dashboards | keep working unchanged | need updating |
| Multiple inverters | each takes its own `inv <n>` IDs -- see below | works for any number |

If you have never used the YAML package, the question is not asked at all —
there is nothing to migrate, and you get new entities.

**Nothing is copied and nothing is deleted, in either direction.** The
integration registers its entities on the IDs the YAML package used; Home
Assistant's recorder then simply carries on writing to the rows that are
already there.

## Before you start

1. **Take a backup.** Settings → System → Backups. This is not because the
   migration is risky, but because it is the only way to undo a decision about
   years of data. A Home Assistant backup holds the recorder only when it is
   the default SQLite database. MariaDB, PostgreSQL and InfluxDB live outside
   it and need their own backup.
2. **Keep what you use from the package that is not an entity.** It carries
   seven scenes (`Zero Export Power`, `Battery Forced Charge`, ...) and three
   automations, and they go when the file goes. Copy the ones you use into
   your own configuration first. With the YAML package's IDs they work
   unchanged.
3. **Remove the YAML package.** Delete or rename `modbus_sungrow.yaml` (rename
   the extension to `.yaml.bak` — the deprecated `!include_dir_named`
   directive picks up anything ending in `.yaml`), then restart Home
   Assistant.

   This step is not optional for migrating. Home Assistant hands out an entity
   ID only if nothing else is using it, so while the YAML package is still
   loaded its entities still hold the IDs, and the integration would silently
   get `sensor.total_dc_power_2` instead.

   **You do not have to guess whether you got this right.** The setup dialog
   checks the running instance and tells you: either "The YAML package is not
   running, so its entity IDs are free to take over", or "The YAML package is
   still running", with how many of its entities are holding IDs. If it is
   still running, migrating is not offered as the default and is refused if
   you pick it.
4. **The old entities can stay in the registry, or not — either works.**
   After the restart they show as unavailable, and
   [cleanup_entities.md](../legacy/doc/cleanup_entities.md) tells you to delete
   them. If you leave them, the integration releases each entry as it takes the
   ID over. If you already deleted them, it asks the recorder instead, which
   still has the rows. Deleting them never touches your history — the recorder
   keys on the entity ID and knows nothing about the registry.

## Setting it up

Settings → Devices & Services → **Add integration** → *Sungrow Modbus* →
*Set up my inverter*. Either let it search your network, or choose *I know the
address* and enter what your `secrets.yaml` already has:

- `sungrow_modbus_host_ip` → IP address or hostname
- `sungrow_modbus_port` → Port
- `sungrow_modbus_device_address` → Device address

The model is detected from the inverter itself. If the search finds more than
one inverter, you are asked what to call this one, since that name goes into
every device-scoped ID. If existing entities are found, the next screen asks
the question above and tells you how many.

## More than one inverter

`modbus_sungrow_multiple_inverters_<n>.yaml` gives every entity of the
`n`th inverter ` inv <n>` in its name, so its IDs end in `_inv_<n>`. The
integration works out which slot each inverter was by **comparing serial
numbers**: each slot's `Sungrow inverter serial` sensor holds its inverter's
serial as its state, and the integration knows which serial it is talking to.
You are never asked which inverter was `inv 2`.

The comparison works best with the YAML package **running**, and migrating
needs it **removed**, so with more than one inverter the order is:

1. With the YAML package still running, add each inverter and choose
   **Start fresh**. Each entry finds and remembers its slot.
2. Remove the YAML package and restart.
3. On each entry, open the options and set **Entity IDs** to the YAML
   package's IDs (see [Changing your mind](#changing-your-mind)). Each
   inverter takes its own slot's IDs and continues its own history.

With the package already gone, the serial is still found in the recorder's
history, which keeps it for ten days unless you changed that. Where it is not
found either, setup says so and gives the inverter its own IDs, rather than
guessing and handing it another inverter's history. To fix that, put the YAML
package back for one restart, so the serial is recorded, remove it again,
restart, and switch **Entity IDs** in the options. A house that only ever
ran the plain `modbus_sungrow.yaml` has a single slot, and needs none of
this.

## Afterwards

Check a long-running energy sensor — `sensor.total_pv_generation` is a good
one — and confirm its history graph still shows last year. You will see a
single one-pixel gap where the YAML package stopped and the integration
started. That gap is one recorded "unavailable" state; long-term statistics,
which is what the Energy dashboard reads, do not see it at all.

Things that do **not** follow the entity IDs automatically:

- **InfluxDB, and anything else writing to an external store.** Those keep
  their own copy keyed by entity ID, so a move to device-scoped IDs splits the
  series there. See `scripts/helpers/influx_migration.py`.
- **Hand-built Lovelace cards that hard-code an entity ID**, if you chose
  device-scoped IDs.

## What the entities look like now

Whichever answer you gave, the entities themselves follow Home Assistant's
conventions rather than the YAML package's:

- names are consistent — the YAML had `Battery min SoC` beside
  `Battery Min Soc`, and this does not;
- names come from translation files, so they can be translated; only English
  ships so far;
- identity strings, nameplate values and raw register codes are grouped under
  **Diagnostic** on the device page rather than mixed in with the readings;
- entities your hardware does not have are **not created**. A two-tracker
  inverter gets no MPPT3 sensors, and a single-phase one gets no phase B or C
  — rather than a permanently unavailable entity you have to go and delete.

Migrating does not opt you out of any of that. Only the ID is inherited, with
one difference: the raw register codes (`Running state raw` and friends) exist
only with the YAML package's IDs, for the dashboards that read them. With
device-scoped IDs the decoded value stands in their place — a binary sensor
for an on/off mode, a ratio with its unit.

## Three entities that do not come across

Everything the YAML package reads or sets has a replacement on the same ID,
including the seven `(delay)` flags and `sensor.daily_consumed_energy_filtered`.
Three entities deliberately do not, and if your dashboard uses them the cards
will break. All three are the YAML working around things Home Assistant now
does properly.

| Was | Now |
| --- | --- |
| `button.start_inverter` | Action `sungrow_modbus.start_inverter` |
| `button.stop_inverter` | Action `sungrow_modbus.stop_inverter` |
| `switch.sungrow_dashboard_enable_danger_mode` | Nothing — see below |

**Start and stop became actions rather than buttons** because Home Assistant
has no confirmation dialog for a button press. A button would sit in every
dashboard picker and automation editor, and a misclick while scrolling on a
phone stops your inverter. An action has to be written into a script or called
from Developer Tools.

Who may call them is **yours to choose**, in *Options → Permissions* on the
integration: administrators only, which is the default, or anyone who can
already control the inverter. A read-only account never can, whichever you
pick, and neither setting affects automations and scripts — those act for the
household rather than for a person. A button could not have been restricted at
all.

If a script or automation of yours pressed those buttons, replace the
`button.press` with the action. The register written is the same one.

**The danger-mode switch was a guard for the YAML's own dashboard** — it
enabled the inverter and EMS controls so that browsing on a phone could not
change them by accident, and an automation reset it after a minute. It was
never a device setting, so the integration does not provide it. If you keep
using that dashboard, keep the guard: before removing the package, copy its
`Sungrow dashboard enable danger mode` template switch and the
`sungrow dashboard enable danger mode auto reset` automation into your own
configuration. The switch keeps its unique ID, so it keeps its entity ID and
the dashboard keeps working.

The integration's own answer to the same worry is different and does not need
a switch. Home Assistant decides who may change a setting, by account: a
read-only account under *Settings → People* sees every reading and can change
nothing at all, which is a stronger guard than a toggle on a dashboard and
cannot be un-toggled by the person browsing. Start and stop are further behind
the Permissions option above.

## Changing your mind

Open the integration's options and change **Entity IDs**. The next page says
how many entities move and where, before anything does; nothing is copied and
nothing is deleted, and the names, areas and settings you gave the entities
go with them.

- **To device-scoped IDs**, each entity is renamed and its history and
  statistics move with it.
- **To the YAML package's IDs**, an ID that still holds the package's old
  history continues that history, which is what choosing these IDs is for.
  What was recorded under the device-scoped ID stays under that ID. An ID
  with no old history simply takes the device-scoped history across.
- **Older history already sitting on a target ID** -- from an earlier move the
  other way -- is renamed aside to `<id>_archive` first, never merged and
  never deleted.

The YAML package must not be running when you move to its IDs: its live
entities hold them, and the options page says so rather than handing out
`_2` IDs. An entity whose ID you changed yourself is left where you put it.
Dashboards, automations and scripts are not rewritten, so check them after a
move.
