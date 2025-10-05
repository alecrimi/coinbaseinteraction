import os
import time
import pandas as pd
import requests
from dotenv import load_dotenv
import cbpro  # Coinbase Exchange client

# === Load environment variables ===
load_dotenv()
API_KEY = os.getenv("COINBASE_API_KEY")
API_SECRET = os.getenv("COINBASE_API_SECRET")
API_PASSPHRASE = os.getenv("COINBASE_API_PASSPHRASE")

if not all([API_KEY, API_SECRET, API_PASSPHRASE]):
    raise ValueError("Missing Coinbase API keys in .env file!")

# === Connect to Coinbase API ===
client = cbpro.AuthenticatedClient(API_KEY, API_SECRET, API_PASSPHRASE)

# === Parameters ===
PRODUCT_ID = "SOL-USD"  # trading pair
FAST_MA = 20
SLOW_MA = 50
TRADE_SIZE = 0.1  # in SOL
SLEEP_TIME = 60  # seconds between updates

# === Helper: fetch recent candle data ===
def get_recent_data():
    url = f"https://api.exchange.coinbase.com/products/{PRODUCT_ID}/candles"
    params = {"granularity": 60}  # 1-minute candles
    r = requests.get(url, params=params)
    data = r.json()
    df = pd.DataFrame(data, columns=["time", "low", "high", "open", "close", "volume"])
    df = df.sort_values("time")
    return df

# === Helper: place order ===
def place_order(side, size):
    try:
        order = client.place_market_order(product_id=PRODUCT_ID, side=side, size=size)
        print(f"✅ {side.upper()} order placed:", order)
    except Exception as e:
        print(f"⚠️ Order failed: {e}")

# === Main trading loop ===
def run_bot():
    position = None  # can be "long" or "flat"

    while True:
        try:
            df = get_recent_data()
            df["fast_ma"] = df["close"].rolling(FAST_MA).mean()
            df["slow_ma"] = df["close"].rolling(SLOW_MA).mean()

            last_fast = df["fast_ma"].iloc[-1]
            last_slow = df["slow_ma"].iloc[-1]
            last_price = df["close"].iloc[-1]

            print(f"Price: ${last_price:.2f} | Fast MA: {last_fast:.2f} | Slow MA: {last_slow:.2f}")

            # --- Decision logic ---
            if last_fast > last_slow and position != "long":
                print("📈 Buy signal!")
                place_order("buy", TRADE_SIZE)
                position = "long"

            elif last_fast < last_slow and position == "long":
                print("📉 Sell signal!")
                place_order("sell", TRADE_SIZE)
                position = "flat"

        except Exception as e:
            print(f"⚠️ Error: {e}")

        time.sleep(SLEEP_TIME)

# === Entry point ===
if __name__ == "__main__":
    print("🚀 Starting Momentum Bot for SOL-USD on Coinbase...")
    run_bot()
