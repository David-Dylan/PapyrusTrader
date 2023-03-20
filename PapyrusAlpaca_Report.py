import os
import smtplib
import ssl
import schedule
import time
import json
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import requests
import talib
from tqdm import trange
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from finviz.screener import Screener
from yahoo_fin import stock_info as si
from alpaca_trade_api import REST
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Email settings
smtp_server = "smtp.gmail.com"
port = 465
sender_email = os.getenv('SENDER_EMAIL')
receiver_email = os.getenv('RECEIVER_EMAIL')
password = os.getenv('EMAIL_PASSWORD')

# Alpaca API initialization
api_key = os.getenv('ALPACA_API_KEY_ID')
api_secret = os.getenv('ALPACA_API_SECRET_KEY')
base_url = os.getenv('BASE_URL')
api = REST(api_key, api_secret, base_url, api_version='v2')

# Function to send email
def send_email(subject, body):
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"Email sent to {receiver_email} with subject '{subject}'")

# Function to generate report and send email
def generate_report_and_send_email():
    # Generate the report here
    report = "Report content"

    # Send report email
    send_email("Stock Report", report)

# Function to send trade email
def send_trade_email(trade_info):
    # Generate trade email content
    trade_email_body = f"Trade details:\n\n{trade_info}"

    # Send trade email
    send_email("Trade Executed", trade_email_body)

# Calculate technical indicators (BB, RSI, SMA) from historical data
def calculate_technical_indicators(historical_data):
    close_prices = np.array(historical_data['chart']['result'][0]['indicators']['quote'][0]['close'])
    high_prices = np.array(historical_data['chart']['result'][0]['indicators']['quote'][0]['high'])
    low_prices = np.array(historical_data['chart']['result'][0]['indicators']['quote'][0]['low'])
    volume = np.array(historical_data['chart']['result'][0]['indicators']['quote'][0]['volume'])

    # Calculate RSI
    rsi = talib.RSI(close_prices, timeperiod=14)[-1]

    # Calculate Bollinger Bands
    upper_bb, middle_bb, lower_bb = talib.BBANDS(close_prices, timeperiod=20)

    # Calculate SMA (5 days)
    sma_5 = talib.SMA(close_prices, timeperiod=5)[-1]

    return {
        'rsi': rsi,
        'lower_bb': lower_bb[-1],
        'sma_5': sma_5,
        'volume': volume[-1]
    }

# B-Score System
def calculate_b_score(stock_df):
    b_score = 0
    
    # 1. RSI <= 40
    if stock_df['rsi'] <= 40:
        b_score += 1

    # 2. Volume >= 100
    if stock_df['volume'] >= 100:
        b_score += 1

    # 3. Filled price <= Lower Bollinger band
    if stock_df['filled_price'] <= stock_df['lower_bb']:
        b_score += 1

    # 4. SMA (5 days) <= VWAP
    if stock_df['sma_5'] <= stock_df['vwap']:
        b_score += 1

    # 5. Spread > -0.05 (This might change in the future)
    if stock_df['spread'] > -0.05:
        b_score += 1

    # 6. Filled price = Current Bid
    if stock_df['filled_price'] == stock_df['current_bid']:
        b_score += 1

    # 7. IV <= 40
    if stock_df['iv'] <= 40:
        b_score += 1

    # 8. Today gain <= 0
    if stock_df['today_gain'] <= 0:
        b_score += 1

    return b_score

# Function to get historical data from the custom Yahoo endpoint
def get_historical_data(symbol, period1, period2):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?symbol={symbol}&period1={period1}&period2={period2}&useYfid=true&interval=5m&includePrePost=false&lang=en-US&region=US"
    response = requests.get(url)
    data = response.json()
    return data

# Function to execute trades
def execute_trade():
    # Initialize Alpaca API with environment variables
    api_key = os.getenv('ALPACA_API_KEY_ID')
    api_secret = os.getenv('ALPACA_API_SECRET_KEY')
    base_url = os.getenv('BASE_URL')
    api = REST(api_key, api_secret, base_url, api_version='v2')


    # ...
    # Initialize progress bar
    progress_bar = trange(3, desc="Executing trade", leave=True)
    
    # 1. Connect to SMTP server
    progress_bar.set_description("Connecting to SMTP server")
    context = ssl.create_default_context()
    try:
        server = smtplib.SMTP_SSL(smtp_server, port, context=context)
        server.login(sender_email, password)
    except Exception as e:
        print(f"Error connecting to SMTP server: {e}")
        return
    progress_bar.update(1)  # Increment progress bar

    # 2. Generate report and send email
    progress_bar.set_description("Generating report and sending email")
    generate_report_and_send_email()
    progress_bar.update(1)  # Increment progress bar
    
    # 3. Calculate B-Score and display stock data
    progress_bar.set_description("Calculating B-Score and displaying stock data")

    # ... (get stock data, calculate B-Score, and filter options as before)

    # Get account info using Alpaca API
    account_info = api.get_account()
    available_funds = float(account_info.cash)

    # Determine the amount to invest (20% of available funds)
    investment_amount = available_funds * 0.2
    
    # Display stock data
    print("Stock data:")
    print(stock_df)
    
    progress_bar.update(1)  # Increment progress bar
    progress_bar.close()

    # Generate report and send email
    generate_report_and_send_email()

    # Make the trade
    if best_options:
        selected_option = best_options[0]
        num_contracts = int(investment_amount // (selected_option['option_price'] * 100))
        if num_contracts > 0:
            try:
                order = api.submit_order(
                    symbol=selected_option['option_symbol'],
                    qty=num_contracts,
                    side='buy',
                    type='limit',
                    time_in_force='gtc',
                    limit_price=selected_option['option_price']
                )
                print(f"Placed order: {order}")

                # Send trade email
                send_trade_email(order)

            except Exception as e:
                print(f"Error placing order: {e}")
        else:
            print("Not enough funds to place the order.")
    else:
        print("No suitable options found.")
        
def main():
    # Schedule the execute_trade function to run every 4 hours
    schedule.every(4).hours.do(execute_trade)

    # Run the scheduled tasks
    while True:
        schedule.run_pending()
        time.sleep(60)  # Wait for 60 seconds before checking again

if __name__ == "__main__":
    main()