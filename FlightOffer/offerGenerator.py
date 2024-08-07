from datetime import datetime, timedelta
import json
import re
import openai
import sys
import os

import Auxiliary.compressed_json
from Auxiliary.verbose_checkpoint import verbose
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import keys
from urllib.parse import urlencode, quote

def getDeepLink(flightDetails, email_comment_id=None):
    flightDetails = dict(flight_offers=flightDetails)
    if email_comment_id:
        flightDetails["email_comment_id"] = email_comment_id
    command = f"/travelai createoffer {Auxiliary.compressed_json.encode_json_to_string(flightDetails)}"
    deeplink = bb_code_link(send_chat_deeplink(command), "Prepare draft")
    return deeplink

def url_encode(params):
    return urlencode(params, quote_via=quote)


def send_chat_deeplink(msg):
    return f"intheloop://send-chat?{url_encode({'msg': msg})}"

def bb_code_link(link, content, preview: bool = None):
    if preview is not None and isinstance(preview, bool):
        return "[url href=\"{}\" preview={}]{}[/url]".format(link, preview, content)
    else:
        return "[url href=\"{}\"]{}[/url]".format(link, content)
    
def iso_to_custom_date(iso_date):
    parsed_date = datetime.fromisoformat(iso_date)
    return parsed_date.strftime("%d%b%Y").upper()

# Function to calculate duration in hours and minutes from ISO duration string
def iso_to_hours_minutes(iso_duration):
    hours = re.findall(r'(\d+)H', iso_duration)
    minutes = re.findall(r'(\d+)M', iso_duration)

    hours = int(hours[0]) if hours else 0
    minutes = int(minutes[0]) if minutes else 0

    duration = timedelta(hours=hours, minutes=minutes)
    formatted_duration = f'{duration.seconds // 3600:02d}h:{(duration.seconds % 3600) // 60:02d}min'

    return formatted_duration
    
def generateFlightTable(offerDetails):
    flightTable = ""
    for flight in offerDetails["flights"]:
        departure_date = iso_to_custom_date(flight["departure"]["at"])
        flight_number = flight["carrierCode"] + " " + flight["flightNumber"]
        origin = flight["departure"]["iataCode"]
        destination = flight["arrival"]["iataCode"]
        arrival_time = datetime.fromisoformat(flight["arrival"]["at"]).strftime("%H:%M")
        departure_time = datetime.fromisoformat(flight["departure"]["at"]).strftime("%H:%M")
        cabin = flight["travelClass"]
        duration = iso_to_hours_minutes(flight["duration"])
        
        flightTable += f"{flight_number:<8} {departure_date}  {origin}{destination:<12} {departure_time}-{arrival_time} ({cabin}) ({duration})\n"

    return flightTable

