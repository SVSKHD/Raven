import MetaTrader5 as mt5
def place_trade(symbol, order_type, volume, price, slippage, comment, stop_loss=None, take_profit=None):
    """
    Places a trade order in MetaTrader 5.

    :param symbol: Trading symbol (e.g., 'EURUSD')
    :param order_type: Type of order (mt5.ORDER_BUY or mt5.ORDER_SELL)
    :param volume: Volume of the trade (in lots)
    :param price: Price at which to place the order
    :param slippage: Allowed slippage (in points)
    :param comment: Comment for the order
    :param stop_loss: Optional stop loss price
    :param take_profit: Optional take profit price
    :return: Order result or error message
    """
    # Create an order request
    order_request = {
        "action": mt5.TRADE_ACTION_DEAL,  # Correct action for placing a market trade
        "symbol": symbol,
        "volume": volume,
        "price": price,
        "slippage": slippage,
        "type": order_type,  # Either mt5.ORDER_BUY or mt5.ORDER_SELL
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
        return f"Order failed, retcode={result.retcode}, error={result.comment}"

    return f"Order placed successfully, order ticket={result.order}"


import MetaTrader5 as mt5
from datetime import datetime

# Initialize MT5 connection
if not mt5.initialize():
    print("Failed to initialize MetaTrader 5")
    quit()

# Define parameters for the trade
symbol = "EURUSD"
order_type = mt5.ORDER_TYPE_BUY  # You can switch to mt5.ORDER_SELL for a sell order
volume = 0.1  # Trading volume (in lots)
price = mt5.symbol_info_tick(symbol).ask  # Get the current ask price (for buy orders)
slippage = 20  # Allowed slippage in points
comment = "Test buy order"
stop_loss = price - 0.0010  # Set Stop Loss 10 pips below the price
take_profit = price + 0.0020  # Set Take Profit 20 pips above the price

# Place the trade using the place_trade function
result = place_trade(symbol, order_type, volume, price, slippage, comment, stop_loss, take_profit)

# Print the result
print(result)

# Shutdown MT5 connection
mt5.shutdown()
