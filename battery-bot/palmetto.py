import requests
import os
import json
from typing import Dict, Any

PALMETTO_API_URL = "https://ei.palmetto.com/api/v0/bem/calculate"
from dotenv import load_dotenv
load_dotenv(dotenv_path = "../.env")  # load from .env

def get_palmetto_data(address: str) -> Dict[str, Any]:
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
            "from_datetime": "2025-01-01T00:00:00",
            "to_datetime": "2025-01-10T23:59:59",
            "variables": ["consumption.electricity"],
            "group_by": "month"
        },
        "location": {
            "address": address
        }
    }
    
    try:
        response = requests.post(PALMETTO_API_URL, headers=headers, json=customer_payload)
        response.raise_for_status()
        
        # Print the response for debugging
        print("Palmetto API Response:")
        print(json.dumps(response.json(), indent=2))
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to Palmetto API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        raise
