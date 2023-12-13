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

def get_latest_currency_rates(baseCurrency, currency, api_key=keys.currencyFreaks_APIKEY):
    base_url = "https://api.currencyfreaks.com/v2.0/rates/latest"
    params = {
        'base': baseCurrency,
        'symbols': 'EUR',
        'apikey': api_key
    }

    response = requests.get(base_url, params=params)

    print(currency)
    print(baseCurrency)
    if response.status_code == 200:
        data = response.json()
        date = data['date']
        base_currency = data['base']
        rates = data['rates']
        
        return float(rates[currency])
    else:
        print("Failed to fetch data from the API.")
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

def getTransferOffer(startGooglePlaceId, endGooglePlaceId, LocationCode, passengers, startDatetime, verbose_checkpoint=None):
    access_token = get_access_token()

    transferOffers = getTransferOffers(access_token, LocationCode, startGooglePlaceId, endGooglePlaceId, passengers, startDatetime)
    #print(transferOffers)

    sortedTransferOffers = sorted(transferOffers, key=lambda x: float(x['quotation']['monetaryAmount']))

    print(sortedTransferOffers[0])
    chosenOffer = sortedTransferOffers[0]

    return {"carType": chosenOffer["vehicle"]["description"], "startTime": chosenOffer["start"]["dateTime"], "price": chosenOffer["quotation"]["monetaryAmount"], "currency": chosenOffer["quotation"]["currencyCode"]}
    #return {"price": total, "currency": currency, "checkInDate": checkInDate, "checkOutDate": checkOutDate, "hotelName": hotelName, "googlePlaceID": googlePlaceID}

#transferOffer = getTransferOffer("ChIJZwkilQJfpkcRRfEptBP_Lik", "ChIJub76MURjpkcREZePvIreCrA", "LEJ", 1, "2024-01-17T13:30:00")
#print(transferOffer)