# Moving InfluxDB series to new entity ids: a guide for an AI assistant

This page is written for an AI assistant (Claude, ChatGPT, a local model)
that a user has asked to carry their InfluxDB data across an entity id
change. A user can hand it over as is: *"Read this guide and help me move my
InfluxDB data."* It is also a checklist a person can follow by hand.

The integration does not do this itself, on purpose. It cannot reach the
user's InfluxDB, and should not be able to. The work depends on details only
the user's own installation has: InfluxDB 1.x or 2.x, the measurement
settings, retention policies, downsampling tasks. A write that goes wrong
mixes up the user's history and cannot be undone. A guided session, in which
every write is shown first and confirmed, is the safer tool.

## Ground rules

1. **Find out first whether anything needs moving.** By default the
   integration adopts the YAML package's entity ids
   ([integration_migration.md](integration_migration.md)), so InfluxDB keeps
   writing to the same series and nothing needs doing. Only a user who chose
   device-scoped ids, or renamed entities, has split series.
2. **Offer the free fix first.** A Grafana regex that matches both ids, for
   example `/^(total_dc_power|sh10rt_total_pv_input_power)$/`, joins the two
   halves in every panel without touching data. Many users stop there.
3. **Read before writing.** Every step before the copy is a read-only query.
4. **A backup comes first**: `influx backup` (2.x) or
   `influxd backup -portable` (1.x). Ask the user to confirm it exists.
5. **Copy, never move.** Write the old points under the new id and leave the
   old series in place. Never delete anything unless the user asks for it
   later, separately, after looking at their dashboards.
6. **Show every write before running it, and get a yes for each batch.**
   Start with one entity, check it, then do the rest.
7. **Credentials stay with the user.** Ask them to put the token or password
   in an environment variable. Never echo it, write it to a file, or paste it
   into a query you show.

## Step 1: how the user's InfluxDB stores Home Assistant

Read the `influxdb:` section of the user's `configuration.yaml`, or the
InfluxDB integration's options in the UI, and note:

| Setting | Why it matters |
| --- | --- |
| `api_version` (1 or 2), host, `database` / `bucket` | Which query language and client to use. The defaults are `home_assistant` (1.x) and `Home Assistant` (2.x), not `homeassistant` |
| `measurement_attr`, `override_measurement`, `default_measurement` | The **measurement** a point lands in. By default it is the entity's unit (`W`, `kWh`, `%`); an entity without a unit falls back to `default_measurement`, or else to the entity id |
| `tags`, `tags_attributes` | Extra tags that are part of every series key and must be copied unchanged |
| `include` / `exclude` | Whether the new ids are recorded at all |

On every point Home Assistant writes the tags `entity_id` and `domain`. The
`entity_id` tag holds the **object id** only, without the domain:
`total_dc_power`, not `sensor.total_dc_power`. A numeric state goes in the
field `value`, a text state in `state`, and attributes become further fields.

Check this against the data instead of assuming it:

```sql
-- 1.x
SHOW MEASUREMENTS
SHOW TAG VALUES FROM "W" WITH KEY = "entity_id" WHERE "entity_id" =~ /total_dc_power/
```

```flux
// 2.x
import "influxdata/influxdb/schema"
schema.tagValues(bucket: "Home Assistant", tag: "entity_id",
                 predicate: (r) => r.entity_id =~ /total_dc_power/, start: 0)
```

## Step 2: the pairs of old and new ids

Ask the user for the pairs from their own Home Assistant, which is the only
reliable source: a renamed entity has the name the user gave it, not a
generated one. Two ways to get them:

- **This repository's helper** prints every pair the integration produces,
  given the device's name *exactly as Home Assistant shows it*. The new ids'
  prefix is slugified from that name, so "Garage SH10RT" gives
  `garage_sh10rt_…`:

  ```bash
  python scripts/helpers/influx_migration.py --device "SH10RT" --format table
  ```

- **The user's entity list** (Settings → Entities, filtered by the
  integration) for the ids that exist now.

Keep only the pairs where **both** ids appear in InfluxDB. For each pair,
query the old id's last point and the new id's first point. The old series
should end where the new one starts, at the migration. If they overlap, stop
and ask: two sources wrote at once, and copying would mix them up.

**Check the measurement too.** If an entity's unit changed, its points move
to another measurement as well as to another id. For the integration this
applies to one entity: *Daily consumed energy (filtered)* had no unit in the
YAML package and has `kWh` now. Copy such a series into the new measurement.

## Step 3: what to copy

For each pair, copy every point of the old series that is **older than the
new series' first point**, into the new id, the measurement it now uses, the
same fields and the same other tags. Copying only up to that cut-off
matters: InfluxDB merges points that share a measurement, tag set and
timestamp, so an overlapping copy would overwrite real points in the new
series.

Count the points to copy, per pair, and show the user the table before
writing anything:

```sql
-- 1.x
SELECT COUNT("value") FROM "W" WHERE "entity_id" = 'total_dc_power' AND time < '<first new point>'
```

```flux
// 2.x
from(bucket: "Home Assistant")
  |> range(start: 0, stop: <first new point>)
  |> filter(fn: (r) => r.entity_id == "total_dc_power")
  |> count()
```

## Step 4: the copy

**InfluxDB 2.x**: one Flux query per pair, in the Data Explorer or with
`influx query`. If `range(start: 0)` times out, split it by year or month:

```flux
from(bucket: "Home Assistant")
  |> range(start: 0, stop: <first new point>)
  |> filter(fn: (r) => r.entity_id == "total_dc_power")
  |> set(key: "entity_id", value: "sh10rt_total_pv_input_power")
  |> to(bucket: "Home Assistant")
```

`scripts/helpers/influx_migration.py --format flux --bucket "<bucket>"`
prints this for every pair. Add the `stop:` yourself.

**InfluxDB 1.x**: InfluxQL cannot rewrite a tag value, because the tag is
part of the series key and `SELECT … INTO` keeps it. There are two routes:

- A short script with the `influxdb` Python client that reads the old series
  in chunks of a month and writes each point back with the new `entity_id`.
  It works the same on every installation, and each chunk can be checked.
- The export, rewrite and import route the helper prints
  (`--format influxql`): `influx_inspect export`, a `sed` per pair on the
  line protocol, import into a **new** database. Use it for very large
  series. It needs shell access to the InfluxDB host.

Whichever route: one entity first, the counts compared (Step 3's count must
now also be found under the new id), a Grafana panel spanning the migration
looked at together with the user, and only then the rest.

## Step 5: what else keys on the id

- **Downsampling**: InfluxDB 2.x tasks and 1.x continuous queries that filter
  on `entity_id` write future points under the old id, or none. Show them to
  the user, and copy the downsampled buckets the same way if they hold
  history.
- **Grafana**: panels and alerts that name an old id. After a copy, the new
  id alone shows the full history.
- **Retention**: copied points keep their timestamps, so a retention policy
  deletes them on the same schedule as the originals.

## Step 6: the old series

Leave the old series in place. It costs disk space and nothing else. If the
user later asks to delete it, do it only after they confirm that Grafana
shows the copied history, and only for the ids and time range copied:
`influx delete --predicate 'entity_id="total_dc_power"'` (2.x) or
`DELETE FROM "W" WHERE "entity_id" = 'total_dc_power'` (1.x).

## Other stores

- **Prometheus** cannot rewrite history. Use a recording rule, or a query
  that combines both names, such as `label_replace`.
- **MQTT statestream and Node-RED** hold no history. Update the topics and
  flows that name the old ids.
