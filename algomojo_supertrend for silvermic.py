from fyers_apiv3 import fyersModel
from datetime import datetime
import pandas as pd
import numpy as np
import time
import threading

# Fyers API credentials
client_id = "HZOIU8WE37-100"  # Fyers app client ID
client_secret = "VGPLVZM8ZG"
redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"
auth_code = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkubG9naW4uZnllcnMuaW4iLCJpYXQiOjE3MzYyMzE1MzcsImV4cCI6MTczNjI2MTUzNywibmJmIjoxNzM2MjMwOTM3LCJhdWQiOiJbXCJ4OjBcIiwgXCJ4OjFcIiwgXCJ4OjJcIiwgXCJkOjFcIiwgXCJkOjJcIiwgXCJ4OjFcIiwgXCJ4OjBcIl0iLCJzdWIiOiJhdXRoX2NvZGUiLCJkaXNwbGF5X25hbWUiOiJZSzEwODEyIiwib21zIjoiSzEiLCJoc21fa2V5IjoiNDNkYTcwMzBkY2RjZTE1YjgzMWYzY2YwODQ2YmU4NzU0NDc3ZjlmYTZhZmFkOWJlZGMzZjFmN2YiLCJub25jZSI6IiIsImFwcF9pZCI6IkhaT0lVOFdFMzciLCJ1dWlkIjoiMDBjOTYwMWIzNGNhNDlkYzk2ZWVkZWM1NDRmOGI0NzgiLCJpcEFkZHIiOiIwLjAuMC4wIiwic2NvcGUiOiIifQ.iGxAdpeE7jiZ1b7D0X0_PvuPK8OZ0qdkn31E4SQrJFc"  # Generated after logging in
access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3MzYyMzE1NjYsImV4cCI6MTczNjI5NjI0NiwibmJmIjoxNzM2MjMxNTY2LCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbmZNcU81a19oeWlMRGc1Y0wtT041OG8ycmVBUGl5OE5Ed1k4cFNIeE8xZGZsY3FpQlFMY0FFS2o0ZURaNzJEWmV5VzFaY1dFa0Q5SklyOXRwcVhIT0VCZ0hDTlkxbFJTNTU2djJfUWloNXpDUS1WTT0iLCJkaXNwbGF5X25hbWUiOiJLQU5UIEdBVVJBViIsIm9tcyI6IksxIiwiaHNtX2tleSI6IjQzZGE3MDMwZGNkY2UxNWI4MzFmM2NmMDg0NmJlODc1NDQ3N2Y5ZmE2YWZhZDliZWRjM2YxZjdmIiwiZnlfaWQiOiJZSzEwODEyIiwiYXBwVHlwZSI6MTAwLCJwb2FfZmxhZyI6Ik4ifQ.lk1e3b2rnsqA9A1zFy_Hpg7qJx5QPrRlFtUJ1eF7Ra4"

# Set the StrategyName, broker code, Trading symbol, exchange, product, and quantity
strategy = "Supertrend Python"
symbol = "MCX:SILVERMIC25FEBFUT"  # Fyers format for symbols
exchange = "MCX"
quantity = 1

# Supertrend indicator inputs
atr_period = 5
atr_multiplier = 1.0

# Timeframe for historical data
timeframe = "1m"

# Initialize Fyers model
fyers = fyersModel.FyersModel(token=access_token, is_async=False)


def fetch_historical_data(symbol, interval, days=1):
    """
    Fetch historical data using Fyers API.
    """
    try:
        # Define the timeframe mapping for Fyers
        interval_mapping = {
            "1m": "1",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "1d": "D"
        }
        fyers_interval = interval_mapping.get(interval, "1")

        # Calculate the 'from_date' and 'to_date'
        to_date = datetime.now()
        from_date = to_date - pd.Timedelta(days=days)

        # Fetch data from Fyers API
        response = fyers.history(
            data={
                "symbol": symbol,
                "resolution": fyers_interval,
                "date_format": "1",
                "range_from": from_date.strftime('%Y-%m-%d'),
                "range_to": to_date.strftime('%Y-%m-%d'),
                "cont_flag": "1"
            }
        )

        if "candles" not in response or not response["candles"]:
            raise ValueError("No data retrieved from Fyers API")

        # Convert response to DataFrame
        candles = response["candles"]
        data = pd.DataFrame(
            candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="s")
        data.set_index("timestamp", inplace=True)

        return data
    except Exception as e:
        print("Error fetching historical data:", e)
        return pd.DataFrame()


def calculate_supertrend(df, atr_period, atr_multiplier):
    """
    Calculate Supertrend indicator.
    """
    hl2 = (df['high'] + df['low']) / 2
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean()

    upper_band = hl2 + (atr_multiplier * atr)
    lower_band = hl2 - (atr_multiplier * atr)

    supertrend = pd.DataFrame(index=df.index)
    supertrend['Final Upperband'] = upper_band
    supertrend['Final Lowerband'] = lower_band
    supertrend['In Uptrend'] = True

    for i in range(1, len(supertrend)):
        if df['close'].iloc[i] > supertrend['Final Lowerband'].iloc[i - 1]:
            supertrend.loc[supertrend.index[i], 'In Uptrend'] = True
        elif df['close'].iloc[i] < supertrend['Final Upperband'].iloc[i - 1]:
            supertrend.loc[supertrend.index[i], 'In Uptrend'] = False

        if supertrend.loc[supertrend.index[i], 'In Uptrend']:
            supertrend.loc[supertrend.index[i], 'Final Upperband'] = max(
                supertrend['Final Upperband'].iloc[i], supertrend['Final Upperband'].iloc[i - 1]
            )
        else:
            supertrend.loc[supertrend.index[i], 'Final Lowerband'] = min(
                supertrend['Final Lowerband'].iloc[i], supertrend['Final Lowerband'].iloc[i - 1]
            )

    return supertrend


def supertrend_strategy():
    position = 0

    while True:
        try:
            # Fetch historical data
            df = fetch_historical_data(symbol=symbol, interval=timeframe, days=1)

            if df.empty or len(df) < atr_period:
                print("Not enough data retrieved. Waiting for more data...")
                time.sleep(15)
                continue

            # Calculate Supertrend
            supertrend = calculate_supertrend(df, atr_period, atr_multiplier)

            if len(supertrend) < 2:
                print("Supertrend calculation resulted in insufficient data. Waiting...")
                time.sleep(15)
                continue

            is_uptrend = supertrend['In Uptrend']

            long_entry = is_uptrend.iloc[-2] and not is_uptrend.iloc[-3]
            short_entry = not is_uptrend.iloc[-2] and is_uptrend.iloc[-3]

            if long_entry and position <= 0:
                position = quantity
                print(f"Placing BUY order for {symbol}...")
                # Add order placement logic here

            elif short_entry and position >= 0:
                position = -quantity
                print(f"Placing SELL order for {symbol}...")
                # Add order placement logic here

            print(f"Position: {position}, Last Price: {df['close'].iloc[-1]}")
        except Exception as e:
            print("Error in supertrend_strategy:", e)

        time.sleep(15)


# Start strategy in a separate thread
t = threading.Thread(target=supertrend_strategy)
t.start()