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
from timeframeExpander import expandTimeframes

apiType = "personal" #personal/enterprise

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
        auth_url = 'https://test.travel.api.amadeus.com/v1/security/oauth2/token'
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
        url = 'https://test.travel.api.amadeus.com/v1/shopping/flight-offers/pricing'
        
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
    
def get_flight_offers(access_token, search_params, ama_Client_Ref, verbose_checkpoint=None):
    if apiType == "personal":
        endpoint = 'https://api.amadeus.com/v2/shopping/flight-offers'
    else:
        endpoint = 'https://test.travel.api.amadeus.com/v2/shopping/flight-offers'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json',
        'ama-Client-Ref': ama_Client_Ref
    }
    try:
        response = requests.post(endpoint, headers=headers, data=json.dumps(search_params))
        #response = requests.get(endpoint, headers=headers, params=search_params)
        responseJson = response.json()
        if "errors" in responseJson:
            combined_detail = ""
            print(f"Error with fetching flight offers: {responseJson}")
            verbose(f"Error with fetching flight offers: {responseJson}", verbose_checkpoint)
            for error in responseJson["errors"]:
                if "detail" in error:
                    combined_detail += "\n" + error['detail']
                else:
                    combined_detail += "\nSYSTEM ERROR HAS OCCURRED"
            return {"status": "error", "details": combined_detail}
        else:
            print(responseJson)
            print("initial flight offers length: ", len(responseJson["data"]))
            verbose(f"initial flight offers:\n{responseJson}", verbose_checkpoint)
            verbose(("initial flight offers length: ", len(responseJson["data"])), verbose_checkpoint)
            return {"status": "ok", "details": responseJson}
    except ResponseError as error:
        print(error)
        verbose(f"Error getting flight offers {error}", verbose_checkpoint=verbose_checkpoint)
        return responseJson
    
