import math
import requests
import flightSearch

def getHigherClasses(travelClass):
    if travelClass == "ECONOMY":
      return ["PREMIUM_ECONOMY", "BUSINESS", "FIRST"]
    elif travelClass == "PREMIUM_ECONOMY":
      return ["BUSINESS", "FIRST"]
    elif travelClass == "BUSINESS":
      return ["FIRST"]
    elif travelClass == "FIRST":
      return []

def get_upsell_offer(access_token, flight_offers, amenities, travelClass, checkedBags):
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
            'flightOffers': flight_offers 
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print('Flight Offers upsell information retrieved successfully!')
        res = response.json()
        #print(response.json())
        if "status" in res:
            if res["status"] == "400":
                return None
        
        offersWithAmenityCount = []
        #print(len(res["data"]))

        for offer in res["data"]:
            wrongTravelClass = False
            includedBagsInSegment = math.inf
            for traveler in offer["travelerPricings"]:
                if wrongTravelClass:
                    break
                for segment in traveler["fareDetailsBySegment"]:
                    if segment["cabin"] in getHigherClasses(travelClass):
                        wrongTravelClass = True
                        break
                    if "quantity" in segment["includedCheckedBags"]:
                        if segment["includedCheckedBags"]["quantity"] <= includedBagsInSegment:
                            includedBagsInSegment = segment["includedCheckedBags"]["quantity"]
                    else:
                        if includedBagsInSegment > 1:
                            includedBagsInSegment = 1

        if includedBagsInSegment == checkedBags:
            offersWithAmenityCount.append({"offer": offer, "amenityCount": 0, "amenities": []})

        print(f"All upsell offers: {len(res['data'])}")
        print(f"Upsell offers with correct amount of included checked bags ({checkedBags}): {len(offersWithAmenityCount)}")

        if len(offersWithAmenityCount) <= 0:
            print("No upsell offers with correct amount of included checked bags found.. using non optimal upsell offers")
            for offer in res["data"]:
                offersWithAmenityCount.append({"offer": offer, "amenityCount": 0, "amenities": []})

        for offer in res["data"]:
            includedAmenities = {}
            wrongTravelClass = False
            for amenity in amenities:
                includedAmenities[amenity["amenity_description"]] = {"included": True, "isChargeable": False, "isRequested": amenity["isRequested"]}
  
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
            amenityCount = sum(value["included"] is True and value["isRequested"] is True for value in includedAmenities.values())
            for index, offer_ in enumerate(offersWithAmenityCount):
                if offer == offer_["offer"]:
                    offersWithAmenityCount[index]["amenityCount"] = amenityCount
                    for includedAmenity_ in includedAmenities.keys():
                        #if includedAmenities[includedAmenity_]["included"] == True:
                        offersWithAmenityCount[index]["amenities"].append({"amenity_description": includedAmenity_, "included": includedAmenities[includedAmenity_]["included"], "isChargeable": includedAmenities[includedAmenity_]["isChargeable"], "isRequested": includedAmenities[includedAmenity_]["isRequested"]})
    
        sorted_offers = sorted(offersWithAmenityCount, key=lambda x: x["amenityCount"], reverse=True)

        #if sorted_offers[0]["amenityCount"] == 0:
        #    return None
        #else:
        return sorted_offers[0]
        
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None

def getUpsellOffers(offers, get_price_offer, travelClass, refundableTicket, changeableTicket, checkedBags, access_token):
    for index, offer in enumerate(offers):
        print("----------------------------")
        print("offer to get upsell for:\n", offer)

        amenitiesToSearchFor = [{"amenity_description": "REFUNDABLE TICKET", "isRequested": False},
                                {"amenity_description": "REFUNDS ANYTIME", "isRequested": False},
                                {"amenity_description": "CHANGEABLE TICKET", "isRequested": False}]
        
        for index1, amenity in enumerate(amenitiesToSearchFor):
            if (amenity["amenity_description"] == "REFUNDABLE TICKET" or amenity["amenity_description"] == "REFUNDS ANYTIME") and refundableTicket:
                amenity["isRequested"] = True
                amenitiesToSearchFor[index1] = amenity

            if amenity["amenity_description"] == "CHANGEABLE TICKET" and changeableTicket:
                amenity["isRequested"] = True
                amenitiesToSearchFor[index1] = amenity
        
        upsold = get_upsell_offer(access_token, [offer], amenitiesToSearchFor, travelClass, checkedBags) #CHANGEABLE TICKET

        if upsold != None:
            print(f"UPSOLD OFFER: {upsold['offer']}")
            print(f"AMENITIES OF UPSOLD OFFER: {upsold['amenities']}")
        
            if len(upsold["amenities"]) > 0:
                upsold_price_offer = get_price_offer(access_token, [upsold["offer"]])["data"]["flightOffers"][0]
                offers[index] = {"offer": upsold_price_offer, "amenities": upsold['amenities']}
            else:
                includedAmenities = []
                for amenity in amenitiesToSearchFor:
                    includedAmenities.append({"amenity_description": amenity["amenity_description"], "included": False, "isChargeable": False, "isRequested": amenity["isRequested"]})

                    offers[index] = {"offer": offer, "amenities": includedAmenities}
        else:
            includedAmenities = []
            for amenity in amenitiesToSearchFor:
                includedAmenities.append({"amenity_description": amenity["amenity_description"], "included": False, "isChargeable": False, "isRequested": amenity["isRequested"]})

            offers[index] = {"offer": offer, "amenities": includedAmenities}

        print("----------------------------")
    
    return offers