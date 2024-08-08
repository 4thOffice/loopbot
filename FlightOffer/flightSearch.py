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
    
def getFlightOffer(structuredFlightDetails, automatic_order, ama_Client_Ref, verbose_checkpoint=None):
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
    
    if apiType == "personal":
        access_token = get_access_token(enterprise=False)
    else:
        access_token = get_access_token()
    
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
    
    verbose(("initial flight offers length:", len(flightOffers)), verbose_checkpoint)
    verbose(("initial flight offers:\n", flightOffers), verbose_checkpoint)
    print("initial flight offers:\n", len(flightOffers))
    print(flightOffers)

    originalFlightOffers = list(flightOffers)
    for flightOffer in flightOffers:
        sameFlights = flightAuxiliary.getSameFlights(flightOffer, originalFlightOffers, returnSelf=True)
        if sameFlights:
            lowestPrice = sorted(sameFlights, key=lambda x: (float(x["price"]["grandTotal"])))[0]
            #remove everything but lowest price offer
            for flightOffer1 in flightOffers:
                if flightOffer1 in sameFlights and flightOffer1 != lowestPrice:
                    flightOffers.remove(flightOffer1)

    print("removed duplicates:\n", len(flightOffers), flightOffers)
    #if amadeus returned no flight offers
    if len(flightOffers) <= 0:
        print("no flights")
        verbose("no flights", verbose_checkpoint)
        return {"status": "ok", "data": None}


    if flightNumbersPerItinerary:
        flightOffersWithCorrectFlightNumbers = []
        numberOfFlightNumbers = 0
        for itineraryIndex in flightNumbersPerItinerary.keys():
            numberOfFlightNumbers += len(flightNumbersPerItinerary[itineraryIndex]["flightNumbers"])

        for flightOffer in flightOffers:
            numberOfFlightNumbersFound = 0
            for index, itinerary in enumerate(flightOffer['itineraries']):
                for segment in itinerary["segments"]:
                    if index in flightNumbersPerItinerary:
                        for flightNumber in flightNumbersPerItinerary[index]["flightNumbers"]:
                            if flightNumber == segment["number"]:
                                numberOfFlightNumbersFound += 1

            if numberOfFlightNumbers == numberOfFlightNumbersFound:
                flightOffersWithCorrectFlightNumbers.append(flightOffer)

        verbose(f"Flight offers with correct flight numbers: {flightOffersWithCorrectFlightNumbers}", verbose_checkpoint)
        print(f"Flight offers with correct flight numbers: {flightOffersWithCorrectFlightNumbers}")
        if len(flightOffersWithCorrectFlightNumbers) > 0:
            flightOffers = flightOffersWithCorrectFlightNumbers
        else:
            verbose("no flight offers satisfied all flight numbers.. using not optimal flights..", verbose_checkpoint)
            print("no flight offers satisfied all flight numbers.. using not optimal flights..")

    expanding = True
    iteration = 0
    while expanding:
        if iteration > 0:
            extraTimeframes, end = expandTimeframes(extraTimeframes)
            print(f"Expanded timeframes, iteration {iteration}: {extraTimeframes}")
            verbose(f"Expanded timeframes, iteration {iteration}", verbose_checkpoint)
            if end:
                expanding = False

        cheapestFlightOffers = []
        #check which offers qualify
        for flightOffer in flightOffers:
            timeframesSatisfied = True
            for index, itinerary in enumerate(flightOffer['itineraries']):
                departure_time = itinerary['segments'][0]['departure']['at']
                arrival_time = itinerary['segments'][-1]['arrival']['at']

                departure_time = datetime.datetime.fromisoformat(departure_time).time()
                arrival_time = datetime.datetime.fromisoformat(arrival_time).time()

                if "earliestDepartureTime" in extraTimeframes[index] and extraTimeframes[index]["earliestDepartureTime"] != "":
                    if departure_time < datetime.datetime.strptime(extraTimeframes[index]["earliestDepartureTime"], '%H:%M:%S').time():
                        timeframesSatisfied = False
                        break
                if "latestDepartureTime" in extraTimeframes[index] and extraTimeframes[index]["latestDepartureTime"] != "":
                    if departure_time > datetime.datetime.strptime(extraTimeframes[index]["latestDepartureTime"], '%H:%M:%S').time():
                        timeframesSatisfied = False
                        break
                if "earliestArrivalTime" in extraTimeframes[index] and extraTimeframes[index]["earliestArrivalTime"] != "":
                    if arrival_time < datetime.datetime.strptime(extraTimeframes[index]["earliestArrivalTime"], '%H:%M:%S').time():
                        timeframesSatisfied = False
                        break
                if "latestArrivalTime" in extraTimeframes[index] and extraTimeframes[index]["latestArrivalTime"] != "":
                    if arrival_time > datetime.datetime.strptime(extraTimeframes[index]["latestArrivalTime"], '%H:%M:%S').time():
                        timeframesSatisfied = False
                        break

            if timeframesSatisfied:
                cheapestFlightOffers.append(flightOffer)
                print("satisfied all timeframes")

        if len(cheapestFlightOffers) <= 0:
            cheapestFlightOffers = flightOffers
            print("no flight offers satisfied all timeframes..")
            verbose("no flight offers satisfied all timeframes..", verbose_checkpoint)
        else:
            print(f"Flights that satisfied timeframes:\n{cheapestFlightOffers}")
            verbose(f"Flights that satisfied timeframes:\n{cheapestFlightOffers}", verbose_checkpoint)
            expanding = False

        iteration += 1

    flightOffers = cheapestFlightOffers

    bestFlightOffersPerStopNumber = []
    for numberOfStops in range(0, 3):
        print(f"Looking at flight offers - number of stops: {numberOfStops}")
        verbose(f"Looking at flight offers - number of stops: {numberOfStops}", verbose_checkpoint)
        toAppend = {"numberOfStops": numberOfStops, "offers": []}

        cheapestFlightOffers = []
        if numberOfStops <= 2:
            for flightOffer in flightOffers:
                if not flightAuxiliary.check_number_of_stops(flightOffer["itineraries"], numberOfStops):
                    print("satisfies number of stops")
                    cheapestFlightOffers.append(flightOffer)

        if len(cheapestFlightOffers) <= 0:
            print(f"no flight offers satisfied all stop number conditions - number of stops: {numberOfStops}")
            verbose(f"no flight offers satisfied all stop number conditions - number of stops: {numberOfStops}", verbose_checkpoint)
            bestFlightOffersPerStopNumber.append(toAppend)
            continue

        print(f"cheapestFlightOffers with {numberOfStops} number of stops: {len(cheapestFlightOffers)}")
        verbose(f"cheapestFlightOffers with {numberOfStops} number of stops: {len(cheapestFlightOffers)}", verbose_checkpoint)
        
        cheapestFlightOffers = flightAuxiliary.get_time_difference_data(cheapestFlightOffers, extraTimeframes)
        cheapestFlightOffers = sorted(cheapestFlightOffers, key=lambda x: (x["time_difference"], float(x["offer"]["price"]["total"])))
        cheapestFlightOffers = [offer["offer"] for offer in cheapestFlightOffers][:6]

        print("length 1:", len(cheapestFlightOffers))
        print("get price offers for:\n", cheapestFlightOffers)
        verbose(f"get price offers for:\n{cheapestFlightOffers}", verbose_checkpoint)

        price_offers = []
        for offer in cheapestFlightOffers:
            try:
                price_offer = get_price_offer(access_token, ama_Client_Ref, [offer])["data"]["flightOffers"][0]
                price_offers.append(price_offer)
            except:
                continue
        
        cheapestPriceOffers = flightAuxiliary.get_time_difference_data(price_offers, extraTimeframes)
        cheapestPriceOffers = sorted(cheapestPriceOffers, key=lambda x: (x["time_difference"], float(x["offer"]["price"]["grandTotal"])))
        cheapestPriceOffers = [offer["offer"] for offer in cheapestPriceOffers]
        cheapestPriceOffers = cheapestPriceOffers[:3]
        toAppend["offers"] = cheapestPriceOffers
        if numberOfStops == 3:
            toAppend["numberOfStops"] = "unlimited"
        bestFlightOffersPerStopNumber.append(toAppend)
    
    #print("-----------")
    #print(bestFlightOffersPerStopNumber)
    #print("-----------")

    print(f"best offers per number of stops:\n{bestFlightOffersPerStopNumber}")
    verbose(f"best offers per number of stops:\n{bestFlightOffersPerStopNumber}", verbose_checkpoint)
    cheapestPriceOffers = []
    for numberOfStops, offers in enumerate(bestFlightOffersPerStopNumber):
        offersList = offers["offers"]
        if numberOfStops == 0:
            if len(offersList) > 0:
                print("added offers from flights with number of stops: 0")
                verbose("added offers from flights with number of stops: 0", verbose_checkpoint)
                for i in range(0, min(2, len(offersList))):
                    cheapestPriceOffers.append(offersList[i])
        elif (3-len(cheapestPriceOffers)) > 0 and len(offersList) > 0:
                print(f"added offers from flights with number of stops: {numberOfStops}")
                verbose(f"added offers from flights with number of stops: {numberOfStops}", verbose_checkpoint)
                for i in range(min(len(offersList), 3-len(cheapestPriceOffers))):
                    cheapestPriceOffers.append(offersList[i])

    cheapestPriceOffers = flightAuxiliary.get_time_difference_data(cheapestPriceOffers, extraTimeframes)
    cheapestPriceOffers = sorted(cheapestPriceOffers, key=lambda x: (x["time_difference"]))
    print("----------------")
    print([offer["time_difference"] for offer in cheapestPriceOffers])
    print("----------------")
    all_zero = all(offer["time_difference"] == 0 for offer in cheapestPriceOffers)
    cheapestPriceOffers = [offer["offer"] for offer in cheapestPriceOffers]
    if all_zero:
        offersBySegment = []
        for offer_ in cheapestPriceOffers:
            all_segments = []
            for itinerary in offer_.get("itineraries", []):
                all_segments.extend(itinerary.get("segments", []))
            total_segments = len(all_segments)
            toAppend = {"offer": offer_, "numberOfSegments": total_segments}
            offersBySegment.append(toAppend)

        cheapestPriceOffers = sorted(offersBySegment, key=lambda x: float(x["numberOfSegments"]))
        cheapestPriceOffers = [offer["offer"] for offer in cheapestPriceOffers]
    print(f"final offers:\n{cheapestPriceOffers}")
    
    #######################
    for index, offer in enumerate(cheapestPriceOffers):
        fares = upsellHandler.getUpsellOffer(offer, get_price_offer, travelClass, access_token, apiType, ama_Client_Ref, verbose_checkpoint)
        
        sameFlights = flightAuxiliary.getSameFlights(offer, originalFlightOffers)
        print("offer to search same flights for:\n", offer)
        print("same flights:\n", sameFlights)
        if sameFlights:
            for sameFlight in [sameFlights[0]]:
                fares += upsellHandler.getUpsellOffer(sameFlight, get_price_offer, travelClass, access_token, apiType, ama_Client_Ref, verbose_checkpoint)
        
        if len(fares) > 1:
            if not fares[0]["amenities"] and not fares[1]["amenities"]:
                fares.pop(1)

        cheapestPriceOffers[index] = fares

    #just_offers = offerBagHandler.addBags(just_offers, checkedBags, get_price_offer, access_token, ama_Client_Ref, verbose_checkpoint)

    print(f"final offers with amenities:\n{cheapestPriceOffers}")
    verbose(f"final offers with amenities:\n{cheapestPriceOffers}", verbose_checkpoint)

    #create orders
    order_reference = None
    if len(people) > 0 and automatic_order:
        verbose("CREATING ORDER..", verbose_checkpoint)
        print("CREATING ORDER..")
        try:
            order_reference = create_order(cheapestPriceOffers, people, ama_Client_Ref, access_token, verbose_checkpoint)
        except:
            verbose("FAILED CREATING ORDER", verbose_checkpoint)
            print("FAILED CREATING ORDER")

    returnData = {"status": "ok", "data": {"offers": [], "people": people}}
    for index, cheapest_price_offer in enumerate(cheapestPriceOffers):
        geoCode, cityCode, airportName = get_airport_coordinates(access_token, cheapest_price_offer[0]["fare"]["itineraries"][0]["segments"][-1]["arrival"]["iataCode"])
        
        flights = []
        for iteraryIndex, iterary in enumerate(cheapest_price_offer[0]["fare"]["itineraries"]):
            for segment in iterary["segments"]:
                fareBasis = ""
                for detailsBySegment in cheapest_price_offer[0]["fare"]["travelerPricings"][0]["fareDetailsBySegment"]:
                    if detailsBySegment["segmentId"] == segment["id"]:
                        if "fareBasis" in detailsBySegment:
                            fareBasis = detailsBySegment["fareBasis"][0]
                            
                        print("detailsBySegment", detailsBySegment)
                        if "cabin" in detailsBySegment:
                            travelClass = detailsBySegment["cabin"]
                        else:
                            travelClass = "ECONOMY"
                        break
                
                if "duration" in segment:
                    duration = segment["duration"]
                else:
                    duration = flightAuxiliary.getDuration(segment["departure"]["at"], segment["arrival"]["at"])
                flights.append({"departure": segment["departure"], "arrival": segment["arrival"], "duration": duration, "flightNumber": (fareBasis + segment["number"]), "carrierCode": segment["carrierCode"], "iteraryNumber": iteraryIndex, "travelClass": travelClass})
        
        fares = []
        for fareOffer in cheapest_price_offer:
            fare = {}
            fare["amenities"] = fareOffer["amenities"]
            fare["price"] = {"grandTotal": str(round(float(fareOffer["fare"]["price"]["grandTotal"]), 2)), "billingCurrency": fareOffer["fare"]["price"]["currency"]}

            includedBags = 0
            if "includedCheckedBags" in fareOffer["fare"]["travelerPricings"][0]["fareDetailsBySegment"][0]:
                if "quantity" in fareOffer["fare"]["travelerPricings"][0]["fareDetailsBySegment"][0]["includedCheckedBags"]:
                    includedBags = fareOffer["fare"]["travelerPricings"][0]["fareDetailsBySegment"][0]["includedCheckedBags"]["quantity"]
                elif "weight" in fareOffer["fare"]["travelerPricings"][0]["fareDetailsBySegment"][0]["includedCheckedBags"]:
                    includedBags = 1
            else:
                includedBags = 0

            fare["checkedBags"] = includedBags
            fares.append(fare)
            
        if index > 0:
            order_reference = None
            
        returnData["data"]["offers"].append({"passengers": len(cheapest_price_offer[0]["fare"]["travelerPricings"]), "fares": fares, "flights": flights, "geoCode": geoCode, "airportName": airportName, "cityCode": cityCode, "order_reference": order_reference})
        
    return returnData