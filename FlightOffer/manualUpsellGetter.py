import json
import requests
import sys
import os
sys.path.append("../")
import keys

def get_access_token(api_key=keys.amadeus_client_id, api_secret=keys.amadeus_client_secret):
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
            'flightOffers': [json.loads(flight_offers)] 
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
            amenityCount = sum(value["included"] is True for value in includedAmenities.values())
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
    
offer = """{
   "type":"flight-offer",
   "id":"3",
   "source":"GDS",
   "instantTicketingRequired":false,
   "nonHomogeneous":false,
   "paymentCardRequired":false,
   "lastTicketingDate":"2024-01-09",
   "itineraries":[
      {
         "segments":[
            {
               "departure":{
                  "iataCode":"LHR",
                  "terminal":"4",
                  "at":"2024-01-09T06:30:00"
               },
               "arrival":{
                  "iataCode":"AMS",
                  "at":"2024-01-09T09:00:00"
               },
               "carrierCode":"KL",
               "number":"1000",
               "aircraft":{
                  "code":"73H"
               },
               "operating":{
                  "carrierCode":"KL"
               },
               "duration":"PT1H30M",
               "id":"35",
               "numberOfStops":0,
               "co2Emissions":[
                  {
                     "weight":54,
                     "weightUnit":"KG",
                     "cabin":"ECONOMY"
                  }
               ]
            },
            {
               "departure":{
                  "iataCode":"AMS",
                  "at":"2024-01-09T13:25:00"
               },
               "arrival":{
                  "iataCode":"LJU",
                  "at":"2024-01-09T15:10:00"
               },
               "carrierCode":"KL",
               "number":"2577",
               "aircraft":{
                  "code":"73H"
               },
               "operating":{
                  "carrierCode":"HV"
               },
               "duration":"PT1H45M",
               "id":"36",
               "numberOfStops":0,
               "co2Emissions":[
                  {
                     "weight":95,
                     "weightUnit":"KG",
                     "cabin":"ECONOMY"
                  }
               ]
            }
         ]
      },
      {
         "segments":[
            {
               "departure":{
                  "iataCode":"LJU",
                  "at":"2024-01-11T12:30:00"
               },
               "arrival":{
                  "iataCode":"CDG",
                  "terminal":"2G",
                  "at":"2024-01-11T14:30:00"
               },
               "carrierCode":"AF",
               "number":"1037",
               "aircraft":{
                  "code":"E90"
               },
               "operating":{
                  "carrierCode":"AF"
               },
               "duration":"PT2H",
               "id":"46",
               "numberOfStops":0,
               "co2Emissions":[
                  {
                     "weight":134,
                     "weightUnit":"KG",
                     "cabin":"ECONOMY"
                  }
               ]
            },
            {
               "departure":{
                  "iataCode":"CDG",
                  "terminal":"2E",
                  "at":"2024-01-11T16:10:00"
               },
               "arrival":{
                  "iataCode":"LHR",
                  "terminal":"4",
                  "at":"2024-01-11T16:35:00"
               },
               "carrierCode":"AF",
               "number":"1280",
               "aircraft":{
                  "code":"223"
               },
               "operating":{
                  "carrierCode":"AF"
               },
               "duration":"PT1H25M",
               "id":"47",
               "numberOfStops":0,
               "co2Emissions":[
                  {
                     "weight":48,
                     "weightUnit":"KG",
                     "cabin":"ECONOMY"
                  }
               ]
            }
         ]
      }
   ],
   "price":{
      "currency":"EUR",
      "total":"343.11",
      "base":"194.00",
      "fees":[
         {
            "amount":"0.00",
            "type":"SUPPLIER"
         },
         {
            "amount":"0.00",
            "type":"TICKETING"
         },
         {
            "amount":"0.00",
            "type":"FORM_OF_PAYMENT"
         }
      ],
      "grandTotal":"343.11",
      "billingCurrency":"EUR"
   },
   "pricingOptions":{
      "fareType":[
         "PUBLISHED"
      ],
      "includedCheckedBagsOnly":false
   },
   "validatingAirlineCodes":[
      "AF"
   ],
   "travelerPricings":[
      {
         "travelerId":"1",
         "fareOption":"STANDARD",
         "travelerType":"ADULT",
         "price":{
            "currency":"EUR",
            "total":"343.11",
            "base":"194.00",
            "taxes":[
               {
                  "amount":"6.65",
                  "code":"JJ"
               },
               {
                  "amount":"17.79",
                  "code":"SI"
               },
               {
                  "amount":"12.00",
                  "code":"QX"
               },
               {
                  "amount":"8.29",
                  "code":"CJ"
               },
               {
                  "amount":"44.34",
                  "code":"YQ"
               },
               {
                  "amount":"4.68",
                  "code":"YR"
               },
               {
                  "amount":"15.17",
                  "code":"GB"
               },
               {
                  "amount":"5.03",
                  "code":"FR"
               },
               {
                  "amount":"9.50",
                  "code":"RN"
               },
               {
                  "amount":"25.66",
                  "code":"UB"
               }
            ],
            "refundableTaxes":"124.60"
         },
         "fareDetailsBySegment":[
            {
               "segmentId":"35",
               "cabin":"ECONOMY",
               "fareBasis":"LYS0ABLA",
               "brandedFare":"LIGHT",
               "class":"L",
               "includedCheckedBags":{
                  "quantity":0
               }
            },
            {
               "segmentId":"36",
               "cabin":"ECONOMY",
               "fareBasis":"LYS0ABLA",
               "brandedFare":"LIGHT",
               "class":"L",
               "includedCheckedBags":{
                  "quantity":0
               }
            },
            {
               "segmentId":"46",
               "cabin":"ECONOMY",
               "fareBasis":"TYS0ABLA",
               "brandedFare":"LIGHT",
               "class":"T",
               "includedCheckedBags":{
                  "quantity":0
               }
            },
            {
               "segmentId":"47",
               "cabin":"ECONOMY",
               "fareBasis":"TYS0ABLA",
               "brandedFare":"LIGHT",
               "class":"T",
               "includedCheckedBags":{
                  "quantity":0
               }
            }
         ]
      }
   ]
}"""

upsold = get_upsell_offer(get_access_token(keys.amadeus_client_id, keys.amadeus_client_secret), offer, ["REFUNDABLE TICKET", "CHANGEABLE TICKET", "REFUNDS ANYTIME"], "ECONOMY")

print(upsold)