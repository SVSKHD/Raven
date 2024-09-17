from pymongo import MongoClient
import pytz
from datetime import datetime

# MongoDB Configuration
MONGO_URI = 'mongodb+srv://hithesh:hithesh@utbiz.npdehas.mongodb.net/'
client = MongoClient(MONGO_URI)
db = client['pip_tracking_db']
ist = pytz.timezone('Asia/Kolkata')

# Save or update threshold data in MongoDB
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
    return result

# Check if data already exists in MongoDB
def check_data_exists_in_mongo(symbol, date):
    collection_name = "pip_check"
    pip_check_collection = db[collection_name]
    date_str = date.strftime('%Y-%m-%d')
    query = {"symbol": symbol, "date": date_str}
    return pip_check_collection.find_one(query)

# Generic function to update any field in a MongoDB document
def update_variable_in_mongo(symbol, date, updates):
    """
    Update any field in the MongoDB document based on the symbol and date.

    :param symbol: The currency symbol to identify the document.
    :param date: The date to identify the document.
    :param updates: A dictionary containing the fields and their new values.
    :return: The result of the MongoDB update operation.
    """
    collection_name = "pip_check"
    pip_check_collection = db[collection_name]
    date_str = date.strftime('%Y-%m-%d')

    # Query to find the document
    query = {"symbol": symbol, "date": date_str}

    # Prepare the update data using the $set operator
    update_data = {"$set": updates}

    # Update the document
    result = pip_check_collection.update_one(query, update_data, upsert=True)

    if result.matched_count > 0:
        print(f"Document for {symbol} on {date_str} updated successfully.")
    else:
        print(f"New document for {symbol} on {date_str} created.")

    return result
