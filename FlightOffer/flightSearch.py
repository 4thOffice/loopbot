import json
import sys
import openai
import requests
sys.path.append("../")
import keys
from amadeus import Client, ResponseError

def extractSearchParameters(emailText, offerCount):
    user_msg = "I want you to extract flight details and replace values in this parameter json:\n"
    user_msg += """{
  "currencyCode": "EUR",
  "originLocationCode": "LJU",
  "destinationLocationCode": "PAR",
  "departureDate": "2024-06-09",
  "returnDate": "2024-06-15",
  "adults": 2
}\n\n
"""
    user_msg += "You can change parameter values but you cant add new parameters. Remove all parameters that are empty or have value 0 or are not mentioned in email.\n\nEmail to extract details from:\n"
    user_msg += emailText
    user_msg += "\n\nOutput should be ONLY json and NO other text!"

    openai.api_key = keys.openAI_APIKEY
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": user_msg}
        ]
    )

    if response.choices:
        flightOffers = json.loads(response.choices[0].message.content)
        flightOffers["max"] = offerCount
        return flightOffers
    else:
        print("Unexpected or empty response received.")

amadeus = Client(
    client_id=keys.client_id,
    client_secret=keys.client_secret
)

def get_access_token(api_key=keys.client_id, api_secret=keys.client_secret):
    auth_url = 'https://test.api.amadeus.com/v1/security/oauth2/token'
    response = requests.post(auth_url, data={
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': api_secret
    })
    return response.json().get('access_token')

endpoint = 'https://test.api.amadeus.com/v2/shopping/flight-offers'

def get_price_offer(access_token, flight_details):
    url = 'https://test.api.amadeus.com/v1/shopping/flight-offers/pricing'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }
    payload = {
        'data': {
            'type': 'flight-offers-pricing',
            'flightOffers': flight_details
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print('Flight Offers Pricing information retrieved successfully!')
        return response.json()  # Return the JSON response
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None
    
def get_flight_offers(access_token, search_params):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }
    try:
        response = requests.get(endpoint, headers=headers, params=search_params)
        return response.json()
    except ResponseError as error:
        print(error)
        return response.json()
    
def getFlightOffer(flightDetails):
    search_params = extractSearchParameters(flightDetails, 10)
    print(search_params)
    access_token = get_access_token()
    flightOffers = get_flight_offers(access_token, search_params)["data"]
    #print(flightOffers)

    cheapestFlightOffers = []

    #check which offers qualify
    for flightOffer in flightOffers:
        if flightOffer["numberOfBookableSeats"] >= search_params["adults"]:
            cheapestFlightOffers.append(flightOffer)

    cheapestFlightOffers = sorted(cheapestFlightOffers, key=lambda x: float(x["price"]["grandTotal"]))[:min(len(cheapestFlightOffers)-1, 6)]
    price_offers = get_price_offer(access_token, cheapestFlightOffers)["data"]["flightOffers"]
    cheapestPriceOffers = sorted(price_offers, key=lambda x: float(x["price"]["grandTotal"]))
    print(cheapestPriceOffers)

    return {"price": cheapestPriceOffers[0]["price"]["grandTotal"], "itineraries": cheapestPriceOffers[0]["itineraries"]}