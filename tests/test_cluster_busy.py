"""A cluster's inverters are tested one at a time.

A slave's 13050 follows the master's (wiki:
does-a-cluster-slave-mirror-the-masters-ems-mode), so a run on one member
writes over what a run on the other has to put back.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.capability_test import (
    CapabilityTestRunner,
    ClusterBusyError,
    async_leftover,
)
from custom_components.sungrow_modbus.const import DOMAIN
from custom_components.sungrow_modbus.write_owner import (
    WriteOwner,
    async_test_owns_writes,
    cluster_busy,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from sungrow_modbus.hybrid_inverter.capabilities import Capability

from .test_capability_test_ha import _setup

CLUSTER_MODE_ADDRESS = 33499
MEMBER = frozenset({Capability.CLUSTER_MEMBER})
RUN_BY = "SH10RT master"


def _other(
    hass: HomeAssistant, *, member: bool = True, testing: bool = True
) -> MockConfigEntry:
    """Add the cluster's other inverter, loaded and perhaps under test."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="the-other", title=RUN_BY)
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(
        capabilities=MEMBER if member else frozenset(),
        write_owners=[WriteOwner(by=RUN_BY, since=dt_util.utcnow())] if testing else [],
    )
    return entry


@pytest.fixture
def member_unit(ready_unit: MockModbusUnit) -> MockModbusUnit:
    """Return an inverter that is in a cluster."""
    ready_unit.holding[CLUSTER_MODE_ADDRESS] = 0xAA
    return ready_unit


async def test_a_run_is_refused_before_it_saves_or_writes(
    hass: HomeAssistant, member_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, member_unit)
    _other(hass)
    writes: list[Any] = []
    member_unit.on_write(writes.append)

    with pytest.raises(ClusterBusyError, match=RUN_BY):
        await CapabilityTestRunner(hass, entry).async_run()

    assert writes == []
    assert entry.runtime_data.write_owners == []
    assert await async_leftover(hass, entry) is None


async def test_the_action_says_which_inverter_is_under_test(
    hass: HomeAssistant, member_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, member_unit)
    _other(hass)
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]

    with pytest.raises(ServiceValidationError) as raised:
        await hass.services.async_call(
            DOMAIN, "run_capability_test", {"device_id": device.id}, blocking=True
        )

    assert raised.value.translation_key == "cluster_under_test"
    assert raised.value.translation_placeholders["other"] == RUN_BY


async def test_the_button_refuses_too(
    hass: HomeAssistant, member_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, member_unit)
    _other(hass)
    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": "select.sh10rt_diagnosis_mode",
            "option": "extended",
        },
        blocking=True,
    )

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.sh10rt_diagnosis_start"},
            blocking=True,
        )

    assert not entry.runtime_data.diagnosis.state.running


@pytest.mark.parametrize(
    ("ours", "theirs", "testing", "busy"),
    [
        (0xAA, True, True, True),
        (0xAA, True, False, False),
        (0xAA, False, True, False),
        (0x55, True, True, False),
    ],
)
async def test_only_two_members_of_a_cluster_exclude_each_other(
    hass: HomeAssistant,
    ready_unit: MockModbusUnit,
    *,
    ours: int,
    theirs: bool,
    testing: bool,
    busy: bool,
) -> None:
    ready_unit.holding[CLUSTER_MODE_ADDRESS] = ours
    entry = await _setup(hass, ready_unit)
    _other(hass, member=theirs, testing=testing)

    assert (cluster_busy(hass, entry) is not None) is busy


async def test_its_own_run_does_not_refuse_it(
    hass: HomeAssistant, member_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, member_unit)

    async with async_test_owns_writes([entry], entry.title):
        assert cluster_busy(hass, entry) is None


async def test_a_restore_is_never_refused(
    hass: HomeAssistant, member_unit: MockModbusUnit
) -> None:
    """The one thing that must go through is putting a house back."""
    entry = await _setup(hass, member_unit)
    _other(hass)

    with patch(
        "custom_components.sungrow_modbus.capability_test.CapabilityTest"
    ) as test:
        test.return_value.async_restore.return_value = []

        async def restored(_snapshot: Any) -> list[Any]:
            return []

        test.return_value.async_restore = restored
        snapshot = SimpleNamespace(stopped_at=None)
        assert await CapabilityTestRunner(hass, entry).async_restore(snapshot)


async def test_auto_repeat_waits_rather_than_failing(
    hass: HomeAssistant, member_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, member_unit)
    runner = entry.runtime_data.diagnosis
    other = _other(hass)

    started = runner.continuous._inverter_tick(dt_util.utcnow(), None, [], forced=False)

    assert started is False
    assert RUN_BY in runner.continuous.waiting
    other.runtime_data.write_owners.clear()
