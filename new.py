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
    print("MetaTrader 5 initialized successfully")


# Function to check if the market is open
def is_market_open(symbol):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise ValueError(f"Failed to get market info for {symbol}. Ensure the symbol is correct.")
    print(f"Market open status for {symbol}: {symbol_info.session_open != 0}")
    return symbol_info.session_open != 0  # Non-zero means the market is open


# Function to get the latest price from MetaTrader5
def get_latest_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise ValueError(
            f"Failed to get the latest price for {symbol}. Ensure the symbol is correct and the market is open.")
    print(f"Latest price for {symbol}: Bid: {tick.bid}, Ask: {tick.ask}")
    return tick.bid, tick.ask


# Async function to get the first price when the market resumes (usually on Monday)
async def get_market_resumed_price(symbol):
    now = datetime.now(pytz.utc)
    print(f"Checking if the market has resumed for {symbol} at {now}")

    if now.weekday() == 0 or now.weekday() == 6:  # Sunday (6) or Monday (0)
        if not is_market_open(symbol):
            await send_telegram_message(f"Market is closed for {symbol}. Waiting for it to resume...")
            print(f"Market is closed for {symbol}. Waiting for the market to open...")
            await wait_for_market_open(symbol)  # Wait until the market opens after the weekend

    first_tick = mt5.symbol_info_tick(symbol)
    if first_tick is None:
        raise ValueError(f"Failed to retrieve the first price when the market resumed for {symbol}.")

    print(f"Market resumed for {symbol}. First available price: {first_tick.ask}")
    return first_tick.ask, datetime.now(pytz.utc)


# Wait until the market opens
async def wait_for_market_open(symbol):
    while not is_market_open(symbol):
        print(f"Market is currently closed for {symbol}. Waiting for it to open...")
        await asyncio.sleep(60)  # Check every 60 seconds
    print(f"Market is now open for {symbol}.")


# Function to get the historical price at 2:00 AM or 2:30 AM IST
def get_historical_price(symbol, date):
    ist = pytz.timezone('Asia/Kolkata')
    target_time_2am = ist.localize(datetime(date.year, date.month, date.day, 2, 0, 0)).astimezone(pytz.utc)
    target_time_230am = ist.localize(datetime(date.year, date.month, date.day, 2, 30, 0)).astimezone(pytz.utc)

    print(f"Fetching historical price for {symbol} at 2:00 AM IST or 2:30 AM IST on {date}")
    rates_2am = mt5.copy_rates_range(symbol, TIMEFRAME, target_time_2am, target_time_2am + timedelta(minutes=1))
    if rates_2am is not None and len(rates_2am) > 0:
        print(f"Found 2:00 AM price for {symbol}: {rates_2am[0]['close']}")
        return rates_2am[0]['close']  # Return the close price at 2:00 AM

    rates_230am = mt5.copy_rates_range(symbol, TIMEFRAME, target_time_230am, target_time_230am + timedelta(minutes=1))
    if rates_230am is not None and len(rates_230am) > 0:
        print(f"Found 2:30 AM price for {symbol}: {rates_230am[0]['close']}")
        return rates_230am[0]['close']  # Return the close price at 2:30 AM

    raise ValueError(f"Could not fetch historical price for {symbol} at 2:00 AM or 2:30 AM IST.")


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


# Async function to handle 2:00 AM IST logic or fetch price when the market resumes on Monday
async def get_2am_or_market_resumed_price(symbol):
    now = datetime.now(ist)
    print(f"Attempting to fetch 2:00 AM or market resumed price for {symbol} at {now}")

    start_price = None
    start_price_time = None

    # If it's Monday or Sunday evening, check for market resumption price
    if now.weekday() == 0 or now.weekday() == 6:
        start_price, start_price_time = await get_market_resumed_price(symbol)
        await send_telegram_message(f"Fetched market resumed price for {symbol} on Monday: {start_price}")
    else:
        if now.hour >= 2:
            try:
                start_price = get_historical_price(symbol, now)
                start_price_time = now
                existing_data = check_data_exists_in_mongo(symbol, now.date())
                if existing_data:
                    await send_telegram_message(f"Data for {symbol} already exists in MongoDB: {existing_data}")
                else:
                    await send_telegram_message(f"Fetched historical price at 2:00 AM for {symbol}: {start_price}")
                    await save_or_update_threshold_in_mongo(symbol, start_price, start_price, start_price, 0, "up", [],
                                                            datetime.now(pytz.utc), start_price_time)
            except ValueError as e:
                await send_telegram_message(str(e))
                start_price = None

    if start_price is not None and start_price_time is not None:
        print(f"Start price fetched for {symbol}: {start_price} at {start_price_time}")
    else:
        print(f"Failed to retrieve start price for {symbol} at 2:00 AM or market open.")

    return start_price, start_price_time


