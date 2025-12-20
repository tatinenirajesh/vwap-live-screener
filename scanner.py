import yfinance as yf
from vwap import calculate_vwap
from option_selector import suggest_option
from data_oanda import fetch_oanda


def pullback_confirmed(df, direction):
    """
    Checks last 2 completed candles for pullback confirmation
    """
    c1 = df.iloc[-3]  # pullback candle
    c2 = df.iloc[-2]  # confirmation candle

    if direction == "Bullish":
        return (
            c1["Close"] < c1["Open"] and
            c2["Close"] > c2["Open"] and
            c1["Close"] > c1["VWAP"] and
            c2["Close"] > c2["VWAP"]
        )

    if direction == "Bearish":
        return (
            c1["Close"] > c1["Open"] and
            c2["Close"] < c2["Open"] and
            c1["Close"] < c1["VWAP"] and
            c2["Close"] < c2["VWAP"]
        )

    return False


def scan_symbol(symbol, market):
    # ---------------- DATA FETCH ----------------
    if market == "Commodities":
        df = fetch_oanda(symbol)
    else:
        df = yf.download(
            symbol,
            interval="5m",
            period="1d",
            progress=False
        )

    if df is None or df.empty or len(df) < 10:
        return None

    # Fix Yahoo multi-index columns
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    # ---------------- VWAP ----------------
    df = calculate_vwap(df)
    last = df.iloc[-1]

    price = float(last["Close"])
    vwap = float(last["VWAP"])

    # ---------------- CONTEXT ----------------
    distance_pct = ((price - vwap) / vwap) * 100
    vwap_slope = df["VWAP"].iloc[-1] - df["VWAP"].iloc[-5]

    # ---------------- SIGNAL ----------------
    if price > vwap and vwap_slope > 0:
        signal = "Bullish"
    elif price < vwap and vwap_slope < 0:
        signal = "Bearish"
    else:
        signal = "WAIT"

    # ---------------- TRADE STATE ----------------
    confirmed = False

    if abs(distance_pct) < 0.15 and signal in ["Bullish", "Bearish"]:
        confirmed = pullback_confirmed(df, signal)

    if abs(distance_pct) > 0.8:
        trade_state = "AVOID (Extended)"

    elif signal == "WAIT":
        trade_state = "WAIT"

    elif abs(distance_pct) < 0.15:
        if confirmed:
            trade_state = f"{signal.upper()} Pullback (CONFIRMED)"
        else:
            trade_state = f"{signal.upper()} Pullback (WAIT)"

    else:
        trade_state = f"{signal.upper()} Continuation (RISKY)"

    # ---------------- OPTION SELECTOR ----------------
    option_bias = None
    if market in ["Index", "Stocks"] and "CONFIRMED" in trade_state:
        option_bias = suggest_option(symbol, price, signal, abs(distance_pct))

    return {
        "Symbol": symbol,
        "Signal": signal,
        "Price": round(price, 2),
        "VWAP": round(vwap, 2),
        "Distance %": round(distance_pct, 2),
        "VWAP Slope": round(vwap_slope, 4),
        "Trade State": trade_state,
        "Option Bias": option_bias
    }
