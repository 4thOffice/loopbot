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

def get_flight_offers(access_token, search_params, ama_Client_Ref, apiType, verbose_checkpoint=None):
    if apiType == "personal":
        endpoint = 'https://api.amadeus.com/v2/shopping/flight-offers'
    else:
        endpoint = 'https://travel.api.amadeus.com/v2/shopping/flight-offers'

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
            #print(responseJson)
            #print("flight offers length: ", len(responseJson["data"]))
            #verbose(f"initial flight offers:\n{responseJson}", verbose_checkpoint)
            #verbose(("initial flight offers length: ", len(responseJson["data"])), verbose_checkpoint)
            return {"status": "ok", "details": responseJson}
    except ResponseError as error:
        print(error)
        verbose(f"Error getting flight offers {error}", verbose_checkpoint=verbose_checkpoint)
        return responseJson
    

def fetchOffers(search_params, extraTimeframes, checkedBags, refundableTicket, changeableTicket, travelClass, flightNumbersPerItinerary, access_token, ama_Client_Ref, apiType, verbose_checkpoint=None):
    #print(f"Search parameters: {search_params}")
    #print(f"Extra timeframes: {extraTimeframes}")
    #print(f"checked bags: {checkedBags}")
    #print(f"refundable ticket: {refundableTicket}")
    #print(f"changeable ticket: {changeableTicket}")
    #print(f"travel class: {travelClass}")
    #print(f"Flight numbers per itinerary: {flightNumbersPerItinerary}")
    #verbose(f"Flight numbers per itinerary: {flightNumbersPerItinerary}", verbose_checkpoint)
    #verbose(f"refundable ticket: {refundableTicket}", verbose_checkpoint)
    #verbose(f"changeable ticket: {changeableTicket}", verbose_checkpoint)
    #verbose(f"travel class: {travelClass}", verbose_checkpoint)
    #verbose(f"Search parameters: {search_params}", verbose_checkpoint)
    #verbose(f"Extra timeframes: {extraTimeframes}", verbose_checkpoint)
    #verbose(f"Checked bags per person: {checkedBags}", verbose_checkpoint)

    #repeat this and expand time window untill amadeus returns at least 1 flight offer
    iteration = 0
    flightsFound = False
    while iteration < 4 and not flightsFound:
        flightOffers = get_flight_offers(access_token, search_params, ama_Client_Ref, apiType, verbose_checkpoint)
        if flightOffers["status"] == "error":
            print("Error with getting flights")
            verbose("Error with getting flights", verbose_checkpoint)
            return []
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

    return flightOffers