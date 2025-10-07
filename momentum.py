import os
import time
import pandas as pd
from dotenv import load_dotenv
from coinbase.rest import RESTClient

# === Load environment variables ===
load_dotenv(dotenv_path="/home/alecrimi/Documents/coinbot/my.env")
API_KEY = os.getenv("COINBASE_API_KEY_ID")
PRIVATE_KEY = os.getenv("COINBASE_PRIVATE_KEY")

if not all([API_KEY, PRIVATE_KEY]):
    raise ValueError("❌ Missing Coinbase API keys in .env file!")

# === Configuration ===
PRODUCT_ID = "SOL-EUR"  # Changed to EUR since you're in Poland
FAST_MA = 20
SLOW_MA = 50
TRADE_SIZE = 0.1  # in SOL
SLEEP_TIME = 60  # seconds
PAPER_TRADING = False  # ← Set to False for real trades (LIVE)

# === Initialize Coinbase Client ===
def initialize_client():
    """Initialize the Coinbase REST client"""
    fixed_private_key = PRIVATE_KEY.replace('\\n', '\n')
    client = RESTClient(
        api_key=API_KEY,
        api_secret=fixed_private_key
    )
    print("✅ Coinbase Advanced API client initialized")
    return client

client = initialize_client()

# === Get recent price candles ===
def get_recent_data():
    """Get recent candle data for the product"""
    try:
        response = client.get_product_candles(
            product_id=PRODUCT_ID,
            granularity="ONE_MINUTE"
        )
        
        if hasattr(response, 'candles'):
            candles = response.candles
            data = []
            for candle in candles:
                data.append({
                    'start': getattr(candle, 'start', ''),
                    'low': float(getattr(candle, 'low', 0)),
                    'high': float(getattr(candle, 'high', 0)),
                    'open': float(getattr(candle, 'open', 0)),
                    'close': float(getattr(candle, 'close', 0)),
                    'volume': float(getattr(candle, 'volume', 0))
                })
            
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['start'])
            df = df.sort_values('time')
            return df
        else:
            raise Exception("No candle data received")
            
    except Exception as e:
        raise Exception(f"Error fetching data: {e}")

# === Get current position ===
def get_current_position():
    """Check if we already have a position in SOL"""
    try:
        accounts = client.get_accounts()
        for account in accounts.accounts:
            if getattr(account, 'currency', '') == 'SOL':
                available_balance = getattr(getattr(account, 'available_balance', None), 'value', '0')
                return float(available_balance) if available_balance else 0.0
        return 0.0
    except Exception as e:
        print(f"Error checking position: {e}")
        return 0.0

# === Place buy/sell order ===
def place_order(side, size):
    """Place a market order"""
    if PAPER_TRADING:
        print(f"🧪 PAPER TRADE: Would place {side.upper()} order for {size} SOL")
        return {"success": True, "order_id": "paper_trade"}

    try:
        if side.upper() == "BUY":
            order_config = {
                "market_market_ioc": {
                    "quote_size": str(size)  # For EUR amount, or use "base_size" for SOL amount
                }
            }
        else:  # SELL
            order_config = {
                "market_market_ioc": {
                    "base_size": str(size)  # Sell specific SOL amount
                }
            }
        
        response = client.create_order(
            client_order_id=str(int(time.time())),
            product_id=PRODUCT_ID,
            side=side.upper(),
            order_configuration=order_config
        )
        
        print(f"✅ {side.upper()} order placed successfully!")
        print(f"   Order ID: {getattr(response, 'order_id', 'Unknown')}")
        print(f"   Success: {getattr(response, 'success', False)}")
        return response
        
    except Exception as e:
        print(f"❌ Order failed: {e}")
        return None

# === Get current price ===
def get_current_price():
    """Get current product price"""
    try:
        product = client.get_product(product_id=PRODUCT_ID)
        return float(getattr(product, 'price', '0'))
    except Exception as e:
        print(f"Error getting price: {e}")
        return 0.0

