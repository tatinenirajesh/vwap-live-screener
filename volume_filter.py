import yfinance as yf


def has_high_relative_volume(symbol, lookback_days=5, threshold=1.5):
    """
    Returns True if today's intraday volume
    is significantly higher than recent average
    """

    try:
        df = yf.download(
            symbol,
            period=f"{lookback_days}d",
            interval="5m",
            progress=False
        )

        if df.empty:
            return False

        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)

        today_date = df.index[-1].date()

        today = df[df.index.date == today_date]
        past = df[df.index.date < today_date]

        if today.empty or past.empty:
            return False

        today_vol = today["Volume"].sum()
        avg_vol = (
            past.groupby(past.index.date)["Volume"]
            .sum()
            .mean()
        )

        if avg_vol == 0:
            return False

        rvol = today_vol / avg_vol
        return rvol >= threshold

    except Exception:
        return False
