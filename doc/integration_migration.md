# Moving from the YAML package to the integration

The integration is meant to replace `modbus_sungrow.yaml`. Your recorder
history, your long-term statistics and every dashboard card are stored against
**entity IDs**, so the only thing that decides whether they survive the switch
is which IDs the new entities claim.

You are asked once, during setup, and either answer is a real answer:

| | Migrate my existing entities | Create new entities |
| --- | --- | --- |
| Entity IDs | `sensor.total_dc_power` | `sensor.sh10rt_total_dc_power` |
| Recorder history | continues, uninterrupted | old history stays under the old IDs |
| Energy dashboard | keeps its statistics | needs the new sensors selected |
| Your dashboards | keep working unchanged | need updating |
| Multiple inverters | one inverter only | works for any number |

If you have never used the YAML package, the question is not asked at all —
there is nothing to migrate, and you get new entities.

**Nothing is copied and nothing is deleted, in either direction.** The
integration registers its entities on the IDs the YAML package used; Home
Assistant's recorder then simply carries on writing to the rows that are
already there.

## Before you start

1. **Take a backup.** Settings → System → Backups. This is not because the
   migration is risky, but because it is the only way to undo a decision about
   years of data.
2. **Remove the YAML package.** Delete or rename `modbus_sungrow.yaml` (rename
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
3. **The old entities can stay in the registry, or not — either works.**
   After the restart they show as unavailable, and
   [cleanup_entities.md](../legacy/doc/cleanup_entities.md) tells you to delete
   them. If you leave them, the integration releases each entry as it takes the
   ID over. If you already deleted them, it asks the recorder instead, which
   still has the rows. Deleting them never touches your history — the recorder
   keys on the entity ID and knows nothing about the registry.

## Setting it up

Settings → Devices & Services → **Add integration** → *Sungrow Modbus*. Enter
the host, port and Modbus unit ID your `secrets.yaml` already has:

- `sungrow_modbus_host_ip` → Host
- `sungrow_modbus_port` → Port
- `sungrow_modbus_device_address` → Modbus unit ID

The model is detected from the inverter itself. If existing entities are
found, the next screen asks the question above and tells you how many.

## Afterwards

Check a long-running energy sensor — `sensor.total_pv_generation` is a good
one — and confirm its history graph still shows last year. You will see a
single one-pixel gap where the YAML package stopped and the integration
started. That gap is one recorded "unavailable" state; long-term statistics,
which is what the Energy dashboard reads, do not see it at all.

Things that do **not** follow the entity IDs automatically:

- **InfluxDB, and anything else writing to an external store.** Those keep
  their own copy keyed by entity ID, so a `Create new entities` migration
  splits the series there. See `scripts/influx_migration.py`.
- **Hand-built Lovelace cards that hard-code an entity ID**, if you chose new
  entities.

## What the entities look like now

Whichever answer you gave, the entities themselves are the same, and they
follow Home Assistant's conventions rather than the YAML package's:

- names are consistent — the YAML had `Battery min SoC` beside
  `Battery Min Soc`, and this does not;
- they are translated, so a German interface shows German names;
- raw register codes (`Running state raw` and friends), identity strings and
  nameplate values are grouped under **Diagnostic** on the device page rather
  than mixed in with the readings;
- entities your hardware does not have are **not created**. A two-tracker
  inverter gets no MPPT3 sensors, and a single-phase one gets no phase B or C
  — rather than a permanently unavailable entity you have to go and delete.

Migrating does not opt you out of any of that. Only the ID is inherited.

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
change them by accident, and an automation reset it after a few seconds. It
was never a device setting, so the integration does not provide it. If you
keep using that dashboard, create a helper to take its place:

*Settings → Devices & services → Helpers → Create helper → Toggle*, named
`Sungrow dashboard enable danger mode`. It will land on the same entity ID and
your dashboard and its reset automation keep working, provided you remove the
YAML package first so the ID is free.

The integration's own answer to the same worry is different and does not need
a switch. Home Assistant decides who may change a setting, by account: a
read-only account under *Settings → People* sees every reading and can change
nothing at all, which is a stronger guard than a toggle on a dashboard and
cannot be un-toggled by the person browsing. Start and stop are further behind
the Permissions option above.

## Changing your mind

Both directions work, because a rename moves the recorder's row rather than
copying it. Migrating back returns the history to where it came from, and
nothing is lost on the way.

> **Not built yet.** The options-flow control that switches an already-created
> entry between the two styles is still open work — see
> [integration_plan.md](integration_plan.md). Until it lands, changing your
> mind means removing the config entry and adding it again, which is safe:
> removing an entry does not remove recorded history.
