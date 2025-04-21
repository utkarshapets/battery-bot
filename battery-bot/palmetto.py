import pandas as pd
import requests
import os
import json
from typing import Dict, Any

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
        hvac_heating_capacity = 0.0
    ) -> Dict[str, Any]:
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
            "from_datetime": "2024-04-01T00:00:00",
            "to_datetime": "2025-04-01T00:00:00",
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
    
    try:
        response = requests.post(PALMETTO_API_URL, headers=headers, json=customer_payload)
        response.raise_for_status()
        
        # Print the response for debugging
        print("Palmetto API Response:")
        print(json.dumps(response.json(), indent=2))
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