# === Main trading loop ===
def run_bot():
    print(f"🚀 Starting LIVE Momentum Bot for {PRODUCT_ID}")
    print(f"📈 Strategy: {FAST_MA}/{SLOW_MA} Moving Average Crossover")
    print(f"💵 Trade Size: {TRADE_SIZE} SOL")
    print(f"⏰ Check Interval: {SLEEP_TIME} seconds")
    print("=" * 50)
    
    while True:
        try:
            # Get current position
            current_sol = get_current_position()
            position = "long" if current_sol >= TRADE_SIZE else "flat"
            
            print(f"\n🕒 {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 Position: {position.upper()} ({current_sol:.4f} SOL)")
            
            # Get market data
            df = get_recent_data()
            if len(df) < SLOW_MA:
                print(f"⚠️  Not enough data points. Have {len(df)}, need {SLOW_MA}")
                time.sleep(SLEEP_TIME)
                continue
            
            # Calculate indicators
            df["fast_ma"] = df["close"].rolling(FAST_MA).mean()
            df["slow_ma"] = df["close"].rolling(SLOW_MA).mean()

            last_fast = df["fast_ma"].iloc[-1]
            last_slow = df["slow_ma"].iloc[-1]
            last_price = get_current_price()

            print(f"💰 Price: €{last_price:.2f} | Fast MA: €{last_fast:.2f} | Slow MA: €{last_slow:.2f}")

            # === Strategy Logic ===
            if last_fast > last_slow and position != "long":
                print("🎯 BUY SIGNAL: Fast MA crossed above Slow MA!")
                print(f"💸 Buying {TRADE_SIZE} SOL...")
                place_order("BUY", TRADE_SIZE)

            elif last_fast < last_slow and position == "long":
                print("🎯 SELL SIGNAL: Fast MA crossed below Slow MA!")
                print(f"💸 Selling {current_sol:.4f} SOL...")
                place_order("SELL", current_sol)

            else:
                print("⚪ No trade signal - waiting...")

        except Exception as e:
            print(f"⚠️  Error in main loop: {e}")
            import traceback
            traceback.print_exc()

        print(f"😴 Sleeping for {SLEEP_TIME} seconds...")
        time.sleep(SLEEP_TIME)

# === Safety Checks ===
def safety_checks():
    """Perform safety checks before starting"""
    print("🔒 Performing safety checks...")
    
    # Check if we can access the API
    try:
        accounts = client.get_accounts()
        print("✅ API connection: OK")
    except Exception as e:
        raise Exception(f"❌ API connection failed: {e}")
    
    # Check if product exists
    try:
        product = client.get_product(product_id=PRODUCT_ID)
        product_name = getattr(product, 'display_name', PRODUCT_ID)
        print(f"✅ Product {PRODUCT_ID}: OK ({product_name})")
    except Exception as e:
        raise Exception(f"❌ Product {PRODUCT_ID} not found: {e}")
    
    # Check EUR balance if we're going to buy
    try:
        accounts = client.get_accounts()
        eur_balance = 0.0
        for account in accounts.accounts:
            if getattr(account, 'currency', '') == 'EUR':
                eur_balance = float(getattr(getattr(account, 'available_balance', None), 'value', '0'))
                break
        
        required_eur = TRADE_SIZE * get_current_price()
        print(f"💰 EUR Balance: €{eur_balance:.2f}")
        print(f"💵 Required for trade: €{required_eur:.2f}")
        
        if eur_balance < required_eur:
            print(f"⚠️  Warning: Low EUR balance. Need €{required_eur:.2f}, have €{eur_balance:.2f}")
        
    except Exception as e:
        print(f"⚠️  Could not check balance: {e}")
    
    print("✅ Safety checks completed!")

# === Entry point ===
if __name__ == "__main__":
    try:
        safety_checks()
        print("\n" + "="*50)
        if not PAPER_TRADING:
            print("🚨 LIVE TRADING MODE - REAL MONEY AT RISK!")
            confirmation = input("Type 'YES' to confirm you want to start LIVE trading: ")
            if confirmation != "YES":
                print("❌ Trading cancelled.")
                exit()
        run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
