from Auxiliary.verbose_checkpoint import verbose
from Auxiliary.generateErrorID import generate_error_id
import offersFetcherBooking
import traceback
import time
import pandas as pd
import travelModels

def getFlightOffer(structuredData,  verbose_checkpoint):
    
    
    try:
        print('\n\nFinding booking api flight offers')
        offersBooking = offersFetcherBooking.flightShoping(structuredData, verbose_checkpoint)
        offersBooking['details']['result'] = removeEmptyProvides(offersBooking)
    
    except Exception as e:
        traceback_msg = traceback.format_exc()
        error_id = generate_error_id()
        print(f"Error ID: {error_id}")
        print(traceback_msg)
        verbose(f"Error ID: {error_id}", verbose_checkpoint)
        verbose(traceback_msg, verbose_checkpoint)
        time.sleep(0.5)
        return {"status": "error", "data": ("Error ID: " + error_id)}
    
    
    return createObjectOffers(offers=offersBooking['details']['result'], data=structuredData)    

    
def removeEmptyProvides(offers):
    valid_providers = []

    for item in offers['details']['result']:

        if 'code' not in item or not item['code'].startswith('AGW_'):
            valid_providers.append(item)

    return valid_providers

def createObjectOffers(offers, data):
    
    print(data)
    offer_list = []
    for index, offer in enumerate(offers):
        
        print(index, offer)
        cityCode = offer['flights'][0]['arrival']['airportCode']
        airportName = offer['flights'][0]['arrival']['airportName']
        flight_offer = travelModels.FlightOffer(
            api = 'bookingPad',
            airportName=travelModels.AirportName(airportName=airportName),
            cityCode=travelModels.CityCode(cityCode=cityCode),
        )
        
        price = travelModels.Price(grandTotal=offer['price']['consumer']['total'], billingCurrency=offer['price']['consumer']['currency'])
        fares = travelModels.Fare(price=price)
        flight_offer.fares = fares
        
        passanger = travelModels.Passengers(passengers=str(len(data['search_params']["travelers"])))
        flight_offer.passengers = passanger
        offer_list.append(flight_offer)

        
    return offer_list

        
