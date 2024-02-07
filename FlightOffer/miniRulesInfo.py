def getMiniRulesInfo(offer, refundableTicket, changeableTicket):
    amenities = [
         {
            "amenity_description": "EXCHANGE",
            "included": False,
            "penalty": "0.0",
            "isRequested": changeableTicket
         },
         {
            "amenity_description": "REFUND",
            "included": False,
            "penalty": "0.0",
            "isRequested":refundableTicket
         }]
    
    if "fareRules" in offer:
        for rule in offer["fareRules"]["rules"]:
            for amenity in amenities:
                if rule["category"] == amenity["amenity_description"]:
                    if "maxPenaltyAmount" in rule:
                        amenity["penalty"] = rule["maxPenaltyAmount"]
                        amenity["included"] = True
    
    return {"offer": offer, "amenities": amenities}

def convertMiniRulesAmenities(offer):
    amenities = offer["amenities"]
    for amenity in amenities:
        if amenity["amenity_description"] == "REFUND":
            amenity["amenity_description"] = "REFUNDABLE TICKET"
        elif amenity["amenity_description"] == "EXCHANGE":
            amenity["amenity_description"] = "CHANGEABLE TICKET"

        if float(amenity["penalty"]) > 0.0:
            amenity["isChargeable"] = True
        else:
            amenity["isChargeable"] = False

        del amenity["penalty"]

    offer["amenities"] = amenities

    return offer

"""
offers = [{'type': 'flight-offer', 'id': '1', 'source': 'LTC', 'instantTicketingRequired': True, 'nonHomogeneous': False, 'oneWay': False, 'lastTicketingDate': '2024-02-07', 'lastTicketingDateTime': '2024-02-07', 'numberOfBookableSeats': 9, 'itineraries': [{'duration': 'PT2H15M', 'segments': [{'departure': {'iataCode': 'VCE', 'at': '2024-03-01T21:45:00'}, 'arrival': {'iataCode': 'STN', 'at': '2024-03-01T23:00:00'}, 'carrierCode': 'FR', 'number': '799', 'aircraft': {'code': '738'}, 'operating': {'carrierCode': 'FR'}, 'id': '5', 'numberOfStops': 0, 'blacklistedInEU': False}]}, {'duration': 'PT2H', 'segments': [{'departure': {'iataCode': 'STN', 'at': '2024-03-10T05:55:00'}, 'arrival': {'iataCode': 'VCE', 'at': '2024-03-10T08:55:00'}, 'carrierCode': 'FR', 'number': '792', 'aircraft': {'code': '7M8'}, 'operating': {'carrierCode': 'FR'}, 'id': '6', 'numberOfStops': 0, 'blacklistedInEU': False}]}], 'price': {'currency': 'EUR', 'total': '65.98', 'base': '65.98', 'fees': [{'amount': '0.00', 'type': 'SUPPLIER'}, {'amount': '0.00', 'type': 'TICKETING'}], 'grandTotal': '65.98'}, 'pricingOptions': {'fareType': ['PUBLISHED'], 'includedCheckedBagsOnly': False}, 'validatingAirlineCodes': ['FR'], 'travelerPricings': [{'travelerId': '1', 'fareOption': 'STANDARD', 'travelerType': 'ADULT', 'price': {'currency': 'EUR', 'total': '65.98', 'base': '65.98'}, 'fareDetailsBySegment': [{'segmentId': '5', 'cabin': 'ECONOMY', 'fareBasis': 'TZ6LOW', 'class': 'Y', 'includedCheckedBags': {'quantity': 0}}, {'segmentId': '6', 'cabin': 'ECONOMY', 'fareBasis': 'TZ6LOW', 'class': 'Y', 'includedCheckedBags': {'quantity': 0}}]}]}]

for offer in offers:
    rulesInfoOffer = getMiniRulesInfo(offer, True, True)
    offerWithAmenities = convertMiniRulesAmnities(rulesInfoOffer)
    print(offerWithAmenities)
"""
