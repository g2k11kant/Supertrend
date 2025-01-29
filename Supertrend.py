from fyers_apiv3 import fyersModel
from datetime import datetime
import pandas as pd
import numpy as np
import time
import threading
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Fyers API credentials (use environment variables or config files for better security)
client_id = "HZOIU8WE37-100"  # Replace with your client ID
client_secret = "VGPLVZM8ZG"
redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"
access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3MzgxMzU3NTAsImV4cCI6MTczODE5NzAxMCwibmJmIjoxNzM4MTM1NzUwLCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbm1kakdPcWN6Q1hJNmdkVGdXdzJTRkE4UmZsNHJnNUFkWFdwS0ZJXzNHZVE2RXRmZG5ORFhudUwybXplUTN3N0g4VF9kM3JJdU5WWVVyYzdqLTdqUUhFVGtXMjI1RDFEdl9EbU9BeW9TcWIyVnVJMD0iLCJkaXNwbGF5X25hbWUiOiJLQU5UIEdBVVJBViIsIm9tcyI6IksxIiwiaHNtX2tleSI6IjQzZGE3MDMwZGNkY2UxNWI4MzFmM2NmMDg0NmJlODc1NDQ3N2Y5ZmE2YWZhZDliZWRjM2YxZjdmIiwiaXNEZHBpRW5hYmxlZCI6Ik4iLCJpc010ZkVuYWJsZWQiOiJOIiwiZnlfaWQiOiJZSzEwODEyIiwiYXBwVHlwZSI6MTAwLCJwb2FfZmxhZyI6Ik4ifQ.I3-hgjsScQsQjjZfIw9IKeJFfQjszJgUSx2SJ2ioGWM"  # Replace with your access token

# Strategy settings
strategy = "Supertrend Python"
symbol = "MCX:SILVERMIC25FEBFUT"
exchange = "MCX"
quantity = 1
timeframe = "1m"
atr_period = 5
atr_multiplier = 1.0

# Initialize Fyers model
fyers = fyersModel.FyersModel(token=access_token, is_async=False)

def fetch_historical_data(symbol, interval, days=1):
    """
    Fetch historical data using Fyers API.
    """
    try:
        interval_mapping = {
            "1m": "1",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "1d": "D"
        }
        fyers_interval = interval_mapping.get(interval, "1")
        to_date = datetime.now()
        from_date = to_date - pd.Timedelta(days=days)

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
        if response.get("s") != "ok" or "candles" not in response:
            raise ValueError(f"Failed to fetch data: {response.get('message', 'Unknown error')}")

        # Convert data to DataFrame
        candles = response["candles"]
        data = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="s")
        data.set_index("timestamp", inplace=True)
        return data

    except Exception as e:
        logging.error(f"Error fetching historical data: {e}")
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

def get_current_position(symbol):
    """
    Fetch current position for the symbol using Fyers API.
    """
    try:
        response = fyers.positions()
        if response.get("s") == "ok":
            for pos in response["netPositions"]:
                if pos["symbol"] == symbol:
                    return pos["qty"]
        return 0
    except Exception as e:
        logging.error(f"Error fetching current position: {e}")
        return 0

def supertrend_strategy():
    position = get_current_position(symbol)
    logging.info(f"Starting strategy with current position: {position}")

    while True:
        try:
            # Fetch historical data
            df = fetch_historical_data(symbol=symbol, interval=timeframe, days=1)

            if df.empty or len(df) < atr_period:
                logging.warning("Not enough data retrieved. Waiting for more data...")
                time.sleep(15)
                continue

            # Calculate Supertrend
            supertrend = calculate_supertrend(df, atr_period, atr_multiplier)

            if len(supertrend) < 2:
                logging.warning("Supertrend calculation resulted in insufficient data. Waiting...")
                time.sleep(15)
                continue

            is_uptrend = supertrend['In Uptrend']
            long_entry = is_uptrend.iloc[-2] and not is_uptrend.iloc[-3]
            short_entry = not is_uptrend.iloc[-2] and is_uptrend.iloc[-3]

            if long_entry and position <= 0:
                position = quantity
                data = {
                    "symbol": symbol,
                    "qty": quantity,
                    "type": 2,
                    "side": 1,
                    "productType": "MARGIN",
                    "limitPrice": 0,
                    "stopPrice": 0,
                    "validity": "DAY",
                    "disclosedQty": 0,
                    "offlineOrder": False,
                    "orderTag": "tag1"
                }
                response = fyers.place_order(data=data)
                logging.info(f"Buy Order Response: {response}")

            elif short_entry and position >= 0:
                position = -quantity
                data = {
                    "symbol": symbol,
                    "qty": quantity,
                    "type": 2,
                    "side": -1,
                    "productType": "MARGIN",
                    "limitPrice": 0,
                    "stopPrice": 0,
                    "validity": "DAY",
                    "disclosedQty": 0,
                    "offlineOrder": False,
                    "orderTag": "tag1"
                }
                response = fyers.place_order(data=data)
                logging.info(f"Sell Order Response: {response}")

            logging.info(f"Position: {position}, Last Price: {df['close'].iloc[-1]}")

        except Exception as e:
            logging.error(f"Error in supertrend_strategy: {e}")

        time.sleep(15)

# Start the strategy in a thread
t = threading.Thread(target=supertrend_strategy)
t.start()
