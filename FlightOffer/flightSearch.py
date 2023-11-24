import datetime
import json
import sys
import time
import openai
import requests
import os
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import keys
from amadeus import Client, ResponseError
#import getParametersJson

def verbose(message, verbose_checkpoint=None):
    if verbose_checkpoint:
        verbose_checkpoint(message)

# Function to check time difference between flights
def check_time_between_flights(itineraries, buffer):
    for itinerary in itineraries:
        segments = itinerary.get('segments', [])
        for i in range(len(segments) - 1):
            current_arrival_time = datetime.datetime.fromisoformat(segments[i]['arrival']['at'])
            next_departure_time = datetime.datetime.fromisoformat(segments[i + 1]['departure']['at'])
            time_difference = next_departure_time - current_arrival_time
            hours_difference = time_difference.total_seconds() / 3600

            if hours_difference > (2.5+buffer) or hours_difference < 1.7:
                return True

    return False

def check_number_of_stops(itineraries):
    for itinerary in itineraries:
        segments = itinerary.get('segments', [])
        if len(segments) > 2:
            return True

    return False

def find_closest_flight_offer(flight_offers, outbound_departure_time="", return_departure_time=""):
    closest_offer = None
    smallest_time_diff = float('inf')
    if outbound_departure_time != "":
        outbound_departure_time = datetime.datetime.strptime(outbound_departure_time, '%H:%M:%S').time()
    if return_departure_time != "":
        return_departure_time = datetime.datetime.strptime(return_departure_time, '%H:%M:%S').time()

    for index, offer in enumerate(flight_offers):
        print(index)
        time_diff = 0
        if outbound_departure_time != "":
            departure_time = offer["itineraries"][0]["segments"][0]["departure"]["at"]
            departure_time = datetime.datetime.fromisoformat(departure_time).time()
            time_diff += abs(outbound_departure_time.hour - departure_time.hour)

        if return_departure_time != "":
            departure_time = offer["itineraries"][1]["segments"][0]["departure"]["at"]
            departure_time = datetime.datetime.fromisoformat(departure_time).time()
            time_diff += abs(return_departure_time.hour - departure_time.hour)
        if time_diff < smallest_time_diff:
            smallest_time_diff = time_diff
            closest_offer = offer

    return closest_offer


def extractSearchParameters(emailText, offerCount, verbose_checkpoint):
    user_msg = "I want you to extract flight details and replace values in this parameter json:\n"

    """
        "latestOutboundDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
        "earliestOutboundDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
        "latestReturnDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
        "earliestReturnDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
    """
    user_msg += """{
        "currencyCode": "EUR", //Keep EUR if not specified
        "originLocationCode": "LJU", //Leave "LJU" if not specified! Location codes must be EXACTLY 3-letter IATA codes! Exactly 3 letters!
        "destinationLocationCode": "PAR", //Location codes must be EXACTLY 3-letter IATA codes! Exactly 3 letters!
        "departureDate": "2023-12-09", //must be in format: YYYY-MM-DD
        "returnDate": "2023-12-15", //must be in format: YYYY-MM-DD
        "exactOutboundDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
        "exactReturnDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
        "adults": 1,
        "nonStop": "true", //leave like this if not specified explicitly, options to choose from: ["true", "false"] set to true, ONLY if person 
         requested 
        for flight to go from the origin to the destination with no stop in between
        "children": 0,
        "infants": 0,
        "travelClass": "ECONOMY" // ONLY choose from these options and no other: ["ECONOMY", "PREMIUM_ECONOMY", 
         "BUSINESS", "FIRST"]
      }\n\n"""
    user_msg += "Change json parameter values according to the email which I will give you. If year is not specified, use 2023. Location codes must be 3-letter IATA codes. if origin is not provided, make the value empty string ''. You can change parameter values but you cant add new parameters. Do not leave any parameters empty, except if returnDate is not specified in email text, then you MUSt leave it empty.\n\nEmail to extract details from:\n"
    user_msg += emailText
    user_msg += "\n\nOutput should be ONLY json above with replaced parameter values and NO other text!"

    print(user_msg)

    # new_obj = {"messages": [{"role": "user", "content": user_msg}, {"role": "assistant", "content": "test"}]}
    # with open("./FlightOffer/finetuning.json", 'r') as file:
    #     existing_data = json.load(file)
    # existing_data["samples"].append(new_obj)
    # with open("./FlightOffer/finetuning.json", 'w') as file:
    #     json.dump(existing_data, file, indent=4)
    

    max_attempts = 2  # Maximum number of attempts
    retry_interval = 10  # Retry interval in seconds

    for attempt in range(max_attempts):
        openai.api_key = keys.openAI_APIKEY
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": user_msg}
            ]
        )

        if response.choices:
            #print(response.choices[0].message.content)
            verbose(response.choices[0].message.content, verbose_checkpoint)
            flight = json.loads(response.choices[0].message.content)

            # with open("./FlightOffer/finetuning.json", 'r') as file:
            #     existing_data = json.load(file)
            # existing_data["samples"][-1]["messages"][-1]["content"] = json.dumps(flight)
            # with open("./FlightOffer/finetuning.json", 'w') as file:
            #     json.dump(existing_data, file, indent=4)
            print("----------------------------")
            print(flight)
            print("----------------------------")

            year_from_string = int(flight["departureDate"][:4])
            date_from_string = datetime.datetime.strptime(flight["departureDate"], "%Y-%m-%d")
            current_date = datetime.datetime.now()
            if date_from_string < current_date:
                flight["departureDate"] = str(year_from_string+1) + flight["departureDate"][4:]
                flight["returnDate"] = str(year_from_string+1) + flight["returnDate"][4:]

            flight["max"] = offerCount
            if "nonStop" in flight and (flight["nonStop"] == "false" or flight["nonStop"] == False):
                flight.pop("nonStop")
            if "children" in flight and flight["children"] == 0:
                flight.pop("children")
            if "infants" in flight and flight["infants"] == 0:
                flight.pop("infants")
            if "returnDate" in flight and flight["returnDate"] == "":
                flight.pop("returnDate")
                flight["oneWay"] = True
            if "originLocationCode" in flight and flight["originLocationCode"] == "":
                flight["originLocationCode"] = "LJU"

            return flight
        else:
            if attempt < max_attempts - 1:
                print("No response received. Retrying in {} seconds...".format(retry_interval))
                time.sleep(retry_interval)  # Wait for the specified interval before retrying
            else:
                print("Exceeded maximum attempts. No response received.")

