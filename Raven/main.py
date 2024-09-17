import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz
import asyncio
from notifications import send_telegram_message
from pymongo import MongoClient
from trade_management import place_trade, close_all_trades
# MongoDB Configuration
MONGO_URI = 'mongodb+srv://hithesh:hithesh@utbiz.npdehas.mongodb.net/'
client = MongoClient(MONGO_URI)
db = client['pip_tracking_db']

correlation_list = [
    {"currency": 'EURUSD', "pip_difference": 15},
    {"currency": 'GBPUSD', "pip_difference": 15}
]

TIMEFRAME = mt5.TIMEFRAME_M5

# IST Timezone
ist = pytz.timezone('Asia/Kolkata')


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
        raise ValueError(
            f"Failed to get the latest price for {symbol}. Ensure the symbol is correct and the market is open.")
    return tick.bid, tick.ask


# Save or update threshold data in MongoDB (single collection named pip_check)
async def save_or_update_threshold_in_mongo(symbol, start_price, current_price, previous_threshold, pips_from_start,
                                            direction, thresholds_list, timestamp, start_price_time):
    collection_name = "pip_check"
    pip_check_collection = db[collection_name]

    current_date_ist = timestamp.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')

    query = {"symbol": symbol, "date": current_date_ist.split()[0]}

    threshold_data = {
        "symbol": symbol,
        "start_price": start_price,
        "start_price_time": start_price_time.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S'),
        "initial_threshold_price": current_price,
        "previous_threshold": previous_threshold,
        "pips_from_start": pips_from_start,
        "direction": direction,
        "timestamp": timestamp.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')
    }

    update_data = {
        "$set": threshold_data,
        "$addToSet": {"thresholds_list": {"$each": thresholds_list}}
    }

    result = pip_check_collection.update_one(query, update_data, upsert=True)

    if result.matched_count > 0:
        message = f"Updated existing document for {symbol} on {current_date_ist}. Data saved successfully."
    else:
        message = f"Inserted new document for {symbol} on {current_date_ist}. Data saved successfully."

    print(message)
    await send_telegram_message(message)  # Await the coroutine here



# Function to check if data already exists in MongoDB
def check_data_exists_in_mongo(symbol, date):
    collection_name = "pip_check"
    pip_check_collection = db[collection_name]

    # Convert the date to a string
    date_str = date.strftime('%Y-%m-%d')

    # Query MongoDB for the existing document
    query = {"symbol": symbol, "date": date_str}
    return pip_check_collection.find_one(query)


# Function to calculate pips and handle threshold logic
async def pip_calculator(start_price, current_price, threshold_price, previous_threshold, direction, symbol,
                         thresholds_list, pip_difference, start_price_time):
    diff_from_start = (current_price - start_price) if direction == "up" else (start_price - current_price)
    diff_from_previous = (current_price - previous_threshold) if direction == "up" else (
            previous_threshold - current_price)

    pips_from_start = diff_from_start * 10000
    pips_from_previous = diff_from_previous * 10000

    if abs(pips_from_previous) >= pip_difference:
        thresholds_list.append(current_price)
        message = (
            f"Threshold reached at {current_price:.4f} for {symbol}, "
            f"previous threshold {previous_threshold:.4f}, start price {start_price:.4f}, "
            f"{pips_from_start:.2f} pips from start, {direction.capitalize()}.\n"
            f"Thresholds list: {thresholds_list}"
        )
        await send_telegram_message(message)

        current_time = datetime.now(pytz.utc)
        await save_or_update_threshold_in_mongo(symbol, start_price, current_price, previous_threshold, pips_from_start,
                                                direction, thresholds_list, current_time, start_price_time)

        return current_price
    else:
        return threshold_price



# Function to get the historical price at 2:00 AM or 2:30 AM IST
def get_historical_price(symbol, date):
    # Convert the date to 2:00 AM IST or 2:30 AM IST
    ist = pytz.timezone('Asia/Kolkata')
    target_time_2am = ist.localize(datetime(date.year, date.month, date.day, 2, 0, 0)).astimezone(pytz.utc)
    target_time_230am = ist.localize(datetime(date.year, date.month, date.day, 2, 30, 0)).astimezone(pytz.utc)

    # Attempt to fetch historical price at 2:00 AM IST
    rates_2am = mt5.copy_rates_range(symbol, TIMEFRAME, target_time_2am, target_time_2am + timedelta(minutes=1))
    if rates_2am is not None and len(rates_2am) > 0:
        return rates_2am[0]['close']  # Return the close price at 2:00 AM

    # If no data at 2:00 AM, try to fetch at 2:30 AM IST
    rates_230am = mt5.copy_rates_range(symbol, TIMEFRAME, target_time_230am, target_time_230am + timedelta(minutes=1))
    if rates_230am is not None and len(rates_230am) > 0:
        return rates_230am[0]['close']  # Return the close price at 2:30 AM

    # If both attempts fail, raise an error
    raise ValueError(f"Could not fetch historical price for {symbol} at 2:00 AM or 2:30 AM IST.")


