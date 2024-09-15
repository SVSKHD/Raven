import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# Initialize the MT5 connection
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Set the symbol and time frame
symbol = "GBPUSD"  # Replace with the symbol you want
timeframe = mt5.TIMEFRAME_M5  # 5-minute time frame

# Set the date range with specific start time
start_date = datetime(2024, 8, 30, 2, 0)  # 2:00 AM on August 30th, 2024
end_date = datetime(2024, 8, 30, 23, 59)  # End of day on August 30th, 2024

# Fetch the historical data
rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)

# Shutdown MT5 connection
mt5.shutdown()

# Create a DataFrame
df = pd.DataFrame(rates)

# Convert the timestamp to a readable date format
df['time'] = pd.to_datetime(df['time'], unit='s')

# Save the DataFrame to a CSV file (optional, if you want to keep a record)
csv_filename = f"{symbol}_5M_data_{start_date.strftime('%Y%m%d_%H%M')}_{end_date.strftime('%Y%m%d_%H%M')}.csv"
df.to_csv(csv_filename, index=False)
print(f"Data saved to {csv_filename}")

# --------------------------------------------------------------
# Pip Calculation Logic
# --------------------------------------------------------------

# Filter the data to start from 02:00 AM on August 30, 2024
filtered_data = df[df['time'] >= start_date].copy()

# Identify the starting price at 02:00 AM
start_price = filtered_data.iloc[0]['close']

# Calculate the pip difference from the start price
filtered_data['pip_difference'] = (filtered_data['close'] - start_price) * 10000

# Initialize variables to track thresholds
threshold = 15  # 15-pip threshold
last_threshold_price = start_price
last_threshold_time = filtered_data.iloc[0]['time']

# List to store the threshold crossing times and prices
thresholds_crossed = []

# Loop through the data to check for threshold crossings
for index, row in filtered_data.iterrows():
    pip_difference = (row['close'] - last_threshold_price) * 10000
    if abs(pip_difference) >= threshold:
        thresholds_crossed.append({
            'time': row['time'],
            'price': row['close'],
            'pip_difference': pip_difference
        })
        # Update the last threshold price and time
        last_threshold_price = row['close']
        last_threshold_time = row['time']

# Convert the results to a DataFrame
thresholds_df = pd.DataFrame(thresholds_crossed)

# Display the results
print("15-Pip Thresholds Crossed:")
print(thresholds_df)

# --------------------------------------------------------------
# Pip Movement After First Threshold
# --------------------------------------------------------------

# Identify the first threshold crossing
first_threshold = thresholds_df.iloc[0]
first_threshold_time = first_threshold['time']
first_threshold_price = first_threshold['price']

# Filter the data to include only points after the first threshold crossing
post_threshold_data = filtered_data[filtered_data['time'] > first_threshold_time].copy()

# Calculate the pip difference from the first threshold price
post_threshold_data['pip_diff_after_first'] = (post_threshold_data['close'] - first_threshold_price) * 10000

# Calculate the maximum and minimum pip movement after the first threshold
max_pip_movement = post_threshold_data['pip_diff_after_first'].max()
min_pip_movement = post_threshold_data['pip_diff_after_first'].min()

# Find the corresponding prices for max and min movements
max_movement_price = post_threshold_data.loc[post_threshold_data['pip_diff_after_first'] == max_pip_movement, 'close'].values[0]
min_movement_price = post_threshold_data.loc[post_threshold_data['pip_diff_after_first'] == min_pip_movement, 'close'].values[0]

# Create a summary DataFrame
movement_summary = pd.DataFrame({
    'max_pip_movement': [max_pip_movement],
    'max_movement_price': [max_movement_price],
    'min_pip_movement': [min_pip_movement],
    'min_movement_price': [min_movement_price]
})

# Display the summary
print("\nPip Movement After First Threshold:")
print(movement_summary)
