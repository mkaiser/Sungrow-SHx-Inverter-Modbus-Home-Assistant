"""A capability survey produced by the integration, not by a terminal.

The evidence in `doc/device-fingerprints/` is nine documents from four
houses, all of them the maintainer's or a friend's, because contributing one
meant running Python on a machine that can reach the inverter. This is the
same document, built by an integration that already has the connection.

Most of what is asserted here is about **not lying**. A document is published
and then reasoned from, sometimes months later by somebody who cannot go back
and check, so the interesting failures are the quiet ones: a real serial that
survived, a claim filed as a measurement, a refusal recorded as a timeout, or
a reading that says nothing was competing for the connection when Home
Assistant demonstrably was.
"""

from __future__ import annotations

import json
import re
from unittest.mock import patch

from modbus_connection import IllegalDataAddressError, ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_MODE,
    CONF_PUBLISH_ADDRESS,
    CONF_REPORTER,
    CONF_SURVEY_BATTERY,
    CONF_SURVEY_COMMENT,
    CONF_SURVEY_POLLERS,
    CONF_SURVEY_PROXY,
    CONF_SURVEY_TRANSPORT,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
)
from custom_components.sungrow_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.sungrow_modbus.fingerprint import _async_probes, async_build
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from sungrow_modbus import fingerprint as survey

from .conftest import SERIAL

HOST = "192.168.178.35"
ENTRY_DATA = {CONF_HOST: HOST, CONF_PORT: 502, CONF_UNIT_ID: 1}


async def _setup(
    hass: HomeAssistant,
    unit: MockModbusUnit,
    options: dict | None = None,
    mode: str = MODE_DEVICES,
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_MODE: mode},
        options=options or {},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


# -- what the document is ------------------------------------------------------


async def test_the_document_leads_with_what_it_is_and_who_said_what(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The same five leading keys the committed documents carry, in order.

    `user_inputs` first among the substantive sections is the whole point of
    the format: the boundary between what a device said and what a person
    claimed is structural, rather than something a reader has to know.
    """
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    assert list(document)[:5] == [
        "schema",
        "command_line",
        "read_on",
        "read_at_local",
        "user_inputs",
    ]
    assert document["schema"] == survey.SCHEMA


async def test_it_says_a_tool_made_it_rather_than_printing_a_command(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """`command_line` exists to repeat a reading, and this one cannot be.

    Printing a plausible invocation would invite somebody to run it and then
    wonder why the output differs -- a scan from a terminal is taken on an
    idle inverter and this one is not.
    """
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    assert document["command_line"].startswith(survey.COLLECTED_BY_INTEGRATION)
    assert "probe.py" not in document["command_line"]
    assert "collect.py" not in document["command_line"]


# -- what must never be in it --------------------------------------------------


async def test_the_serial_is_a_stand_in_and_the_real_one_is_nowhere(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The rule the whole format is built around, asserted over the text.

    Over the serialised document rather than the one field, because moving
    fields around is exactly the change that reintroduces a serial somewhere
    else -- it has reached `fields_read_individually` and a capability
    probe's raw words before now.
    """
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)
    text = json.dumps(document)

    assert SERIAL not in text
    stand_in = document["device"]["serial_anonymized_hashed"]
    assert stand_in == survey.stand_in(SERIAL)
    assert stand_in.startswith(survey.STAND_IN_PREFIX)
    # `anon-` cannot occur in a Sungrow serial, which is what makes the value
    # self-describing wherever somebody copies it to.
    assert not re.search(r"\bA[0-9A-Z]{10}\b", text)


