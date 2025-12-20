def is_confirmed(state):
    return state is not None and "CONFIRMED" in state


def alert_key(symbol, alert_type):
    return f"{symbol}-{alert_type}"
