from palmetto import get_palmetto_data
from utils import series_to_palmetto_records
import pandas as pd
import pytest
from test.utils import elec_usage, get_test_root
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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


def test_all_variants():
    import os
    import time
    from utils import get_electricity_from_bayou_and_format_for_palmetto
    OUTFILE = get_test_root().parent / "data/scenario_data.csv"
    BAYOU_CUSTOMER_ID = int(os.getenv("BAYOU_CUSTOMER_ID_ANSHUL"))
    bayou_start = time.time()
    interval_data = get_electricity_from_bayou_and_format_for_palmetto(bayou_customer_id=BAYOU_CUSTOMER_ID)
    bayou_end = time.time()
    logger.info("Bayou API call took: ", bayou_end - bayou_start)
    address = "285 Lee Street, Apt 102, Oakland, CA 94610"

    granularity = "hour"
    solar_size_kw = 1.0
    battery_size_kwh = 0.0
    hvac_heating_capacity = 25.0

    ev, hvac  = False, False

    all_load_data = {}

    for ev in [True, False]:
        for hvac in [True, False]:
            palmetto_start = time.time()
            res = get_palmetto_data(
                address=address,
                granularity=granularity,
                solar_size_kw=solar_size_kw,
                batt_size_kwh=battery_size_kwh,
                ev_charging_present=ev,
                hvac_heat_pump_present=hvac,
                hvac_heating_capacity=hvac_heating_capacity,
                known_kwh_usage=interval_data
            )
            palmetto_end = time.time()
            logging.info("Palmetto API call took: ", palmetto_end - palmetto_start)
            df = pd.DataFrame.from_records(res).set_index(["from_datetime", "variable"])["value"].unstack("variable")
            load_data = df["consumption.electricity"]
            load_key = f"load__ev_{ev}__hvac_{hvac}"
            all_load_data[load_key] = load_data

    all_load_df = pd.DataFrame(all_load_data)
    all_load_df.to_csv(OUTFILE, float_format="%.3f")
    logger.info(f"Saved all load data to {OUTFILE}")
    print("Done")
