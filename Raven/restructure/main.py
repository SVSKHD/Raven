import asyncio
import MetaTrader5 as mt5
from mt5_init_operations import initialize_mt5, get_latest_price, get_historical_price
from pip_calculator import pip_calculator
from notifications import send_telegram_message

correlation_list = [
    {"currency": 'EURUSD', "pip_difference": 15},
    {"currency": 'GBPUSD', "pip_difference": 15}
]

async def log_currency(symbol, pip_difference):
    trade_status = {"open_trade": None, "threshold_count": 0}
    try:
        start_price, start_price_time = await get_historical_price(symbol)
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

async def main():
    initialize_mt5()
    tasks = []
    for currency in correlation_list:
        tasks.append(log_currency(currency['currency'], currency['pip_difference']))
    await asyncio.gather(*tasks)

# Run the main script
if __name__ == "__main__":
    asyncio.run(main())
