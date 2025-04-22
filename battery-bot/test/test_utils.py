import numpy as np
import pandas as pd

from test.utils import elec_usage, ng_usage, ng_cost


def validate_usage_data(s):
    assert s is not None, "usage data should not be None"
    assert isinstance(s, pd.Series), "usage data should be a pandas Series"
    assert s.index.tz.zone == 'US/Pacific', "usage data should be in US/Pacific timezone"
    assert np.all(s >= 0), "usage data should not contain negative values"


def test_elec_usage(elec_usage):
    validate_usage_data(elec_usage)

def test_ng_usage(ng_usage):
    validate_usage_data(ng_usage)

def test_ng_cost(ng_cost):
    validate_usage_data(ng_cost)