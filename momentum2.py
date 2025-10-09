import os
import time
import pandas as pd
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from datetime import datetime, timedelta

# === Load environment variables ===
load_dotenv(dotenv_path="/home/alecrimi/Documents/coinbot/my.env")
API_KEY = os.getenv("COINBASE_API_KEY_ID")
PRIVATE_KEY = os.getenv("COINBASE_PRIVATE_KEY")

if not all([API_KEY, PRIVATE_KEY]):
    raise ValueError("❌ Missing Coinbase API keys in .env file!")

# === Configuration ===
PRODUCT_ID = "SOL-EUR"
FAST_MA = 5
SLOW_MA = 15
MIN_TRADE_SIZE = 0.006  # Minimum SOL amount to trade (your current balance)
SLEEP_TIME = 60
PAPER_TRADING = False  # Real trading

# === Initialize Coinbase Client ===
def initialize_client():
    fixed_private_key = PRIVATE_KEY.replace('\\n', '\n')
    client = RESTClient(
        api_key=API_KEY,
        api_secret=fixed_private_key
    )
    print("✅ Coinbase Advanced API client initialized")
    return client

client = initialize_client()
  
# === Get recent price candles (with epoch timestamps) ===
# === Get recent price candles ===
def get_recent_data():
    """Get recent candle data using epoch timestamps"""
    try:
        # Calculate start and end times (last 2 hours)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=2)
        
        # Convert to epoch seconds
        start_epoch = int(start_time.timestamp())
        end_epoch = int(end_time.timestamp())
        
        print(f"📊 Fetching candles from {start_time} to {end_time}")
        
        response = client.get_candles(
            product_id=PRODUCT_ID,
            start=str(start_epoch),
            end=str(end_epoch),
            granularity="ONE_MINUTE"
        )
        
        return process_candle_response(response)
            
    except Exception as e:
        print(f"❌ SDK candle error: {e}")
        return get_simple_price_data()


def process_candle_response(response):
    """Process the candle response with correct timestamp handling"""
    try:
        if hasattr(response, 'candles'):
            candles = response.candles
            print(f"✅ Received {len(candles)} candles")
            
            data = []
            for candle in candles:
                # Get the start timestamp - it might be epoch seconds or ISO string
                start_attr = getattr(candle, 'start', '')
                
                # Convert to proper datetime
                if isinstance(start_attr, (int, float)) or (isinstance(start_attr, str) and start_attr.isdigit()):
                    # It's an epoch timestamp
                    timestamp = int(start_attr)
                    if timestamp > 1e9:  # If it's in seconds (not milliseconds)
                        dt = datetime.fromtimestamp(timestamp)
                    else:  # If it's in milliseconds
                        dt = datetime.fromtimestamp(timestamp / 1000)
                    start_str = dt.isoformat() + 'Z'
                else:
                    # It's probably already an ISO string
                    start_str = start_attr
                
                data.append({
                    'start': start_str,
                    'low': float(getattr(candle, 'low', 0)),
                    'high': float(getattr(candle, 'high', 0)),
                    'open': float(getattr(candle, 'open', 0)),
                    'close': float(getattr(candle, 'close', 0)),
                    'volume': float(getattr(candle, 'volume', 0))
                })
            
            df = pd.DataFrame(data)
            if len(df) > 0:
                # Parse timestamps properly
                df['time'] = pd.to_datetime(df['start'], utc=True)
                df = df.sort_values('time')
                print(f"✅ Processed {len(df)} candles with proper timestamps")
                print(f"📅 Time range: {df['time'].min()} to {df['time'].max()}")
                return df
            else:
                print("⚠️ No candle data in response, using fallback")
                return get_simple_price_data()
        else:
            print("⚠️ No candles attribute in response, using fallback")
            return get_simple_price_data()
            
    except Exception as e:
        print(f"❌ Error processing candles: {e}")
        return get_simple_price_data()
        

