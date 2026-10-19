Todo.md contains only next steps (forward looking).
Anything done should be removed here.


# Open

1. **A charging car at gerd's.** Settles what input 21313 does over a session
   (does it go to 0 when charging stops?) and whether 21308/21310 are signed.
   Two dongle runs about five minutes apart, 90 s of quiet before each, while
   the car charges. `doc/wallbox_registers.md` has both questions.

# Next steps

## Integration

- [ ] Have the integration's own fingerprint carry `export_scale` once its
      entity has probed. Entry data holds only the factor, not the write
      that measured it.
- [ ] Grant `Capability.SUNGROW_BATTERY` when an SBR pack is found. No probe
      grants it, so the datasheet rung of `battery_ceiling` never fires
      (`number.py`, `control_test._battery_ceiling`, `config_flow.py`) and
      the bounds fall back to BMS current x voltage. Granting it changes
      write bounds.
- [ ] `ControlTestButton.async_press` (`survey_entities.py`) does not check
      `PERMISSION_CONTROL_TEST`; the `run_control_test` action does.
- [ ] `strings.json`: `config.step.user.description` and the options
      survey section say "four houses" / "nine readings"; there are more.
      Only the `entity` block is generated, so this text is edited by hand.
- [ ] `doc/preview-mirror/sync.yml` (change it here and in the mirror
      together): its README says "Options -> Help this project", now
      "Contribute a capability survey", and links `installing_a_preview.md`
      as "Installing without HACS", which it is not.
- [ ] `release.yml` runs ruff and pytest only; add mypy, `make gen-check`
      and `check_pinned_library.py --wheel`.
- [ ] Confirm the wallbox serial prefix `A25A` (words `[16690, 13633]`) in
      `test_fingerprint_label.py`, `test_gui_fingerprint.py` and
      `test_survey_api.py` does not identify a unit; it is allowlisted in
      `test_no_real_serials.py` as the model prefix.

### Smaller

- [ ] `survey.async_read_retrying` retries refusals, so a refusal followed
      by a timeout ends as "no answer" in published probe states.
- [ ] `_measure_export_scale` leaves `left_changed` unset when
      `export_scale.async_probe`'s read-after-write fails.
- [ ] Unused: `fingerprint.async_build`'s `options` and `control_test`
      parameters, the `export_cap` arguments, `components.InverterReadings`,
      `FIRMWARE_BLOCK_IS_TEXT`, `probe.py`'s `_cmd_mdns_legacy`.
- [ ] `FaultWord.register` holds a protocol address; rename it `address`.
- [ ] Wrong folder named in `probe.py`'s `--save` help and in
      `sungrow_control_test.py`'s `_workspace()` docstring.
- [ ] `probe.py`'s schema-history comment stops at 20; `SCHEMA` is 22.
- [ ] `raw_client.py` does not check the transaction id.
- [ ] `tests/test_dump_reads.py` fakes refusals with a bare `ModbusError`;
      raise the real exception type.

## Wallbox

What is known -- both paths, the map of valid starts over TLS, what only the
direct path shows -- is in `doc/wallbox_registers.md`.

- [ ] Decode what only the direct path shows: input 21241-21250 (a second
      version string), 21267, 21332-21336, 21360, 21363-21365, and holding
      21250-21313 (register numbers). 21211-21214 stays masked until a
      second wallbox shows whether it identifies the unit.


# Future work

## EVCC connection

- [ ] Hand inverter and wallbox readings to evcc, e.g. over MQTT, so evcc
      need not open a Modbus session of its own. To find out: does evcc have
      a standard configuration for that?

## iHomeManager

Never measured; survey one (port 502 or 503, unit 247). The register map is
in `doc/cross_reference_modbus_manager.md`; Sungrow's protocol PDF:
https://github.com/TCzerny/ha-modbus-manager/blob/main/docs/Communication%20Protocol%20of%20iHomeManager_V1.0.2.pdf
