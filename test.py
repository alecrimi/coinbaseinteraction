import requests, time, hmac, hashlib, base64, os
from datetime import datetime

API_KEY = os.getenv("COINBASE_API_KEY")
API_SECRET = os.getenv("COINBASE_API_SECRET")
API_PASSPHRASE = os.getenv("COINBASE_API_PASSPHRASE")
BASE_URL = "https://api.coinbase.com/api/v3/brokerage"  # Advanced Trade base URL

def sign(message):
    return base64.b64encode(
        hmac.new(base64.b64decode(API_SECRET), message.encode(), hashlib.sha256).digest()
    ).decode()

def headers(path, method="GET", body=""):
    timestamp = str(int(time.time()))
    prehash = f"{timestamp}{method}{path}{body}"
    signature = sign(prehash)
    return {
        "CB-ACCESS-KEY": API_KEY,
        "CB-ACCESS-SIGN": signature,
        "CB-ACCESS-TIMESTAMP": timestamp,
        "CB-ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json",
    }

def get_accounts():
    r = requests.get(BASE_URL + "/accounts", headers=headers("/api/v3/brokerage/accounts"))
    return r.json()

def market_buy(product_id="SOL-USD", size="1"):
    path = "/api/v3/brokerage/orders"
    body = f'{{"product_id":"{product_id}","side":"BUY","order_configuration":{{"market_market_ioc":{{"base_size":"{size}"}}}}}}'
    r = requests.post(BASE_URL + "/orders", headers=headers(path, "POST", body), data=body)
    return r.json()

print(get_accounts())
print(market_buy())
