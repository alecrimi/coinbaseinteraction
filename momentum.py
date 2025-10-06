import os, time, hmac, hashlib, base64, json, requests, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# === Load keys ===
load_dotenv()
API_KEY = os.getenv("COINBASE_API_KEY")
API_SECRET = os.getenv("COINBASE_API_SECRET")
if not (API_KEY and API_SECRET):
    raise ValueError("❌ Missing API_KEY or API_SECRET in .env file")

# === API endpoints ===
API_URL = "https://api.coinbase.com/api/v3"
PRODUCT_ID = "SOL-USD"

# === Strategy parameters ===
FAST_MA = 20
SLOW_MA = 50
TRADE_SIZE = "0.1"  # in SOL
SLEEP_TIME = 60

# --- Sign requests ---
def sign_request(method: str, path: str, body: dict | None = None):
    timestamp = str(int(time.time()))
    message = timestamp + method + path + (json.dumps(body) if body else "")
    secret_decoded = base64.b64decode(API_SECRET)
    signature = hmac.new(secret_decoded, message.encode(), hashlib.sha256)
    signature_b64 = base64.b64encode(signature.digest()).decode()
    headers = {
        "CB-ACCESS-KEY": API_KEY,
        "CB-ACCESS-SIGN": signature_b64,
        "CB-ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json",
    }
    return headers

# --- Get recent candles (1 min) ---
def get_candles():
    url = f"{API_URL}/brokerage/products/{PRODUCT_ID}/candles?granularity=ONE_MINUTE"
    r = requests.get(url, headers=sign_request("GET", f"/api/v3/brokerage/products/{PRODUCT_ID}/candles"))
    data = r.json().get("candles", [])
    df = pd.DataFrame(data)
    df["close"] = df["close"].astype(float)
    df = df.sort_values("start")
    return df

# --- Place market order ---
def place_order(side: str, size: str):
    body = {
        "client_order_id": str(int(time.time()*1000)),
        "product_id": PRODUCT_ID,
        "side": side,
        "order_configuration": {"market_market_ioc": {"base_size": size}},
    }
    path = "/api/v3/brokerage/orders"
    headers = sign_request("POST", path, body)
    resp = requests.post(API_URL + "/brokerage/orders", headers=headers, json=body)
    print(f"{side.upper()} order →", resp.status_code, resp.text)

# --- Main loop ---
def run_bot():
    position = "flat"
    while True:
        try:
            df = get_candles()
            df["fast_ma"] = df["close"].rolling(FAST_MA).mean()
            df["slow_ma"] = df["close"].rolling(SLOW_MA).mean()
            last_fast, last_slow, last_price = df.iloc[-1][["fast_ma","slow_ma","close"]]
            print(f"{datetime.utcnow()} | Price ${last_price:.2f} | Fast {last_fast:.2f} | Slow {last_slow:.2f}")

            if last_fast > last_slow and position != "long":
                print("📈 Buy signal!")
                place_order("BUY", TRADE_SIZE)
                position = "long"

            elif last_fast < last_slow and position == "long":
                print("📉 Sell signal!")
                place_order("SELL", TRADE_SIZE)
                position = "flat"

        except Exception as e:
            print("⚠️ Error:", e)

        time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    print("🚀 Starting Momentum Bot (Advanced Trade API)…")
    run_bot()
