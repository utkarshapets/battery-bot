from palmetto import get_palmetto_data
from utils import series_to_palmetto_records
import pandas as pd
import pytest
from test.utils import elec_usage

def test_palmetto_data_from_address():
    res = get_palmetto_data(address="468 Noe St, San Francisco, CA 94114",
                            granularity="hour",
                            solar_size_kw=0.0,
                            batt_size_kwh=0.0,
                            ev_charging_present=False,
                            hvac_heat_pump_present=False,
                            hvac_heating_capacity=0.0,
                            known_kwh_usage=None)
    assert all(res.columns == ['from_datetime', 'to_datetime', 'variable', 'value'])
    assert all(res.variable.unique() == ['consumption.electricity', 'grid.electricity.import'])
    consumption = res[res.variable == 'consumption.electricity']['value'].reset_index(drop=True)
    imports = res[res.variable == 'grid.electricity.import']['value'].reset_index(drop=True)
    assert consumption.equals(imports)


def test_palmetto_data_from_kwh(elec_usage):
    payload = series_to_palmetto_records(elec_usage)
    payload = payload[0:72]

    res = get_palmetto_data(address="468 Noe St, San Francisco, CA 94114",
                            granularity="hour",
                            solar_size_kw=0.0,
                            batt_size_kwh=0.0,
                            ev_charging_present=False,
                            hvac_heat_pump_present=False,
                            hvac_heating_capacity=0.0,
                            known_kwh_usage=payload)
    assert all(res.columns == ['from_datetime', 'to_datetime', 'variable', 'value'])
    assert all(res.variable.unique() == ['consumption.electricity', 'grid.electricity.import'])
    consumption = res[res.variable == 'consumption.electricity']['value'].reset_index(drop=True)
    imports = res[res.variable == 'grid.electricity.import']['value'].reset_index(drop=True)
    assert consumption.equals(imports)
