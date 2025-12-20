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

    # Hide Option Bias for Commodities
    if market == "Commodities":
        df = df.drop(columns=["Option Bias"], errors="ignore")

    # -------- ALERT ENGINE --------
    for _, row in df.iterrows():
        symbol = row["Symbol"]
        state = row["Trade State"]
        price = row["Price"]
        vwap = row["VWAP"]
        distance = abs(row["Distance %"])

        prev_state = st.session_state.last_confirmed_state.get(symbol)

        # Store last confirmed state
        if is_confirmed(state):
            st.session_state.last_confirmed_state[symbol] = state

        # ⚠️ VWAP LOST
        if prev_state and "BULLISH" in prev_state and price < vwap:
            key = alert_key(symbol, "VWAP_LOST_LONG")
            if key not in st.session_state.alerted_events:
                st.session_state.alerted_events.add(key)
                st.error(f"⚠️ {symbol} — VWAP LOST AFTER CONFIRMATION")

        if prev_state and "BEARISH" in prev_state and price > vwap:
            key = alert_key(symbol, "VWAP_LOST_SHORT")
            if key not in st.session_state.alerted_events:
                st.session_state.alerted_events.add(key)
                st.error(f"⚠️ {symbol} — VWAP LOST AFTER CONFIRMATION")

        # 🛑 OPPOSITE CONFIRMATION
        if prev_state and is_confirmed(state) and prev_state != state:
            key = alert_key(symbol, "OPPOSITE_CONFIRMED")
            if key not in st.session_state.alerted_events:
                st.session_state.alerted_events.add(key)
                st.error(f"🛑 {symbol} — OPPOSITE CONFIRMED | Bias Flip")

        # 📈 EXTENSION WARNING
        if prev_state and distance > 0.6:
            key = alert_key(symbol, "EXTENDED")
            if key not in st.session_state.alerted_events:
                st.session_state.alerted_events.add(key)
                st.warning(f"📈 {symbol} — EXTENDED FROM VWAP | Protect Profits")

    st.dataframe(df, use_container_width=True)

else:
    st.info("No valid VWAP signals at the moment.")
