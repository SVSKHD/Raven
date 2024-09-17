import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz

def get_historical_data(symbol, start_date, end_date=None, time_hour=12, timeframe=mt5.TIMEFRAME_M1):
    """
    Fetch historical data for the given symbol at a specific time of day (default is 12:00).
    If no data is found for 12:00 AM on a Monday, it will return the first available data after market opens.

    :param symbol: Trading symbol (e.g., 'EURUSD')
    :param start_date: The date to fetch historical data from (as a datetime object).
    :param end_date: The end date to fetch historical data until (optional, defaults to the same day as start_date).
    :param time_hour: The hour of the day to fetch data (defaults to 12:00).
    :param timeframe: The timeframe for historical data (default is M1 - 1 minute).
    :return: Historical data if found, or a message indicating failure.
    """
    if end_date is None:
        end_date = start_date

    # Set the timezone to UTC
    utc = pytz.utc

    # Set the start time and end time to 12:00 (or specified hour) UTC
    start_time = utc.localize(datetime(start_date.year, start_date.month, start_date.day, time_hour, 0, 0))
    end_time = utc.localize(datetime(end_date.year, end_date.month, end_date.day, time_hour, 0, 0)) + timedelta(minutes=1)

    # Fetch historical data for the given symbol at the requested time
    rates = mt5.copy_rates_range(symbol, timeframe, start_time, end_time)

    # If data is available at the specified time, return it
    if rates is not None and len(rates) > 0:
        print(f"Historical data for {symbol} on {start_date.strftime('%Y-%m-%d')} at {time_hour}:00")
        for rate in rates:
            print(f"Time: {datetime.utcfromtimestamp(rate['time']).strftime('%Y-%m-%d %H:%M:%S')} Close: {rate['close']}")
        return rates

    # Handle the case for Monday when there may not be 12:00 AM data
    if start_date.weekday() == 0:  # Monday
        print(f"No data available at {time_hour}:00 for {symbol} on Monday. Fetching the first available data.")

        # Look for the first available data on Monday after 12:00 AM
        next_available_time = start_time + timedelta(hours=1)
        while next_available_time < end_time + timedelta(days=1):  # Check within the next 24 hours
            rates = mt5.copy_rates_range(symbol, timeframe, next_available_time, next_available_time + timedelta(minutes=1))
            if rates is not None and len(rates) > 0:
                print(f"First available data for {symbol} after 12:00 AM: ")
                for rate in rates:
                    print(f"Time: {datetime.utcfromtimestamp(rate['time']).strftime('%Y-%m-%d %H:%M:%S')} Close: {rate['close']}")
                return rates
            next_available_time += timedelta(minutes=1)

    print(f"No data found for {symbol} on {start_date.strftime('%Y-%m-%d')} after checking the market open on Monday.")
    return None

# Example Usage
if __name__ == "__main__":
    # Initialize MetaTrader 5 connection
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        quit()

    # Example to fetch EURUSD data at 12:00 on a Monday
    start_date = datetime(2023, 10, 2)  # A Monday
    get_historical_data('EURUSD', start_date, time_hour=0)  # Fetch data at 12:00 AM

    # Shutdown MetaTrader 5 connection
    mt5.shutdown()


def get_5min_data_for_day(symbol, date):
    """
    Fetch 5-minute time frame data for the given symbol from 12:00 AM to the end of the day.

    :param symbol: Trading symbol (e.g., 'EURUSD')
    :param date: The date for which to fetch the 5-minute time frame data (as a datetime object).
    :return: Historical data if found, or a message indicating failure.
    """
    # Set the timezone to UTC
    utc = pytz.utc

    # Set start time to 12:00 AM of the given date
    start_time = utc.localize(datetime(date.year, date.month, date.day, 0, 0, 0))

    # Set end time to 11:59:59 PM of the same date (the end of the day)
    end_time = utc.localize(datetime(date.year, date.month, date.day, 23, 59, 59))

    # Fetch historical data for the given symbol at a 5-minute time frame (M5)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start_time, end_time)

    if rates is not None and len(rates) > 0:
        print(f"5-Minute historical data for {symbol} on {date.strftime('%Y-%m-%d')}")
        for rate in rates:
            print(f"Time: {datetime.utcfromtimestamp(rate['time']).strftime('%Y-%m-%d %H:%M:%S')} Close: {rate['close']}")
        return rates
    else:
        print(f"No 5-minute historical data found for {symbol} on {date.strftime('%Y-%m-%d')}")
        return None

# Example Usage
# if __name__ == "__main__":
#     # Initialize MetaTrader 5 connection
#     if not mt5.initialize():
#         print("Failed to initialize MetaTrader 5")
#         quit()
#
#     # Example to fetch EURUSD 5-minute data from 12:00 AM to end of the day on a specific date
#     date = datetime(2023, 9, 30)  # Replace with your desired date
#     get_5min_data_for_day('EURUSD', date)
#
#     # Shutdown MetaTrader 5 connection
#     mt5.shutdown()
