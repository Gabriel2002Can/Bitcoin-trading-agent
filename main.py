import requests 
import os
from dotenv import load_dotenv
import yfinance as yf

def get_data():

    return yf.Ticker("BTC-USD")

BTC = get_data() 

print("Bitcoin Open : ", round(BTC.info['open'],0))
print("        Day     : ", round(BTC.info['dayLow'], 0), "-", round(BTC.info['dayHigh'], 0))
print("        52 Week : ", round(BTC.info['fiftyTwoWeekLow'], 0), "-", round(BTC.info['fiftyTwoWeekHigh'], 0))

CurrentPrice = BTC.fast_info['lastPrice']

print(CurrentPrice)

print(BTC.info)