import datetime
import json
import math
import sys
import time
import traceback
import openai
import requests
import os
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import keys
from Auxiliary.verbose_checkpoint import verbose
from Auxiliary.generateErrorID import generate_error_id
from amadeus import Client, ResponseError
import getParametersJson
import offerBagHandler
import upsellHandler
import flightAuxiliary
from miniRulesInfo import getMiniRulesInfo, convertMiniRulesAmenities
from timeframeExpander import expandTimeframes
from FlightOffer.offersFetcherAmadeus import fetchOffers
from createOrder import create_order
import copy
import travelModels

apiType = "enterprise" #personal/enterprise

if apiType == "personal":
    hostname = "production"
else:
    hostname = "test"

amadeus = Client(
    client_id=keys.amadeus_client_id,
    client_secret=keys.amadeus_client_secret,
    hostname=hostname
)

def get_access_token(api_key=keys.amadeus_client_id, api_secret=keys.amadeus_client_secret, enterprise=True):
    if enterprise:
        auth_url = 'https://travel.api.amadeus.com/v1/security/oauth2/token'
    else:
        api_key=keys.amadeus_client_id_personal
        api_secret=keys.amadeus_client_secret_personal
        auth_url = 'https://api.amadeus.com/v1/security/oauth2/token'
        
    response = requests.post(auth_url, data={
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': api_secret
    })
    print("Access key:\n", response.json())
    return response.json().get('access_token')

def get_price_offer(access_token, ama_Client_Ref, flight_offers):
    if apiType == "personal":
        url = 'https://api.amadeus.com/v1/shopping/flight-offers/pricing'
    else:
        url = 'https://travel.api.amadeus.com/v1/shopping/flight-offers/pricing'
        
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json',
        'ama-Client-Ref': ama_Client_Ref
    }
    payload = {
        'data': {
            'type': 'flight-offers-pricing',
            'flightOffers': flight_offers,
            'ama-Client-Ref': ama_Client_Ref
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print('Flight Offers price information retrieved successfully!')
        return response.json()  # Return the JSON response
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None
    
def get_airport_coordinates(access_token, IATA):
    print(f"IATA {IATA}")
    access_token = get_access_token(keys.amadeus_client_id_personal, keys.amadeus_client_secret_personal, enterprise=False)
    url = 'https://api.amadeus.com/v1/reference-data/locations/A' + IATA
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print('Airport information retrieved successfully!')

        res = response.json()
        geoCode = res["data"]["geoCode"]
        cityCode = res["data"]["address"]["cityCode"]
        airportName = res["data"]["name"]

        return geoCode, cityCode, airportName
    else:
        print(f'Failed to retrieve airport information: {response.status_code} - {response.text}')
        return None

if apiType == "personal":
    access_token = get_access_token(enterprise=False)
else:
    access_token = get_access_token()    

def getFlightOffer(structuredFlightDetails, automatic_order, ama_Client_Ref, verbose_checkpoint):
    search_params = structuredFlightDetails["search_params"]
    extraTimeframes = structuredFlightDetails["extraTimeframes"]
    checkedBags = structuredFlightDetails["checkedbags"]
    refundableTicket = structuredFlightDetails["refundableTicket"]
    changeableTicket = structuredFlightDetails["changeableTicket"]
    flightNumbersPerItinerary = structuredFlightDetails["flightNumbersPerItinerary"]
    people = structuredFlightDetails["people"]

    travelClass = search_params["searchCriteria"]["flightFilters"]["cabinRestrictions"][0]["cabin"]

    print(f"Search parameters: {search_params}")
    verbose(f"Search parameters: {search_params}", verbose_checkpoint)

    print(f"Extra timeframes: {extraTimeframes}")
    verbose(f"Extra timeframes: {extraTimeframes}", verbose_checkpoint)

    
    flightOffers = []
    index = 0
    for source in ["GDS", "NDC", "EAC", "LTC", "PYTON"]:
        search_params["sources"] = [source]
        try:
            print("Looking for flight offers in:", source)
            fetchedOffers = fetchOffers(copy.deepcopy(search_params), extraTimeframes, checkedBags, refundableTicket, changeableTicket, travelClass, flightNumbersPerItinerary, access_token, ama_Client_Ref, apiType, verbose_checkpoint=verbose_checkpoint)
            print("flight offers length: ", len(fetchedOffers))
            verbose(("flight offers length: ", len(fetchedOffers)), verbose_checkpoint)
            flightOffers += fetchedOffers
        except Exception as e:
            traceback_msg = traceback.format_exc()
            error_id = generate_error_id()
            print(f"Error ID: {error_id}")
            print(traceback_msg)
            verbose(f"Error ID: {error_id}", verbose_checkpoint)
            verbose(traceback_msg, verbose_checkpoint)
            time.sleep(0.5)
            return {"status": "error", "data": ("Error ID: " + error_id)}
    
    verbose(("\n\ninitial flight offers length:", len(flightOffers)), verbose_checkpoint)
    verbose(("initial flight offers:\n", flightOffers), verbose_checkpoint)
    print("initial flight offers:\n", len(flightOffers))
    
    originalFlightOffers = list(flightOffers)
    for flightOffer in flightOffers:
        sameFlights = flightAuxiliary.getSameFlights(flightOffer, originalFlightOffers, returnSelf=True)
        if sameFlights:
            lowestPrice = sorted(sameFlights, key=lambda x: (float(x["price"]["grandTotal"])))[0]
            #remove everything but lowest price offer
            for flightOffer1 in flightOffers:
                if flightOffer1 in sameFlights and flightOffer1 != lowestPrice:
                    flightOffers.remove(flightOffer1)
                    
    print("removed duplicates:\n", len(flightOffers), flightOffers, '\n\n')
    
    return crateObjectOffers(flightOffers)

def crateObjectOffers(flightOffers):
    
    airport_cache = {}
    offerList = []
    for index, flightOffer in enumerate(flightOffers):

        aitacodeDestination = flightOffer['itineraries'][0]["segments"][-1]["arrival"]["iataCode"]
        
        if aitacodeDestination in airport_cache:
            
            geoCode, cityCode, airportName = airport_cache[aitacodeDestination]
        else:
            geoCode, cityCode, airportName = get_airport_coordinates(access_token, aitacodeDestination)
            airport_cache[aitacodeDestination] = (geoCode, cityCode, airportName)
            
        flight_offer = travelModels.FlightOffer(
            geoCode=travelModels.GeoCode(geoCode=geoCode),
            airportName=travelModels.AirportName(airportName=airportName),
            cityCode=travelModels.CityCode(cityCode=cityCode),
        )
        flight_offer.api = 'amadeus'
        
        offerList.append(flight_offer)
        
    return offerList