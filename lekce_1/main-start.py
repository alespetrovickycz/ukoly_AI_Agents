import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import json
import yfinance as yf
from pprint import pprint

import requests
import datetime
import time
from datetime import date, timedelta

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
owmapi_key = os.environ.get("OPENWEATHERMAP_API_KEY")

# Function Implementations
def get_stock_price(ticker: str):
    ticker_info = yf.Ticker(ticker).info
    current_price = ticker_info.get("currentPrice")
    return {"ticker": ticker, "current_price": current_price}


def get_dividend_date(ticker: str):
    ticker_info = yf.Ticker(ticker).info
    dividend_date = ticker_info.get("dividendDate")
    return {"ticker": ticker, "dividend_date": dividend_date}

def get_coordinates(city_name, api_key):
    """
    Převede název města na zeměpisné souřadnice (lat/lon) pomocí geocoding API.
    """
    # Geocoding API (hledání souřadnic)
    geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name},CZ&limit=1&appid={api_key}"
    
    try:
        response = requests.get(geocode_url)
        response.raise_for_status()
        data = response.json()
        
        if data:
            lat = data[0]['lat']
            lon = data[0]['lon']
            return lat, lon
        else:
            print(f"Chyba: Souřadnice pro město '{city_name}' nebyly nalezeny.")
            return None, None
            
    except requests.exceptions.RequestException as e:
        print(f"Chyba při volání Geocoding API: {e}")
        return None, None

def get_tomorrow_weather(city_name, api_key = owmapi_key):
    """
    Získá zítřejší předpověď počasí pro zadané město pomocí bezplatného OWM API 
    (5 Day / 3 Hour Forecast).
    """
    
    # 1. Získání souřadnic z názvu města (předpokládáme, že tato funkce funguje)
    # Pro testování použijeme souřadnice Prahy, které jste uvedl/a
    lat, lon = get_coordinates(city_name, api_key)
    if lat is None:
        return None
    
    # 2. Volání 5 Day / 3 Hour Forecast API (URL je s /data/2.5/forecast)
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=cz"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        tomorrow = date.today() + timedelta(days=1)
        
        tomorrow_forecasts = []
        
        # Projdeme všechny 3hodinové intervaly
        for item in data['list']:
            # Převedeme čas předpovědi z Unix timestamp na objekt datetime
            forecast_date_time = datetime.datetime.fromtimestamp(item['dt'])
            
            # Pokud datum předpovědi odpovídá zítřku, uložíme teplotu
            if forecast_date_time.date() == tomorrow:
                tomorrow_forecasts.append(item['main']['temp'])
        
        if not tomorrow_forecasts:
            print("Chyba: Předpověď pro zítřek nebyla v datech nalezena.")
            return None

        # Najdeme maximální a minimální teplotu z nalezených 3hodinových intervalů
        max_temp = max(tomorrow_forecasts)
        min_temp = min(tomorrow_forecasts)
        
        return {
            "city": city_name, 
            "date": tomorrow.strftime("%d.%m.%Y"),
            "min_temp_celsius": round(min_temp),
            "max_temp_celsius": round(max_temp)
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Chyba při volání Forecast API: {e}")
        return None

tools = [
    {
        "name": "get_stock_price",
        "description": "Use this function to get the current price of a stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol for the stock, e.g. GOOG",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_dividend_date",
        "description": "Use this function to get the next dividend payment date of a stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol for the stock, e.g. GOOG",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_tomorrow_weather",
        "description": "Use this function to get tomorrow minimum and maximum temperature in specified city",
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "Name of city",
                }
            },
            "required": ["city_name"],
        },
    },
]

available_functions = {
    "get_stock_price": get_stock_price,
    "get_dividend_date": get_dividend_date,
    "get_tomorrow_weather": get_tomorrow_weather,
}

# Configure the client and tools
client = genai.Client(api_key=api_key)
gemini_tools = types.Tool(function_declarations=tools)
config = types.GenerateContentConfig(tools=[gemini_tools])

# Function to process messages and handle function calls
def get_completion_from_messages(messages, model="gpt-4o"):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=messages,
        config=config,
    )

    print("--- Full response: ---")
    print(response)

    response_message = response.text

    print("First response:", response_message)

    if response.candidates[0].content.parts[0].function_call:
        # Find the tool call content
        tool_call = response.candidates[0].content.parts[0].function_call

        # Extract tool name and arguments
        function_name = tool_call.name
        function_args = tool_call.args 
        tool_id = tool_call.id
        
        # Call the function
        function_to_call = available_functions[function_name]
        function_response = function_to_call(**function_args)

        print(function_response)

        messages.append(response.candidates[0].content)

        tool_response = types.Part.from_function_response(
            name=function_name,
            response={
                "result": function_response
            }
            
        )

        messages.append(types.Content(role="tool", parts=[tool_response]))

        # Second call to get final response based on function output
        second_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=config,
        )
        final_answer = second_response.text

        print("Second response:", final_answer)
        return final_answer

    return "No relevant function call found."

# Example usage
prompt = types.Part.from_text(text="Jake bude zitra pocasi v Hradci Kralove?")

messages = [types.Content(
    role="user", 
    parts=[prompt]
    )
    ]

response = get_completion_from_messages(messages)
print("--- Full response: ---")
pprint(response)
