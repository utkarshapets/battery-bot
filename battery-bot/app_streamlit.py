import streamlit as st
import pandas as pd
import pathlib
import os
import plotly.express as px
from app import get_data

def get_package_root() -> pathlib.Path:
    return pathlib.Path(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="My App",
    layout="wide"  
)

# Streamlit app layout
st.title("BatteryBot 🤖⚡️")

def read_csv_personal_usage():


    # Hardcoded for now
    file_path = get_package_root() / "data" / "pge-e78ff14c-c8c0-11ec-8cc7-0200170a3297-DailyUsageData" / "pge_electric_usage_interval_data_Service 1_1_2024-02-01_to_2025-01-31.csv"

    class CSVFile:
        def __init__(self, name, content):
            self.name = name
            self.content = content

    with open(file_path, "r", encoding="utf-8") as f:
        csv_file = CSVFile(name=file_path, content=f.read())
    return csv_file


def run_scenario(
        solar_size_kw = 0, 
        batt_size_kwh = 0, 
        ev_charging_present = "No",
        hvac_heat_pump_present = "No",
        kwh_price = 0.30, # Assumption
        address = "",
        hvac_heating_capacity = 0.0
):
    """ Output average kwh consumption per month"""

    # Default values

    csv_file = read_csv_personal_usage()
    
    all_input = get_data(       
        address,
        solar_size_kw,
        batt_size_kwh,
        ev_charging_present,
        hvac_heat_pump_present,
        hvac_heating_capacity,
        csv_file)
    
    df = all_input

    # Function to filter data to last year
    def filter_last_year(df):
        max_date = df.index.max().normalize()
        one_year_ago = max_date - pd.DateOffset(years=1)
        return df[df.index >= one_year_ago]

    # Filter to last year
    df_last_year = filter_last_year(df)

    #ATTENTION: is this the right column? The cost look not correct
    df_last_year["cost"] = df_last_year['P_grid']*kwh_price

    return df_last_year



# Create tabs
tabs = st.tabs(["Home", "BatteryBot Insights 🤖"])

with tabs[0]:
    st.header("Start")
    st.write("We give you transparency what greener options make sense for you. ")
    address = st.text_input("Let's start as easy as input your US Adress", value="550 Moreland Way, 95054 Santa Clara")
    option = st.selectbox('(Optional) Get a even more personalized for you by retrieving YOUR last years energy data.:',('Yes', 'No'), index=1)
    if option == "No":
        csv_file = read_csv_personal_usage()
    else:
        csv_file = st.file_uploader("Upload CSV File", type=["csv"])

def select_scenario(option_pv, option_bat, option_bev, option_hvac):
    """ Select scenarios, currently preselected to computation time"""

    df_default = run_scenario(solar_size_kw = 0)

    if (option_pv == True) & (option_bat==False) & (option_bev==False) & (option_hvac==False): 
        df = run_scenario(solar_size_kw = 1.0) # Assumption for optimal solar power
    elif (option_pv == True) & (option_bat==True) & (option_bev==False) & (option_hvac==False):
        df = run_scenario(solar_size_kw = 1.0, 
                     batt_size_kwh = 13.5)
    elif (option_pv == True) & (option_bat==True) & (option_bev==True) & (option_hvac==False):
        df = run_scenario(solar_size_kw = 1.0, 
                     batt_size_kwh = 13.5, 
                     ev_charging_present = "Yes",
                     )
    elif (option_pv == True) & (option_bat==True) & (option_bev==True) & (option_hvac==True):
        df = run_scenario(solar_size_kw = 13.0, 
                     batt_size_kwh = 13.5, 
                     ev_charging_present = "Yes",
                     hvac_heat_pump_present = "Yes",
                    hvac_heating_capacity = 1.0 
                     ) 
    else:
        df = df_default
    return df_default, df       

with tabs[1]:
    st.header("Your Battery Bot Analysis")

    col1, col2, col3 = st.columns([1, 2, 1])

    # Select Scenario
    with col1:
        st.subheader("Options")
        option_pv = st.checkbox("Solar Power")
        option_bat = st.checkbox("Battery")
        option_bev = st.checkbox("Electric Vehicle")
        option_hvac = st.checkbox("Heat Pump HVAC")
        df_default, df = select_scenario(
            option_pv,
            option_bat,
            option_bev,
            option_hvac
            )

    # Caclulate Monthly Costs
    with col2:
        st.title('Monthly Cost Overview')
        monthly_cost = df['cost'].resample('M').sum().reset_index()
        monthly_cost['Month'] = monthly_cost['Datetime'].dt.strftime('%B %Y')
        fig = px.bar(monthly_cost, x='Month', y='cost', title='Monthly Costs (Aggregated)', labels={'cost': 'Cost in USD'}, color='cost', height=500)

        st.plotly_chart(fig, use_container_width=True)


    #  Price total
    with col3:
        old_monthly_cost = df_default["cost"].sum()/12
        new_monthly_cost = df['cost'].sum()/12
        ten_year_savings = (new_monthly_cost - new_monthly_cost)*12*10 
        st.metric(label="Today's Monthly Price", value=f"${old_monthly_cost:.2f}")
        st.metric(label="New Monthly Price", value=f"${new_monthly_cost:.2f}")
        st.metric(label="Savings over 10 years", value=f"${ten_year_savings:.2f}")



    

    







