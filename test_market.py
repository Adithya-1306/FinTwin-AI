from market_data import get_live_market_data
import json

with open("stocks.json", "r") as f:
    stocks = json.load(f)

data = get_live_market_data(stocks)

print("Requested:", len(stocks))
print("Received:", len(data))

for symbol, stock in list(data.items())[:10]:
    print(symbol, stock["price"])