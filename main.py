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

data = get_data().json()        

print(data)