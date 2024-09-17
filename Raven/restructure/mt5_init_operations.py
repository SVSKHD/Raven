import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz
import asyncio

# Initialize MT5 connection
def initialize_mt5():
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        quit()

# Check if the market is open
def is_market_open(symbol):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise ValueError(f"Failed to get market info for {symbol}. Ensure the symbol is correct.")
    return symbol_info.session_open != 0  # Non-zero means the market is open

# Function to get the latest price from MetaTrader5
def get_latest_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise ValueError(f"Failed to get the latest price for {symbol}. Ensure the symbol is correct and the market is open.")
    return tick.bid, tick.ask

# Function to get historical price at 12:00 AM IST, or current price on Monday if not available
def get_historical_price(symbol, date):
    ist = pytz.timezone('Asia/Kolkata')
    target_time_12am = ist.localize(datetime(date.year, date.month, date.day, 0, 0, 0)).astimezone(pytz.utc)

    # Try to fetch the price at 12:00 AM IST
    rates_12am = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, target_time_12am, target_time_12am + timedelta(minutes=1))
    if rates_12am is not None and len(rates_12am) > 0:
        return rates_12am[0]['close']  # Return the close price at 12:00 AM

    # If it's Monday and no 12:00 AM data, fetch the latest available price
    if date.weekday() == 0:  # Monday
        print(f"No data available for {symbol} at 12:00 AM on Monday. Fetching the latest available price.")
        bid_price, ask_price = get_latest_price(symbol)
        return ask_price  # Return the latest available ask price (or bid as needed)

    raise ValueError(f"Could not fetch historical price for {symbol} at 12:00 AM IST.")

# Wait until the market opens
async def wait_for_market_open(symbol):
    while not is_market_open(symbol):
        print(f"Market is currently closed for {symbol}. Waiting for it to open...")
        await asyncio.sleep(60)
    print(f"Market is now open for {symbol}.")

