import json
import requests
import sys
import os
sys.path.append("../")
import keys

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


def getHigherClasses(travelClass):
    if travelClass == "ECONOMY":
      return ["PREMIUM_ECONOMY", "BUSINESS", "FIRST"]
    elif travelClass == "PREMIUM_ECONOMY":
      return ["BUSINESS", "FIRST"]
    elif travelClass == "BUSINESS":
      return ["FIRST"]
    elif travelClass == "FIRST":
      return []

def get_upsell_offer(access_token, flight_offers, amenities, travelClass, apiType):
    if apiType == "personal":
        url = 'https://api.amadeus.com/v1/shopping/flight-offers/upselling'
    else:
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
            for amenity in amenities:
                includedAmenities[amenity] = {"included": True, "isChargeable": False}
  
            for traveler in offer["travelerPricings"]:
                if wrongTravelClass:
                    break
                for segment in traveler["fareDetailsBySegment"]:
                    if segment["cabin"] in getHigherClasses(travelClass):
                        wrongTravelClass = True
                        break
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

            if wrongTravelClass:
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
    
offer = {'type': 'flight-offer', 'id': '4', 'source': 'GDS', 'instantTicketingRequired': False, 'nonHomogeneous': False, 'paymentCardRequired': False, 'lastTicketingDate': '2024-04-06', 'itineraries': [{'segments': [{'departure': {'iataCode': 'GRZ', 'at': '2024-04-20T14:00:00'}, 'arrival': {'iataCode': 'AMS', 'at': '2024-04-20T15:55:00'}, 'carrierCode': 'KL', 'number': '1910', 'aircraft': {'code': 'E7W'}, 'operating': {'carrierCode': 'KL'}, 'duration': 'PT1H55M', 'id': '28', 'numberOfStops': 0, 'co2Emissions': [{'weight': 140, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}, {'departure': {'iataCode': 'AMS', 'at': '2024-04-20T17:05:00'}, 'arrival': {'iataCode': 'ATL', 'terminal': 'I', 'at': '2024-04-20T20:20:00'}, 'carrierCode': 'KL', 'number': '621', 'aircraft': {'code': '77W'}, 'operating': {'carrierCode': 'KL'}, 'duration': 'PT9H15M', 'id': '29', 'numberOfStops': 0, 'co2Emissions': [{'weight': 369, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}, {'departure': {'iataCode': 'ATL', 'terminal': 'S', 'at': '2024-04-20T22:55:00'}, 'arrival': {'iataCode': 'PHX', 'terminal': '3', 'at': '2024-04-21T00:10:00'}, 'carrierCode': 'KL', 'number': '5162', 'aircraft': {'code': '321'}, 'operating': {'carrierCode': 'DL'}, 'duration': 'PT4H15M', 'id': '30', 'numberOfStops': 0, 'co2Emissions': [{'weight': 199, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}]}, {'segments': [{'departure': {'iataCode': 'PHX', 'terminal': '3', 'at': '2024-05-05T10:05:00'}, 'arrival': {'iataCode': 'SLC', 'at': '2024-05-05T12:43:00'}, 'carrierCode': 'AF', 'number': '2722', 'aircraft': {'code': '321'}, 'operating': {'carrierCode': 'DL'}, 'duration': 'PT1H38M', 'id': '115', 'numberOfStops': 0, 'co2Emissions': [{'weight': 97, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}, {'departure': {'iataCode': 'SLC', 'at': '2024-05-05T16:05:00'}, 'arrival': {'iataCode': 'AMS', 'at': '2024-05-06T10:00:00'}, 'carrierCode': 'AF', 'number': '8945', 'aircraft': {'code': '339'}, 'operating': {'carrierCode': 'DL'}, 'duration': 'PT9H55M', 'id': '116', 'numberOfStops': 0, 'co2Emissions': [{'weight': 385, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}, {'departure': {'iataCode': 'AMS', 'at': '2024-05-06T11:50:00'}, 'arrival': {'iataCode': 'GRZ', 'at': '2024-05-06T13:30:00'}, 'carrierCode': 'KL', 'number': '1909', 'aircraft': {'code': 'E7W'}, 'operating': {'carrierCode': 'KL'}, 'duration': 'PT1H40M', 'id': '117', 'numberOfStops': 0, 'co2Emissions': [{'weight': 140, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}]}], 'price': {'currency': 'EUR', 'total': '3038.52', 'base': '1632.00', 'fees': [{'amount': '0.00', 'type': 'SUPPLIER'}, {'amount': '0.00', 'type': 'TICKETING'}, {'amount': '0.00', 'type': 'FORM_OF_PAYMENT'}], 'grandTotal': '3038.52', 'billingCurrency': 'EUR'}, 'pricingOptions': {'fareType': ['PUBLISHED'], 'includedCheckedBagsOnly': False}, 'validatingAirlineCodes': ['AF'], 'travelerPricings': [{'travelerId': '1', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '1012.84', 'base': '544.00', 'taxes': [{'amount': '6.40', 'code': 'XY'}, {'amount': '19.08', 'code': 'CJ'}, {'amount': '3.50', 'code': 'XA'}, {'amount': '6.37', 'code': 'YC'}, {'amount': '4.12', 'code': 'XF'}, {'amount': '18.81', 'code': 'AT'}, {'amount': '12.00', 'code': 'QD'}, {'amount': '63.00', 'code': 'YQ'}, {'amount': '10.24', 'code': 'AY'}, {'amount': '243.00', 'code': 'YR'}, {'amount': '21.40', 'code': 'RN'}, {'amount': '40.58', 'code': 'US'}, {'amount': '20.34', 'code': 'ZY'}], 'refundableTaxes': '256.64'}, 'fareDetailsBySegment': [{'segmentId': '28', 'cabin': 'ECONOMY', 'fareBasis': 'QYL0TALA', 'brandedFare': 'LIGHT', 'class': 'L', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '29', 'cabin': 'ECONOMY', 'fareBasis': 'QYL0TALA', 'brandedFare': 'LIGHT', 'class': 'Q', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '30', 'cabin': 'ECONOMY', 'fareBasis': 'QYL0TALA', 'brandedFare': 'LIGHT', 'class': 'Q', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '115', 'cabin': 'ECONOMY', 'fareBasis': 'RYL8TALA', 'brandedFare': 'LIGHT', 'class': 'R', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '116', 'cabin': 'ECONOMY', 'fareBasis': 'RYL8TALA', 'brandedFare': 'LIGHT', 'class': 'R', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '117', 'cabin': 'ECONOMY', 'fareBasis': 'RYL8TALA', 'brandedFare': 'LIGHT', 'class': 'L', 'includedCheckedBags': {'quantity': 0}}]}, {'travelerId': '2', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '1012.84', 'base': '544.00', 'taxes': [{'amount': '6.40', 'code': 'XY'}, {'amount': '19.08', 'code': 'CJ'}, {'amount': '3.50', 'code': 'XA'}, {'amount': '6.37', 'code': 'YC'}, {'amount': '4.12', 'code': 'XF'}, {'amount': '18.81', 'code': 'AT'}, {'amount': '12.00', 'code': 'QD'}, {'amount': '63.00', 'code': 'YQ'}, {'amount': '10.24', 'code': 'AY'}, {'amount': '243.00', 'code': 'YR'}, {'amount': '21.40', 'code': 'RN'}, {'amount': '40.58', 'code': 'US'}, {'amount': '20.34', 'code': 'ZY'}], 'refundableTaxes': '256.64'}, 'fareDetailsBySegment': [{'segmentId': '28', 'cabin': 'ECONOMY', 'fareBasis': 'QYL0TALA', 'brandedFare': 'LIGHT', 'class': 'L', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '29', 'cabin': 'ECONOMY', 'fareBasis': 'QYL0TALA', 'brandedFare': 'LIGHT', 'class': 'Q', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '30', 'cabin': 'ECONOMY', 'fareBasis': 'QYL0TALA', 'brandedFare': 'LIGHT', 'class': 'Q', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '115', 'cabin': 'ECONOMY', 'fareBasis': 'RYL8TALA', 'brandedFare': 'LIGHT', 'class': 'R', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '116', 'cabin': 'ECONOMY', 'fareBasis': 'RYL8TALA', 'brandedFare': 'LIGHT', 'class': 'R', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '117', 'cabin': 'ECONOMY', 'fareBasis': 'RYL8TALA', 'brandedFare': 'LIGHT', 'class': 'L', 'includedCheckedBags': {'quantity': 0}}]}, {'travelerId': '3', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '1012.84', 'base': '544.00', 'taxes': [{'amount': '6.40', 'code': 'XY'}, {'amount': '19.08', 'code': 'CJ'}, {'amount': '3.50', 'code': 'XA'}, {'amount': '6.37', 'code': 'YC'}, {'amount': '4.12', 'code': 'XF'}, {'amount': '18.81', 'code': 'AT'}, {'amount': '12.00', 'code': 'QD'}, {'amount': '63.00', 'code': 'YQ'}, {'amount': '10.24', 'code': 'AY'}, {'amount': '243.00', 'code': 'YR'}, {'amount': '21.40', 'code': 'RN'}, {'amount': '40.58', 'code': 'US'}, {'amount': '20.34', 'code': 'ZY'}], 'refundableTaxes': '256.64'}, 'fareDetailsBySegment': [{'segmentId': '28', 'cabin': 'ECONOMY', 'fareBasis': 'QYL0TALA', 'brandedFare': 'LIGHT', 'class': 'L', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '29', 'cabin': 'ECONOMY', 'fareBasis': 'QYL0TALA', 'brandedFare': 'LIGHT', 'class': 'Q', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '30', 'cabin': 'ECONOMY', 'fareBasis': 'QYL0TALA', 'brandedFare': 'LIGHT', 'class': 'Q', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '115', 'cabin': 'ECONOMY', 'fareBasis': 'RYL8TALA', 'brandedFare': 'LIGHT', 'class': 'R', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '116', 'cabin': 'ECONOMY', 'fareBasis': 'RYL8TALA', 'brandedFare': 'LIGHT', 'class': 'R', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '117', 'cabin': 'ECONOMY', 'fareBasis': 'RYL8TALA', 'brandedFare': 'LIGHT', 'class': 'L', 'includedCheckedBags': {'quantity': 0}}]}]}

upsold = get_upsell_offer(get_access_token(keys.amadeus_client_id, keys.amadeus_client_secret), offer, ["REFUNDABLE TICKET", "CHANGEABLE TICKET", "REFUNDS ANYTIME"], "ECONOMY")

print(upsold)