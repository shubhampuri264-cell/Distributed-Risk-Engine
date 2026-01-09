import streamlit as st
import pandas as pd
import requests
import plotly.figure_factory as ff

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Distributed Risk Engine", layout="wide")

st.title("Distributed Risk Engine")

tabs = st.tabs(["Data Ingestion", "Simulation", "Stress Test"])

with tabs[0]:
    st.header("Data Ingestion")
    col1, col2 = st.columns(2)
    with col1:
        tickers_input = st.text_input("Tickers (comma separated)", "AAPL,MSFT")
        start_date = st.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
        end_date = st.date_input("End Date", value=pd.to_datetime("2023-12-31"))
        
        if st.button("Fetch Data"):
            tickers = [t.strip() for t in tickers_input.split(",")]
            payload = {
                "tickers": tickers,
                "start_date": str(start_date),
                "end_date": str(end_date)
            }
            with st.spinner("Fetching data via API..."):
                try:
                    response = requests.post(f"{API_URL}/ingest", json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "success":
                            st.success(f"Success: {data.get('rows')} rows loaded.")
                        else:
                            st.warning(data.get("message"))
                    else:
                        st.error(f"API Error: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to API. Please ensure it is running.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        st.subheader("Stored Data")
        st.info("Direct DB access from dashboard is disabled in API mode (cleaner architecture).")
        # In a real app, we'd add an endpoint to fetch data for display.
        # Check if we can just show a placeholder or add a 'preview' endpoint later.

with tabs[1]:
    st.header("Monte Carlo Simulation")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        sim_ticker = st.text_input("Ticker", "AAPL")
        sim_initial = st.number_input("Initial Price", value=100.0)
        sim_vol = st.slider("Volatility (Annual)", 0.05, 1.0, 0.20)
        sim_drift = st.slider("Drift (Annual)", -0.2, 0.5, 0.05)
        sim_days = st.number_input("Days", value=252)
        sim_paths = st.number_input("Paths", value=10000)
        
        run_sim = st.button("Run Simulation")
        
    with col2:
        if run_sim:
            payload = {
                "ticker": sim_ticker,
                "initial_price": sim_initial,
                "volatility": sim_vol,
                "drift": sim_drift,
                "days": int(sim_days),
                "paths": int(sim_paths)
            }
            with st.spinner("Running Simulation via API..."):
                try:
                    response = requests.post(f"{API_URL}/simulate", json=payload)
                    if response.status_code == 200:
                        res = response.json()
                        st.metric("Mean Final Price", f"{res['mean_price']:.2f}")
                        
                        m1, m2 = st.columns(2)
                        m1.metric("VaR (95%)", f"{res['var_95']:.2f}")
                        m2.metric("CVaR (95%)", f"{res['cvar_95']:.2f}")
                        
                        st.json(res)
                    else:
                        st.error(f"API Error: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to API. Please ensure it is running.")

with tabs[2]:
    st.header("Stress Tests")
    st.write("Simple scenario analysis.")
    st.info("Stress test endpoints coming soon to API.")