def get_simple_price_data():
    """Fallback: Create synthetic data from recent prices"""
    try:
        print("🔄 Using simple price data fallback...")
        
        # Get current product info
        product = client.get_product(product_id=PRODUCT_ID)
        current_price = float(getattr(product, 'price', 0))
        
        # Create synthetic data for last 30 minutes
        data = []
        for i in range(30):
            time_point = datetime.utcnow() - timedelta(minutes=30-i)
            # Add some random variation to the price
            variation = current_price * (0.99 + 0.02 * (i / 30))  # Gradual increase
            data.append({
                'start': time_point.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'close': variation,
                'low': variation * 0.998,
                'high': variation * 1.002,
                'open': variation * 0.999,
                'volume': 100.0
            })
        
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['start'])
        df = df.sort_values('time')
        print(f"✅ Created synthetic data with {len(df)} points")
        return df
        
    except Exception as e:
        print(f"❌ Simple data fallback failed: {e}")
        # Last resort: create very basic data
        return create_basic_data()

def create_basic_data():
    """Create minimal data to keep bot running"""
    print("⚠️ Creating basic data structure...")
    current_price = get_current_price()
    data = []
    for i in range(50):
        data.append({
            'start': (datetime.utcnow() - timedelta(minutes=50-i)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'close': current_price + (i * 0.01),  # Simple trend
            'low': current_price * 0.998 + (i * 0.01),
            'high': current_price * 1.002 + (i * 0.01),
            'open': current_price + (i * 0.01),
            'volume': 100.0
        })
    
    df = pd.DataFrame(data)
    df['time'] = pd.to_datetime(df['start'])
    return df

# === Get current position ===
# === Get current position ===
def get_current_position():
    try:
        accounts = client.get_accounts()
        for account in accounts.accounts:
            if getattr(account, 'currency', '') == 'SOL':
                # Extract the available_balance dictionary and get the value
                available_balance_obj = getattr(account, 'available_balance', {})
                if hasattr(available_balance_obj, 'value'):
                    available_balance = getattr(available_balance_obj, 'value', '0')
                else:
                    # If it's a dictionary, access it directly
                    available_balance = available_balance_obj.get('value', '0') if isinstance(available_balance_obj, dict) else '0'
                
                sol_balance = float(available_balance) if available_balance else 0.0
                print(f"📊 SOL balance: {sol_balance:.6f}")
                return sol_balance
        return 0.0
    except Exception as e:
        print(f"❌ Error checking position: {e}")
        return 0.0
        
# === Place buy/sell order ===
def place_order(side, amount=None):
    if PAPER_TRADING:
        print(f"🧪 PAPER TRADE: Would place {side.upper()} order for {amount} {'EUR' if side.upper() == 'BUY' else 'SOL'}")
        return {"success": True, "order_id": "paper_trade"}

    try:
        if side.upper() == "BUY":
            order_config = {
                "market_market_ioc": {
                    "quote_size": str(amount)  # Spend exact EUR amount
                }
            }
        else:  # SELL
            order_config = {
                "market_market_ioc": {
                    "base_size": str(amount)  # Sell exact SOL amount
                }
            }
        
        print(f"🎯 Placing {side.upper()} order for {amount}...")
        response = client.create_order(
            client_order_id=str(int(time.time())),
            product_id=PRODUCT_ID,
            side=side.upper(),
            order_configuration=order_config
        )
        
        print(f"✅ {side.upper()} order placed successfully!")
        print(f"   Order ID: {getattr(response, 'order_id', 'Unknown')}")
        return response
        
    except Exception as e:
        print(f"❌ Order failed: {e}")
        return None

# === Get current price ===
def get_current_price():
    try:
        product = client.get_product(product_id=PRODUCT_ID)
        price = float(getattr(product, 'price', '0'))
        print(f"💰 Current price: €{price:.2f}")
        return price
    except Exception as e:
        print(f"❌ Error getting price: {e}")
        return 196.0  # Fallback price

# === Get EUR balance ===
def get_eur_balance():
    try:
        accounts = client.get_accounts()
        for account in accounts.accounts:
            if getattr(account, 'currency', '') == 'EUR':
                # Extract the available_balance dictionary and get the value
                available_balance_obj = getattr(account, 'available_balance', {})
                if hasattr(available_balance_obj, 'value'):
                    available_balance = getattr(available_balance_obj, 'value', '0')
                else:
                    # If it's a dictionary, access it directly
                    available_balance = available_balance_obj.get('value', '0') if isinstance(available_balance_obj, dict) else '0'
                
                balance = float(available_balance) if available_balance else 0.0
                print(f"💰 EUR balance: €{balance:.2f}")
                return balance
        return 0.0
    except Exception as e:
        print(f"❌ Error checking EUR balance: {e}")
        return 0.0

# === Main trading loop ===
def run_bot():
    print(f"🚀 Starting LIVE Momentum Bot for {PRODUCT_ID}")
    print(f"📈 Strategy: {FAST_MA}/{SLOW_MA} Moving Average Crossover")
    print(f"💵 Minimum Trade Size: {MIN_TRADE_SIZE} SOL")
    print(f"⏰ Check Interval: {SLEEP_TIME} seconds")
    print("=" * 50)
    
    while True:
        try:
            # Get current position and price
            current_sol = get_current_position()
            current_price = get_current_price()
            
            # Determine position (you're LONG since you have SOL)
            has_position = current_sol >= MIN_TRADE_SIZE
            
            print(f"\n🕒 {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 Position: {'LONG' if has_position else 'FLAT'} ({current_sol:.6f} SOL)")
            print(f"💰 Portfolio Value: €{current_sol * current_price:.2f}")
            
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

            print(f"📊 Fast MA: €{last_fast:.2f} | Slow MA: €{last_slow:.2f}")

            # === Strategy Logic ===
            if has_position:
                # You have SOL - look for SELL signal
                if last_fast < last_slow:
                    print("🎯 SELL SIGNAL: Fast MA crossed below Slow MA!")
                    print(f"💸 Selling {current_sol:.6f} SOL...")
                    if current_sol >= MIN_TRADE_SIZE:
                        place_order("SELL", current_sol)
                    else:
                        print("❌ SOL balance below minimum trade size")
                else:
                    print("💎 Holding SOL - waiting for sell signal...")
                    
            else:
                # You don't have SOL - look for BUY signal
                eur_balance = get_eur_balance()
                if last_fast > last_slow and eur_balance >= (MIN_TRADE_SIZE * current_price):
                    print("🎯 BUY SIGNAL: Fast MA crossed above Slow MA!")
                    buy_amount = min(eur_balance, MIN_TRADE_SIZE * current_price)
                    print(f"💸 Buying €{buy_amount:.2f} worth of SOL...")
                    place_order("BUY", buy_amount)
                elif last_fast > last_slow:
                    print("🎯 BUY SIGNAL detected but insufficient EUR balance")
                else:
                    print("⚪ No buy signal - waiting...")

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
    
    # Check balances
    current_sol = get_current_position()
    current_price = get_current_price()
    eur_balance = get_eur_balance()
    
    print(f"💰 SOL Balance: {current_sol:.6f} SOL (€{current_sol * current_price:.2f})")
    print(f"💰 EUR Balance: €{eur_balance:.2f}")
    
    if current_sol >= MIN_TRADE_SIZE:
        print(f"✅ Ready to SELL {current_sol:.6f} SOL when signal appears")
    elif eur_balance >= (MIN_TRADE_SIZE * current_price):
        print(f"✅ Ready to BUY with €{eur_balance:.2f} when signal appears")
    else:
        print(f"⚠️  Low balances. Need €{MIN_TRADE_SIZE * current_price:.2f} EUR to buy, or {MIN_TRADE_SIZE} SOL to sell")
    
    print("✅ Safety checks completed!")

# === Entry point ===
if __name__ == "__main__":
    try:
        safety_checks()
        print("\n" + "="*50)
        if not PAPER_TRADING:
            print("🚨 LIVE TRADING MODE - REAL MONEY AT RISK!")
            print(f"💎 You have {get_current_position():.6f} SOL to trade")
            confirmation = input("Type 'YES' to confirm you want to start LIVE trading: ")
            if confirmation != "YES":
                print("❌ Trading cancelled.")
                exit()
        run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
         
