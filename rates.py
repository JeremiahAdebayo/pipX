import requests

def get_rate(pair: str) -> float:
    """Fetch live mid-market rate from Frankfurter API."""
    base  = pair[:3]
    quote = pair[3:]
    url   = f"https://api.frankfurter.app/latest?from={base}&to={quote}"
    r     = requests.get(url, timeout=5)
    r.raise_for_status()
    data  = r.json()
    rate  = data["rates"].get(quote)
    if rate is None:
        raise ValueError(f"No rate found for {pair}")
    return rate