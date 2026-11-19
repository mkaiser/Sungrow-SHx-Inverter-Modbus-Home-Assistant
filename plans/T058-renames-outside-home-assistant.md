# T058 - Renames and the databases outside Home Assistant

The stores that do not follow the recorder -- InfluxDB and with it Grafana,
Prometheus, MQTT statestream, Node-RED -- get the print-only script
(`scripts/helpers/influx_migration.py`) and a guide a user follows or hands
to an AI assistant (`doc/influx_migration_llm_guide.md`, linked from
`doc/integration_migration.md`). There is no built-in path: the integration
cannot reach the user's InfluxDB, and versions, measurement settings and
downsampling differ per installation. The legacy-id adoption keeps ids, so
most users need neither.

Open: what the integration should do when an id does change (a repair naming
the affected entities and linking the guide; an export of old and new ids),
how a rename after release is announced, and whether a real InfluxDB with
migrated data is worth testing once the production copy exists (Release item
4). The guide has never run against a real InfluxDB.
