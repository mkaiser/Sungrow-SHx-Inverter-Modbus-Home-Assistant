"""Naming a Sungrow battery from the capacity register 5639 reports."""

import pytest

from sungrow_modbus.battery.power import MODELS, model_for_capacity


@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.name)
def test_a_rated_capacity_names_its_own_model(model):
    assert model_for_capacity(model.capacity_kwh) == model


def test_two_packs_summed_name_no_model():
    """44.8 kWh is two SBR224 (22.4 kWh each) on one SH10RS, through a WiNet-S.

    The register sums the packs while the voltage is one stack's, so no single
    model fits it; the caller falls back to what the BMS reports rather than
    handing the pair one pack's datasheet power.
    """
    assert model_for_capacity(44.8) is None


def test_no_capacity_names_no_model():
    assert model_for_capacity(None) is None
