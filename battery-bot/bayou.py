import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path = "../.env")  # load from .env

BAYOU_API_KEY = os.getenv("BAYOU_API_KEY")
BAYOU_DOMAIN = "staging.bayou.energy"
BAYOU_CUSTOMER_ID = os.getenv("BAYOU_CUSTOMER_ID_ERIC")

def get_all_bayou_customers() -> dict:
    """
    Get all customers for your Bayou account.
    :return: List of dicts containing. Each dict is a customer.
    """
    url = f'https://{BAYOU_DOMAIN}/api/v2/customers'
    headers = {'accept': 'application/json'}
    auth = (BAYOU_API_KEY, '')

    try:
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to Bayou API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        raise

def get_bayou_customer_info(customer_id: int) -> dict:
    """
    Get Bayou's metadata for a customer.
    :param customer_id: Bayou numerical id of the customer.
    :return: Dict of metadata.
    """
    url = f'https://{BAYOU_DOMAIN}/api/v2/customers/{customer_id}'
    headers = {'accept': 'application/json'}
    auth = (BAYOU_API_KEY, '')

    try:
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to Bayou API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        raise

def get_all_bayou_intervals_for_customer(customer_id: int) -> dict:
    """
    Get utility energy usage for each interval (generally 15 min long) for each meter for a customer.
    :param customer_id: Bayou numerical id of the customer.
    :return: List of dicts containing the customer's utility energy usage.
    """
    customer = get_bayou_customer_info(customer_id)
    while not customer['intervals_are_ready']:
        time.sleep(1)
        customer = get_bayou_customer_info(customer_id)

    url = f'https://{BAYOU_DOMAIN}/api/v2/customers/{customer_id}/intervals'
    headers = {'accept': 'application/json'}
    auth = (BAYOU_API_KEY, '')

    try:
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to Bayou API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        raise