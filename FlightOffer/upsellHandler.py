import math
import traceback
import requests
import flightSearch
from Auxiliary.verbose_checkpoint import verbose

def getHigherClasses(travelClass):
    if travelClass == "ECONOMY":
        return ["PREMIUM_ECONOMY", "BUSINESS", "FIRST"]
    elif travelClass == "PREMIUM_ECONOMY":
        return ["BUSINESS", "FIRST"]
    elif travelClass == "BUSINESS":
        return ["FIRST"]
    elif travelClass == "FIRST":
        return []
    else:
        return []

def get_upsell_offer(access_token, flight_offers, amenities, travelClass, checkedBags, apiType, verbose_checkpoint=None):
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

        res["data"].insert(0, flight_offers[0])
        print(f"All upsell offers: {len(res['data'])}")
        #print(f"Upsell offers with correct amount of included checked bags ({checkedBags}): {len(offersWithAmenityCount)}")

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
                    if "cabin" in segment:
                        if segment["cabin"] in getHigherClasses(travelClass):
                            wrongTravelClass = True
                            break
                    for includedAmenity in includedAmenities:
                        amenityFoundInSegment = False
                        isChargeable = False
                        if "amenities" not in segment:
                            includedAmenities[includedAmenity]["included"] = False
                            continue
                        for amenity in segment["amenities"]:
                            if amenity["description"] == includedAmenity:
                                amenityFoundInSegment = True
                                if not isChargeable:
                                    isChargeable = amenity["isChargeable"]
                                break
                            
                        includedAmenities[includedAmenity]["isChargeable"] = isChargeable
                        if not amenityFoundInSegment:
                            includedAmenities[includedAmenity]["included"] = False

            if wrongTravelClass:
                continue
            
            print(f"included amenities: {includedAmenities}")
            verbose(f"included amenities: {includedAmenities}", verbose_checkpoint)

            amenityCount = 0
            refundFound = False
            changeFound = False
            for amenity_ in includedAmenities.keys():
                if includedAmenities[amenity_]["included"] and includedAmenities[amenity_]["isRequested"]:
                    if amenity_ in ["REFUNDABLE TICKET", "REFUND BEFORE DEPARTURE", "REFUND AFTER DEPARTURE", "REFUNDS ANYTIME"]:
                        if not refundFound:
                            refundFound = True
                            amenityCount += 1
                    elif amenity_ in ["CHANGEABLE TICKET", "CHANGE BEFORE DEPARTURE", "CHANGE AFTER DEPARTURE"]:
                        if not changeFound:
                            changeFound = True
                            amenityCount += 1
                    else:
                        amenityCount += 1

            #amenityCount = sum(value["included"] is True and value["isRequested"] is True for value in includedAmenities.values())
            for index, offer_ in enumerate(offersWithAmenityCount):
                if offer == offer_["offer"]:
                    offersWithAmenityCount[index]["amenityCount"] = amenityCount
                    print("offer found on index:", index)
                    print("amenity count:", amenityCount)
                    for includedAmenity_ in includedAmenities.keys():
                        print("amenity key:", {"amenity_description": includedAmenity_, "included": includedAmenities[includedAmenity_]["included"], "isChargeable": includedAmenities[includedAmenity_]["isChargeable"], "isRequested": includedAmenities[includedAmenity_]["isRequested"]})
                        #if includedAmenities[includedAmenity_]["included"] == True:
                        offersWithAmenityCount[index]["amenities"].append({"amenity_description": includedAmenity_, "included": includedAmenities[includedAmenity_]["included"], "isChargeable": includedAmenities[includedAmenity_]["isChargeable"], "isRequested": includedAmenities[includedAmenity_]["isRequested"]})
        sorted_offers = sorted(offersWithAmenityCount, key=lambda x: x["amenityCount"], reverse=True)
        
        new_sorted_offers = []
        for sorted_offer in sorted_offers:
            wrongTravelClass = False
            includedBagsInSegment = math.inf
            for traveler in sorted_offer["offer"]["travelerPricings"]:
                for segment in traveler["fareDetailsBySegment"]:
                    if "quantity" in segment["includedCheckedBags"]:
                        if segment["includedCheckedBags"]["quantity"] <= includedBagsInSegment:
                            includedBagsInSegment = segment["includedCheckedBags"]["quantity"]
                    else:
                        includedBagsInSegment = 1

            if includedBagsInSegment >= checkedBags:
                new_sorted_offers.append({"offer": sorted_offer["offer"], "amenityCount": sorted_offer["amenityCount"], "amenities": sorted_offer["amenities"]})


        #print("----------------------------")
        #print("Compare offers")
        #print("new sorted offers:\n", new_sorted_offers)
        #print("old sorted offers:\n", sorted_offers)
        #print("----------------------------")

        if len(new_sorted_offers) <= 0:
            new_sorted_offers = sorted_offers

        #if sorted_offers[0]["amenityCount"] == 0:
        #    return None
        #else:
        return new_sorted_offers[0]
        
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None

