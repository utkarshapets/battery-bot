import os
import time
from solar import REF_SOLAR_DATA
import pytest
import pandas as pd
import numpy as np
from batteryopt import (optimization_usage_from_batt_solar_size, get_daily_optimized_cost,
                        get_daily_cost_from_pgrid, simple_self_consumption, run_endogenous_sizing_optimization)
from utils import process_pge_meterdata, merge_solar_and_load_data, build_tariff
from test.utils import elec_usage, get_test_root
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BATT_RT_EFF = 0.85
BATT_SIZE_EMAX = 13.5
BATT_SIZE_PMAX = 5.0
SOLAR_SIZE_KW = 1.0


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
    sc_data = simple_sc.join(site_data)
    average_daily_cost = get_daily_cost_from_pgrid(simple_sc['P_grid'], tariff)
    assert average_daily_cost >= 0, "Total cost should be non-negative"


def load_palmetto_df(infile: os.PathLike) -> pd.DataFrame:
    # Because of bad tz-naive indexing we need to drop-reindex-interpolate over the bad timestamps
    load_df = pd.read_csv(infile, index_col=0, parse_dates=[0])
    load_df = load_df[load_df.index.tz_localize('US/Pacific', ambiguous='NaT', nonexistent="NaT").notnull()]
    load_df.index = load_df.index.tz_localize('US/Pacific')
    load_df = load_df.resample('1H').last().interpolate(method='linear')
    load_df = load_df / 1000.0  # convert to kWh
    return load_df


def test_all_scenarios():
    package_root = get_test_root().parent
    data_root = package_root / "data"
    infile = data_root / "scenario_data.csv"
    output_root = package_root / "data" / "output"

    load_df = load_palmetto_df(infile)
    tariff = build_tariff(load_df.index)
    solar_size_kw = 4.0
    batt_size_kwh = 13.5

    result_stats = pd.DataFrame(columns=["daily_cost", "solar_size_kw", "batt_size_kwh"],
                                index=load_df.columns)

    for lbl, elec_usage in load_df.items():
        battery_dispatch = optimization_usage_from_batt_solar_size(elec_usage.rename("load"),
                                                                   tariff=tariff,
                                                                   solar_size_kw=solar_size_kw,
                                                                   batt_size_kwh=batt_size_kwh)

        result_stats.loc[lbl, "daily_cost"] = get_daily_cost_from_pgrid(battery_dispatch['P_grid'], tariff) * 30
        result_stats.loc[lbl, "solar_size_kw"] = solar_size_kw
        result_stats.loc[lbl, "batt_size_kwh"] = batt_size_kwh

        battery_dispatch.to_csv(output_root / (lbl + "_battery_dispatch.csv"))

    result_stats.to_csv(output_root / "result_stats.csv")


def test_all_scenarios_incl_sizing():
    solar_annualized_cost_per_kw = 3 / 20 * 1000
    batt_annualized_cost_per_unit = 14000 / 10
    batt_rt_eff = 0.85
    batt_block_e_max = 13.5
    batt_p_max = 5
    load_multiplier = 8  # For demo only
    integer_problem = True

    package_root = get_test_root().parent
    data_root = package_root / "data"
    infile = data_root / "scenario_data.csv"
    output_root = package_root / "data" / "output"

    load_df = load_palmetto_df(infile)
    tariff = build_tariff(load_df.index)
    solar_series_per_kw = REF_SOLAR_DATA
    solar_data = merge_solar_and_load_data(load_df, solar_series_per_kw)['solar']

    result_stats = pd.DataFrame(columns=["energy_cost", "equipment_cost", "solar_size_kw", "batt_size_kwh"],
                                index=load_df.columns)

    for lbl, elec_usage in load_df.items():
        opt_start = time.time()
        res = run_endogenous_sizing_optimization(pd.concat([solar_data, elec_usage.rename("load") * load_multiplier], axis=1),
                                                 tariff=tariff,
                                                 solar_annualized_cost_per_kw=solar_annualized_cost_per_kw,
                                                 batt_annualized_cost_per_unit=batt_annualized_cost_per_unit,
                                                 batt_rt_eff=batt_rt_eff,
                                                 batt_block_e_max=batt_block_e_max,
                                                 batt_p_max=batt_p_max,
                                                 integer_problem=integer_problem,
                                                 )
        opt_end = time.time()
        logger.info(f"Optimization done in {opt_end - opt_start} seconds")
        n_batts, s_size_kw, battery_dispatch = res

        result_stats.loc[lbl, "energy_cost"] = get_daily_cost_from_pgrid(battery_dispatch['P_grid'], tariff) * 30
        result_stats.loc[lbl, "equipment_cost"] = (n_batts * batt_annualized_cost_per_unit + s_size_kw * solar_annualized_cost_per_kw) / 365 * 30
        result_stats.loc[lbl, "solar_size_kw"] = s_size_kw
        result_stats.loc[lbl, "batt_size_kwh"] = n_batts * batt_block_e_max

        battery_dispatch.to_csv(output_root / (lbl + "_battery_dispatch.csv"))

    result_stats["total_cost"] = result_stats["energy_cost"] + result_stats["equipment_cost"]
    result_stats.to_csv(output_root / "result_stats.csv")
