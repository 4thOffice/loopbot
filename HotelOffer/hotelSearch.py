import sys
import requests
import os
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))

sys.path.append("../")
import keys
from Auxiliary.verbose_checkpoint import verbose
from amadeus import Client, ResponseError
import googleAPI

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

def getHotelList(access_token, latitude, longitude, radius):
    url = 'https://api.amadeus.com/v1/reference-data/locations/hotels/by-geocode'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
        "radiusUnit": "KM",
        "ratings": 4,
        "hotelSource": "ALL"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        print('Hotel list information retrieved successfully!')

        hotelIDs = []
        hotelList = response.json()["data"]
        for hotel in hotelList:
            hotelIDs.append(hotel["hotelId"])

        return hotelIDs  # Return the JSON response
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None
    
def getOfferPrice(access_token, offerID):
    url = 'https://api.amadeus.com/v3/shopping/hotel-offers/' + offerID
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print('Hotel offer price information retrieved successfully!')
        return response.json()
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None
    
def getHotelOffers(access_token, hotelIDs, checkInDate, checkOutDate, adults, currency):
    #https://test.api.amadeus.com/v3/shopping/hotel-offers?hotelIds=YXPARVVH,UIPARWTH,FGPARIFE&adults=1&checkInDate=2024-11-22&checkOutDate=2024-11-28&roomQuantity=1&paymentPolicy=NONE&includeClosed=false&bestRateOnly=true
    url = 'https://api.amadeus.com/v3/shopping/hotel-offers'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }
    print("currency", currency)
    hotelIDs_ = ""
    for hotelID in hotelIDs:
        hotelIDs_ += hotelID + ","
    
    hotelIDs_ = hotelIDs_[:-1]
    print(hotelIDs_)
    params = {
        "hotelIds": hotelIDs_,
        "adults": adults,
        "checkInDate": checkInDate,
        "checkOutDate": checkOutDate,
        "roomQuantity": 1,
        "currency": "EUR",
        "paymentPolicy": "NONE",
        "includeClosed": "false",
        "bestRateOnly": "true"
    }

    print(params)

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        print('Hotel offer list information retrieved successfully!')
        return response.json()["data"]  # Return the JSON response
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None

def getHotelOffer(hotelDetails, verbose_checkpoint=None):
    access_token = get_access_token()

    radius = 5
    hotelOffers = []
    for i in range(5):
        hotelsIDs = getHotelList(access_token, hotelDetails["latitude"], hotelDetails["longitude"], radius)
        #print(hotelsIDs)

        if not hotelsIDs:
            print("No hotels found, increasing search radius..")
            radius += 10
            continue

        hotelOffers = getHotelOffers(access_token, hotelsIDs, hotelDetails["checkInDate"], hotelDetails["checkOutDate"], hotelDetails["adults"], hotelDetails["currency"])

        print(f"Hotel offers found: {len(hotelOffers)}")

        if len(hotelOffers) > 0:
            break
            
        print("No hotel offers found, increasing search radius..")
        radius += 10
    

    if len(hotelOffers) <= 0:
        return {"price": 0, "currency": "", "checkInDate": "", "checkOutDate": "", "hotelName": ""}
    
    for i in range(min(5, len(hotelOffers))):
        try:
            chosenOffer = None
            for offer in hotelOffers:
                for specificOffer in offer['offers']:
                    if chosenOffer == None:
                        chosenOffer = specificOffer
                    elif chosenOffer["price"]["total"] > specificOffer["price"]["total"]:
                        chosenOffer = specificOffer

            offerPrice = getOfferPrice(access_token, chosenOffer["id"])["data"]
            hotelOffers.remove(chosenOffer)
            i = 5
            break
        except Exception:
            continue

    print(f"Offer price:\n {offerPrice}")

    currency = offerPrice["offers"][0]["price"]["currency"]
    total = offerPrice["offers"][0]["price"]["total"]
    checkInDate = offerPrice["offers"][0]["checkInDate"]
    checkOutDate = offerPrice["offers"][0]["checkOutDate"]
    hotelName = offerPrice["hotel"]["name"]

    convert_factor = get_latest_currency_rates(currency, hotelDetails["currency"])
    print(convert_factor)
    if convert_factor != None:
        total = convert_factor * float(total)
        total = round(total, 2)
        currency = hotelDetails["currency"]

    googlePlaceID = googleAPI.get_place_id(hotelDetails["latitude"], hotelDetails["longitude"], radius, hotelName)

    photosReferenceID = googleAPI.place_details(googlePlaceID)[:3]

    return {"price": total, "currency": currency, "checkInDate": checkInDate, "checkOutDate": checkOutDate, "hotelName": hotelName, "googlePlaceID": googlePlaceID, "photosReferenceID": photosReferenceID}

#getHotelOffer({"latitude": 49.01278, "longitude": 2.55, "checkInDate": "2024-09-06", "checkOutDate": "2024-09-13"})