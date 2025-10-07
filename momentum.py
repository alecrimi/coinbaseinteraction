import os
import time
import json
import hmac
import hashlib
import base64
import requests
import pandas as pd
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
API_KEY = os.getenv("COINBASE_API_KEY")
API_SECRET = os.getenv("COINBASE_API_SECRET")

if not all([API_KEY, API_SECRET]):
    raise ValueError("❌ Missing Coinbase API keys in .env file!")

# === Configuration ===
PRODUCT_ID = "SOL-USD"
FAST_MA = 20
SLOW_MA = 50
TRADE_SIZE = 0.1  # in SOL
SLEEP_TIME = 60  # seconds
PAPER_TRADING = True  # ← Change to False when you want to go LIVE

BASE_URL = "https://api.coinbase.com"  # For live trading
# BASE_URL = "https://api.sandbox.coinbase.com"  # For sandbox testing

# === Helper: sign Advanced Trade API requests ===
def sign_request(method, request_path, body=""):
    timestamp = str(int(time.time()))
    message = timestamp + method + request_path + body
    hmac_key = base64.b64decode(API_SECRET)
    signature = hmac.new(hmac_key, message.encode("utf-8"), hashlib.sha256)
    signature_b64 = base64.b64encode(signature.digest()).decode("utf-8")
    return {
        "CB-ACCESS-KEY": API_KEY,
        "CB-ACCESS-SIGN": signature_b64,
        "CB-ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json",
    }

# === Get recent price candles ===
def get_recent_data():
    # Use public endpoint (no API key needed)
    url = f"https://api.coinbase.com/api/v3/brokerage/products/{PRODUCT_ID}/candles?granularity=ONE_MINUTE"
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"Error fetching data: {r.text}")
    data = r.json().get("candles", [])
    if not data:
        raise Exception("No candle data received")
    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["start"])
    df["close"] = df["close"].astype(float)
    df = df.sort_values("time")
    return df

# === Place buy/sell order ===
def place_order(side, size):
    if PAPER_TRADING:
        print(f"🧪 PAPER TRADE: Would place {side.upper()} order for {size} SOL")
        return

    url = f"{BASE_URL}/api/v3/brokerage/orders"
    order = {
        "client_order_id": str(int(time.time())),
        "product_id": PRODUCT_ID,
        "side": side,
        "order_configuration": {
            "market_market_ioc": {
                "base_size": str(size)
            }
        },
    }
    body = json.dumps(order)
    headers = sign_request("POST", "/api/v3/brokerage/orders", body)
    r = requests.post(url, headers=headers, data=body)

    if r.status_code == 200:
        print(f"✅ {side.upper()} order placed:", r.json())
    else:
        print(f"⚠️ Order failed: {r.status_code} {r.text}")

# === Main trading loop ===
def run_bot():
    position = None  # "long" or "flat"
    while True:
        try:
            df = get_recent_data()
            df["fast_ma"] = df["close"].rolling(FAST_MA).mean()
            df["slow_ma"] = df["close"].rolling(SLOW_MA).mean()

            last_fast = df["fast_ma"].iloc[-1]
            last_slow = df["slow_ma"].iloc[-1]
            last_price = df["close"].iloc[-1]

            print(f"💰 Price: ${last_price:.2f} | Fast MA: {last_fast:.2f} | Slow MA: {last_slow:.2f}")

            # === Strategy Logic ===
            if last_fast > last_slow and position != "long":
                print("📈 Buy signal!")
                place_order("BUY", TRADE_SIZE)
                position = "long"

            elif last_fast < last_slow and position == "long":
                print("📉 Sell signal!")
                place_order("SELL", TRADE_SIZE)
                position = "flat"

        except Exception as e:
            print(f"⚠️ Error: {e}")

        time.sleep(SLEEP_TIME)

# === Entry point ===
if __name__ == "__main__":
    print("🚀 Starting Momentum Bot for SOL-USD on Coinbase Advanced Trade API...")
    run_bot()
