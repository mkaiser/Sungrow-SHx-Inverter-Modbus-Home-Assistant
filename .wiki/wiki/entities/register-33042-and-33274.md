---
type: entity
title: Registers 33042 and 33274 (unread specification registers)
tags: [register, holding, specification, unread]
created: '2026-11-04'
---

# Registers 33042 and 33274 (unread specification registers)

Two holding registers in V1.1.16 that the integration does not read: 33042, the charge cutoff
voltage (wide range), and 33274, the load rated power. ha-modbus-manager carries both commented
out ([cross-reference](../sources/cross-reference-modbus-manager-summary.md)). The diagnosis's register dump reads both
(`src/sungrow_modbus/dump.py`).

## What the corpus shows

- **33042 reads 0xFFFF, the unavailable value, in all 42 inverter diagnoses whose dump has it**:
  SH6.0RS, SH10RS, SH10RT, SH10RT-20, SH6.0RT-V112, SH8.0RT-V112, SH10RT-V112, SH15T and SH20T, on
  P020, P022, P023, P059, P065, P068 and P071, cable and dongle alike
  (`device-diagnosis/results/inverter/`, `register_dump.holding`, protocol address 33041).
- **33274 reads 0 in all 19 diagnoses whose dump answered it**, the same spread of models
  (protocol address 33273). A zero is not evidence of a capability
  ([zero means absent](../concepts/zero-means-absent.md)).

So neither becomes an entity: one is absent on every machine measured, and the other carries
nothing. A diagnosis where either reads anything else reopens this.
