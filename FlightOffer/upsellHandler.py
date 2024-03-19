import math
import traceback
import requests
import flightSearch
from Auxiliary.verbose_checkpoint import verbose

class ExitLoop(Exception):
    pass

def get_upsell_offer(access_token, flight_offers, apiType, verbose_checkpoint=None):
    if apiType == "personal":
        url = 'https://api.amadeus.com/v1/shopping/flight-offers/upselling'
    else:
        url = 'https://travel.api.amadeus.com/v1/shopping/flight-offers/upselling'

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
        print(res)
        #print(response.json())
        if "status" in res:
            if res["status"] == "400":
                return None
        return res["data"]
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None

def getFareByDetail(upsell_offers, checkedBags, refundable, changeable):
    for offer in upsell_offers:
        try:
            amenities = {}
            for travelerPricing in offer["travelerPricings"]:
                for segment in travelerPricing["fareDetailsBySegment"]:
                    if "quantity" in segment["includedCheckedBags"]:
                        if segment["includedCheckedBags"]["quantity"] != checkedBags:
                            raise ExitLoop
                    elif "weight" in segment["includedCheckedBags"]:
                        if checkedBags != 1:
                            raise ExitLoop
                    else:
                        raise ExitLoop
                    refundabilityStage = 0
                    changeabilityStage = 0
                    if "amenities" not in segment:
                        raise ExitLoop
                    for amenity in segment["amenities"]:
                        if amenity["description"] in ["CHANGE AFTER DEPARTURE", "CHANGE BEFORE DEPARTURE"] and changeabilityStage != 2:
                            amenities[amenity["description"]] = {"isChargeable": amenity["isChargeable"], "isRequested": False}
                            changeabilityStage += 1
                        if amenity["description"] in ["CHANGEABLE TICKET", "CHANGE ANYTIME"]:
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

def getUpsellOffer(offer, get_price_offer, travelClass, access_token, apiType, ama_Client_Ref, verbose_checkpoint=None):
    print("----------------------------")
    print("offer to get fares for:\n", offer)

    if offer["source"] == "GDS" or offer["source"] == "NDC" or offer["source"] == "PYTON":
        upsell_offers = get_upsell_offer(access_token, [offer], apiType, verbose_checkpoint)

        if upsell_offers == None:
            fares = []
            verbose("No upsell offers found. Adding the default offer to fares list...", verbose_checkpoint)
            print("No upsell offers found. Adding the default offer to fares list...")
            fares.append({"fare": offer, "amenities": {}})
        else:
            basic = getFareByDetail(upsell_offers, 0, refundable=False, changeable=False)
            classic = getFareByDetail(upsell_offers, 1, refundable=False, changeable=True)
            flex = getFareByDetail(upsell_offers, 1, refundable=True, changeable=True)
            
            fares = []
            if basic:
                fares.append(basic)
            if classic:
                fares.append(classic)
            if flex:
                fares.append(flex)

            if not fares:
                verbose("No basic, classic, flex offers found. Adding the default offer to fares list...", verbose_checkpoint)
                print("No basic, classic, flex offers found. Adding the default offer to fares list...")
                fares.append({"fare": offer, "amenities": {}})

    else:
        fares = []
        verbose("Upsells not supported on LTC/EAC. Adding the default offer to fares list...", verbose_checkpoint)
        print("Upsells not supported on LTC/EAC. Adding the default offer to fares list...")
        fares.append({"fare": offer, "amenities": {}})

    return fares