# Async function to handle fetching the price at 2:00 AM IST or 2:30 AM IST, or the current market price if before 2:00 AM
async def get_2am_or_historical_price(symbol):
    now = datetime.now(ist)

    # If current time is after 2:00 AM, fetch historical price for today at 2:00 AM or 2:30 AM
    if now.hour >= 2:
        try:
            start_price = get_historical_price(symbol, now)
            start_price_time = now  # Use the current time as the "fetch time"

            # Check if the data already exists in MongoDB
            existing_data = check_data_exists_in_mongo(symbol, now.date())
            if existing_data:
                await send_telegram_message(f"Data for {symbol} already exists in MongoDB: {existing_data}")
            else:
                await send_telegram_message(f"Fetched historical price at 2:00 AM or 2:30 AM IST for {symbol}: {start_price}")
                save_or_update_threshold_in_mongo(symbol, start_price, start_price, start_price, 0, "up", [], datetime.now(pytz.utc), start_price_time)
        except ValueError as e:
            await send_telegram_message(str(e))
            start_price = None
    else:
        # If before 2:00 AM, wait for 2:00 AM market price using original logic
        next_2am, start_price, start_price_time = await get_next_2am_ist(symbol)

    print(f"{symbol} - {start_price_time} - {start_price}")
    return start_price, start_price_time


# Async function to handle 2:00 AM IST logic
async def get_next_2am_ist(symbol):
    now = datetime.now(ist)

    if now.hour >= 2:
        next_2am = (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)
    else:
        next_2am = now.replace(hour=2, minute=30, second=0, microsecond=0)

    # Fetch the market open price
    start_price = await get_market_open_price(symbol)

    # Capture the current UTC time for start price timestamp
    start_price_time = datetime.now(pytz.utc)

    await send_telegram_message(f"Market open price retrieved: {start_price} for {symbol} on Monday")
    print(f"{symbol} - {next_2am} - {start_price}")
    return next_2am.astimezone(pytz.utc), start_price, start_price_time


# Get the market opening price on Monday (or Sunday evening)
async def get_market_open_price(symbol):
    # Wait until market opens if closed (especially on Monday)
    if not is_market_open(symbol):
        await wait_for_market_open(symbol)  # Wait for the market to open

    # Get the first price when the market opens
    first_tick = mt5.symbol_info_tick(symbol)
    if first_tick is None:
        raise ValueError(f"Failed to retrieve the first price when the market opened for {symbol}.")

    # Return the ask price at market open
    return first_tick.ask


# Wait until the market opens
async def wait_for_market_open(symbol):
    while not is_market_open(symbol):
        print(f"Market is currently closed for {symbol}. Waiting for it to open...")
        await asyncio.sleep(60)  # Wait for 1 minute before checking again
    print(f"Market is now open for {symbol}.")


# Function to handle the processing for each currency
async def log_currency(symbol, pip_difference):
    try:
        start_price, start_price_time = await get_2am_or_historical_price(symbol)
        if start_price is None:
            return  # Exit if no start price is available

        await send_telegram_message(f"Started with {symbol} - {start_price}")

        threshold_price_up = start_price
        threshold_price_down = start_price

        thresholds_list = [start_price]

        while True:
            bid_price, ask_price = get_latest_price(symbol)

            threshold_price_up = await pip_calculator(
                start_price, ask_price, threshold_price_up, threshold_price_up,
                direction="up", symbol=symbol, thresholds_list=thresholds_list, pip_difference=pip_difference,
                start_price_time=start_price_time
            )

            threshold_price_down = await pip_calculator(
                start_price, bid_price, threshold_price_down, threshold_price_down,
                direction="down", symbol=symbol, thresholds_list=thresholds_list, pip_difference=pip_difference,
                start_price_time=start_price_time
            )

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print(f"Stopping the script for {symbol}.")

    finally:
        mt5.shutdown()


# Main function to run for multiple currencies
async def main():
    initialize_mt5()
    tasks = []
    for currency in correlation_list:
        tasks.append(log_currency(currency['currency'], currency['pip_difference']))
    await asyncio.gather(*tasks)


# Run the asynchronous main function
asyncio.run(main())