def generateOffer(offerDetails):
    print("---------------------")
    print(offerDetails)

    # Generating the output strings
    #flights_string = generateFlightsString(dict(offers=[offerDetails]), usedForDraft=True)

    offerDraftText = "Pozdravljeni,\n\nHvala za povpraševanje. Glede na želje posredujem sledečo ponudbo:\n\n"

    offerDraftText += generateFlightTable(offerDetails) + "\n\n"

    for fare in offerDetails["fares"]:
        pricePerPerson = float(fare["price"]["grandTotal"])/float(offerDetails["passengers"])
        pricePerPerson = round(pricePerPerson, 2)
        
        offerDraftText += "Cena: " + str(pricePerPerson) + " " + fare["price"]["billingCurrency"] + "/osebo - "
        
        if fare['checkedBags'] >= 1:
            offerDraftText += f"(Vključena ročna prtljaga in {fare['checkedBags']}x oddan kos do 23kg"
        else:
            offerDraftText += f"(Vključena zgolj ročna prtljaga"

        isRefundableTicket = False
        isRefundChargeable = False
        isChangeableTicket = False
        isChangeChargeable = False

        if "REFUNDABLE TICKET" in fare.amenities:
            isRefundableTicket = True
            if fare.amenities["REFUNDABLE TICKET"]["isChargeable"]:
                isRefundChargeable = True

        if "REFUNDS ANYTIME" in fare.amenities and not isRefundableTicket:
            isRefundableTicket = True
            if fare.amenities["REFUNDS ANYTIME"]["isChargeable"]:
                isRefundChargeable = True

        if "REFUND BEFORE DEPARTURE" in fare.amenities and not isRefundableTicket:
            isRefundableTicket = True
            if fare.amenities["REFUND BEFORE DEPARTURE"]["isChargeable"]:
                isRefundChargeable = True


        if "CHANGEABLE TICKET" in fare.amenities:
            isChangeableTicket = True
            if fare.amenities["CHANGEABLE TICKET"]["isChargeable"]:
                isChangeChargeable = True

        if "CHANGE ANYTIME" in fare.amenities:
            isChangeableTicket = True
            if fare.amenities["CHANGE ANYTIME"]["isChargeable"]:
                isChangeChargeable = True

        if "CHANGE BEFORE DEPARTURE" in fare.amenities and "CHANGE AFTER DEPARTURE" in fare.amenities and not isChangeableTicket:
            isChangeableTicket = True
            if fare.amenities["CHANGE BEFORE DEPARTURE"]["isChargeable"] or fare.amenities["CHANGE AFTER DEPARTURE"]["isChargeable"]:
                isChangeChargeable = True
                
        if isRefundableTicket:
            if isRefundChargeable:
                offerDraftText += ", povračilo z odpovednimi stroški"
            else:
                offerDraftText += ", povračilo za odpoved je možno"
        else:
            offerDraftText += ", povračilo za odpoved ni možno"

        if isChangeableTicket:
            if isChangeChargeable:
                offerDraftText += ", naknadne spremembe možne z doplačilom"
            else:
                offerDraftText += ", naknadne spremembe možne"
        else:
            offerDraftText += ", naknadne spremembe niso možne"

        offerDraftText += ")\n"

    for upsellOffer in offerDetails["upsellOffers"]:
        hotelDetails = upsellOffer["hotelDetails"]
        AirportToHotelTransfer = upsellOffer["AirportToHotelTransferDetails"]
        HotelToAirportTransfer = upsellOffer["HotelToAirportTransferDetails"]

        googlePlacebaseURL = "https://www.google.com/maps/search/?api=1&query=Google&query_place_id="
        if hotelDetails:
            offerDraftText += "\n\n"
            offerDraftText += f"Predlagana namestitev:\n\n"
            offerDraftText += f"Ime hotela: {hotelDetails['hotelName']}\n"
            offerDraftText += f"Opis sobe: {hotelDetails['descriptionSLO']}\n"
            offerDraftText += f"Termin:\n od: {hotelDetails['checkInDate']}\n do: {hotelDetails['checkOutDate']}\n"
            offerDraftText += f"Kliknite za podrobnejši ogled: {googlePlacebaseURL + hotelDetails['googlePlaceID']}\n"
            offerDraftText += f"Namestitev v želenem terminu znaša skupaj za nočitve: {float(hotelDetails['price'])/float(offerDetails['passengers'])} {hotelDetails['currency']}/osebo\n"
            for i in range(len(hotelDetails['photosReferenceID'])):
                offerDraftText += f"GooglePlacesRef::<{hotelDetails['photosReferenceID'][i]}>::"

            if AirportToHotelTransfer:
                offerDraftText += "\n\n"
                offerDraftText += f"Predlagan prevoz od letališča do namestitve:\n\n"
                offerDraftText += f"Opis prevoza: {AirportToHotelTransfer['carType']}\n"
                offerDraftText += f"Čas, ko Vas bodo pobrali: {AirportToHotelTransfer['startTime'].split('T')[1]}\n"
                offerDraftText += f"Celotni prevoz znaša: {AirportToHotelTransfer['price']} {HotelToAirportTransfer['currency']}\n"

            if HotelToAirportTransfer:
                offerDraftText += "\n\n"
                offerDraftText += f"Predlagan prevoz od namestitve do letališča:\n\n"
                offerDraftText += f"Opis prevoza: {HotelToAirportTransfer['carType']}\n"
                offerDraftText += f"Čas, ko Vas bodo pobrali: {HotelToAirportTransfer['startTime'].split('T')[1]}\n"
                offerDraftText += f"Celotni prevoz znaša: {HotelToAirportTransfer['price']} {HotelToAirportTransfer['currency']}\n"

    return offerDraftText

