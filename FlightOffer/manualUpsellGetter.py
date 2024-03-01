import json
import requests
import sys
import os
sys.path.append("../")
import keys

class ExitLoop(Exception):
    pass

def get_access_token(api_key=keys.amadeus_client_id, api_secret=keys.amadeus_client_secret):
    auth_url = 'https://travel.api.amadeus.com/v1/security/oauth2/token'
    #auth_url = 'https://test.travel.api.amadeus.com/v1/security/oauth2/token'

    response = requests.post(auth_url, data={
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': api_secret
    })
    print("Access key:\n", response.json())
    return response.json().get('access_token')

def get_upsell_offers(access_token, flight_offers):
    url = 'https://travel.api.amadeus.com/v1/shopping/flight-offers/upselling'
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
        return res["data"]
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None
    

def getFareByDetail(upsell_offers, checkedBags, refundable, changeable):
    amenities = {}
    for offer in upsell_offers:
        try:
            for travelerPricing in offer["travelerPricings"]:
                for segment in travelerPricing["fareDetailsBySegment"]:
                    if segment["includedCheckedBags"]["quantity"] != checkedBags:
                        raise ExitLoop
                    refundabilityStage = 0
                    changeabilityStage = 0
                    for amenity in segment["amenities"]:
                        if amenity["description"] in ["CHANGE AFTER DEPARTURE", "CHANGE BEFORE DEPARTURE"] and changeabilityStage != 2:
                            amenities[amenity["description"]] = {"isChargeable": amenity["isChargeable"], "isRequested": False}
                            changeabilityStage += 1
                        if amenity["description"] in ["CHANGEABLE TICKET"]:
                            amenities[amenity["description"]] = {"isChargeable": amenity["isChargeable"], "isRequested": False}
                            changeabilityStage = 2
                        if amenity["description"] in ["REFUNDS ANYTIME", "REFUNDABLE TICKET", "REFUND BEFORE DEPARTURE"]:
                            amenities[amenity["description"]] = {"isChargeable": amenity["isChargeable"], "isRequested": False}
                            refundabilityStage = 2
                    if (refundable and refundabilityStage < 2) or (changeable and changeabilityStage < 2) or (not refundable and refundabilityStage >= 2) or (not changeable and changeabilityStage >= 2):
                        raise ExitLoop
        except ExitLoop:
            continue
        return {"fare": offer, "amenities": amenities}
    return None

