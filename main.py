import requests 
import os
from dotenv import load_dotenv

load_dotenv(".env")

def get_data():

    api_key = os.getenv("API_KEY") 

    response = requests.get(
        "https://pro-api.coinmarketcap.com/v3/cryptocurrency/quotes/latest",
        params={                  
            "slug": "bitcoin",           
            "convert": "USD"
        },
        headers={
            "X-CMC_PRO_API_KEY": api_key
        }
    )

    return response

current_data = get_data().json() 

btc = current_data["data"][0]

quote_usd = btc["quote"][0]

current_price = quote_usd["price"]
percent_1h    = quote_usd["percent_change_1h"]

print(f"Current BTC price: ${current_price:,.2f}")
print(f"Percent change 1h: {percent_1h:.2f}%")