import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt

from solar import REF_SOLAR_DATA
from batteryopt import process_pge_meterdata, merge_solar_and_load_data, build_tariff, run_optimization
from palmetto import get_palmetto_data

from dotenv import load_dotenv
load_dotenv(dotenv_path = "../.env")  # load from .env

def process_submission(address, solar_size_kw, batt_size_kwh, csv_file):
    # Convert text input to float
    solar_size_kw = float(solar_size_kw)
    batt_size_kwh = float(batt_size_kwh)
    
    # Get solar data from Palmetto API
    try:
        palmetto_data = get_palmetto_data(address)
        # plot_palmetto_data(palmetto_data)
    except Exception as e:
        print(f"Error getting Palmetto data: {e}")
        
    # TODO: Process palmetto_data to get solar production data
    # For now, we'll use the existing REF_SOLAR_DATA
    solar_data = solar_size_kw * REF_SOLAR_DATA
    
    
    # Read CSV file into a DataFrame
    elec_usage = process_pge_meterdata(csv_file.name)

    site_data = merge_solar_and_load_data(elec_usage, solar_data)
    tariff = build_tariff(site_data.index)
    battery_dispatch = run_optimization(site_data, tariff, batt_e_max=batt_size_kwh)
    all_input = pd.concat([site_data, tariff, battery_dispatch], axis=1)

    final_week = all_input.loc[all_input.index[-1] - pd.DateOffset(days=7):]

    # Plot the result
    fig, ax = plt.subplots()
    final_week.plot(ax=ax)
    return fig


# Define the Gradio interface
iface = gr.Interface(
    fn=process_submission,  # Function to call on submit
    inputs=[
        gr.Textbox(label="Enter your address:", value="20 West 34th Street, New York, NY 10118"),
        gr.Textbox(label="Enter solar array size (kW):", value="1.0", type="text"),
        gr.Textbox(label="Battery size (kWh):", value="13.5", type="text"),
        gr.File(label="Upload CSV File")
    ],
    outputs=gr.Plot(),  # Output a Matplotlib figure
)

# Launch the Gradio app
iface.launch()
