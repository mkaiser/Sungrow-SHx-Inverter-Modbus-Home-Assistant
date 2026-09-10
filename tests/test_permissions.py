"""Who may change what.

Home Assistant's permission model is real rather than decorative:
`helpers/service.py` enforces `POLICY_CONTROL` on every entity service call,
and there are three built-in groups whose policies differ. What it has **no**
user interface for is per-entity policy, so the ladder an installation can
actually express is coarse — and that makes it worth writing down, because
the choice of *which shape* each control takes is what decides where it sits.

The ladder, and it is asserted below rather than described in a document
nobody reads:

* **admin** — everything, including starting and stopping the inverter;
* **normal user** — every entity, so the SoC limits and the EMS mode, and
  start/stop only if the owner has opened it to them in the options;
* **read-only** — every reading, and nothing writable at all, start/stop
  included whatever the option says.

That middle row is the one that needed a decision. Start/stop is an action
precisely so its audience can be decided at all; a `button` entity could not
have been, and would have been pressable by any normal user from any
dashboard.

The read-only row is the reason the audience check is not simply "is there a
user". A plainly-registered service has no `POLICY_CONTROL` behind it, so
opening start/stop to "users" without asking whether they can control this
device would hand it to the one account whose whole purpose is that it cannot
change anything.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from custom_components.sungrow_modbus.const import (
    AUDIENCE_USERS,
    CONF_PERMISSIONS,
    CONF_UNIT_ID,
    DOMAIN,
    PERMISSION_START_STOP,
)
from homeassistant.auth.const import GROUP_ID_READ_ONLY, GROUP_ID_USER
from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID, CONF_HOST, CONF_PORT
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import device_registry as dr

from .conftest import (
    SERIAL,
    SH10RT_HOLDING_REGISTERS,
    SH10RT_INPUT_REGISTERS,
    encode_string,
)

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

MIN_SOC = "number.sh10rt_battery_min_soc"
EMS = "select.sh10rt_ems_mode"
SOC_ADDRESS = 13058
EMS_ADDRESS = 13049


@pytest.fixture
async def entry(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> MockConfigEntry:
    sungrow_unit.holding[SOC_ADDRESS] = 100  # 10.0 %
    sungrow_unit.holding[EMS_ADDRESS] = 0  # self-consumption
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _open_entry(
    hass: HomeAssistant, unit: MockModbusUnit, audience: str
) -> MockConfigEntry:
    """Set an entry up with start/stop already opened to `audience`.

    The option is set at creation rather than changed afterwards, because
    changing an entry's options reloads it -- correctly, since a permission
    has to take effect without a restart -- and a reload inside a test would
    go looking for a real inverter.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        unique_id=SERIAL,
        title="SH10RT",
        options={CONF_PERMISSIONS: {PERMISSION_START_STOP: audience}},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _user(hass: HomeAssistant, group_id: str) -> MockUser:
    """Return a user in one of Home Assistant's built-in groups."""
    group = await hass.auth.async_get_group(group_id)
    user = MockUser(groups=[group], name=f"Someone in {group_id}")
    user.add_to_hass(hass)
    return user


def _device_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, SERIAL), entry.entry_id
    )
    assert device is not None
    return device.id


async def test_a_normal_user_can_set_the_state_of_charge_limits(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """Deliberate: this is a setting a household member may reasonably change."""
    user = await _user(hass, GROUP_ID_USER)

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: MIN_SOC, ATTR_VALUE: 20},
        blocking=True,
        context=Context(user_id=user.id),
    )

    assert sungrow_unit.holding[SOC_ADDRESS] == 200


async def test_a_normal_user_can_change_the_ems_mode(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    user = await _user(hass, GROUP_ID_USER)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: EMS, ATTR_OPTION: "vpp"},
        blocking=True,
        context=Context(user_id=user.id),
    )

    assert sungrow_unit.holding[EMS_ADDRESS] == 4


async def test_a_normal_user_cannot_stop_the_inverter(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """The default line, and why start/stop is an action rather than a button.

    A normal user may change every entity this integration has. Stopping the
    inverter is not an entity, and the action is admin-only unless the owner
    says otherwise -- so by default the one control whose worst case is a
    house that generates nothing is the one control they cannot reach.
    """
    user = await _user(hass, GROUP_ID_USER)
    before = sungrow_unit.holding.get(12999)

    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            "stop_inverter",
            {ATTR_DEVICE_ID: _device_id(hass, entry)},
            blocking=True,
            context=Context(user_id=user.id),
        )

    assert sungrow_unit.holding.get(12999) == before


async def test_a_read_only_user_cannot_change_a_setting(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """`READ_ONLY_POLICY` grants read on every entity and control on none."""
    user = await _user(hass, GROUP_ID_READ_ONLY)

    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: MIN_SOC, ATTR_VALUE: 30},
            blocking=True,
            context=Context(user_id=user.id),
        )

    assert sungrow_unit.holding[SOC_ADDRESS] == 100