amadeus = Client(
    client_id=keys.amadeus_client_id,
    client_secret=keys.amadeus_client_secret
)

def get_access_token(api_key=keys.amadeus_client_id, api_secret=keys.amadeus_client_secret):
    auth_url = 'https://test.api.amadeus.com/v1/security/oauth2/token'
    response = requests.post(auth_url, data={
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': api_secret
    })
    return response.json().get('access_token')

endpoint = 'https://test.api.amadeus.com/v2/shopping/flight-offers'

def get_price_offer(access_token, flight_offers):
    url = 'https://test.api.amadeus.com/v1/shopping/flight-offers/pricing'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }
    payload = {
        'data': {
            'type': 'flight-offers-pricing',
            'flightOffers': flight_offers
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print('Flight Offers price information retrieved successfully!')
        return response.json()  # Return the JSON response
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None

def get_upsell(access_token, flight_offers):
    url = 'https://test.api.amadeus.com/v1/shopping/flight-offers/upselling'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }
    payload = {
        'data': {
            'type': 'flight-offers-pricing',
            'flightOffers': flight_offers
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print('Flight Offers upsell information retrieved successfully!')
        return response.json()  # Return the JSON response
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None
    
def get_flight_offers(access_token, search_params, verbose_checkpoint=None):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }
    try:
        #response = requests.post(endpoint, headers=headers, data=json.dumps(search_params))
        response = requests.get(endpoint, headers=headers, params=search_params)
        responseJson = response.json()
        if "errors" in responseJson:
            print(f"Error with fetching flight offers: {responseJson}")
            verbose(f"Error with fetching flight offers: {responseJson}", verbose_checkpoint)
            combined_detail = '\n'.join(error['detail'] for error in responseJson["errors"])
            return {"status": "error", "details": combined_detail}
        else:
            #print(responseJson)
            print("initial flight offers: ", len(responseJson["data"]))
            return {"status": "ok", "details": responseJson}
    except ResponseError as error:
        print(error)
        return responseJson
    
def getFlightOffer(flightDetails, verbose_checkpoint=None):
    search_params = extractSearchParameters(flightDetails, 250, verbose_checkpoint)
    #search_params = getParametersJson.extractSearchParameters(flightDetails, 250)
    
    exactOutboundDepartureTime = ""
    exactReturnDepartureTime = ""

    if "exactOutboundDepartureTime" in search_params:
        exactOutboundDepartureTime = search_params.pop("exactOutboundDepartureTime")
    if "exactReturnDepartureTime" in search_params:
        exactReturnDepartureTime = search_params.pop("exactReturnDepartureTime")
    oneWay = False
    if "oneWay" in search_params:
        oneWay = search_params.pop("oneWay")

    try:
        print(search_params)
        verbose(search_params, verbose_checkpoint)
        access_token = get_access_token()
        flightOffers = get_flight_offers(access_token, search_params, verbose_checkpoint)
        if flightOffers["status"] == "error":
            print("error 1")
            verbose("error 1", verbose_checkpoint)
            return {"status": "error", "data": flightOffers["details"]}
        elif flightOffers["status"] == "ok":
            flightOffers = flightOffers["details"]["data"]
            time.sleep(0.5)

        if len(flightOffers) <= 0:
            print("No direct flights, now searching for fights with stops")
            verbose("No direct flights, now searching for fights with stops", verbose_checkpoint)
            if "nonStop" in search_params:
                search_params.pop("nonStop")
                flightOffers = get_flight_offers(access_token, search_params)
                if flightOffers["status"] == "error":
                    print("error 2")
                    verbose("error 2", verbose_checkpoint)
                    return {"status": "error", "data": flightOffers["details"]}
                elif flightOffers["status"] == "ok":
                    flightOffers = flightOffers["details"]["data"]
                    time.sleep(0.5)

        if len(flightOffers) <= 0:
            print("no class specific flights found, removing travel class")
            verbose("no class specific flights found, removing travel class", verbose_checkpoint)
            if "travelClass" in search_params:
                search_params.pop("travelClass")
                flightOffers = get_flight_offers(access_token, search_params)
                if flightOffers["status"] == "error":
                    print("error 3")
                    verbose("error 3", verbose_checkpoint)
                    return {"status": "error", "data": flightOffers["details"]}
                elif flightOffers["status"] == "ok":
                    flightOffers = flightOffers["details"]["data"]
                    time.sleep(0.5)
    except ResponseError as error:
        print("error 4")
        verbose("error 4", verbose_checkpoint)
        print(error)
        verbose(error, verbose_checkpoint)
        time.sleep(0.5)
        return {"status": "error", "data": "Unknown error occured"}
    #print(flightOffers)

    if len(flightOffers) <= 0:
        print("no flights")
        verbose("no flights", verbose_checkpoint)
        return {"status": "ok", "data": None}
    
    cheapestFlightOffers = []
    #check which offers qualify

    iteration = 0
    foundFlights = False
    while not foundFlights and iteration < 10:
        print(iteration)
        cheapestFlightOffers = []
        for flightOffer in flightOffers:
            satisfiesConditions = True
            #if flightOffer["numberOfBookableSeats"] < len(search_params["travelers"]):
            if flightOffer["numberOfBookableSeats"] < search_params["adults"]:
                satisfiesConditions = False

            if check_time_between_flights(flightOffer["itineraries"], iteration*0.5):
                satisfiesConditions = False

            if check_number_of_stops(flightOffer["itineraries"]):
                satisfiesConditions = False

            if satisfiesConditions:
                print("satisfies all conditions")
                cheapestFlightOffers.append(flightOffer)
                foundFlights = True
        iteration += 1

    if len(cheapestFlightOffers) <= 0:
        cheapestFlightOffers = flightOffers
        print("no flight offers satisfied all conditions.. using not optimal flights..")
        verbose("no flight offers satisfied all conditions.. using not optimal flights..", verbose_checkpoint)
    
    print("cheapestFlightOffers:\n", str(len(cheapestFlightOffers)))
    verbose(("cheapestFlightOffers:\n" + str(len(cheapestFlightOffers))), verbose_checkpoint)
    if exactOutboundDepartureTime != "" or exactReturnDepartureTime != "":
        cheapestFlightOffers = [find_closest_flight_offer(cheapestFlightOffers, outbound_departure_time=exactOutboundDepartureTime, return_departure_time=exactReturnDepartureTime)]
    print(cheapestFlightOffers)
    print("length 1:", len(cheapestFlightOffers))
    if len(cheapestFlightOffers) > 1:
        cheapestFlightOffers = sorted(cheapestFlightOffers, key=lambda x: float(x["price"]["grandTotal"]))[:min(len(cheapestFlightOffers), 6)]
    #print("upsell data:\n", get_upsell(access_token, cheapestFlightOffers))
    print("length 2:", len(cheapestFlightOffers))
    print("get price offers for:\n", cheapestFlightOffers)
    verbose(f"get price offers for:\n{cheapestFlightOffers}", verbose_checkpoint)
    try:
        price_offers = get_price_offer(access_token, cheapestFlightOffers)["data"]["flightOffers"]
    except:
        return {"status": "error", "data": "Error with getting final price offer"}
    cheapestPriceOffers = sorted(price_offers, key=lambda x: float(x["price"]["grandTotal"]))
    print(f"cheapest flight price offer:\n{cheapestPriceOffers}")
    
    flights = []
    for iterary in cheapestPriceOffers[0]["itineraries"]:
        for segment in iterary["segments"]:
            flights.append({"departure": segment["departure"], "arrival": segment["arrival"], "duration": segment["duration"], "flightNumber": segment["number"], "carrierCode": segment["carrierCode"]})

    return {"status": "ok", "data": {"price": {"grandTotal": cheapestPriceOffers[0]["price"]["grandTotal"], "billingCurrency": cheapestPriceOffers[0]["price"]["billingCurrency"]}, "flights": flights}}