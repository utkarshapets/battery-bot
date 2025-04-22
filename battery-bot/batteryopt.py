from solar import REF_SOLAR_DATA

import cvxpy as cp
import pandas as pd
import numpy as np
import time

from dotenv import load_dotenv

from utils import merge_solar_and_load_data

load_dotenv(dotenv_path = "../.env")  # load from .env


def run_optimization(site_data: pd.DataFrame, tariff: pd.DataFrame, batt_rt_eff=0.85,
                     batt_e_max=13.5, batt_p_max=5) -> pd.DataFrame:
    assert site_data.index.equals(tariff.index), "Dataframes must have the same index"

    dt = 1.0 

    oneway_eff = np.sqrt(batt_rt_eff)
    backup_reserve = 0.2
    e_min = backup_reserve * batt_e_max

    n = site_data.shape[0]
    E_0 = e_min

    E_transition = np.hstack([np.eye(n), np.zeros(n).reshape(-1,1)])

    P_batt_charge = cp.Variable(n)
    P_batt_discharge = cp.Variable(n)
    P_grid_buy = cp.Variable(n)
    P_grid_sell = cp.Variable(n)
    E = cp.Variable(n+1)

    # Power flows are all AC, and are signed relative to the bus: injections to the bus are positive, withdrawals/exports from the bus are negative

    constraints = [-batt_p_max <= P_batt_charge,
                P_batt_charge <= 0,
                0 <= P_batt_discharge,
                P_batt_discharge <= batt_p_max,
                0 <= P_grid_buy,
                P_grid_sell <= 0,
                e_min <= E,
                E <= batt_e_max,
                E[1:] == E_transition @ E - (P_batt_charge * oneway_eff + P_batt_discharge / oneway_eff) * dt,
                P_batt_charge + P_batt_discharge + P_grid_buy + P_grid_sell - site_data['load'] + site_data['solar'] == 0,
                E[0] == E_0
                ]

    obj = cp.Minimize(P_grid_sell @ tariff['px_sell'] + P_grid_buy @ tariff['px_buy'])

    prob = cp.Problem(obj, constraints)

    opt_start = time.time()
    prob.solve()
    print(f"Optimization done in {time.time() - opt_start :.3f} seconds")

    res = pd.DataFrame.from_dict({'P_batt': P_batt_charge.value + P_batt_discharge.value,
                        'P_grid': P_grid_buy.value + P_grid_sell.value,
                        'E': E[1:].value}).set_index(site_data.index)
    return res


def optimization_usage_from_batt_solar_size(elec_usage:pd.Series,
                                            tariff: pd.DataFrame,
                                            solar_size_kw: float,
                                            batt_size_kwh:float,
                                            solar_series_per_kw: pd.Series = REF_SOLAR_DATA,
                                            ) -> pd.DataFrame:
    site_data = merge_solar_and_load_data(elec_usage, solar_size_kw * solar_series_per_kw)
    battery_dispatch = run_optimization(site_data, tariff, batt_e_max=batt_size_kwh)
    return battery_dispatch


def get_daily_cost_from_pgrid(elec_usage:pd.Series,
                              tariff: pd.DataFrame,
                              ) -> float:
    assert isinstance(elec_usage.index, pd.DatetimeIndex), "Must have a Datetimeindex"
    p_grid_buy = elec_usage.clip(lower=0)
    p_grid_sell = elec_usage.clip(upper=0)
    total_cost = ((p_grid_buy @ tariff['px_buy']) + (p_grid_sell @ tariff['px_sell'])).sum()
    elapsed_days = (elec_usage.index[-1] - elec_usage.index[0]).days
    return total_cost / elapsed_days


def get_daily_optimized_cost(elec_usage:pd.Series,
                             tariff: pd.DataFrame,
                             solar_size_kw: float,
                             batt_size_kwh:float,
                             solar_series_per_kw: pd.Series = REF_SOLAR_DATA,) -> float:
    site_data = merge_solar_and_load_data(elec_usage, solar_size_kw * solar_series_per_kw)
    res = run_optimization(site_data, tariff, batt_e_max=batt_size_kwh)

    return get_daily_cost_from_pgrid(res['P_grid'], tariff)

def simple_self_consumption(site_data: pd.DataFrame,
                            tariff: pd.DataFrame,
                            batt_rt_eff=0.85,
                            batt_size_kwh=13.5,
                            batt_p_max=5) -> pd.DataFrame:
    assert site_data.index.equals(tariff.index), "Dataframes must have the same index"
    site_data['net_load'] = site_data['load'] - site_data['solar']
    dt = (site_data.index[1] - site_data.index[0]).total_seconds() / 3600  # Time step in hours
    oneway_eff = np.sqrt(batt_rt_eff)
    n = len(site_data)

    # Initialize battery state of charge (SOC)
    e_batt = np.zeros(n+1)
    p_batt = np.zeros(n)
    p_grid = np.zeros(n)

    for i, (t, s) in enumerate(site_data.iterrows()):
        if s['net_load'] < 0:  # Solar is generating
            charge_power = -min(-s['net_load'], batt_p_max, (batt_size_kwh - e_batt[i]) / (oneway_eff * dt))
            p_batt[i] = charge_power
            e_batt[i+1] = e_batt[i] - charge_power * oneway_eff * dt
            p_grid[i] = s['net_load'] - charge_power
        else:  # Solar is not generating
            # Discharge the battery (limited by power, efficiency, and capacity)
            discharge_power = min(s['net_load'], batt_p_max, e_batt[i] * oneway_eff * dt)
            p_batt[i] = discharge_power  # Positive for discharging
            e_batt[i+1] = e_batt[i] - discharge_power / oneway_eff * dt
            p_grid[i] = s['net_load'] - discharge_power

    return pd.DataFrame({
        'P_batt': p_batt,
        'P_grid': p_grid,
        'E_batt': e_batt[1:]
    }, index=site_data.index)