async def test_a_read_only_user_can_still_read_everything(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The point of the group: a household dashboard that cannot be broken."""
    assert hass.states.get(MIN_SOC) is not None
    assert hass.states.get("sensor.sh10rt_total_dc_power") is not None
    # Reading a state is not a service call, so nothing is gated -- which is
    # exactly the shape a family dashboard wants.


async def test_an_admin_can_do_everything(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    sungrow_unit: MockModbusUnit,
    hass_admin_user,
) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: MIN_SOC, ATTR_VALUE: 25},
        blocking=True,
        context=Context(user_id=hass_admin_user.id),
    )
    await hass.services.async_call(
        DOMAIN,
        "stop_inverter",
        {ATTR_DEVICE_ID: _device_id(hass, entry)},
        blocking=True,
        context=Context(user_id=hass_admin_user.id),
    )

    assert sungrow_unit.holding[SOC_ADDRESS] == 250
    assert sungrow_unit.holding[12999] == 0xCE


async def test_a_normal_user_can_stop_it_once_the_owner_opens_it(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The setting the owner came looking for, and the point of the option."""
    entry = await _open_entry(hass, sungrow_unit, AUDIENCE_USERS)
    user = await _user(hass, GROUP_ID_USER)

    await hass.services.async_call(
        DOMAIN,
        "stop_inverter",
        {ATTR_DEVICE_ID: _device_id(hass, entry)},
        blocking=True,
        context=Context(user_id=user.id),
    )

    assert sungrow_unit.holding[12999] == 0xCE


async def test_opening_it_to_users_does_not_open_it_to_read_only_ones(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Opened to users means users who can already change this device.

    A read-only account exists so a household dashboard cannot be broken by
    the person using it. An action is not gated by `POLICY_CONTROL` the way an
    entity is, so this has to be checked here or the option would quietly
    grant the one thing that account must never have.
    """
    entry = await _open_entry(hass, sungrow_unit, AUDIENCE_USERS)
    user = await _user(hass, GROUP_ID_READ_ONLY)
    before = sungrow_unit.holding.get(12999)

    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            "stop_inverter",
            {ATTR_DEVICE_ID: _device_id(hass, entry)},
            blocking=True,
            context=Context(user_id=user.id),
        )

    assert sungrow_unit.holding.get(12999) == before


async def test_an_automation_is_not_a_user_and_is_not_gated(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """A call with no user behind it acts for the household, not for a person.

    This is core's own rule -- `_async_admin_handler` allows a context with no
    `user_id` -- and it has to hold here too, or an automation somebody wrote
    while logged in as an admin would stop working the moment it ran on its
    own schedule.
    """
    await hass.services.async_call(
        DOMAIN,
        "stop_inverter",
        {ATTR_DEVICE_ID: _device_id(hass, entry)},
        blocking=True,
        context=Context(),
    )

    assert sungrow_unit.holding[12999] == 0xCE


async def test_the_option_is_per_entry_not_per_integration(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """One entry is one endpoint, and a household may have two.

    The actions are registered once for the integration, so the audience has
    to be read from the entry the call targets. Registering them as admin
    actions instead would have made this unexpressible: one answer for every
    inverter in the house.
    """
    second = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_HOST: "127.0.0.2"},
        unique_id=f"{SERIAL}2",
        title="Second inverter",
        options={CONF_PERMISSIONS: {PERMISSION_START_STOP: AUDIENCE_USERS}},
    )
    second.add_to_hass(hass)
    other_unit = MockModbusConnection().for_unit(1)
    other_unit.input = {**SH10RT_INPUT_REGISTERS, 4989: encode_string(f"{SERIAL}2", 10)}
    other_unit.holding = dict(SH10RT_HOLDING_REGISTERS)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=other_unit
    ):
        assert await hass.config_entries.async_setup(second.entry_id)
        await hass.async_block_till_done()

    user = await _user(hass, GROUP_ID_USER)

    # Permitted on the second entry, which opened it...
    await hass.services.async_call(
        DOMAIN,
        "stop_inverter",
        {ATTR_DEVICE_ID: _second_device_id(hass, second)},
        blocking=True,
        context=Context(user_id=user.id),
    )
    assert other_unit.holding[12999] == 0xCE

    # ...and still refused on the first, which did not.
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            "stop_inverter",
            {ATTR_DEVICE_ID: _device_id(hass, entry)},
            blocking=True,
            context=Context(user_id=user.id),
        )
    assert sungrow_unit.holding.get(12999) is None


def _second_device_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, f"{SERIAL}2"), entry.entry_id
    )
    assert device is not None
    return device.id
