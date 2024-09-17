import MetaTrader5 as mt5
from notifications import send_telegram_message

async def place_trade(symbol, direction, volume, price, slippage, comment, stop_loss=None, take_profit=None):
    """
    Places a trade order (buy or sell) in MetaTrader 5 based on the given direction.

    :param symbol: Trading symbol (e.g., 'EURUSD')
    :param direction: 'up' for buy (long) and 'down' for sell (short)
    :param volume: Volume of the trade (in lots)
    :param price: Price at which to place the order
    :param slippage: Allowed slippage (in points)
    :param comment: Comment for the order
    :param stop_loss: Optional stop loss price
    :param take_profit: Optional take profit price
    :return: Order result or error message
    """
    # Determine the order type based on direction
    if direction == "up":
        order_type = mt5.ORDER_BUY
    elif direction == "down":
        order_type = mt5.ORDER_SELL
    else:
        raise ValueError("Invalid direction. Use 'up' for buy or 'down' for sell.")

    # Create an order request
    order_request = {
        "action": mt5.TRADE_ACTION_DEAL,  # Specifies that the trade is a market order
        "symbol": symbol,
        "volume": volume,
        "price": price,
        "slippage": slippage,
        "type": order_type,  # Order type (BUY or SELL)
        "comment": comment,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "magic": 0,
        "type_time": mt5.ORDER_TIME_GTC,  # Good-Til-Canceled
        "type_filling": mt5.ORDER_FILLING_FOK,  # Fill-Or-Kill
    }

    # Send the order
    result = mt5.order_send(order_request)

    # Check if the order was placed successfully
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        message = f"Order failed for {symbol}, retcode={result.retcode}"
        await send_telegram_message(message)
        return message

    # Send a success message to Telegram and return result
    message = f"Trade successful for {symbol}. Order ticket: {result.order}, Direction: {direction.capitalize()}, Volume: {volume} lots."
    await send_telegram_message(message)
    return message


def close_all_trades():
    # Initialize connection to MetaTrader 5
    if not mt5.initialize():
        print("Failed to initialize MT5, error code:", mt5.last_error())
        return

    # Retrieve open positions
    open_positions = mt5.positions_get()

    if open_positions is None or len(open_positions) == 0:
        print("No open positions.")
        return

    # Loop through each open position and close it
    for position in open_positions:
        symbol = position.symbol
        ticket = position.ticket
        lot = position.volume

        # Determine the type of trade (buy or sell) to create the opposite order
        if position.type == mt5.ORDER_TYPE_BUY:
            trade_type = mt5.ORDER_TYPE_SELL
        elif position.type == mt5.ORDER_TYPE_SELL:
            trade_type = mt5.ORDER_TYPE_BUY
        else:
            print(f"Unknown position type for ticket {ticket}.")
            continue

        # Create close request
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": trade_type,
            "position": ticket,
            "deviation": 20,
            "magic": 123456,  # Your unique identifier for trades
            "comment": "Closing trade",
        }

        # Send close order
        result = mt5.order_send(close_request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to close trade {ticket}, error code: {result.retcode}")
        else:
            print(f"Successfully closed trade {ticket}.")
