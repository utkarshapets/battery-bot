import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import tempfile
import time
from solar import REF_SOLAR_DATA
from batteryopt import merge_solar_and_load_data, build_tariff, run_optimization, process_pge_meterdata

def process_submission(solar_size_kw, batt_size_kwh, uploaded_file):
    # Convert text input to float
    solar_size_kw = float(solar_size_kw)
    batt_size_kwh = float(batt_size_kwh)
    
    # Save uploaded file to a temp file and pass its name
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_file_path = tmp_file.name

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



def calculate_data_and_price(option_a, option_b):
    # Example: Create different data based on selections

    cost_saving = 0  # base price
    solar_size_kw = 0
    batt_size_kwh = 0

    if option_a:
        solar_size_kw = 1.0 #st.text_input("Enter solar array size (kW):", value="1.0")
        cost_saving = 300
    if option_b:
        batt_size_kwh = 13.5 #st.text_input("Battery size (kWh):", value="13.5")
        cost_saving = 100
    if option_a & option_b:
        cost_savings = 400

    return solar_size_kw, batt_size_kwh, cost_saving

# Streamlit app layout
st.title("Electplan?")

if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Home"

def go_to_tab(tab_name):
    st.session_state.active_tab = tab_name



# Create tabs
tabs = st.tabs(["Home", "Explore Options", "Summary"])

# Content for each tab
print("Session_variable:",st.session_state.active_tab)


with tabs[0]:
    st.session_state.active_tab = "Home"
    st.header("Start")
    st.write("We give you transparency what greener options make sense for you. ")
    us_adress = st.text_input("Let's start as easy as input your US Adress", value="550 Moreland Way, 95054 Santa Clara")
    if st.button("Submit"):
        st.success(f"Sucessfully input your adress: "+str(us_adress))
        go_to_tab("Explore Options")

        

with tabs[1]:
    st.header("Energy Calculator")
    st.write("Based on your address we show you your options.")

    with st.spinner("Retrieve typical usage data for your address... please wait ⏳"):
        time.sleep(1)

    st.write("If you want personalized information, you can upload your data here to make it more accurate.")
    show_field = st.checkbox("Upload own usage data")

    csv_file = None
    if show_field:
        time.sleep(1)
        csv_file = st.file_uploader("Upload CSV File", type=["csv"])

    # Pre-calculate defaults (optional / placeholder values)
    st.write("")
    st.write("")
    if csv_file != None:
        solar_size_kw, batt_size_kwh, cost_saving = calculate_data_and_price(False, False)

        col1, col2, col3 = st.columns([1, 2, 1])

        # --- Left column: Checkboxes ---
        with col1:
            st.subheader("Options")
            option_a = st.checkbox("Photovoltaik")
            option_b = st.checkbox("Battery")

        # --- Show "Run Optimization" button only if CSV is uploaded ---
        with col2:
            solar_size_kw, batt_size_kwh, cost_saving = calculate_data_and_price(option_a, option_b)
            fig = process_submission(solar_size_kw, batt_size_kwh, csv_file)
            st.pyplot(fig)

        # --- Right column: Price ---
        with col3:
            old_price = 600
            st.metric(label="Todays Price", value=f"${old_price}")
            st.metric(label="New Price", value=f"${old_price - cost_saving}")

        # --- Always available button ---
        if st.button("Go to your 10-year Plan"):
            st.header("Your 10-year Electriplan")

with tabs[2]:
    st.header("Your 10-year Electriplan")
    st.write("Under development.")

    

    