# Function to calculate pips and handle threshold logic
async def pip_calculator(start_price, current_price, threshold_price, previous_threshold, direction, symbol,
                         thresholds_list, pip_difference, start_price_time, trade_status):
    print(f"Calculating pips for {symbol}. Current price: {current_price}, Start price: {start_price}")

    diff_from_start = (current_price - start_price) if direction == "up" else (start_price - current_price)
    diff_from_previous = (current_price - previous_threshold) if direction == "up" else (
            previous_threshold - current_price)

    pips_from_start = diff_from_start * 10000
    pips_from_previous = diff_from_previous * 10000

    print(
        f"Pips from start for {symbol}: {pips_from_start:.2f}, Pips from previous threshold: {pips_from_previous:.2f}")

    if abs(pips_from_previous) >= pip_difference:
        thresholds_list.append(current_price)
        message = (
            f"Threshold reached at {current_price:.4f} for {symbol}, "
            f"previous threshold {previous_threshold:.4f}, start price {start_price:.4f}, "
            f"{pips_from_start:.2f} pips from start, {direction.capitalize()}.\n"
            f"Thresholds list: {thresholds_list}"
        )
        await send_telegram_message(message)

        # Place trade at first threshold and close at second in the same direction
        if direction == "up":
            trade_result = place_trade(
                symbol=symbol,
                order_type=mt5.ORDER_TYPE_BUY,  # Buy order for upward movement
                volume=0.1,  # Adjust the volume as needed
                price=current_price,
                slippage=20,  # Example slippage
                comment="Auto trade due to 15-pip upward movement",
                stop_loss=None,  # Optional stop loss
                take_profit=None  # Optional take profit
            )
            trade_status["open_trade"] = "buy"
        elif direction == "down":
            trade_result = place_trade(
                symbol=symbol,
                order_type=mt5.ORDER_TYPE_SELL,  # Sell order for downward movement
                volume=0.1,  # Adjust the volume as needed
                price=current_price,
                slippage=20,  # Example slippage
                comment="Auto trade due to 15-pip downward movement",
                stop_loss=None,  # Optional stop loss
                take_profit=None  # Optional take profit
            )
            trade_status["open_trade"] = "sell"

            trade_status["threshold_count"] = 1  # Start counting thresholds in the same direction
            print(f"Trade placed for {symbol}. Trade status: {trade_status['open_trade'].upper()}")

        elif trade_status["open_trade"]:
            print(f"Checking if second threshold for {symbol} has been reached to close the trade.")
            # Second threshold: close the trade if it hits the second threshold in the same direction
            if direction == "up" and trade_status["open_trade"] == "buy":
                trade_status["threshold_count"] += 1
                if trade_status["threshold_count"] == 2:
                    close_all_trades()
                    trade_status["open_trade"] = None
                    trade_status["threshold_count"] = 0
                    print(f"Closed BUY trade at second upward threshold for {symbol}.")

            elif direction == "down" and trade_status["open_trade"] == "sell":
                trade_status["threshold_count"] += 1
                if trade_status["threshold_count"] == 2:
                    close_all_trades()
                    trade_status["open_trade"] = None
                    trade_status["threshold_count"] = 0
                    print(f"Closed SELL trade at second downward threshold for {symbol}.")

        current_time = datetime.now(pytz.utc)
        await save_or_update_threshold_in_mongo(symbol, start_price, current_price, previous_threshold, pips_from_start,
                                                direction, thresholds_list, current_time, start_price_time)

        return current_price
    else:
        return threshold_price


# Function to handle the processing for each currency
async def log_currency(symbol, pip_difference):
    trade_status = {"open_trade": None, "threshold_count": 0}  # Track whether a trade is open and threshold count
    try:
        start_price, start_price_time = await get_2am_or_market_resumed_price(symbol)
        if start_price is None:
            return

        await send_telegram_message(f"Started with {symbol} - {start_price}")

        threshold_price_up = start_price
        threshold_price_down = start_price

        thresholds_list = [start_price]

        while True:
            bid_price, ask_price = get_latest_price(symbol)

            threshold_price_up = await pip_calculator(
                start_price, ask_price, threshold_price_up, threshold_price_up,
                direction="up", symbol=symbol, thresholds_list=thresholds_list, pip_difference=pip_difference,
                start_price_time=start_price_time, trade_status=trade_status
            )

            threshold_price_down = await pip_calculator(
                start_price, bid_price, threshold_price_down, threshold_price_down,
                direction="down", symbol=symbol, thresholds_list=thresholds_list, pip_difference=pip_difference,
                start_price_time=start_price_time, trade_status=trade_status
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
