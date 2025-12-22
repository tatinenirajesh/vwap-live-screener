import yfinance as yf
from vwap import calculate_vwap
from option_selector import suggest_option
from data_oanda import fetch_oanda


# ---------------- PULLBACK CONFIRMATION ----------------
def pullback_confirmed(df, direction):
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


# ---------------- MAIN SCANNER ----------------
def scan_symbol(symbol, market, trade_book):

    # ---------------- DATA FETCH ----------------
    if market == "Commodities":
        df = fetch_oanda(symbol)
    else:
        df = yf.download(symbol, interval="5m", period="1d", progress=False)

    if df is None or df.empty or len(df) < 25:
        return None

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    df = calculate_vwap(df)

    last = df.iloc[-1]
    price = float(last["Close"])
    vwap = float(last["VWAP"])

    # ---------------- VOLUME FILTER ----------------
    recent_vol = df["Volume"].iloc[-3:-1].mean()   # last 2 completed candles
    avg_vol = df["Volume"].iloc[-21:-1].mean()     # last 20 candles
    vol_ratio = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 0

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

    # ---------------- ACTIVE TRADE MANAGEMENT ----------------
    if symbol in trade_book:
        trade = trade_book[symbol]
        side = trade["side"]

        # EXIT: VWAP lost
        if side == "LONG" and price < vwap:
            del trade_book[symbol]
            return {
                "Symbol": symbol,
                "Trade State": "EXIT LONG (VWAP LOST)",
                "Price": round(price, 2),
                "VWAP": round(vwap, 2),
                "Volume Ratio": vol_ratio
            }

        if side == "SHORT" and price > vwap:
            del trade_book[symbol]
            return {
                "Symbol": symbol,
                "Trade State": "EXIT SHORT (VWAP LOST)",
                "Price": round(price, 2),
                "VWAP": round(vwap, 2),
                "Volume Ratio": vol_ratio
            }

        # Momentum fade
        if vol_ratio < 0.7:
            trade_state = f"ACTIVE {side} — MOMENTUM FADING"
        elif abs(distance_pct) > 0.8:
            trade_state = f"ACTIVE {side} — EXTENDED"
        else:
            trade_state = f"ACTIVE {side} — HEALTHY"

        return {
            "Symbol": symbol,
            "Trade State": trade_state,
            "Price": round(price, 2),
            "VWAP": round(vwap, 2),
            "Volume Ratio": vol_ratio
        }

    # ---------------- ENTRY LOGIC (ASSUMED ENTRY) ----------------
    confirmed = (
        abs(distance_pct) < 0.15
        and signal in ["Bullish", "Bearish"]
        and vol_ratio >= 1.2
        and pullback_confirmed(df, signal)
    )

    if confirmed:
        trade_book[symbol] = {
            "side": "LONG" if signal == "Bullish" else "SHORT",
            "entry_price": price,
            "entry_vwap": vwap
        }

        trade_state = f"ACTIVE {'LONG' if signal == 'Bullish' else 'SHORT'} (VWAP Pullback)"

    else:
        if signal in ["Bullish", "Bearish"] and abs(distance_pct) <= 0.30:
            trade_state = f"{signal} Setup Forming (WAIT)"
        elif abs(distance_pct) > 0.8:
            trade_state = "AVOID (Extended)"
        else:
            trade_state = "WAIT"

    option_bias = None
    if market in ["Index", "Stocks"] and confirmed:
        option_bias = suggest_option(symbol, price, signal, abs(distance_pct))

    return {
        "Symbol": symbol,
        "Trade State": trade_state,
        "Price": round(price, 2),
        "VWAP": round(vwap, 2),
        "Distance %": round(distance_pct, 2),
        "Volume Ratio": vol_ratio,
        "Option Bias": option_bias
    }