offer =  {'type': 'flight-offer', 'id': '1', 'source': 'GDS', 'instantTicketingRequired': False, 'nonHomogeneous': False, 'oneWay': False, 'lastTicketingDate': '2024-03-01', 'lastTicketingDateTime': '2024-03-01', 'numberOfBookableSeats': 9, 'itineraries': [{'duration': 'PT4H25M', 'segments': [{'departure': {'iataCode': 'VCE', 'at': '2024-06-08T07:00:00'}, 'arrival': {'iataCode': 'ZRH', 'at': '2024-06-08T08:05:00'}, 'carrierCode': 'LX', 'number': '1667', 'aircraft': {'code': '223'}, 'operating': {'carrierCode': 'LX'}, 'id': '11', 'numberOfStops': 0, 'blacklistedInEU': False}, {'departure': {'iataCode': 'ZRH', 'at': '2024-06-08T09:00:00'}, 'arrival': {'iataCode': 'ARN', 'terminal': '5', 'at': '2024-06-08T11:25:00'}, 'carrierCode': 'LX', 'number': '1252', 'aircraft': {'code': '223'}, 'operating': {'carrierCode': 'LX'}, 'id': '12', 'numberOfStops': 0, 'blacklistedInEU': False}]}, {'duration': 'PT5H30M', 'segments': [{'departure': {'iataCode': 'ARN', 'terminal': '5', 'at': '2024-06-13T17:30:00'}, 'arrival': {'iataCode': 'BRU', 'at': '2024-06-13T19:50:00'}, 'carrierCode': 'SN', 'number': '2294', 'aircraft': {'code': '319'}, 'operating': {'carrierCode': 'SN'}, 'id': '41', 'numberOfStops': 0, 'blacklistedInEU': False}, {'departure': {'iataCode': 'BRU', 'at': '2024-06-13T21:20:00'}, 'arrival': {'iataCode': 'VCE', 'at': '2024-06-13T23:00:00'}, 'carrierCode': 'SN', 'number': '3207', 'aircraft': {'code': '320'}, 'operating': {'carrierCode': 'SN'}, 'id': '42', 'numberOfStops': 0, 'blacklistedInEU': False}]}], 'price': {'currency': 'EUR', 'total': '297.45', 'base': '149.00', 'fees': [{'amount': '0.00', 'type': 'SUPPLIER'}, {'amount': '0.00', 'type': 'TICKETING'}], 'grandTotal': '297.45'}, 'pricingOptions': {'fareType': ['PUBLISHED'], 'includedCheckedBagsOnly': True}, 'validatingAirlineCodes': ['LX'], 'travelerPricings': [{'travelerId': '1', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '297.45', 'base': '149.00'}, 'fareDetailsBySegment': [{'segmentId': '11', 'cabin': 'ECONOMY', 'fareBasis': 'KETCLSE3', 'class': 'K', 'includedCheckedBags': {'quantity': 1}, 'includedCabinBags': {'quantity': 1}}, {'segmentId': '12', 'cabin': 'ECONOMY', 'fareBasis': 'KETCLSE3', 'class': 'K', 'includedCheckedBags': {'quantity': 1}, 'includedCabinBags': {'quantity': 1}}, {'segmentId': '41', 'cabin': 'ECONOMY', 'fareBasis': 'SETCLSE3', 'class': 'S', 'includedCheckedBags': {'quantity': 1}, 'includedCabinBags': {'quantity': 1}}, {'segmentId': '42', 'cabin': 'ECONOMY', 'fareBasis': 'SETCLSE3', 'class': 'S', 'includedCheckedBags': {'quantity': 1}, 'includedCabinBags': {'quantity': 1}}]}], 'fareRules': {'rules': [{'category': 'EXCHANGE', 'maxPenaltyAmount': '60.00'}, {'category': 'REFUND', 'notApplicable': True}, {'category': 'REVALIDATION', 'notApplicable': True}]}}
#offer =  {'type': 'flight-offer', 'id': '1', 'source': 'LTC', 'instantTicketingRequired': True, 'nonHomogeneous': False, 'paymentCardRequired': True, 'lastTicketingDate': '2024-02-28', 'itineraries': [{'segments': [{'departure': {'iataCode': 'DUB', 'at': '2024-06-22T17:00:00'}, 'arrival': {'iataCode': 'TRS', 'at': '2024-06-22T20:40:00'}, 'carrierCode': 'FR', 'number': '9319', 'aircraft': {'code': '738'}, 'operating': {'carrierCode': 'FR'}, 'duration': 'PT2H40M', 'id': '1', 'numberOfStops': 0, 'co2Emissions': [{'weight': 140, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}]}, {'segments': [{'departure': {'iataCode': 'TRS', 'at': '2024-06-29T21:05:00'}, 'arrival': {'iataCode': 'DUB', 'at': '2024-06-29T22:55:00'}, 'carrierCode': 'FR', 'number': '9320', 'aircraft': {'code': '738'}, 'operating': {'carrierCode': 'FR'}, 'duration': 'PT2H50M', 'id': '2', 'numberOfStops': 0, 'co2Emissions': [{'weight': 140, 'weightUnit': 'KG', 'cabin': 'ECONOMY'}]}]}], 'price': {'currency': 'EUR', 'total': '263.98', 'base': '257.98', 'fees': [{'amount': '0.00', 'type': 'SUPPLIER'}, {'amount': '0.00', 'type': 'TICKETING'}, {'amount': '0.00', 'type': 'FORM_OF_PAYMENT'}], 'grandTotal': '263.98', 'billingCurrency': 'EUR'}, 'pricingOptions': {'fareType': ['PUBLISHED'], 'includedCheckedBagsOnly': False}, 'validatingAirlineCodes': ['FR'], 'travelerPricings': [{'travelerId': '1', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '263.98', 'base': '257.98', 'taxes': [{'amount': '6.00', 'code': 'FD'}]}, 'fareDetailsBySegment': [{'segmentId': '1', 'fareBasis': 'KZ8LOW', 'brandedFare': 'BASIC', 'class': 'Y', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '2', 'fareBasis': 'PZ8LOW', 'brandedFare': 'BASIC', 'class': 'Y', 'includedCheckedBags': {'quantity': 0}}]}]}

upsell_offers = get_upsell_offers(get_access_token(), offer)

basic = getFareByDetail(upsell_offers, 0, refundable=False, changeable=False)
classic = getFareByDetail(upsell_offers, 1, refundable=False, changeable=True)
flex = getFareByDetail(upsell_offers, 1, refundable=True, changeable=True)

print("------BASIC------\n", basic)
print("------CLASSIC------\n", classic)
print("------FLEX------\n", flex)

is_basic_none = basic is not None
is_classic_none = classic is not None
is_flex_none = flex is not None
print("BASIC:", is_basic_none)
print("CLASSIC:", is_classic_none)
print("FLEX:", is_flex_none)