def getFlightOffer(flightDetails, ama_Client_Ref, verbose_checkpoint=None):
    try:
        search_params, extraTimeframes, checkedBags, refundableTicket, changeableTicket, flightNumbersPerItinerary, people = getParametersJson.extractSearchParameters(flightDetails, 250, verbose_checkpoint)
    except Exception as e:
        traceback_msg = traceback.format_exc()
        error_id = generate_error_id()
        print(f"Exception {e=} while trying to extract search parameters into json. Error ID: {error_id} {flightDetails=}")
        print(traceback_msg) 
        verbose(f"Exception {e=} while trying to extract search parameters into json. Error ID: {error_id} {flightDetails=}", verbose_checkpoint)
        verbose(traceback_msg, verbose_checkpoint)
        return {"status": "error", "data": ("Error with calling amadeus API - Error ID: " + generate_error_id())}

    travelClass = search_params["searchCriteria"]["flightFilters"]["cabinRestrictions"][0]["cabin"]

    try:
        print(f"Search parameters: {search_params}")
        print(f"Extra timeframes: {extraTimeframes}")
        print(f"checked bags: {checkedBags}")
        print(f"refundable ticket: {refundableTicket}")
        print(f"changeable ticket: {changeableTicket}")
        print(f"Flight numbers per itinerary: {flightNumbersPerItinerary}")
        verbose(f"Flight numbers per itinerary: {flightNumbersPerItinerary}", verbose_checkpoint)
        verbose(f"refundable ticket: {refundableTicket}", verbose_checkpoint)
        verbose(f"changeable ticket: {changeableTicket}", verbose_checkpoint)
        verbose(f"Search parameters: {search_params}", verbose_checkpoint)
        verbose(f"Extra timeframes: {extraTimeframes}", verbose_checkpoint)
        verbose(f"Checked bags per person: {checkedBags}", verbose_checkpoint)
        
        if apiType == "personal":
            access_token = get_access_token(enterprise=False)
        else:
            access_token = get_access_token()

        #repeat this and expand time window untill amadeus returns at least 1 flight offer
        iteration = 0
        flightsFound = False
        while iteration < 4 and not flightsFound:
            flightOffers = get_flight_offers(access_token, search_params, ama_Client_Ref, verbose_checkpoint)
            if flightOffers["status"] == "error":
                print("Error with getting flights")
                verbose("Error with getting flights", verbose_checkpoint)
                return {"status": "error", "data": flightOffers["details"]}
            elif flightOffers["status"] == "ok":
                flightOffers = flightOffers["details"]["data"]
            time.sleep(0.5)

            if len(flightOffers) <= 0:
                print("No flights found.. expanding time window by 2 hours")
                verbose("No flights found.. expanding time window by 2 hours", verbose_checkpoint)
                if iteration == 0:
                    for originDestination in search_params['originDestinations']:
                        if "time" in originDestination["departureDateTimeRange"]:
                            del originDestination["originRadius"]
                            del originDestination["destinationRadius"]
                            originDestination["departureDateTimeRange"]["timeWindow"] = "4H"
                else:        
                    for originDestination in search_params['originDestinations']:
                        if "time" in originDestination["departureDateTimeRange"]:
                            current_time_window = originDestination['departureDateTimeRange']['timeWindow']
                            new_time_window = int(current_time_window[:-1]) + 2
                            new_time_window = f"{new_time_window}H"
                            originDestination['departureDateTimeRange']['timeWindow'] = new_time_window
                iteration += 1
            else:
                flightsFound = True

    except Exception as e:
        traceback_msg = traceback.format_exc()
        error_id = generate_error_id()
        print(f"Error ID: {error_id}")
        print(traceback_msg)
        verbose(f"Error ID: {error_id}", verbose_checkpoint)
        verbose(traceback_msg, verbose_checkpoint)
        time.sleep(0.5)
        return {"status": "error", "data": ("Error ID: " + error_id)}
    #print(flightOffers)

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

        print(f"Flight offers with correct flight numbers: {flightOffersWithCorrectFlightNumbers}")
        if len(flightOffersWithCorrectFlightNumbers) > 0:
            flightOffers = flightOffersWithCorrectFlightNumbers
        else:
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
            print("no flight offers satisfied all timeframes.. using not optimal flights..")
            verbose("no flight offers satisfied all timeframes.. using not optimal flights..", verbose_checkpoint)
        else:
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
        try:
            price_offers = get_price_offer(access_token, ama_Client_Ref, cheapestFlightOffers)["data"]["flightOffers"]
        except:
            return {"status": "error", "data": "Flight fully booked."}
        
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

    cheapestPriceOffers = upsellHandler.getUpsellOffers(cheapestPriceOffers, get_price_offer, travelClass, refundableTicket, changeableTicket, checkedBags, access_token, apiType, ama_Client_Ref, verbose_checkpoint)

    cheapestPriceOffers = flightAuxiliary.get_time_difference_data(cheapestPriceOffers, extraTimeframes)
    for i, x in enumerate(cheapestPriceOffers):
        amenityCount = 0
        refundFound = False
        changeFound = False
        for amenity_ in x["offer"]["amenities"]:
            if amenity_["included"] and amenity_["isRequested"]:
                if amenity_["amenity_description"] in ["REFUNDABLE TICKET", "REFUND BEFORE DEPARTURE", "REFUND AFTER DEPARTURE", "REFUNDS ANYTIME"]:
                    if not refundFound:
                        refundFound = True
                        amenityCount += 1
                elif amenity_["amenity_description"] in ["CHANGEABLE TICKET", "CHANGE BEFORE DEPARTURE", "CHANGE AFTER DEPARTURE"]:
                    if not changeFound:
                        changeFound = True
                        amenityCount += 1
                else:
                    amenityCount += 1

        #amenityCount = sum(value["included"] is True and value["isRequested"] is True for value in x["offer"]["amenities"])
        cheapestPriceOffers[i]["amenityCount"] = amenityCount
    
    print("-------------------------")
    print("SORTING BY AMENITIES")
    print(cheapestPriceOffers)
    print("-------------------------")
    cheapestPriceOffers = sorted(cheapestPriceOffers, key=lambda x: (-x["amenityCount"]))
    cheapestPriceOffers = [offer["offer"] for offer in cheapestPriceOffers]

    just_offers = [item["offer"] for item in cheapestPriceOffers]

    just_offers = offerBagHandler.addBags(just_offers, checkedBags, get_price_offer, access_token, ama_Client_Ref, verbose_checkpoint)

    for index, offer_ in enumerate(just_offers):
        cheapestPriceOffers[index] = {"offer": offer_, "amenities": cheapestPriceOffers[index]["amenities"]}

    print(f"final offers with amenities:\n{cheapestPriceOffers}")
    verbose(f"final offers with amenities:\n{cheapestPriceOffers}", verbose_checkpoint)

    returnData = {"status": "ok", "data": {"offers": [], "people": people}}
    for cheapest_price_offer in cheapestPriceOffers:
        amenities = cheapest_price_offer["amenities"]
        
        amenities_dict = {}
        for amenity in amenities:
            if amenity["included"]:
                amenities_dict[amenity["amenity_description"]] = {"isChargeable": amenity["isChargeable"], "isRequested": amenity["isRequested"]}

        geoCode, cityCode, airportName = get_airport_coordinates(access_token, cheapest_price_offer["offer"]["itineraries"][0]["segments"][-1]["arrival"]["iataCode"])
        
        flights = []
        for iteraryIndex, iterary in enumerate(cheapest_price_offer["offer"]["itineraries"]):
            for segment in iterary["segments"]:
                for detailsBySegment in cheapest_price_offer["offer"]["travelerPricings"][0]["fareDetailsBySegment"]:
                    if detailsBySegment["segmentId"] == segment["id"]:
                        print("detailsBySegment", detailsBySegment)
                        if "cabin" in detailsBySegment:
                            travelClass = detailsBySegment["cabin"]
                        else:
                            travelClass = "ECONOMY"
                        break
                flights.append({"departure": segment["departure"], "arrival": segment["arrival"], "duration": segment["duration"], "flightNumber": segment["number"], "carrierCode": segment["carrierCode"], "iteraryNumber": iteraryIndex, "travelClass": travelClass})
        
        includedBags = 0
        if "quantity" in cheapest_price_offer["offer"]["travelerPricings"][0]["fareDetailsBySegment"][0]["includedCheckedBags"]:
            includedBags = cheapest_price_offer["offer"]["travelerPricings"][0]["fareDetailsBySegment"][0]["includedCheckedBags"]["quantity"]
        elif "weight" in cheapest_price_offer["offer"]["travelerPricings"][0]["fareDetailsBySegment"][0]["includedCheckedBags"]:
            includedBags = 1
            
        checkedBags = includedBags
        if "additionalServices" in cheapest_price_offer["offer"]["travelerPricings"][0]["fareDetailsBySegment"][0]:
            if "chargeableCheckedBags" in cheapest_price_offer["offer"]["travelerPricings"][0]["fareDetailsBySegment"][0]["additionalServices"]:
                checkedBags += cheapest_price_offer["offer"]["travelerPricings"][0]["fareDetailsBySegment"][0]["additionalServices"]["chargeableCheckedBags"]["quantity"]

        returnData["data"]["offers"].append({"price": {"grandTotal": cheapest_price_offer["offer"]["price"]["grandTotal"], "billingCurrency": cheapest_price_offer["offer"]["price"]["billingCurrency"]}, "passengers": len(cheapest_price_offer["offer"]["travelerPricings"]), "checkedBags": checkedBags, "amenities": amenities_dict, "flights": flights, "geoCode": geoCode, "airportName": airportName, "cityCode": cityCode})
        
    return returnData