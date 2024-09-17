import datetime
import pytz
import asyncio  # Import asyncio to run the async function

# Simulated trade result to replace actual place_trade and close_all_trades
async def simulate_trade(symbol, direction, current_price):
    print(f"Simulated {direction.upper()} trade placed for {symbol} at price {current_price:.4f}")

async def simulate_close_trade(symbol, direction):
    print(f"Simulated {direction.upper()} trade closed for {symbol}")

async def pip_calculator(start_price, current_price, threshold_price, previous_threshold, direction, symbol,
                         thresholds_list, pip_difference, start_price_time, trade_status):
    # Symbol-wise pip factor (EURUSD and GBPUSD use 0.0001; USDJPY and EURJPY use 0.01)
    pip_factor = {
        'EURUSD': 0.0001,
        'GBPUSD': 0.0001,
        'USDJPY': 0.01,
        'EURJPY': 0.01
    }

    # Determine the pip factor for the given symbol, default to 0.0001 if not found
    symbol_pip_factor = pip_factor.get(symbol, 0.0001)

    # Calculate pip differences based on symbol's pip factor
    diff_from_start = (current_price - start_price) if direction == "up" else (start_price - current_price)
    diff_from_previous = (current_price - previous_threshold) if direction == "up" else (
            previous_threshold - current_price)

    # Multiply by the symbol-specific pip factor
    pips_from_start = diff_from_start / symbol_pip_factor
    pips_from_previous = diff_from_previous / symbol_pip_factor

    if abs(pips_from_previous) >= pip_difference:
        thresholds_list.append(current_price)
        message = (
            f"Threshold reached at {current_price:.4f} for {symbol}, "
            f"previous threshold {previous_threshold:.4f}, start price {start_price:.4f}, "
            f"{pips_from_start:.2f} pips from start, {direction.capitalize()}.\n"
            f"Thresholds list: {thresholds_list}"
        )
        # Simulate sending a telegram message
        print(message)

        # Simulate trade placement and closing
        if trade_status["open_trade"] is None:
            # First threshold: simulate trade
            await simulate_trade(symbol, direction, current_price)
            trade_status["open_trade"] = direction  # Mark the trade as open with direction 'up' or 'down'
            trade_status["threshold_count"] = 1  # Start counting thresholds in the same direction

        elif trade_status["open_trade"]:
            # Second threshold: close the trade if it hits the second threshold in the same direction
            if direction == trade_status["open_trade"]:  # Check if the direction matches the open trade direction
                trade_status["threshold_count"] += 1
                if trade_status["threshold_count"] == 2:
                    await simulate_close_trade(symbol, direction)
                    trade_status["open_trade"] = None
                    trade_status["threshold_count"] = 0

        current_time = datetime.datetime.now(pytz.utc)
        # Simulate saving data to MongoDB
        print(f"Simulated saving to DB for {symbol} at {current_time}")

        return current_price
    else:
        return threshold_price

# Simulated data to test the function
async def test_pip_calculator():
    # Test data for EURUSD, GBPUSD, USDJPY, and EURJPY
    test_data = [
        {"symbol": "EURUSD", "start_price": 1.1234, "current_price": 1.1250, "previous_threshold": 1.1230, "direction": "up", "pip_difference": 15},
        {"symbol": "GBPUSD", "start_price": 1.2300, "current_price": 1.2330, "previous_threshold": 1.2295, "direction": "up", "pip_difference": 15},
        {"symbol": "USDJPY", "start_price": 109.50, "current_price": 109.80, "previous_threshold": 109.45, "direction": "up", "pip_difference": 20},
        {"symbol": "EURJPY", "start_price": 123.50, "current_price": 123.90, "previous_threshold": 123.45, "direction": "up", "pip_difference": 20}
    ]

    for data in test_data:
        trade_status = {"open_trade": None, "threshold_count": 0}
        thresholds_list = [data["start_price"]]
        start_price_time = datetime.datetime.now(pytz.utc)

        print(f"\nTesting {data['symbol']}...")
        await pip_calculator(
            start_price=data["start_price"],
            current_price=data["current_price"],
            threshold_price=data["previous_threshold"],
            previous_threshold=data["previous_threshold"],
            direction=data["direction"],
            symbol=data["symbol"],
            thresholds_list=thresholds_list,
            pip_difference=data["pip_difference"],
            start_price_time=start_price_time,
            trade_status=trade_status
        )

# Run the test using asyncio.run
if __name__ == "__main__":
    asyncio.run(test_pip_calculator())