def generateFlightsString(details, usedForDraft=False, email_comment_id=None, verbose_checkpoint=None):
    flights_string = ""

    for index, offer in enumerate(details["offers"]):
        if not usedForDraft:
            if index == 0:
                flights_string += f"Featured offer:\n"
            elif index == 1:
                flights_string += f"\n\n\nAlternative offer 1:\n"
            elif index == 2:
                flights_string += f"\n\n\nAlternative offer 2:\n"
        for flight in offer.flights:
            departure_date = iso_to_custom_date(flight.departure["at"])
            flight_number = flight.carrierCode + " " + flight.flightNumber
            origin = flight.departure["iataCode"]
            destination = flight.arrival["iataCode"]
            arrival_time = datetime.fromisoformat(flight.arrival["at"]).strftime("%H:%M")
            departure_time = datetime.fromisoformat(flight.departure["at"]).strftime("%H:%M")
            cabin = flight.travelClass
            cabinString = "(" + cabin + ")"
            if cabin.lower() == "economy":
                cabinString = ""
            duration = iso_to_hours_minutes(flight.duration)

            flights_string += f"{flight_number:<8} {departure_date}  {origin}{destination:<12} {departure_time}-{arrival_time} ({duration}) {cabinString}\n"
        
        # if offer["order_reference"]:
        #     flights_string += "\nReservation reference: " + str(offer["order_reference"])
            
        for fare in offer.fares:
            if fare.checkedBags == 0:
                flights_string += "\nOnly carry-on included. "
            elif fare.checkedBags == 1:
                flights_string += f"\n{fare.checkedBags} checked bag & carry-on included. "
            elif fare.checkedBags > 1:
                flights_string += f"\n{fare.checkedBags} checked bags & carry-on included. "
            #flights_string += "Number of passengers: " + str(offer["passengers"]) + "\n"
            
            pricePerPerson = float(fare.price["grandTotal"])/float(offer.get_passengers_as_float())

            print("amenities of final offer:\n", fare.amenities)
              
            isRefundableTicket = False
            isRefundChargeable = False
            isChangeableTicket = False
            isChangeChargeable = False

            if "REFUNDABLE TICKET" in fare.amenities:
                isRefundableTicket = True
                if fare.amenities["REFUNDABLE TICKET"]["isChargeable"]:
                    isRefundChargeable = True

            if "REFUNDS ANYTIME" in fare.amenities and not isRefundableTicket:
                isRefundableTicket = True
                if fare.amenities["REFUNDS ANYTIME"]["isChargeable"]:
                    isRefundChargeable = True

            if "REFUND BEFORE DEPARTURE" in fare.amenities and not isRefundableTicket:
                isRefundableTicket = True
                if fare.amenities["REFUND BEFORE DEPARTURE"]["isChargeable"]:
                    isRefundChargeable = True


            if "CHANGEABLE TICKET" in fare.amenities:
                isChangeableTicket = True
                if fare.amenities["CHANGEABLE TICKET"]["isChargeable"]:
                    isChangeChargeable = True

            if "CHANGE ANYTIME" in fare.amenities:
                isChangeableTicket = True
                if fare.amenities["CHANGE ANYTIME"]["isChargeable"]:
                    isChangeChargeable = True

            if "CHANGE BEFORE DEPARTURE" in fare.amenities and "CHANGE AFTER DEPARTURE" in fare.amenities and not isChangeableTicket:
                isChangeableTicket = True
                if fare.amenities["CHANGE BEFORE DEPARTURE"]["isChargeable"] or fare.amenities["CHANGE AFTER DEPARTURE"]["isChargeable"]:
                    isChangeChargeable = True
                    
                    
            if isRefundableTicket:
                if isRefundChargeable:
                    flights_string += "Refundable with a fee, "
                else:
                    flights_string += "Refundable, "
            else:
                flights_string += "Non-refundable, "
            
            if isChangeableTicket:
                if isChangeChargeable:
                    flights_string += "changeable with a fee ticket"
                else:
                    flights_string += "changeable ticket"
            else:
                flights_string += "non-changeable ticket"

            flights_string += "\nPrice: " + str(pricePerPerson) + " " + fare["price"]["billingCurrency"] + "/person"
            
            if usedForDraft and index == 0:
                break
    
    print("deeplink content:\n", details["offers"])
    deeplink = ""
    if email_comment_id:
        deeplink = getDeepLink(details["offers"], email_comment_id)
    flights_string += f"\n\n{deeplink}"
    
    return flights_string