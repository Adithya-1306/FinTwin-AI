import requests


def get_single_stock(symbol):
    symbol = symbol.upper().strip()

    # NSE ticker format on Yahoo Finance
    yahoo_symbol = symbol + ".NS"

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"

    params = {
        "range": "1d",
        "interval": "5m"
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        print(f"{symbol}: HTTP {response.status_code}")

        response.raise_for_status()

        data = response.json()

        result = data["chart"]["result"][0]
        meta = result["meta"]

        price = meta.get("regularMarketPrice")
        previous_close = meta.get("previousClose")

        if price is None:
            print(f"{symbol}: No price returned")
            return None

        change = 0
        change_percent = 0

        if previous_close:
            change = price - previous_close
            change_percent = (change / previous_close) * 100

        return {
            "symbol": symbol,
            "ticker": yahoo_symbol,
            "exchange": "NSE",

            "price": price,
            "previous_close": previous_close,

            "change": change,
            "change_percent": change_percent,

            "day_high": meta.get("regularMarketDayHigh"),
            "day_low": meta.get("regularMarketDayLow"),

            "year_high": meta.get("fiftyTwoWeekHigh"),
            "year_low": meta.get("fiftyTwoWeekLow"),

            "currency": meta.get("currency"),
            "market_state": meta.get("marketState"),

            "source": "Yahoo Finance"
        }

    except Exception as e:
        print(f"{symbol}: ERROR -> {e}")
        return None


def get_live_market_data(symbols):

    results = {}

    for symbol in symbols:

        data = get_single_stock(symbol)

        if data:
            results[symbol.upper()] = data

    return results