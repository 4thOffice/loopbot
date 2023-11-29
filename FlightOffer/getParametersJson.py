import datetime
import json
import sys
import time
import os
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import openai
import keys


def extractSearchParameters(emailText, offerCount):
    user_msg = "I want you to extract flight details and replace values in this parameter json:\n"

    """
        "latestOutboundDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
        "earliestOutboundDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
        "latestReturnDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
        "earliestReturnDepartureTime": "", //leave empty if not specified! format must be: "10:00:00"
    """
    user_msg += """{
        "currencyCode": "EUR", //Keep EUR if not specified
        "adults": 1,
        "maximumNumberOfConnections": 0,
        "children": 0,
        "includedAirlineCodes": "" //leave empty if not specified! must be in format (comma-seperated): "6X,7X,8X"
        "travelClass": "ECONOMY", // ONLY choose from these options and no other: ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]
        "flightSegments": [ //seperate flight segments that customer is asking for. If flight is one-way, there should be only one flight segment. If it is round-trip, it should have 2 flight segments. If customer is asking for multiple options from different origins, then only use EXACTLY one.
                {
                    "originLocationCode": "LJU", //If location is not specified, think logically what it could be. Location codes must be EXACTLY 3-letter IATA codes! Exactly 3 letters! This parameter must NOT be empty!
                    "alternativeOriginsCodes": "", //must be in format: ["LON", "MUC"]. MUST BE AN ARRAY! Leave empty if not specified!
                    "destinationLocationCode": "PAR", //Location codes must be EXACTLY 3-letter IATA codes! Exactly 3 letters! This parameter must NOT be empty!
                    "alternativeDestinationsCodes": "", //must be in format: ["LON", "MUC"]. MUST BE AN ARRAY! Leave empty if not specified!
                    "departureDate": "2023-12-09", //must be in format: YYYY-MM-DD
                    "exactDepartureTime": "" //leave empty if not specified! format must be: ('00:00:00' to '23:59:59) (HH:MM:SS), Connection points dont coount, only final destionation points count
                    "earliestDepartureTime": "" //leave empty if not specified! format must be: ('00:00:00' to '23:59:59) (HH:MM:SS)
                    "latestDepartureTime": "" //leave empty if not specified! format must be: ('00:00:00' to '23:59:59) (HH:MM:SS)
                    "exactArrivalTime": "" //leave empty if not specified! format must be: ('00:00:00' to '23:59:59) (HH:MM:SS), Connection points dont coount, only final destionation points count
                    "earliestArrivalTime": "" //leave empty if not specified! format must be: ('00:00:00' to '23:59:59) (HH:MM:SS)
                    "latestArrivalTime": "" //leave empty if not specified! format must be: ('00:00:00' to '23:59:59) (HH:MM:SS)
                    "includedConnectionPoints": "" //must be in format: ["LON", "MUC"]. MUST BE AN ARRAY! Leave empty if not specified!
                }
        ]
}\n\n"""
    user_msg += "Change json parameter values according to the email which I will give you. If year is not specified, use 2023. Location codes must be 3-letter IATA codes. if origin is not provided, make the value empty string ''. You can change parameter values but you cant add new parameters. Do not leave any parameters empty, except if returnDate is not specified in email text, then you MUSt leave it empty.\n\nEmail to extract details from:\n"
    user_msg += emailText
    user_msg += "\n\nOutput should be ONLY json and NO other text!"

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
            flight = json.loads(response.choices[0].message.content)
            #NDC
            search_params = {
                "currencyCode": flight["currencyCode"],
                "originDestinations": [],
                "travelers": [],
                "sources": [
                    "GDS"
                ],
                "searchCriteria": {
                    "maxFlightOffers": offerCount,
                    "flightFilters": {
                    "connectionRestriction": {
                        "maximumNumberOfConnections": max(flight["maximumNumberOfConnections"], 0)
                    },
                    "cabinRestrictions": [
                        {
                        "cabin": flight["travelClass"],
                        "originDestinationIds": []
                        }
                    ]
                    }
                }
            }

            #remove unwanted flight segments
            usedOriginLocationCodes = []
            usedDestinationLocationCodes = []
            for flightSegment in flight["flightSegments"]:
                found = False
                for code in usedOriginLocationCodes:
                    if code == flightSegment["originLocationCode"]:
                        if flightSegment in flight["flightSegments"]:
                            flight["flightSegments"].remove(flightSegment)
                        found = True
                        break
                if not found:
                    usedOriginLocationCodes.append(flightSegment["originLocationCode"])
                    found = False
                for code in usedDestinationLocationCodes:
                    if code == flightSegment["destinationLocationCode"]:
                        if flightSegment in flight["flightSegments"]:
                            flight["flightSegments"].remove(flightSegment)
                        break
                if not found:
                    usedDestinationLocationCodes.append(flightSegment["destinationLocationCode"])


            if flight["maximumNumberOfConnections"] == 0:
                search_params["searchCriteria"]["flightFilters"]["connectionRestriction"]["nonStopPreferred"] = "true"
            
            search_params["searchCriteria"]["flightFilters"]["maxFlightTime"] = 200

            for index in range(0, flight["adults"]):
                traveler =     {
                    "id": str(index+1),
                    "travelerType": "ADULT"
                }
                search_params["travelers"].append(traveler)
            for index in range(0, flight["children"]):
                traveler =     {
                    "id": str(index+1),
                    "travelerType": "CHILD"
                }
                search_params["travelers"].append(traveler)

            if flight["includedAirlineCodes"] != "":
                search_params["searchCriteria"]["flightFilters"]["AirlineRestrictions"] = {"includedAirlineCodes": flight["includedAirlineCodes"]}

            extraTimeframes = []
            for index, flight_ in enumerate(flight["flightSegments"]):

                year_from_string = int(flight_["departureDate"][:4])
                date_from_string = datetime.datetime.strptime(flight_["departureDate"], "%Y-%m-%d")
                current_date = datetime.datetime.now()
                if date_from_string < current_date:
                    flight_["departureDate"] = str(year_from_string+1) + flight_["departureDate"][4:]

                segment = {
                    "id": str(index+1),
                    "originLocationCode": flight_["originLocationCode"],
                    "destinationLocationCode": flight_["destinationLocationCode"],
                    "departureDateTimeRange": {
                        "date": flight_["departureDate"]
                    }
                }
                    
                if flight_["alternativeDestinationsCodes"] != "" and flight_["alternativeDestinationsCodes"] != []:
                    segment["alternativeDestinationsCodes"] = flight_["alternativeDestinationsCodes"]

                if flight_["alternativeOriginsCodes"] != "" and flight_["alternativeOriginsCodes"] != []:
                    segment["alternativeOriginsCodes"] = flight_["alternativeOriginsCodes"]

                if flight_["includedConnectionPoints"] != "" and flight_["includedConnectionPoints"] != []:
                    segment["includedConnectionPoints"] = flight_["includedConnectionPoints"]
                    
                if flight_["exactDepartureTime"] != "":
                    segment["departureDateTimeRange"]["time"] = flight_["exactDepartureTime"]
                    #segment["departureDateTimeRange"]["timeWindow"] = "12H"

                if flight_["exactArrivalTime"] != "" and flight_["exactDepartureTime"] == "":
                    segment["arrivalDateTimeRange"] = {"time": flight_["exactArrivalTime"]}
                    #segment["departureDateTimeRange"]["timeWindow"] = "2H"

                search_params["originDestinations"].append(segment)
                search_params["searchCriteria"]["flightFilters"]["cabinRestrictions"][0]["originDestinationIds"].append(str(index+1))

                segmentDictionary = {}
                if "earliestDepartureTime" in flight_:
                    segmentDictionary["earliestDepartureTime"] = flight_["earliestDepartureTime"]
                if "latestDepartureTime" in flight_:
                    segmentDictionary["latestDepartureTime"] = flight_["latestDepartureTime"]
                if "exactDepartureTime" in flight_:
                    segmentDictionary["exactDepartureTime"] = flight_["exactDepartureTime"]
                if "earliestArrivalTime" in flight_:
                    segmentDictionary["earliestArrivalTime"] = flight_["earliestArrivalTime"]
                if "latestArrivalTime" in flight_:
                    segmentDictionary["latestArrivalTime"] = flight_["latestArrivalTime"]
                if "exactArrivalTime" in flight_:
                    segmentDictionary["exactArrivalTime"] = flight_["exactArrivalTime"]

                if segmentDictionary["earliestDepartureTime"] == segmentDictionary["exactDepartureTime"]:
                    segmentDictionary["earliestDepartureTime"] = ""
                if segmentDictionary["latestDepartureTime"] == segmentDictionary["exactDepartureTime"]:
                    segmentDictionary["latestDepartureTime"] = ""
                if segmentDictionary["latestArrivalTime"] == segmentDictionary["exactArrivalTime"]:
                    segmentDictionary["latestArrivalTime"] = ""
                if segmentDictionary["earliestArrivalTime"] == segmentDictionary["exactArrivalTime"]:
                    segmentDictionary["earliestArrivalTime"] = ""

                extraTimeframes.append(segmentDictionary)

            return search_params, extraTimeframes
        else:
            if attempt < max_attempts - 1:
                print("No response received. Retrying in {} seconds...".format(retry_interval))
                time.sleep(retry_interval)  # Wait for the specified interval before retrying
            else:
                print("Exceeded maximum attempts. No response received.")