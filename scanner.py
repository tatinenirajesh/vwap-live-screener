import yfinance as yf
from vwap import calculate_vwap
from option_selector import suggest_option
from data_oanda import fetch_oanda


# -------------------------------------------------
# Equity-style pullback confirmation (Index / Stocks)
# -------------------------------------------------
def pullback_confirmed(df, direction):
    c1 = df.iloc[-3]
    c2 = df.iloc[-2]

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


# -------------------------------------------------
# Commodity VWAP rejection logic (Gold / BTC)
# -------------------------------------------------
def vwap_rejection_commodity(df, direction):
    candle = df.iloc[-2]  # last completed candle

    body = abs(candle["Close"] - candle["Open"])

    if direction == "Bullish":
        lower_wick = min(candle["Open"], candle["Close"]) - candle["Low"]
        return (
            candle["Low"] < candle["VWAP"] and
            candle["Close"] > candle["VWAP"] and
            lower_wick > body
        )

    if direction == "Bearish":
        upper_wick = candle["High"] - max(candle["Open"], candle["Close"])
        return (
            candle["High"] > candle["VWAP"] and
            candle["Close"] < candle["VWAP"] and
            upper_wick > body
        )

    return False


# -------------------------------------------------
# Momentum validation (market-specific)
# -------------------------------------------------
def momentum_valid(df, signal, distance_pct, vol_ratio, market):
    if market != "Commodities" and vol_ratio < 1.3:
        return False

    if not (0.3 <= abs(distance_pct) <= 0.8):
        return False

    candle_count = 3 if market == "Commodities" else 6
    recent = df.iloc[-candle_count:]

    if signal == "Bullish":
        return all(recent["Close"] > recent["VWAP"])

    if signal == "Bearish":
        return all(recent["Close"] < recent["VWAP"])

    return False


# -------------------------------------------------
# Main scanner
# -------------------------------------------------
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

    # ---------------- CONTEXT ----------------
    distance_pct = ((price - vwap) / vwap) * 100
    vwap_slope = df["VWAP"].iloc[-1] - df["VWAP"].iloc[-5]

    # ---------------- VOLUME ----------------
    recent_vol = df["Volume"].iloc[-3:-1].mean()
    avg_vol = df["Volume"].iloc[-21:-1].mean()
    vol_ratio = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 0

    # ---------------- SIGNAL ----------------
    if price > vwap and vwap_slope > 0:
        signal = "Bullish"
    elif price < vwap and vwap_slope < 0:
        signal = "Bearish"
    else:
        signal = "WAIT"

    previous_trade = trade_book.get(symbol)

    # ---------------- EXIT ----------------
    if previous_trade:
        side = previous_trade["side"]

        if side == "LONG" and price < vwap:
            trade_book.pop(symbol)
            return {
                "Symbol": symbol,
                "Engine": previous_trade["engine"],
                "Trade State": "EXIT — VWAP LOST",
                "Price": round(price, 2),
                "VWAP": round(vwap, 2),
                "Volume Ratio": vol_ratio
            }

        if side == "SHORT" and price > vwap:
            trade_book.pop(symbol)
            return {
                "Symbol": symbol,
                "Engine": previous_trade["engine"],
                "Trade State": "EXIT — VWAP LOST",
                "Price": round(price, 2),
                "VWAP": round(vwap, 2),
                "Volume Ratio": vol_ratio
            }

        return {
            "Symbol": symbol,
            "Engine": previous_trade["engine"],
            "Trade State": f"ACTIVE {side} ({previous_trade['engine']})",
            "Price": round(price, 2),
            "VWAP": round(vwap, 2),
            "Volume Ratio": vol_ratio
        }

    # ---------------- VWAP ENGINE ----------------
    if market == "Commodities":
        confirmed_vwap = (
            abs(distance_pct) < 0.30 and
            signal in ["Bullish", "Bearish"] and
            vwap_rejection_commodity(df, signal)
        )
    else:
        confirmed_vwap = (
            abs(distance_pct) < 0.15 and
            signal in ["Bullish", "Bearish"] and
            pullback_confirmed(df, signal) and
            vol_ratio >= 1.2
        )

    if confirmed_vwap:
        trade_book[symbol] = {
            "side": "LONG" if signal == "Bullish" else "SHORT",
            "engine": "VWAP"
        }

        return {
            "Symbol": symbol,
            "Engine": "VWAP",
            "Trade State": "ACTIVE (VWAP Pullback)",
            "Price": round(price, 2),
            "VWAP": round(vwap, 2),
            "Volume Ratio": vol_ratio
        }

    # ---------------- MOMENTUM ENGINE ----------------
    if signal in ["Bullish", "Bearish"] and momentum_valid(
        df, signal, distance_pct, vol_ratio, market
    ):
        trade_book[symbol] = {
            "side": "LONG" if signal == "Bullish" else "SHORT",
            "engine": "MOMENTUM"
        }

        return {
            "Symbol": symbol,
            "Engine": "MOMENTUM",
            "Trade State": "ACTIVE (Momentum)",
            "Price": round(price, 2),
            "VWAP": round(vwap, 2),
            "Volume Ratio": vol_ratio
        }

    # ---------------- NO TRADE ----------------
    return {
        "Symbol": symbol,
        "Engine": "-",
        "Trade State": "WAIT",
        "Price": round(price, 2),
        "VWAP": round(vwap, 2),
        "Volume Ratio": vol_ratio
    }
