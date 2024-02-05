import json
import requests
import sys
import os
sys.path.append("../")
import keys

def get_access_token(api_key=keys.amadeus_client_id, api_secret=keys.amadeus_client_secret):
    #auth_url = 'https://api.amadeus.com/v1/security/oauth2/token'
    auth_url = 'https://test.travel.api.amadeus.com/v1/security/oauth2/token'

    response = requests.post(auth_url, data={
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': api_secret
    })
    print("Access key:\n", response.json())
    return response.json().get('access_token')


def getHigherClasses(travelClass):
    if travelClass == "ECONOMY":
      return ["PREMIUM_ECONOMY", "BUSINESS", "FIRST"]
    elif travelClass == "PREMIUM_ECONOMY":
      return ["BUSINESS", "FIRST"]
    elif travelClass == "BUSINESS":
      return ["FIRST"]
    elif travelClass == "FIRST":
      return []

def get_upsell_offer(access_token, flight_offers, amenities, travelClass):
    #url = 'https://api.amadeus.com/v1/shopping/flight-offers/upselling'
    url = 'https://test.travel.api.amadeus.com/v1/shopping/flight-offers/upselling'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }
    #flight_offers["pricingOptions"]["refundableFare"] = True

    #print(json.loads(flight_offers))
    payload = {
        'data': {
            'type': 'flight-offers-upselling',
            'flightOffers': [(flight_offers)] 
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print('Flight Offers upsell information retrieved successfully!')
        res = response.json()
        print(response.json())
        print("------------------------------------------")
        if "status" in res:
            if res["status"] == "400":
                return None
        
        offersWithAmenityCount = []
        print(len(res["data"]))

        for offer in res["data"]:
            offersWithAmenityCount.append({"offer": offer, "amenityCount": 0, "amenities": []})
        
        for offer in res["data"]:
            includedAmenities = {}
            wrongTravelClass = False
            wrongTravelClassNumber = 0
            for amenity in amenities:
                includedAmenities[amenity] = {"included": True, "isChargeable": False}
  
            for traveler in offer["travelerPricings"]:
                #if wrongTravelClass:
                    #break
                for segment in traveler["fareDetailsBySegment"]:
                    if segment["cabin"] in getHigherClasses(travelClass):
                        #wrongTravelClass = True
                        print("Wrong travel class")
                        wrongTravelClassNumber += 1
                        #break
                    for includedAmenity in includedAmenities:
                        amenityFoundInSegment = False
                        isChargeable = False
                        if "amenities" not in segment:
                            includedAmenities[includedAmenity]["included"] = False
                            break
                        for amenity in segment["amenities"]:
                            if amenity["description"] == includedAmenity:
                                amenityFoundInSegment = True
                                isChargeable = amenity["isChargeable"]
                                break
                            
                        includedAmenities[includedAmenity]["isChargeable"] = isChargeable
                        if not amenityFoundInSegment:
                            includedAmenities[includedAmenity]["included"] = False
                if wrongTravelClassNumber > int(len(traveler["fareDetailsBySegment"])/2):
                    wrongTravelClass = True
                    break

            if wrongTravelClass:
                print("DISCARDED")
                continue
            
            print(includedAmenities)


            amenityCount = 0
            refundFound = False
            changeFound = False
            for amenity_ in includedAmenities.keys():
                if includedAmenities[amenity_]["included"] and includedAmenities[amenity_]["isRequested"]:
                    if amenity_ in ["REFUNDABLE TICKET", "REFUND BEFORE DEPARTURE", "REFUND AFTER DEPARTURE", "REFUNDS ANYTIME"]:
                        if not refundFound:
                            refundFound = True
                            amenityCount += 1
                    elif amenity_["amenity_description"] in ["CHANGEABLE TICKET", "CHANGE BEFORE DEPARTURE", "CHANGE AFTER DEPARTURE"]:
                        if not changeFound:
                            changeFound = True
                            amenityCount += 1
                    else:
                        amenityCount += 1

            #amenityCount = sum(value["included"] is True for value in includedAmenities.values())
            for index, offer_ in enumerate(offersWithAmenityCount):
                if offer == offer_["offer"]:
                    offersWithAmenityCount[index]["amenityCount"] = amenityCount
                    for includedAmenity_ in includedAmenities.keys():
                        if includedAmenities[includedAmenity_]["included"] == True:
                            offersWithAmenityCount[index]["amenities"].append({"amenity_description": includedAmenity_, "isChargeable": includedAmenities[includedAmenity_]["isChargeable"]})
    
        sorted_offers = sorted(offersWithAmenityCount, key=lambda x: x["amenityCount"], reverse=True)

        if sorted_offers[0]["amenityCount"] == 0:
            return None
        else:
            return sorted_offers[0]
        
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None
    
#offer =  {'type': 'flight-offer', 'id': '1', 'source': 'NDC', 'sourceReference': 'eJyNzDEOAiEQBdATfZmBgVnKNauJNqurvQEWEgujhSbGwrOrN7B/eanYxf2JaitI0FH0mqWCeVYIxQ6xaIK6FnyYiZisWfZmNb3G87Q/XFb7hvfjuttMuG0Pw4n7k7ikWjwhEieIdPZ7BItWZu87DdE2/3PjGs76pDVlxKoEcczIsTB8rBI4u0aSzc78KTFuwKYfjoY/0/c32Q==', 'instantTicketingRequired': False, 'nonHomogeneous': False, 'oneWay': False, 'lastTicketingDate': '2024-02-01', 'lastTicketingDateTime': '2024-02-01T23:59:00', 'itineraries': [{'duration': 'PT2H35M', 'segments': [{'departure': {'iataCode': 'VCE', 'at': '2024-02-19T08:20:00'}, 'arrival': {'iataCode': 'LHR', 'terminal': '5', 'at': '2024-02-19T09:55:00'}, 'carrierCode': 'BA', 'number': '597', 'aircraft': {'code': '319'}, 'operating': {'carrierCode': 'BA'}, 'duration': 'PT2H35M', 'id': '19', 'numberOfStops': 0, 'blacklistedInEU': False}]}, {'duration': 'PT2H30M', 'segments': [{'departure': {'iataCode': 'LHR', 'terminal': '5', 'at': '2024-02-23T17:35:00'}, 'arrival': {'iataCode': 'VCE', 'at': '2024-02-23T21:05:00'}, 'carrierCode': 'BA', 'number': '596', 'aircraft': {'code': '32N'}, 'operating': {'carrierCode': 'BA'}, 'duration': 'PT2H30M', 'id': '34', 'numberOfStops': 0, 'blacklistedInEU': False}]}], 'price': {'currency': 'EUR', 'total': '153.44', 'base': '73.00', 'fees': [{'amount': '0.00', 'type': 'SUPPLIER'}, {'amount': '0.00', 'type': 'TICKETING'}], 'grandTotal': '153.44'}, 'pricingOptions': {'fareType': ['PUBLISHED'], 'includedCheckedBagsOnly': False}, 'travelerPricings': [{'travelerId': '1', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '153.44', 'base': '73.00'}, 'fareDetailsBySegment': [{'segmentId': '19', 'cabin': 'ECONOMY', 'fareBasis': 'NZLZ0H', 'class': 'N', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '34', 'cabin': 'ECONOMY', 'fareBasis': 'OULZ0H', 'class': 'O', 'includedCheckedBags': {'quantity': 0}}]}], "validatingAirlineCodes": ["BA"]}
offer =  {'type': 'flight-offer', 'id': '5', 'source': 'GDS', 'instantTicketingRequired': False, 'nonHomogeneous': False, 'oneWay': False, 'lastTicketingDate': '2024-02-05', 'lastTicketingDateTime': '2024-02-05', 'numberOfBookableSeats': 9, 'itineraries': [{'duration': 'PT6H20M', 'segments': [{'departure': {'iataCode': 'LJU', 'at': '2024-02-27T07:05:00'}, 'arrival': {'iataCode': 'FRA', 'terminal': '1', 'at': '2024-02-27T08:25:00'}, 'carrierCode': 'LH', 'number': '1461', 'aircraft': {'code': 'CR9'}, 'operating': {'carrierCode': 'CL'}, 'id': '4', 'numberOfStops': 0, 'blacklistedInEU': False}, {'departure': {'iataCode': 'FRA', 'terminal': '1', 'at': '2024-02-27T11:20:00'}, 'arrival': {'iataCode': 'VNO', 'at': '2024-02-27T14:25:00'}, 'carrierCode': 'LH', 'number': '886', 'aircraft': {'code': '320'}, 'operating': {'carrierCode': 'LH'}, 'id': '5', 'numberOfStops': 0, 'blacklistedInEU': False}]}, {'duration': 'PT7H35M', 'segments': [{'departure': {'iataCode': 'VNO', 'at': '2024-03-01T15:10:00'}, 'arrival': {'iataCode': 'FRA', 'terminal': '1', 'at': '2024-03-01T16:25:00'}, 'carrierCode': 'LH', 'number': '887', 'aircraft': {'code': '320'}, 'operating': {'carrierCode': 'LH'}, 'id': '172', 'numberOfStops': 0, 'blacklistedInEU': False}, {'departure': {'iataCode': 'FRA', 'terminal': '1', 'at': '2024-03-01T20:35:00'}, 'arrival': {'iataCode': 'LJU', 'at': '2024-03-01T21:45:00'}, 'carrierCode': 'LH', 'number': '1460', 'aircraft': {'code': 'CR9'}, 'operating': {'carrierCode': 'CL'}, 'id': '173', 'numberOfStops': 0, 'blacklistedInEU': False}]}], 'price': {'currency': 'EUR', 'total': '358.19', 'base': '186.00', 'fees': [{'amount': '0.00', 'type': 'SUPPLIER'}, {'amount': '0.00', 'type': 'TICKETING'}], 'grandTotal': '358.19'}, 'pricingOptions': {'fareType': ['PUBLISHED'], 'includedCheckedBagsOnly': True}, 'validatingAirlineCodes': ['LH'], 'travelerPricings': [{'travelerId': '1', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '358.19', 'base': '186.00'}, 'fareDetailsBySegment': [{'segmentId': '4', 'cabin': 'ECONOMY', 'fareBasis': 'S06CLSE3', 'class': 'S', 'includedCheckedBags': {'quantity': 1}, 'includedCabinBags': {'quantity': 1}}, {'segmentId': '5', 'cabin': 'ECONOMY', 'fareBasis': 'S06CLSE3', 'class': 'S', 'includedCheckedBags': {'quantity': 1}, 'includedCabinBags': {'quantity': 1}}, {'segmentId': '172', 'cabin': 'ECONOMY', 'fareBasis': 'S06CLSE3', 'class': 'S', 'includedCheckedBags': {'quantity': 1}, 'includedCabinBags': {'quantity': 1}}, {'segmentId': '173', 'cabin': 'ECONOMY', 'fareBasis': 'S06CLSE3', 'class': 'S', 'includedCheckedBags': {'quantity': 1}, 'includedCabinBags': {'quantity': 1}}]}], 'fareRules': {'rules': [{'category': 'EXCHANGE', 'maxPenaltyAmount': '60.00'}, {'category': 'REFUND', 'notApplicable': True}, {'category': 'REVALIDATION', 'maxPenaltyAmount': '60.00'}]}}

upsold = get_upsell_offer(get_access_token(), offer, ["REFUNDABLE TICKET", "CHANGEABLE TICKET", "REFUNDS ANYTIME"], "ECONOMY")

print(upsold)