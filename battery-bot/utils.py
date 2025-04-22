import pandas as pd

from bayou import get_dataframe_of_electric_intervals_for_customer
from constants import TIMEZONE, FROM_DATETIME_PALMETTO_FUTURE


def get_electricity_from_bayou_and_format_for_palmetto(bayou_customer_id: int) -> list:
    """
    Gets the electricity usage in intervals for the customer specified by `bayou_customer_id`, filters it to only
    include intervals that occured before FROM_DATETIME_PALMETTO_FUTURE, and then formats the data into a list
    of dicts that can be used for arg `known_kwh_usage` in func get_palmetto_data().
    :param bayou_customer_id: Bayou integer ID number for the customer whose electricity usage is requested.
    :return: List of dicts where each dict represents an interval of electricity usage, formatted to be ingested by Palmetto API.
    """
    intervals_df = get_dataframe_of_electric_intervals_for_customer(customer_id=bayou_customer_id)
    intervals_df = intervals_df.sort_values(by=['start'], ascending=True)

    interval_end_timestamp_without_tz = intervals_df['end'].dt.tz_localize(None)
    end_datetime = pd.to_datetime(FROM_DATETIME_PALMETTO_FUTURE)
    intervals_df = intervals_df[interval_end_timestamp_without_tz < end_datetime].copy(deep=True)

    intervals_df['from_datetime'] = intervals_df['start'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    intervals_df['to_datetime'] = intervals_df['end'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    intervals_df['variable'] = 'consumption.electricity'
    intervals_df['value'] = intervals_df['net_electricity_consumption']

    return intervals_df[['from_datetime', 'to_datetime', 'variable', 'value']].to_dict(orient='records')


def series_to_palmetto_records(s: pd.Series) -> list[dict]:
    s.name = 'value'
    elec_usage = pd.DataFrame(s)
    elec_usage['to_datetime'] = (elec_usage.index.tz_convert('UTC') + pd.DateOffset(hours=1)).tz_convert(elec_usage.index.tzinfo)
    elec_usage["to_datetime"] = elec_usage["to_datetime"].dt.strftime('%Y-%m-%dT%H:%M:%S')
    elec_usage['variable'] = 'consumption.electricity'
    elec_usage = elec_usage.reset_index()
    elec_usage['from_datetime'] = elec_usage['from_datetime'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    return elec_usage.to_dict(orient='records')



def process_pge_meterdata(fname: str, extract_col='USAGE (kWh)') -> pd.Series:
    header_row = None
    with open(fname, 'r') as f:
        for i, line in enumerate(f):
            if line.startswith("TYPE,DATE,START TIME,END TIME"):
                header_row = i
                break
    if header_row is None:
        raise ValueError("Header row not found!")

    sample_consumption = pd.read_csv(fname, parse_dates={'Datetime': ['DATE', 'START TIME']}, skiprows=header_row)
    sample_consumption['Datetime'] = pd.DatetimeIndex(sample_consumption['Datetime']).tz_localize('US/Pacific', ambiguous='NaT', nonexistent='NaT')
    sample_consumption = sample_consumption[sample_consumption['Datetime'].notnull()]
    sample_consumption = sample_consumption.set_index('Datetime')
    s = sample_consumption[extract_col].astype(str).str.replace('$', '').astype(float).rename('load')

    end_date = s.index[-1]
    if s.index[0] < (end_date - pd.DateOffset(years=1)):
        s = s.loc[end_date - pd.DateOffset(years=1):end_date]
    return s


def merge_solar_and_load_data(elec_usage: pd.Series, solar_ac_estimate: pd.Series) -> pd.DataFrame:
    elec_end_date = elec_usage.index[-1]
    leap_day = None
    for t in elec_usage.index:
        if (t.month==2) & (t.day==29):
            leap_day = t
            break

    if leap_day:
        shift_by_yrs = 2020 - leap_day.year
    elif elec_end_date.month == 12 & elec_end_date.day == 31:
        shift_by_yrs = 2019 - elec_end_date.year
    elif elec_end_date.month > 2:
        shift_by_yrs = 2021 - elec_end_date.year
    else:
        shift_by_yrs = 2019 - elec_end_date.year

    print("solar_ac_estimate")
    print(solar_ac_estimate.head())
    print("elec_usage")
    print(elec_usage.head())


    solar_ac_estimate.index = (solar_ac_estimate.index.tz_convert('UTC') - pd.DateOffset(years=shift_by_yrs)).tz_convert(TIMEZONE)
    solar_ac_estimate = solar_ac_estimate.resample('1h', closed='right').last().ffill()  # Deal with any gaps related to shifted DST; thankfully these are in the night

    site_data = pd.DataFrame(elec_usage).join(solar_ac_estimate, how='left')
    return site_data


def build_tariff(idx: pd.DatetimeIndex) -> pd.DataFrame:
    px_buy = pd.Series(0.4, index=idx, name='px_buy')
    px_buy.loc[px_buy.between_time('16:00', '21:00').index] = 0.52

    px_sell = pd.Series(0.05, index=idx, name='px_sell')
    px_sell.loc[px_sell.between_time('15:00', '20:00').index] = 0.08

    return pd.DataFrame({'px_buy': px_buy, 'px_sell': px_sell})
