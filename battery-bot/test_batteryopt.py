from solar import REF_SOLAR_DATA
import pytest
import pandas as pd
import numpy as np
from batteryopt import (process_pge_meterdata, merge_solar_and_load_data, build_tariff, run_optimization,
                        get_daily_optimized_cost, optimization_usage_from_batt_solar_size, get_daily_optimized_cost,
                        get_daily_cost_from_pgrid, simple_self_consumption)

REF_LOAD_DATA_FILE = "data/pge-e78ff14c-c8c0-11ec-8cc7-0200170a3297-DailyUsageData/pge_electric_usage_interval_data_Service 1_1_2024-02-01_to_2025-01-31.csv"
BATT_RT_EFF = 0.85
BATT_SIZE_EMAX = 13.5
BATT_SIZE_PMAX = 5.0
SOLAR_SIZE_KW = 1.0

@pytest.fixture
def elec_usage(csv_file=REF_LOAD_DATA_FILE) -> pd.Series:
    s = process_pge_meterdata(csv_file)
    return s

def test_elec_usage(elec_usage):
    assert elec_usage is not None, "Electric usage data should not be None"
    assert isinstance(elec_usage, pd.Series), "Electric usage data should be a pandas Series"
    assert elec_usage.index.tz.zone == 'US/Pacific', "Electric usage data should be in US/Pacific timezone"
    assert np.all(elec_usage >= 0), "Electric usage data should not contain negative values"


def test_opt(elec_usage, solar_size_kw=1.0, batt_size_kwh=13.5, ):
    # Convert text input to float
    battery_dispatch = optimization_usage_from_batt_solar_size(elec_usage,
                                                               tariff=build_tariff(elec_usage.index),
                                                               solar_size_kw=solar_size_kw,
                                                               batt_size_kwh=batt_size_kwh)
    assert battery_dispatch is not None, "Battery dispatch should not be None"
    assert battery_dispatch.shape[0] == elec_usage.shape[0], "Battery dispatch should have the same number of rows as site data"
    assert np.all(battery_dispatch.abs().sum() != 0), "Battery dispatch should be nonzero"


def test_batt_opt_cost(elec_usage, solar_size_kw=1.0, batt_size_kwh=13.5):
    tariff = build_tariff(elec_usage.index)
    average_daily_cost = get_daily_optimized_cost(elec_usage,
                                                  tariff=tariff,
                                                  solar_size_kw=solar_size_kw,
                                                  batt_size_kwh=batt_size_kwh)
    assert average_daily_cost >= 0, "Total cost should be non-negative"

def test_notech_cost(elec_usage):
    tariff = build_tariff(elec_usage.index)
    average_daily_cost = get_daily_cost_from_pgrid(elec_usage, tariff=tariff)
    assert average_daily_cost >= 0, "Total cost should be non-negative"

def test_simple_self_consumption(elec_usage):
    tariff = build_tariff(elec_usage.index)
    site_data = merge_solar_and_load_data(elec_usage, SOLAR_SIZE_KW * REF_SOLAR_DATA)

    simple_sc = simple_self_consumption(site_data,
                                        tariff,
                                        batt_rt_eff=BATT_RT_EFF,
                                        batt_size_kwh=BATT_SIZE_EMAX,
                                        batt_p_max=BATT_SIZE_PMAX)

    average_daily_cost = get_daily_cost_from_pgrid(simple_sc['P_grid'], tariff)
    assert average_daily_cost >= 0, "Total cost should be non-negative"