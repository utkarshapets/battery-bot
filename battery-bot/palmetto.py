import pandas as pd
import requests
import os
import click

from constants import FROM_DATETIME_PALMETTO_FUTURE, TO_DATETIME_PALMETTO_FUTURE
from utils import process_pge_meterdata, series_to_palmetto_records

PALMETTO_API_URL = "https://ei.palmetto.com/api/v0/bem/calculate"
from dotenv import load_dotenv
load_dotenv(dotenv_path = "../.env")  # load from .env

def get_palmetto_data(
        address: str,
        granularity = "hour",
        solar_size_kw = 0.0,
        batt_size_kwh = 0.0,
        ev_charging_present = False,
        hvac_heat_pump_present = False,
        hvac_heating_capacity = 0.0,
        known_kwh_usage = None,
    ) -> pd.DataFrame:
    """
    Get solar data from Palmetto API for a given address
    
    Args:
        address (str): The address to get solar data for
        
    Returns:
        Dict containing solar data from Palmetto
    """
    api_key = os.getenv("PALMETTO_API_KEY")
    if not api_key:
        raise ValueError("PALMETTO_API_KEY environment variable is not set")

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-Key": api_key
    }

    customer_payload = {
        "parameters": {
            "from_datetime": FROM_DATETIME_PALMETTO_FUTURE,
            "to_datetime": TO_DATETIME_PALMETTO_FUTURE,
            "variables": [
                "consumption.electricity",
                "grid.electricity.import",
            ],
            "group_by": granularity
        },
        "location": {
            "address": address
        },
        "consumption": {
            "attributes": {
                "hypothetical": [
                    {
                        "name": "ev_charging",
                        "value": ev_charging_present
                    },
                    {
                        "name": "ev_charging_strategy",
                        "value": "delayed_by_departure"
                    },
                    {
                        "name": "hvac_heat_pump",
                        "value": hvac_heat_pump_present
                    },
                    {
                        "name": "hvac_heating_capacity",
                        "value": hvac_heating_capacity
                    }
                ]
            }
        },
        "production": {
            "attributes": {
                "hypothetical": [
                    {
                        "name": "panel_arrays",
                        "value": [
                            {
                                "capacity": solar_size_kw
                            }
                        ]
                    }
                ]
            }
        },
        "storage": {
            "attributes": {
                "hypothetical": [
                    {
                        "name": "capacity",
                        "value": batt_size_kwh
                    },
                    {
                        "name": "dispatch_strategy",
                        "value": "self_consumption"
                    }
                ]
            }
        },
    }
    if known_kwh_usage is not None:
        customer_payload["consumption"]['actuals'] = known_kwh_usage
    
    try:
        response = requests.post(PALMETTO_API_URL, headers=headers, json=customer_payload)
        response.raise_for_status()
        
        # Print the response for debugging
        # print("Palmetto API Response:")
        # print(json.dumps(response.json(), indent=2))
        response_json = response.json()
        data = response_json['data']
        interval_data = pd.DataFrame(data['intervals'])
        return interval_data
    except requests.exceptions.RequestException as e:
        print(f"Error making request to Palmetto API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        raise


@click.command()
@click.argument("output_file", type=click.Path())
@click.option("--address", type=str, default=None, help="Address for which to estimate load")
@click.option("--interval_data", type=click.Path(), default=None, help="PGE utility export")
@click.option("--ev", type=bool, default=False, help="EV charging present")
@click.option("--hvac", type=bool, default=False, help="HVAC heat pump present")
def get_palmetto_data_cli(
        address,
        interval_data,
        ev,
        hvac,
        known_kwh_usage,
        output_file
):
    assert address is not None or interval_data is not None, "Must provide either address or interval data"
    if interval_data:
        interval_data = series_to_palmetto_records(process_pge_meterdata(interval_data))

    granularity = "hour"
    solar_size_kw = 1.0
    battery_size_kwh = 0.0
    hvac_heating_capacity = 25.0

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
    res.to_csv(output_file, index=False)


if __name__ == "__main__":
    get_palmetto_data_cli()