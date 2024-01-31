import json
import requests
import sys
import os
sys.path.append("../")
import keys

def get_access_token(api_key=keys.amadeus_client_id_personal, api_secret=keys.amadeus_client_secret_personal):
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

def get_upsell_offer(access_token, flight_offers, amenities, travelClass):
    url = 'https://api.amadeus.com/v1/shopping/flight-offers/upselling'

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
    
offer = {'type': 'flight-offer', 'id': '4', 'source': 'GDS', 'instantTicketingRequired': False, 'nonHomogeneous': False, 'paymentCardRequired': False, 'lastTicketingDate': '2024-02-02', 'itineraries': [{'segments': [{'departure': {'iataCode': 'VIE', 'terminal': '3', 'at': '2024-03-09T09:35:00'}, 'arrival': {'iataCode': 'AGP', 'at': '2024-03-09T12:55:00'}, 'carrierCode': 'OS', 'number': '385', 'aircraft': {'code': '320'}, 'operating': {'carrierCode': 'OS'}, 'duration': 'PT3H20M', 'id': '11', 'numberOfStops': 0, 'co2Emissions': [{'weight': 165, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}]}, {'segments': [{'departure': {'iataCode': 'AGP', 'at': '2024-03-16T13:40:00'}, 'arrival': {'iataCode': 'VIE', 'terminal': '3', 'at': '2024-03-16T16:50:00'}, 'carrierCode': 'OS', 'number': '386', 'aircraft': {'code': '320'}, 'operating': {'carrierCode': 'OS'}, 'duration': 'PT3H10M', 'id': '62', 'numberOfStops': 0, 'co2Emissions': [{'weight': 165, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}]}], 'price': {'currency': 'EUR', 'total': '1213.47', 'base': '894.00', 'fees': [{'amount': '0.00', 'type': 'SUPPLIER'}, {'amount': '0.00', 'type': 'TICKETING'}, {'amount': '0.00', 'type': 'FORM_OF_PAYMENT'}], 'grandTotal': '1213.47', 'billingCurrency': 'EUR'}, 'pricingOptions': {'fareType': ['PUBLISHED'], 'includedCheckedBagsOnly': True}, 'validatingAirlineCodes': ['OS'], 'travelerPricings': [{'travelerId': '1', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '404.49', 'base': '298.00', 'taxes': [{'amount': '10.28', 'code': 'AT'}, {'amount': '12.00', 'code': 'QD'}, {'amount': '3.27', 'code': 'QV'}, {'amount': '34.00', 'code': 'YQ'}, {'amount': '0.63', 'code': 'OG'}, {'amount': '17.50', 'code': 'YR'}, {'amount': '6.42', 'code': 'JD'}, {'amount': '22.39', 'code': 'ZY'}], 'refundableTaxes': '54.99'}, 'fareDetailsBySegment': [{'segmentId': '11', 'cabin': 'ECONOMY', 'fareBasis': 'SEUCLSP4', 'brandedFare': 'CLASSIC', 'class': 'S', 'includedCheckedBags': {'quantity': 1}}, {'segmentId': '62', 'cabin': 'ECONOMY', 'fareBasis': 'SEUCLSP4', 'brandedFare': 'CLASSIC', 'class': 'S', 'includedCheckedBags': {'quantity': 1}}]}, {'travelerId': '2', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '404.49', 'base': '298.00', 'taxes': [{'amount': '10.28', 'code': 'AT'}, {'amount': '12.00', 'code': 'QD'}, {'amount': '3.27', 'code': 'QV'}, {'amount': '34.00', 'code': 'YQ'}, {'amount': '0.63', 'code': 'OG'}, {'amount': '17.50', 'code': 'YR'}, {'amount': '6.42', 'code': 'JD'}, {'amount': '22.39', 'code': 'ZY'}], 'refundableTaxes': '54.99'}, 'fareDetailsBySegment': [{'segmentId': '11', 'cabin': 'ECONOMY', 'fareBasis': 'SEUCLSP4', 'brandedFare': 'CLASSIC', 'class': 'S', 'includedCheckedBags': {'quantity': 1}}, {'segmentId': '62', 'cabin': 'ECONOMY', 'fareBasis': 'SEUCLSP4', 'brandedFare': 'CLASSIC', 'class': 'S', 'includedCheckedBags': {'quantity': 1}}]}, {'travelerId': '3', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '404.49', 'base': '298.00', 'taxes': [{'amount': '10.28', 'code': 'AT'}, {'amount': '12.00', 'code': 'QD'}, {'amount': '3.27', 'code': 'QV'}, {'amount': '34.00', 'code': 'YQ'}, {'amount': '0.63', 'code': 'OG'}, {'amount': '17.50', 'code': 'YR'}, {'amount': '6.42', 'code': 'JD'}, {'amount': '22.39', 'code': 'ZY'}], 'refundableTaxes': '54.99'}, 'fareDetailsBySegment': [{'segmentId': '11', 'cabin': 'ECONOMY', 'fareBasis': 'SEUCLSP4', 'brandedFare': 'CLASSIC', 'class': 'S', 'includedCheckedBags': {'quantity': 1}}, {'segmentId': '62', 'cabin': 'ECONOMY', 'fareBasis': 'SEUCLSP4', 'brandedFare': 'CLASSIC', 'class': 'S', 'includedCheckedBags': {'quantity': 1}}]}]}

upsold = get_upsell_offer(get_access_token(), offer, ["REFUNDABLE TICKET", "CHANGEABLE TICKET", "REFUNDS ANYTIME"], "ECONOMY")

print(upsold)