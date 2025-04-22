import pandas as pd
import requests
import os
import json
from typing import Dict, Any

PALMETTO_API_URL = "https://ei.palmetto.com/api/v0/bem/calculate"
from dotenv import load_dotenv
load_dotenv(dotenv_path = "../.env")  # load from .env

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
        "to_datetime": "2025-03-31T23:59:59",
        "variables": ["consumption.electricity", "grid.electricity.import"],
        "group_by": "hour"
    },
    "location": {
        "address": "20 West 34th Street, New York, NY 10118"
    },
    "consumption":{},
    "production": {
        "attributes": {
            "hypothetical": [
                {
                    "name": "panel_arrays",
                    "value": [
                        {
                            "capacity": 10
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
                    "value": 10
                },
                {
                    "name": "dispatch_strategy",
                    "value": "self_consumption"
                }
            ]
        }
    }
}
known_kwh_usage = [
    {
        "from_datetime": "2024-01-01T00:00:00",
        "to_datetime": "2024-01-31T23:59:59",
        "variable":"consumption.electricity",
        "value": 758
    },
    {
        "from_datetime": "2024-02-01T00:00:00",
        "to_datetime": "2024-02-28T23:59:59",
        "variable":"consumption.electricity",
        "value": 708
    }
]

customer_payload["consumption"]['actuals'] = known_kwh_usage

response = requests.post(PALMETTO_API_URL, headers=headers, json=customer_payload)
response_json = response.json()
print("METADATA: ", response_json['meta'])

data = response_json['data']
print("LOCATION: ", data['location'])
print("COSTS: ", data['costs'])

interval_data = pd.DataFrame(data['intervals'])



import ipdb ; ipdb.set_trace()