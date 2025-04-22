import pandas as pd
import os
import pathlib
import pytest
from utils import process_pge_meterdata


def get_test_root() -> pathlib.Path:
    return pathlib.Path(os.path.dirname(os.path.abspath(__file__)))

REF_ELEC_LOAD_DATA_FILE = get_test_root().parent / "data" / "pge-e78ff14c-c8c0-11ec-8cc7-0200170a3297-DailyUsageData" / "pge_electric_usage_interval_data_Service 1_1_2024-02-01_to_2025-01-31.csv"
REF_NG_LOAD_DATA_FILE = get_test_root().parent / "data" / "pge-e78ff14c-c8c0-11ec-8cc7-0200170a3297-DailyUsageData" / "pge_natural_gas_usage_interval_data_Service 2_2_2024-02-01_to_2025-01-31.csv"


@pytest.fixture
def elec_usage(csv_file=REF_ELEC_LOAD_DATA_FILE) -> pd.Series:
    s = process_pge_meterdata(csv_file)
    return s

@pytest.fixture
def ng_usage(csv_file=REF_NG_LOAD_DATA_FILE) -> pd.Series:
    s = process_pge_meterdata(csv_file, extract_col="USAGE (therms)")
    return s

@pytest.fixture
def ng_cost(csv_file=REF_NG_LOAD_DATA_FILE) -> pd.Series:
    s = process_pge_meterdata(csv_file, extract_col="COST")
    return s