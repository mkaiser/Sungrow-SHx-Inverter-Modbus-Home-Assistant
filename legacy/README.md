# The YAML package

This is `modbus_sungrow.yaml` and everything that belongs to it: five years of
development, in use by thousands of people, and the only part of this project
that is finished.

**It is not deprecated and it is not going anywhere** until the integration in
[`custom_components/`](../custom_components/) reaches parity with it. Nothing
about your installation changes today.

## Why it is in a folder here

Only on the `proper-ha-integration` branch. On [`main`](../../../tree/main) —
which is where users should get it — it sits at the repository root, exactly
where every installation instruction, forum post and issue says it does.

This branch is becoming an integration repository, so the YAML track was moved
aside to stop the two competing for the root directory. The move is scoped to
this branch on purpose: renaming the file that thousands of people download
would break every link that points at it, and that is a decision for the day
the integration is actually ready to replace it.

## What is here

| | |
| --- | --- |
| `modbus_sungrow.yaml` | The package itself. **Edit this one.** |
| `modbus_sungrow_multiple_inverters_{1,2,3}.yaml` | Generated from it by CI — do not hand-edit |
| `secrets.yaml` | The keys the package expects, with comments |
| `additional_sensors/` | SBR battery, multi-inverter aggregates |
| `dashboards/` | The default dashboard and the HACS card variants |
| `debug/` | Register poking and the generated sensor list |
| `doc/` | Installation, usage, FAQ, troubleshooting, migration |

## Start here

- [Installation / Configuration](doc/installation.md)
- [Migration from versions before 2026](doc/migration_guide.md)
- [Usage](doc/usage.md)
- [FAQ](doc/faq.md)
- [Help / Troubleshooting](doc/help.md)
- [Removing orphaned entities](doc/cleanup_entities.md)
- [Dashboard setup](doc/dashboard.md)
- [Changelog](doc/changelog.md)

## Moving to the integration

Not yet — it cannot write registers, so it does not replace this. When it can,
[doc/integration_migration.md](../doc/integration_migration.md) describes the
switch: it can take over your existing entity IDs, so history, statistics and
dashboards carry on.
