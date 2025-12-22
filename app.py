import streamlit as st
import pandas as pd

from scanner import scan_symbol
from universe import INDEX, NIFTY_50, COMMODITIES
from streamlit_autorefresh import st_autorefresh
from alerts import is_confirmed, alert_key
from telegram_alerts import send_telegram_alert
from volume_filter import has_high_relative_volume
from universe import NIFTY_50



# ---------------- UI CONFIG ----------------
st.set_page_config(
    page_title="VWAP Live Screener & Trade Bias Dashboard",
    layout="wide"
)

# ---------------- SESSION STATE ----------------
if "last_confirmed_state" not in st.session_state:
    st.session_state.last_confirmed_state = {}

if "alerted_events" not in st.session_state:
    st.session_state.alerted_events = set()

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=60_000, key="vwap_refresh")

st.title("VWAP Live Screener & Option Selector")

st.markdown(
    """
🟢 **Bullish** → Buy / Buy on pullback  
🔴 **Bearish** → Sell / Sell on pullback  

_VWAP-based screener | Manual execution only_
"""
)

# ---------------- MARKET TOGGLE ----------------
market = st.radio(
    "Select Market",
    ["Index", "Stocks", "Commodities"],
    horizontal=True
)

if market == "Index":
    symbols = INDEX
elif market == "Stocks":
    symbols = NIFTY_50
else:
    symbols = COMMODITIES

# ---------------- SCAN ----------------
results = []

with st.spinner("Scanning symbols..."):
    for symbol in symbols:
    # High volume filter only for stocks
    	if market == "Stocks":
       	   if not has_high_relative_volume(symbol):
               continue

    res = scan_symbol(symbol, market)
    if res:
        results.append(res)


# ---------------- DISPLAY + ALERTS ----------------
if results:
    df = pd.DataFrame(results)

    if market == "Commodities":
        df = df.drop(columns=["Option Bias"], errors="ignore")

    confirmed_df = df[df["Trade State"].str.contains("CONFIRMED", na=False)]
    setup_df = df[df["Trade State"].str.contains("Setup Forming", na=False)]

    if not confirmed_df.empty:
        st.subheader("✅ CONFIRMED TRADES")
        st.dataframe(confirmed_df, use_container_width=True)

    if not setup_df.empty:
        st.subheader("⏳ SETUP FORMING — WATCHLIST")
        st.dataframe(setup_df, use_container_width=True)

    if confirmed_df.empty and setup_df.empty:
        st.info("No actionable VWAP setups right now.")

else:
    st.info("No valid VWAP signals at the moment.")
