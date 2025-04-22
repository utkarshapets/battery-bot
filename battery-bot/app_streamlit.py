import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import tempfile
import time
from solar import REF_SOLAR_DATA
from batteryopt import merge_solar_and_load_data, build_tariff, run_optimization, process_pge_meterdata

st.set_page_config(
    page_title="My App",
    layout="wide"  
)

def process_submission_modified(solar_size_kw, batt_size_kwh, tmp_file_path):
    # Convert text input to float
    solar_size_kw = float(solar_size_kw)
    batt_size_kwh = float(batt_size_kwh)
    
    # Save uploaded file to a temp file and pass its name
    
    #with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
    #    tmp_file.write(uploaded_file.read())
    #    tmp_file_path = tmp_file.name

    elec_usage = process_pge_meterdata(tmp_file_path)

    site_data = merge_solar_and_load_data(elec_usage, solar_size_kw * REF_SOLAR_DATA)
    tariff = build_tariff(site_data.index)
    battery_dispatch = run_optimization(site_data, tariff, batt_e_max=batt_size_kwh)
    all_input = pd.concat([site_data, tariff, battery_dispatch], axis=1)

    final_week = all_input.loc[all_input.index[-1] - pd.DateOffset(days=7):]

    # Plot the result
    fig, ax = plt.subplots()
    final_week.plot(ax=ax)
    return fig



def calculate_data_and_price(option_pv, option_bat):
    # Example: Create different data based on selections

    cost_saving = 0  # base price
    solar_size_kw = 0
    batt_size_kwh = 0

    if option_pv:
        solar_size_kw = 1.0 #st.text_input("Enter solar array size (kW):", value="1.0")
        cost_saving = 300
    if option_bat:
        batt_size_kwh = 13.5 #st.text_input("Battery size (kWh):", value="13.5")
        cost_saving = 100
    if option_pv & option_bat:
        cost_saving = 400

    return solar_size_kw, batt_size_kwh, cost_saving

# Streamlit app layout
st.title("Electriplan?")

def go_to_tab(tab_name):
    st.session_state.active_tab = tab_name



# Create tabs
tabs = st.tabs(["Home", "Your 10-year Electriplan"])

with tabs[0]:
    st.header("Start")
    st.write("We give you transparency what greener options make sense for you. ")
    us_adress = st.text_input("Let's start as easy as input your US Adress", value="550 Moreland Way, 95054 Santa Clara")
    option = st.selectbox('(Optional) Get a even more personalized for you by retrieving YOUR last years energy data.:',('Yes', 'No'), index=1)
    if option == "No":
        #csv_file_name = "C:\Users\Martin\AppData\Local\Temp\gradio\be5eb618966876fd8c439bbee0ab968446ae966d\pge_electric_usage_interval_data_Service 1_1_2024-02-01_to_2025-01-31.csv"
        csv_file_name = "data\pge-e78ff14c-c8c0-11ec-8cc7-0200170a3297-DailyUsageData\pge_electric_usage_interval_data_Service 1_1_2024-02-01_to_2025-01-31.csv"
    else:
        csv_file = st.file_uploader("Upload CSV File", type=["csv"])
        with tempfile.NamedTemporaryFile(delete=False) as csv_file:
            csv_file.write(csv_file.read())
            csv_file_name = csv_file.name
    if st.button("Submit"):
        st.success(f"Sucessfully input your adress: "+str(us_adress))

        

with tabs[1]:
    st.header("Your 10-year Electriplan")

    solar_size_kw, batt_size_kwh, cost_saving = calculate_data_and_price(False, False)

    col1, col2, col3 = st.columns([1, 2, 1])

    # --- Left column: Checkboxes ---
    with col1:
        st.subheader("Options")
        option_pv = st.checkbox("Photovoltaik")
        option_bat = st.checkbox("Battery")

    # --- Show "Run Optimization" button only if CSV is uploaded ---
    with col2:
        solar_size_kw, batt_size_kwh, cost_saving = calculate_data_and_price(option_pv, option_bat)
        fig = process_submission_modified(solar_size_kw, batt_size_kwh, csv_file_name)
        st.pyplot(fig)

    # --- Right column: Price ---
    with col3:
        old_price = 600
        st.metric(label="Todays Price", value=f"${old_price}")
        st.metric(label="New Price", value=f"${old_price - cost_saving}")



    

    







