import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt

from solar import REF_SOLAR_DATA
from batteryopt import run_optimization
from utils import process_pge_meterdata, merge_solar_and_load_data, build_tariff
try:
    from palmetto import get_palmetto_data
except TypeError:
    get_palmetto_data = None

from dotenv import load_dotenv
load_dotenv(dotenv_path = "../.env")  # load from .env

TRY_PALMETTO = False

def get_data(
        address,
        solar_size_kw,
        batt_size_kwh,
        ev_charging_present,
        hvac_heat_pump_present,
        hvac_heating_capacity,
        electricity_csv_file=None,
        natural_gas_csv_file=None,
    ):
    # Convert text input to float
    solar_size_kw = float(solar_size_kw)
    batt_size_kwh = float(batt_size_kwh)
    ev_charging_present = True if ev_charging_present == "Yes" else False
    hvac_heat_pump_present = True if hvac_heat_pump_present == "Yes" else False
    hvac_heating_capacity = float(hvac_heating_capacity)
    
    # Get solar data from Palmetto API
    if TRY_PALMETTO:
        try:
            palmetto_records = get_palmetto_data(
                address,
                solar_size_kw = solar_size_kw,
                batt_size_kwh= batt_size_kwh,
                ev_charging_present = ev_charging_present,
                hvac_heat_pump_present = hvac_heat_pump_present,
                hvac_heating_capacity = hvac_heating_capacity,
                known_kwh_usage = None,
            )
            df = pd.DataFrame.from_records(palmetto_records).set_index(["from_datetime", "variable"])["value"].unstack("variable")
            load_data = df["consumption.electricity"]
            elec_usage = load_data.rename('load')
        except Exception as e:
            print(f"Error getting Palmetto data: {e}")
    else:
        solar_data = solar_size_kw * REF_SOLAR_DATA
        elec_usage = process_pge_meterdata(electricity_csv_file.name)

    site_data = merge_solar_and_load_data(elec_usage, solar_data)
    tariff = build_tariff(site_data.index)
    battery_dispatch = run_optimization(site_data, tariff, batt_e_max=batt_size_kwh)
    all_input = pd.concat([site_data, tariff, battery_dispatch], axis=1)
    return all_input

def process_submission(
        address,
        solar_size_kw,
        batt_size_kwh,
        ev_charging_present,
        hvac_heat_pump_present,
        hvac_heating_capacity,
        csv_file
):

    all_input = get_data(       
        address,
        solar_size_kw,
        batt_size_kwh,
        ev_charging_present,
        hvac_heat_pump_present,
        hvac_heating_capacity,
        csv_file)
    

    final_week = all_input.loc[all_input.index[-1] - pd.DateOffset(days=7):]

    # Plot the result
    fig, ax = plt.subplots()
    final_week.plot(ax=ax)
    return fig


if __name__ == '__main__':

    # Define the Gradio interface
    iface = gr.Interface(
        fn=process_submission,  # Function to call on submit
        inputs=[
            gr.Textbox(label="Enter your address:", value="20 West 34th Street, New York, NY 10118"),
            gr.Textbox(label="Enter solar array size (kW):", value="1.0", type="text"),
            gr.Textbox(label="Battery size (kWh):", value="13.5", type="text"),
            gr.Dropdown(label="Do you have EV charging?",choices = ["Yes", "No"], value="No", type="value"),
            gr.Dropdown(label="Do you have a heat pump?", choices = ["Yes", "No"], value="No", type="value"),
            gr.Textbox(label="What is the heat pump capacity? (in kBtu/hr) ", value="0.0", type="text"),
            gr.File(label="Upload CSV File")
        ],
        outputs=[gr.Plot()],
    )

    # Launch the Gradio app
    iface.launch()