async def test_the_address_is_withheld_unless_its_owner_agreed(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Asked for, never taken -- and a refusal is a complete document.

    The third octet is what separates one contributor's network from
    another's, which is why it is the half that gets asked about.
    """
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    assert document["ip_address_last_two_octets"] == "xxx.xxx"
    assert HOST not in json.dumps(document)
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", json.dumps(document))


async def test_the_address_tail_appears_once_permission_is_given(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """And then only the tail: two octets, never the whole address."""
    entry = await _setup(hass, sungrow_unit, {CONF_PUBLISH_ADDRESS: True})
    document = await async_build(hass, entry)

    assert document["ip_address_last_two_octets"] == "178.35"
    assert HOST not in json.dumps(document)


async def test_a_probe_that_names_a_serial_publishes_no_words(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The failure that actually happened, kept from happening again.

    A wallbox's serial reached a published document as the raw words
    `[16690, 13633]`, which decode to `A25A`. The state of a probe is what a
    capability needs; the value never was.
    """
    entry = await _setup(hass, sungrow_unit)
    device = next(iter(entry.runtime_data.coordinators.values())).device

    with patch.object(
        survey,
        "PROBES",
        (("wallbox serial", "input", 4989, 2, "model"),),
    ):
        probes = await _async_probes(device)

    assert probes["wallbox serial"]["state"] == "present"
    assert "values" not in probes["wallbox serial"]


# -- what an answer means ------------------------------------------------------


async def test_a_refusal_and_a_timeout_are_recorded_differently() -> None:
    """The distinction this project puts in `layout.py` decisions.

    An exception 0x02 is the device saying the register is not there. A
    timeout says only that nothing came back -- from this end a silent
    inverter and a tunnel that lost the answer look identical -- so it is
    evidence about the link and not about the register. Collapsing the two
    would put a guess into the layout table.
    """

    class Device:
        """Answers, refuses and times out, one probe each."""

        async def async_read_words(self, space, address, count):
            if address == 4999:
                return [0x0E00] * count
            if address == 5014:
                raise IllegalDataAddressError("no such register")
            raise ModbusTimeoutError("Response timeout after 10.0 seconds")

    with patch.object(
        survey,
        "PROBES",
        (
            ("device type code (5000)", "input", 4999, 1, "model"),
            ("MPPT3 voltage", "input", 5014, 1, "mppt"),
            ("meter phase A voltage (5741)", "input", 5740, 1, "meter"),
        ),
    ):
        probes = await _async_probes(Device())

    assert probes["device type code (5000)"]["state"] == "present"
    assert probes["MPPT3 voltage"]["state"] == "refused"
    assert probes["meter phase A voltage (5741)"]["state"] == "no answer"


async def test_the_unavailable_sentinel_is_not_a_reading(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """0xFFFF is the specification saying the measuring point is not there."""

    class Device:
        async def async_read_words(self, space, address, count):
            return [0xFFFF] * count

    with patch.object(survey, "PROBES", (("MPPT4 voltage", "input", 5114, 1, "mppt"),)):
        probes = await _async_probes(Device())

    assert probes["MPPT4 voltage"]["state"] == "unavailable"


async def test_every_curated_probe_is_attempted(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """All of them, with a state each.

    The labels are part of the published format -- `doc/compatibility.md` is
    keyed on them -- so a missing one silently unrelates this reading from
    every earlier one rather than showing up as an error.
    """
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    probes = document["capability_probes"]
    assert set(probes) == {label for label, *_ in survey.PROBES}
    known = {state.value for state in survey.State}
    assert all(entry["state"] in known for entry in probes.values())


async def test_the_transport_verdict_follows_the_6100_probe(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Register 6100 is the only reliable transport signal there is.

    Not latency: direct-LAN medians run 2.0-61.5 ms and WiNet medians
    24.3-48.3 across four houses, and one house's direct link is slower than
    its own dongle.
    """
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    answered = document["capability_probes"]["PV power of today (6100, direct-only)"][
        "state"
    ]
    module = document["connection"]["communication_module_firmware"]
    assert document["connection"]["verdict"] == survey.transport_verdict(
        answered_6100=answered == "present", module_named=bool(module)
    )
    assert document["connection"]["wifi_or_ethernet"] == survey.WIFI_OR_ETHERNET


# -- honesty about the circumstances -------------------------------------------


async def test_it_admits_home_assistant_was_polling_throughout(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Because it was, and a silent document would read as an idle machine.

    This project *discards* readings taken under contention -- four were
    thrown away for it -- so a document that did not say would be worth less
    than one that does, not more.
    """
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    contention = document["contention"]
    assert "Home Assistant" in contention["polled_by"]
    assert contention["components"] > 0
    assert contention["coordinators_paused"] is False
    assert "not run" in contention["block_read_test"]


async def test_the_contention_note_is_a_measurement_not_testimony(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """It is filed outside `user_inputs`, where the readings live.

    The integration knows what it was doing; nobody typed it. Putting it in
    the claims section would be the mirror image of the mistake the section
    exists to prevent.
    """
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    assert "contention" not in document["user_inputs"]
    assert "contention" in document


async def test_the_testimony_defaults_to_empty_rather_than_to_a_guess(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Empty means the question was not put, which is a real answer.

    Distinct from `unknown`, where it was put and the owner did not know --
    the format has kept those apart since schema 7 and collapsing them would
    turn silence into testimony.
    """
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    claims = document["user_inputs"]
    assert claims["reporter"] == "anonymous"
    assert claims["transport"] == ""
    assert claims["modbus_proxy"] == ""
    assert claims["battery"] == ""
    assert claims["other_pollers"] == ""


async def test_the_testimony_is_published_when_it_is_given(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """And the values are the format's own keys, not their labels.

    `doc/compatibility.md` groups readings by these keys, so a document
    storing the human wording would not be comparable with any other.
    """
    entry = await _setup(
        hass,
        sungrow_unit,
        {
            CONF_REPORTER: "somebody",
            CONF_SURVEY_TRANSPORT: "winet_lan",
            CONF_SURVEY_PROXY: "no",
            CONF_SURVEY_BATTERY: "SBR096",
            CONF_SURVEY_POLLERS: "nothing else",
            CONF_SURVEY_COMMENT: "a cluster of two",
        },
    )
    document = await async_build(hass, entry)

    assert document["user_inputs"] == {
        "reporter": "somebody",
        "comment": "a cluster of two",
        "battery": "SBR096",
        "transport": "winet_lan",
        "modbus_proxy": "no",
        "other_pollers": "nothing else",
    }
    assert document["user_inputs"]["transport"] in survey.TRANSPORT_CLAIMS
    assert document["user_inputs"]["modbus_proxy"] in survey.PROXY_CLAIMS


async def test_the_firmware_block_carries_all_five_names(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Named as the format names them, so two documents can be compared."""
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    assert set(document["firmware"]) == {name for name, *_ in survey.FIRMWARE_STRINGS}


# -- delivery ------------------------------------------------------------------


async def test_diagnostics_carries_the_document(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The delivery mechanism, which is a button that already exists."""
    entry = await _setup(hass, sungrow_unit)
    report = await async_get_config_entry_diagnostics(hass, entry)

    assert report["fingerprint"]["schema"] == survey.SCHEMA
    assert SERIAL not in json.dumps(report["fingerprint"])


async def test_diagnostics_survives_a_survey_that_raises(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Diagnostics is what you download when things are already broken.

    A survey that failed and took the whole report with it would remove the
    thing the user came for at exactly the moment they need it.
    """
    entry = await _setup(hass, sungrow_unit)

    with patch(
        "custom_components.sungrow_modbus.diagnostics.async_build",
        side_effect=RuntimeError("the link went away"),
    ):
        report = await async_get_config_entry_diagnostics(hass, entry)

    assert "the link went away" in report["fingerprint"]["error"]
    # The rest of the report is still there, which is the point.
    assert report["capabilities"]["resolved"]
    assert report["polling"]


ANSWERS = {
    CONF_REPORTER: "a contributor",
    CONF_SURVEY_TRANSPORT: "direct_lan",
    CONF_SURVEY_PROXY: "no",
    CONF_SURVEY_POLLERS: "",
    CONF_SURVEY_BATTERY: "",
    CONF_SURVEY_COMMENT: "",
    CONF_PUBLISH_ADDRESS: False,
}


async def _survey_form(hass: HomeAssistant, entry: MockConfigEntry) -> dict:
    """Open Options -> the survey page."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "survey"}
    )


async def _submit(hass: HomeAssistant, flow_id: str, answers: dict) -> dict:
    """Submit the answers and let the progress step finish."""
    result = await hass.config_entries.options.async_configure(flow_id, answers)
    # A progress step yields before its task is done; the flow is resumed by
    # Home Assistant when the task completes.
    while result["type"] is FlowResultType.SHOW_PROGRESS:
        await hass.async_block_till_done()
        result = await hass.config_entries.options.async_configure(flow_id)
    return result


async def test_the_options_step_records_the_testimony(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Reachable after setup, because a contributor decides to help later."""
    entry = await _setup(hass, sungrow_unit)
    form = await _survey_form(hass, entry)
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "survey"

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await _submit(hass, form["flow_id"], ANSWERS)
        # The result page, then the confirmation that ends the flow.
        assert result["step_id"] == "survey_result"
        await hass.config_entries.options.async_configure(form["flow_id"], {})
        await hass.async_block_till_done()

    assert entry.options[CONF_REPORTER] == "a contributor"
    assert entry.options[CONF_SURVEY_TRANSPORT] == "direct_lan"


async def test_submitting_the_form_actually_reads_the_inverter(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The gap this closed: a form that saved silently and did nothing.

    A contributor filled it in, submitted, and was shown nothing -- so they
    had no way to tell whether they had helped, and the honest answer was
    that nothing had happened yet. Asserted on the result rather than on a
    call: the page reports a probe count, and a count can only come from
    having read the inverter.
    """
    entry = await _setup(hass, sungrow_unit)
    form = await _survey_form(hass, entry)

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await _submit(hass, form["flow_id"], ANSWERS)

    found = result["description_placeholders"]["found"]
    assert f"**{len(survey.PROBES)} registers probed**" in found


async def test_the_result_page_says_what_to_do_with_the_file(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Where it is, and where to send it -- neither of which was said before.

    The file is behind a menu on a different page, which nobody would guess,
    and a reading nobody sends is worth nothing at all.
    """
    entry = await _setup(hass, sungrow_unit)
    form = await _survey_form(hass, entry)

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await _submit(hass, form["flow_id"], ANSWERS)

    placeholders = result["description_placeholders"]
    assert "issues/new?template=compatibility_report.yml" in placeholders["issue_url"]
    assert "discord.gg" in placeholders["discord_url"]
    # And what was actually found, so the page is a report rather than a
    # thank-you note.
    assert "registers probed" in placeholders["found"]
    assert "stand-in" in placeholders["found"]


async def test_the_result_survives_the_dialog_closing(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A config-flow page is gone the moment it is dismissed.

    What it says is needed afterwards -- the menu path to the download, and
    where to send it -- so the same thing waits under Notifications, carrying
    both links and the reassurance about the serial.
    """
    entry = await _setup(hass, sungrow_unit)
    form = await _survey_form(hass, entry)

    with (
        patch(
            "custom_components.sungrow_modbus.async_get_unit",
            return_value=sungrow_unit,
        ),
        patch(
            "homeassistant.components.persistent_notification.async_create"
        ) as notify,
    ):
        await _submit(hass, form["flow_id"], ANSWERS)
        await hass.config_entries.options.async_configure(form["flow_id"], {})
        await hass.async_block_till_done()

    assert notify.called
    message = notify.call_args.kwargs["message"]
    assert "Download diagnostics" in message
    assert "compatibility_report.yml" in message
    assert "discord.gg" in message
    assert "stand-in" in message


async def test_a_failed_reading_still_saves_the_answers(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """So that offering to help is never wasted effort.

    And the failure is shown rather than swallowed: a link that cannot
    complete 24 reads is a finding in its own right, and the most likely
    cause -- something else competing for one of the inverter's very few
    sessions -- is worth telling somebody about.
    """
    entry = await _setup(hass, sungrow_unit)
    form = await _survey_form(hass, entry)

    with patch(
        "custom_components.sungrow_modbus.config_flow.async_build",
        side_effect=RuntimeError("Response timeout after 10.0 seconds"),
    ):
        result = await _submit(hass, form["flow_id"], ANSWERS)

    assert result["step_id"] == "survey_failed"
    assert "timeout" in result["description_placeholders"]["error"]

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await hass.config_entries.options.async_configure(form["flow_id"], {})
        await hass.async_block_till_done()
    assert entry.options[CONF_REPORTER] == "a contributor"


async def test_the_step_says_what_has_already_been_measured(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """So nobody is asked a question the integration answered itself.

    Cable against dongle is settled by register 6100, 9 times out of 9. What
    the owner adds is the half no register reaches.
    """
    entry = await _setup(hass, sungrow_unit)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "survey"}
    )

    measured = result["description_placeholders"]["measured"]
    assert "SH10RT" in measured
    assert "not determinable" in measured or "no communication module" in measured


@pytest.mark.parametrize(
    "field", ["schema", "device", "firmware", "connection", "readings"]
)
async def test_the_sections_a_reader_needs_are_all_present(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, field: str
) -> None:
    """Each one answers a question the others cannot."""
    entry = await _setup(hass, sungrow_unit)
    document = await async_build(hass, entry)

    assert field in document


# -- the diagnostics-only entry ------------------------------------------------


async def test_the_flow_asks_what_the_entry_is_for_first(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Before anything about wiring, because it changes what else is asked."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {"setup_devices", "setup_diagnostics"}


async def test_a_diagnostics_entry_creates_no_entities(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The whole point: connected and identified, with nothing added.

    A contributor who wants to send a reading has not asked for 198 entities
    in their registry, and creating them would also make the entry a
    migration question in disguise.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    assert entry.state is ConfigEntryState.LOADED
    assert not [
        state
        for state in hass.states.async_all()
        if state.entity_id.endswith("_load_power")
    ]
    assert hass.states.get("sensor.sh10rt_total_dc_power") is None
    # But it is polling, which is what a survey needs.
    assert entry.runtime_data.coordinators


async def test_a_diagnostics_entry_still_produces_a_document(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Which is the only reason it exists.

    The diagnostics download hangs off the config entry rather than off any
    entity, so having none costs nothing here.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)
    report = await async_get_config_entry_diagnostics(hass, entry)

    assert report["fingerprint"]["schema"] == survey.SCHEMA
    assert report["fingerprint"]["capability_probes"]


async def test_a_diagnostics_entry_is_offered_a_way_to_become_a_full_one(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Otherwise it is a dead end, and the menu says so first.

    It is also where the entity-ids question finally gets put -- the one
    decision the diagnostics path skipped, and the only irreversible one.
    """
    entry = await _setup(hass, sungrow_unit, mode=MODE_DIAGNOSTICS)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["menu_options"][0] == "promote"

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "promote"}
        )
        await hass.async_block_till_done()

    assert entry.data[CONF_MODE] == MODE_DEVICES
    # And now the entities exist.
    assert hass.states.get("sensor.sh10rt_total_dc_power") is not None


async def test_an_ordinary_entry_is_not_offered_the_promotion(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A menu item that would do nothing is worse than no menu item."""
    entry = await _setup(hass, sungrow_unit)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert "promote" not in result["menu_options"]
