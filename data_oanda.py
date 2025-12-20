import requests
import pandas as pd
import streamlit as st


OANDA_API_KEY = st.secrets["OANDA_API_KEY"]
ACCOUNT_TYPE = st.secrets["ACCOUNT_TYPE"]

BASE_URL = (
    "https://api-fxpractice.oanda.com"
    if ACCOUNT_TYPE == "practice"
    else "https://api-fxtrade.oanda.com"
)

def fetch_oanda(symbol):
    instrument_map = {
        "XAUUSD": "XAU_USD",
        "BTCUSD": "BTC_USD"
    }

    instrument = instrument_map.get(symbol)
    if not instrument:
        return None

    url = f"{BASE_URL}/v3/instruments/{instrument}/candles"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params = {
        "granularity": "M5",
        "count": 120,
        "price": "M"
    }

    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()

    rows = []
    for c in r.json()["candles"]:
        if not c["complete"]:
            continue
        rows.append({
            "Open": float(c["mid"]["o"]),
            "High": float(c["mid"]["h"]),
            "Low": float(c["mid"]["l"]),
            "Close": float(c["mid"]["c"]),
            "Volume": int(c["volume"])
        })

    return pd.DataFrame(rows)
