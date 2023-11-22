import datetime
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
  "departureDate": "2023-12-09", //must be in format: YYYY-MM-DD
  "returnDate": "2023-12-15", //must be in format: YYYY-MM-DD
  "adults": 1,
  "nonStop": "false", //options to choose from: ["true", "false"] set to true, ONLY if person requested for flight to go from the origin to the destination with no stop in between
  "children": 0,
  "infants": 0,
  "travelClass": "ECONOMY" // options to choose from: ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]
}\n\n
"""
    user_msg += "Change json parameter values according to the email which I will give you. If year is not specified, use 2023. Location codes must be 3-letter IATA codes. You can change parameter values but you cant add new parameters. Remove all parameters that are empty or have value 0 or are not mentioned in email.\n\nEmail to extract details from:\n"
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
        #print(response.choices[0].message.content)
        flightOffers = json.loads(response.choices[0].message.content)

        year_from_string = int(flightOffers["departureDate"][:4])
        date_from_string = datetime.datetime.strptime(flightOffers["departureDate"], "%Y-%m-%d")
        current_date = datetime.datetime.now()
        if date_from_string < current_date:
            flightOffers["departureDate"] = str(year_from_string+1) + flightOffers["departureDate"][4:]

        year_from_string = int(flightOffers["returnDate"][:4])
        date_from_string = datetime.datetime.strptime(flightOffers["returnDate"], "%Y-%m-%d")
        current_date = datetime.datetime.now()
        if date_from_string < current_date:
            flightOffers["returnDate"] = str(year_from_string+1) + flightOffers["returnDate"][4:]

        flightOffers["max"] = offerCount
        if "nonStop" in flightOffers and flightOffers["nonStop"] == "false":
            flightOffers.pop("nonStop")
        if "children" in flightOffers and flightOffers["children"] == 0:
            flightOffers.pop("children")
        if "infants" in flightOffers and flightOffers["infants"] == 0:
            flightOffers.pop("infants")
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
        print(response.json())
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

    if len(flightOffers) <= 0:
        return None
    
    cheapestFlightOffers = []

    #check which offers qualify
    for flightOffer in flightOffers:
        if flightOffer["numberOfBookableSeats"] >= search_params["adults"]:
            cheapestFlightOffers.append(flightOffer)

    cheapestFlightOffers = sorted(cheapestFlightOffers, key=lambda x: float(x["price"]["grandTotal"]))[:min(len(cheapestFlightOffers)-1, 6)]
    price_offers = get_price_offer(access_token, cheapestFlightOffers)["data"]["flightOffers"]
    cheapestPriceOffers = sorted(price_offers, key=lambda x: float(x["price"]["grandTotal"]))
    #print(cheapestPriceOffers)
    
    flights = []
    for iterary in cheapestPriceOffers[0]["itineraries"]:
        for segment in iterary["segments"]:
            flights.append({"departure": segment["departure"], "arrival": segment["arrival"], "duration": segment["duration"], "flightNumber": segment["number"], "carrierCode": segment["carrierCode"]})

    return {"price": {"grandTotal": cheapestPriceOffers[0]["price"]["grandTotal"], "billingCurrency": cheapestPriceOffers[0]["price"]["billingCurrency"]}, "flights": flights}