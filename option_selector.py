def suggest_option(symbol, price, signal, distance_pct):
    """
    Returns ATM / ITM option suggestion based on VWAP distance
    Only for Index & Stocks
    """

    # Strike step
    if symbol == "^NSEI":
        step = 50
    elif symbol == "^BANKNIFTY":
        step = 100
    else:
        step = 10  # stocks

    atm = round(price / step) * step

    # Decide ATM vs ITM
    if distance_pct < 0.15:
        style = "ITM"
    else:
        style = "ATM"

    if signal == "Bullish":
        strike = atm if style == "ATM" else atm - step
        return f"CALL {strike} ({style})"

    if signal == "Bearish":
        strike = atm if style == "ATM" else atm + step
        return f"PUT {strike} ({style})"

    return None
