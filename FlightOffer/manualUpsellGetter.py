import json
import requests
import sys
import os
sys.path.append("../")
import keys

def get_access_token(api_key=keys.amadeus_client_id_personal, api_secret=keys.amadeus_client_secret_personal):
    auth_url = 'https://api.amadeus.com/v1/security/oauth2/token'
    #auth_url = 'https://test.travel.api.amadeus.com/v1/security/oauth2/token'

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
    url = 'https://api.amadeus.com/v1/shopping/flight-offers/upselling'
    #url = 'https://test.travel.api.amadeus.com/v1/shopping/flight-offers/upselling'

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
offer =  {'type': 'flight-offer', 'id': '15', 'source': 'GDS', 'instantTicketingRequired': False, 'nonHomogeneous': False, 'paymentCardRequired': False, 'lastTicketingDate': '2024-02-04', 'itineraries': [{'segments': [{'departure': {'iataCode': 'GRZ', 'at': '2024-06-14T09:40:00'}, 'arrival': {'iataCode': 'MUC', 'terminal': '2', 'at': '2024-06-14T10:30:00'}, 'carrierCode': 'LH', 'number': '2341', 'aircraft': {'code': 'E95'}, 'operating': {'carrierCode': 'LH'}, 'duration': 'PT50M', 'id': '19', 'numberOfStops': 0, 'co2Emissions': [{'weight': 68, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}, {'departure': {'iataCode': 'MUC', 'terminal': '2', 'at': '2024-06-14T11:30:00'}, 'arrival': {'iataCode': 'ORD', 'terminal': '5', 'at': '2024-06-14T14:00:00'}, 'carrierCode': 'LH', 'number': '9268', 'aircraft': {'code': '787'}, 'operating': {'carrierCode': 'UA'}, 'duration': 'PT9H30M', 'id': '20', 'numberOfStops': 0, 'co2Emissions': [{'weight': 383, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}, {'departure': {'iataCode': 'ORD', 'terminal': '1', 'at': '2024-06-14T20:00:00'}, 'arrival': {'iataCode': 'MEM', 'at': '2024-06-14T21:54:00'}, 'carrierCode': 'LH', 'number': '8820', 'aircraft': {'code': '73G'}, 'operating': {'carrierCode': 'UA'}, 'duration': 'PT1H54M', 'id': '21', 'numberOfStops': 0, 'co2Emissions': [{'weight': 113, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}]}, {'segments': [{'departure': {'iataCode': 'MEM', 'at': '2024-06-24T16:55:00'}, 'arrival': {'iataCode': 'ORD', 'terminal': '2', 'at': '2024-06-24T18:50:00'}, 'carrierCode': 'LH', 'number': '7551', 'aircraft': {'code': 'CR7'}, 'operating': {'carrierCode': 'UA'}, 'duration': 'PT1H55M', 'id': '79', 'numberOfStops': 0, 'co2Emissions': [{'weight': 114, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}, {'departure': {'iataCode': 'ORD', 'terminal': '1', 'at': '2024-06-24T22:30:00'}, 'arrival': {'iataCode': 'FRA', 'terminal': '1', 'at': '2024-06-25T14:05:00'}, 'carrierCode': 'LH', 'number': '433', 'aircraft': {'code': '343'}, 'operating': {'carrierCode': 'LH'}, 'duration': 'PT8H35M', 'id': '80', 'numberOfStops': 0, 'co2Emissions': [{'weight': 376, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}, {'departure': {'iataCode': 'FRA', 'terminal': '1', 'at': '2024-06-25T16:40:00'}, 'arrival': {'iataCode': 'GRZ', 'at': '2024-06-25T18:00:00'}, 'carrierCode': 'LH', 'number': '6928', 'aircraft': {'code': 'E95'}, 'operating': {'carrierCode': 'EN'}, 'duration': 'PT1H20M', 'id': '81', 'numberOfStops': 0, 'co2Emissions': [{'weight': 86, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}]}], 'price': {'currency': 'EUR', 'total': '927.97', 'base': '522.00', 'fees': [{'amount': '0.00', 'type': 'SUPPLIER'}, {'amount': '0.00', 'type': 'TICKETING'}, {'amount': '0.00', 'type': 'FORM_OF_PAYMENT'}], 'grandTotal': '927.97', 'billingCurrency': 'EUR'}, 'pricingOptions': {'fareType': ['PUBLISHED'], 'includedCheckedBagsOnly': False}, 'validatingAirlineCodes': ['LH'], 'travelerPricings': [{'travelerId': '1', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '927.97', 'base': '522.00', 'taxes': [{'amount': '10.00', 'code': 'DE'}, {'amount': '6.46', 'code': 'XY'}, {'amount': '3.54', 'code': 'XA'}, {'amount': '6.44', 'code': 'YC'}, {'amount': '4.16', 'code': 'XF'}, {'amount': '44.40', 'code': 'RA'}, {'amount': '18.81', 'code': 'AT'}, {'amount': '12.00', 'code': 'QD'}, {'amount': '211.00', 'code': 'YQ'}, {'amount': '10.34', 'code': 'AY'}, {'amount': '17.50', 'code': 'YR'}, {'amount': '40.98', 'code': 'US'}, {'amount': '20.34', 'code': 'ZY'}], 'refundableTaxes': '132.33'}, 'fareDetailsBySegment': [{'segmentId': '19', 'cabin': 'ECONOMY', 'fareBasis': 'TMPMF8BQ', 'brandedFare': 'ECOLIGHT', 'class': 'T', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '20', 'cabin': 'ECONOMY', 'fareBasis': 'TMPMF8BQ', 'brandedFare': 'ECOLIGHT', 'class': 'T', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '21', 'cabin': 'ECONOMY', 'fareBasis': 'TMPMF8BQ', 'brandedFare': 'ECOLIGHT', 'class': 'T', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '79', 'cabin': 'ECONOMY', 'fareBasis': 'SMPMD8BQ', 'brandedFare': 'ECOLIGHT', 'class': 'S', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '80', 'cabin': 'ECONOMY', 'fareBasis': 'SMPMD8BQ', 'brandedFare': 'ECOLIGHT', 'class': 'S', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '81', 'cabin': 'ECONOMY', 'fareBasis': 'SMPMD8BQ', 'brandedFare': 'ECOLIGHT', 'class': 'S', 'includedCheckedBags': {'quantity': 0}}]}]}

upsold = get_upsell_offer(get_access_token(), offer, ["REFUNDABLE TICKET", "CHANGEABLE TICKET", "REFUNDS ANYTIME"], "ECONOMY")

print(upsold)