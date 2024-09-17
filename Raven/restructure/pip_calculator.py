import datetime
import pytz
from notifications import send_telegram_message
from db_operations import save_or_update_threshold_in_mongo
from trade_management import place_trade, close_all_trades

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
        await send_telegram_message(message)

        # Place trade at first threshold and close at second in the same direction
        if trade_status["open_trade"] is None:
            # First threshold: place trade
            trade_result = await place_trade(
                symbol=symbol,
                direction=direction,  # 'up' for buy and 'down' for sell
                volume=0.1,  # Adjust the volume as needed
                price=current_price,
                slippage=20,  # Example slippage
                comment=f"Auto trade due to {pip_difference}-pip {direction} movement for {symbol}",
                stop_loss=None,  # Optional stop loss
                take_profit=None  # Optional take profit
            )
            trade_status["open_trade"] = direction  # Mark the trade as open with direction 'up' or 'down'
            trade_status["threshold_count"] = 1  # Start counting thresholds in the same direction
            print(f"Trade result for {trade_status['open_trade'].upper()}: {trade_result}")

        elif trade_status["open_trade"]:
            # Second threshold: close the trade if it hits the second threshold in the same direction
            if direction == trade_status["open_trade"]:  # Check if the direction matches the open trade direction
                trade_status["threshold_count"] += 1
                if trade_status["threshold_count"] == 2:
                    close_all_trades()
                    trade_status["open_trade"] = None
                    trade_status["threshold_count"] = 0
                    print(f"Closed {direction.upper()} trade at second threshold.")

        current_time = datetime.now(pytz.utc)
        await save_or_update_threshold_in_mongo(symbol, start_price, current_price, previous_threshold, pips_from_start,
                                                direction, thresholds_list, current_time, start_price_time)

        return current_price
    else:
        return threshold_price
