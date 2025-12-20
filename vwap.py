def calculate_vwap(df):
    df = df.copy()

    # Ensure single-level columns
    df = df.loc[:, ~df.columns.duplicated()]

    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VP"] = df["TP"] * df["Volume"]

    df["CumVP"] = df["VP"].cumsum()
    df["CumVol"] = df["Volume"].cumsum()

    df["VWAP"] = df["CumVP"] / df["CumVol"]

    return df
