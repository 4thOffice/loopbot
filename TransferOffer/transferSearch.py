import json
import sys
import requests
import os
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))

sys.path.append("../HotelOffer")
sys.path.append("../")
import keys
from Auxiliary.verbose_checkpoint import verbose
from amadeus import Client, ResponseError
import HotelOffer.googleAPI

amadeus = Client(
    client_id=keys.amadeus_client_id,
    client_secret=keys.amadeus_client_secret,
    hostname='production'
)

def convert_currency(baseCurrency, currency, api_key=keys.fixer_APIKEY):
    base_url = 'http://data.fixer.io/api/latest'

    print(api_key)
    params = {
        'access_key': api_key,
        'base': baseCurrency,
        'symbols': currency
    }

    response = requests.get(base_url, params=params)

    # Checking if the request was successful (status code 200)
    if response.status_code == 200:
        # Getting the converted amount from the response JSON
        data = response.json()
        if data["success"] == False:
            print(data)
            print("Failed to fetch conversion data")
            return None
        print(f"Converted {baseCurrency} to {currency}")
        return data["rates"][currency]
    else:
        print("Failed to fetch conversion data. Status code:", response.status_code)
        return None


def get_access_token(api_key=keys.amadeus_client_id, api_secret=keys.amadeus_client_secret):
    auth_url = 'https://api.amadeus.com/v1/security/oauth2/token'
    response = requests.post(auth_url, data={
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': api_secret
    })
    print("Access key:\n", response.json())
    return response.json().get('access_token')

def getTransferOffers(access_token, LocationCode, startGooglePlaceId, endGooglePlaceId, passengers, startDateTime):
    url = 'https://api.amadeus.com/v1/shopping/transfer-offers'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }

    params = {
        "startLocationCode": LocationCode,
        "startGooglePlaceId": startGooglePlaceId,
        "endLocationCode": LocationCode,
        "endGooglePlaceId": endGooglePlaceId,
        #"transferType": "TAXI",
        "startDateTime": startDateTime,
        "passengers": passengers
    }
    print(headers)
    print(params)

    response = requests.post(url, headers=headers, data=json.dumps(params))
    if response.status_code == 200:
        print('Transfer offers information retrieved successfully!')

        return response.json()["data"]  # Return the JSON response
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None

def getTransferOffer(startGooglePlaceId, endGooglePlaceId, LocationCode, passengers, startDatetime, currency, verbose_checkpoint=None):
    access_token = get_access_token()

    transferOffers = getTransferOffers(access_token, LocationCode, startGooglePlaceId, endGooglePlaceId, passengers, startDatetime)
    #print(transferOffers)

    sortedTransferOffers = sorted(transferOffers, key=lambda x: float(x['quotation']['monetaryAmount']))

    print(sortedTransferOffers[0])
    chosenOffer = sortedTransferOffers[0]

    price = chosenOffer["quotation"]["monetaryAmount"]
    baseCurrency = chosenOffer["quotation"]["currencyCode"]

    if currency != baseCurrency:
        converion_rate = convert_currency(baseCurrency, currency)
    else:
        converion_rate = None
    print(converion_rate)
    if converion_rate != None:
        converted_price = round(float(price) * float(converion_rate), 2)
        baseCurrency = currency
        price = converted_price

    return {"carType": chosenOffer["vehicle"]["description"], "startTime": chosenOffer["start"]["dateTime"], "price": price, "currency": baseCurrency}
    #return {"price": total, "currency": currency, "checkInDate": checkInDate, "checkOutDate": checkOutDate, "hotelName": hotelName, "googlePlaceID": googlePlaceID}

#transferOffer = getTransferOffer("ChIJZwkilQJfpkcRRfEptBP_Lik", "ChIJub76MURjpkcREZePvIreCrA", "LEJ", 1, "2024-01-17T13:30:00")
#print(transferOffer)