def getUpsellOffers(offers, get_price_offer, travelClass, refundableTicket, changeableTicket, checkedBags, access_token, apiType, verbose_checkpoint=None):
    for index, offer in enumerate(offers):
        print("----------------------------")
        print("offer to get upsell for:\n", offer)

        amenitiesToSearchFor = [{"amenity_description": "REFUNDABLE TICKET", "isRequested": False},
                                {"amenity_description": "REFUND BEFORE DEPARTURE", "isRequested": False},
                                {"amenity_description": "REFUND AFTER DEPARTURE", "isRequested": False},
                                {"amenity_description": "REFUNDS ANYTIME", "isRequested": False},
                                {"amenity_description": "CHANGE BEFORE DEPARTURE", "isRequested": False},
                                {"amenity_description": "CHANGE AFTER DEPARTURE", "isRequested": False},
                                {"amenity_description": "CHANGEABLE TICKET", "isRequested": False}]
        
        for index1, amenity in enumerate(amenitiesToSearchFor):
            if (amenity["amenity_description"] == "REFUNDABLE TICKET" or amenity["amenity_description"] == "REFUNDS ANYTIME" or amenity["amenity_description"] == "REFUND BEFORE DEPARTURE" or amenity["amenity_description"] == "REFUND AFTER DEPARTURE") and refundableTicket:
                amenity["isRequested"] = True
                amenitiesToSearchFor[index1] = amenity

            if (amenity["amenity_description"] == "CHANGEABLE TICKET" or amenity["amenity_description"] == "CHANGE BEFORE DEPARTURE" or amenity["amenity_description"] == "CHANGE AFTER DEPARTURE") and changeableTicket:
                amenity["isRequested"] = True
                amenitiesToSearchFor[index1] = amenity
        
        upsold = get_upsell_offer(access_token, [offer], amenitiesToSearchFor, travelClass, checkedBags, apiType, verbose_checkpoint) #CHANGEABLE TICKET

        if upsold != None:
            print(f"UPSOLD OFFER: {upsold['offer']}")
            print(f"AMENITIES OF UPSOLD OFFER: {upsold['amenities']}")
            verbose(f"AMENITIES OF UPSOLD OFFER: {upsold['amenities']}", verbose_checkpoint)
        
            if len(upsold["amenities"]) > 0:
                try:
                    upsold_price_offer = get_price_offer(access_token, [upsold["offer"]])["data"]["flightOffers"][0]
                    offers[index] = {"offer": upsold_price_offer, "amenities": upsold['amenities']}
                except Exception as e:
                    traceback_str = traceback.format_exc()
                    print(traceback_str)
                    includedAmenities = []
                    for amenity in amenitiesToSearchFor:
                        includedAmenities.append({"amenity_description": amenity["amenity_description"], "included": False, "isChargeable": False, "isRequested": amenity["isRequested"]})
                    
                    offers[index] = {"offer": offer, "amenities": includedAmenities}
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