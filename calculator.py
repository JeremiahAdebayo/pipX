PIP_SIZE = {
    "USDJPY": 0.01, "EURJPY": 0.01, "GBPJPY": 0.01,
    "AUDJPY": 0.01, "CADJPY": 0.01, "CHFJPY": 0.01,
    "XAUUSD": 0.10, "XAGUSD": 0.001,
}
DEFAULT_PIP = 0.0001

CONTRACT_SIZE = {
    "XAUUSD": 100,
    "XAGUSD": 5000,
}
DEFAULT_CONTRACT = 100_000


def get_pip_size(pair: str) -> float:
    return PIP_SIZE.get(pair, DEFAULT_PIP)


def price_to_pips(pair: str, entry: float, sl: float) -> float:
    """Convert entry/SL price distance into pips."""
    pip = get_pip_size(pair)
    return round(abs(entry - sl) / pip, 1)


def get_pip_value_per_std_lot(pair: str, rate: float) -> float:
    """
    Pip value in USD for ONE standard lot.

    - USD-quoted (EURUSD, GBPUSD, AUDUSD, NZDUSD): fixed $10
    - USD-based  (USDJPY, USDCHF, USDCAD):          (pip / rate) * lot
    - Cross pair (EURGBP, EURJPY, GBPJPY ...):       (pip / rate) * lot  [approximation]
    - Metals: uses their own contract size
    """
    base  = pair[:3]
    quote = pair[3:]
    pip   = get_pip_size(pair)
    lot   = CONTRACT_SIZE.get(pair, DEFAULT_CONTRACT)

    if quote == "USD":
        # pip value is always pip * lot in USD — no rate needed
        return pip * lot          # 0.0001 * 100,000 = $10 for forex

    elif base == "USD":
        # e.g. USD/JPY: 1 pip move = pip/rate USD
        return (pip / rate) * lot

    else:
        # Cross pair: quote currency is not USD
        # pip value in quote currency = pip * lot
        # convert to USD using quote/USD rate (passed in as `rate` = base/quote)
        # approximation: pip_val_usd ≈ pip * lot / rate
        return (pip / rate) * lot


def calculate_lot_sizes(
    risk_amount: float,
    sl_pips: float,
    spread_pips: float,
    pip_value_per_std_lot: float,
) -> dict:
    """
    Core formula:
        standard lot = risk / (effective_sl_pips * pip_value_per_std_lot)
        cent lot     = standard lot / 0.01   (JustMarkets / cent account)

    effective_sl includes spread so you don't over-risk.
    """
    if sl_pips <= 0:
        raise ValueError("Stop loss must be greater than zero.")
    if pip_value_per_std_lot <= 0:
        raise ValueError("Pip value must be greater than zero.")

    effective_sl = sl_pips + spread_pips   # sharper calculation

    standard = risk_amount / (effective_sl * pip_value_per_std_lot)

    # Cent lot = how many 0.01-lot units fit into standard
    # i.e.  standard / 0.01
    cent     = standard / 0.01    # = standard * 100

    # Mini = standard / 0.1
    mini     = standard / 0.1

    # Micro = standard / 0.001  (nano on some brokers)
    micro    = standard / 0.001

    # Reality-check: pip value at calculated size
    pip_value_at_size = standard * pip_value_per_std_lot

    return {
        "standard":          round(standard, 5),
        "cent_lot":          round(cent, 2),        # MT4 cent account input
        "mini":              round(mini, 3),
        "micro":             round(micro, 3),
        "units":             round(standard * DEFAULT_CONTRACT),
        "effective_sl":      round(effective_sl, 1),
        "pip_value_at_size": round(pip_value_at_size, 6),
        "total_risk_check":  round(effective_sl * pip_value_at_size, 4),
    }