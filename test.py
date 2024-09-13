import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz
import asyncio
from notifications import send_telegram_message
from trade_management import close_all_trades, place_trade

correlation_list = [
    {"currency": 'EURUSD', "pip_difference": 15},
    {"currency": 'GBPUSD', "pip_difference": 15}
]

TIMEFRAME = mt5.TIMEFRAME_M5


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
    # Check if the market session is open
    return symbol_info.session_open != 0  # Non-zero means the market is open


# Wait until the market opens
async def wait_for_market_open(symbol):
    while not is_market_open(symbol):
        print(f"Market is currently closed for {symbol}. Waiting for it to open...")
        await asyncio.sleep(60)  # Wait for 1 minute before checking again
    print(f"Market is now open for {symbol}.")


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


# Function to calculate pips and handle threshold logic
async def pip_calculator(start_price, current_price, threshold_price, previous_threshold, direction, symbol,
                         thresholds_list, pip_difference):
    diff_from_start = (current_price - start_price) if direction == "up" else (start_price - current_price)
    diff_from_previous = (current_price - previous_threshold) if direction == "up" else (
            previous_threshold - current_price)

    pips_from_start = diff_from_start * 10000  # Difference from start price in pips
    pips_from_previous = diff_from_previous * 10000  # Difference from previous threshold in pips

    if abs(pips_from_previous) >= pip_difference:
        # If the new threshold is crossed, add it to the list and send a message
        thresholds_list.append(current_price)
        message = (
            f"Threshold reached at {current_price:.4f} for {symbol}, "
            f"previous threshold {previous_threshold:.4f}, start price {start_price:.4f}, "
            f"{pips_from_start:.2f} pips from start, {direction.capitalize()}.\n"
            f"Thresholds list: {thresholds_list}"
        )
        await send_telegram_message(message)
        return current_price  # Update the threshold price
    else:
        return threshold_price  # Keep the current threshold if not crossed


# Function to get the latest price
def get_latest_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise ValueError(
            f"Failed to get the latest price for {symbol}. Ensure the symbol is correct and the market is open.")

    return tick.bid, tick.ask


# Async function to handle 2:00 AM IST logic
async def get_next_2am_ist(symbol):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    if now.hour >= 2:
        next_2am = (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)
    else:
        next_2am = now.replace(hour=2, minute=30, second=0, microsecond=0)

    # Instead of fetching the current price, get the price when the market opens on Monday
    start_price = await get_market_open_price(symbol)
    await send_telegram_message(f"Market open price retrieved: {start_price} for {symbol} on Monday")
    print(f"{symbol}-{next_2am}-{start_price}")
    return next_2am.astimezone(pytz.utc), start_price


# Function to handle the processing for each currency
async def log_currency(symbol, pip_difference):
    try:
        next_2am, start_price = await get_next_2am_ist(symbol)
        await send_telegram_message(f"Started with {symbol} - {start_price}")

        threshold_price_up = start_price
        threshold_price_down = start_price

        # To keep track of thresholds
        thresholds_list = [start_price]  # Starts with the initial price at market open

        while True:
            now = datetime.now(pytz.utc)

            if now >= next_2am:
                next_2am, start_price = await get_next_2am_ist(symbol)
                threshold_price_up = start_price
                threshold_price_down = start_price
                thresholds_list = [start_price]  # Reset thresholds list after a new 2 AM price is fetched

            bid_price, ask_price = get_latest_price(symbol)

            # Calculate pips in one direction (up) when threshold is crossed
            threshold_price_up = await pip_calculator(
                start_price, ask_price, threshold_price_up, threshold_price_up,
                direction="up", symbol=symbol, thresholds_list=thresholds_list, pip_difference=pip_difference
            )

            # Calculate pips in the other direction (down) when threshold is crossed
            threshold_price_down = await pip_calculator(
                start_price, bid_price, threshold_price_down, threshold_price_down,
                direction="down", symbol=symbol, thresholds_list=thresholds_list, pip_difference=pip_difference
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
