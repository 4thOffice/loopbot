from datetime import datetime, timedelta
import json
import re
import openai
import sys
import os

import Auxiliary.compressed_json

if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import keys
from urllib.parse import urlencode, quote

def getDeepLink(flightDetails, email_comment_id=None):
    if email_comment_id:
        flightDetails = dict(flightDetails)  # shallow copy
        flightDetails["email_comment_id"] = email_comment_id
    command = f"/travelai createoffer {Auxiliary.compressed_json.encode_json_to_string(flightDetails)}"
    deeplink = bb_code_link(send_chat_deeplink(command), "Prepare offer draft.")
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
    return parsed_date.strftime("%d%b").upper()

# Function to calculate duration in hours and minutes from ISO duration string
def iso_to_hours_minutes(iso_duration):
    duration = re.match(r'PT(\d+)H(?:(\d+)M)?', iso_duration)
    if duration:
        hours = int(duration.group(1))
        minutes = int(duration.group(2)) if duration.group(2) else 0
        return f"{hours:02d}h:{minutes:02d}min"
    else:
        return "00h:00min"
    
def generateFlightTable(offerDetails):
    flightTable = ""
    for flight in offerDetails["flights"]:
        departure_date = iso_to_custom_date(flight["departure"]["at"])
        duration = iso_to_hours_minutes(flight["duration"])
        flight_number = flight["carrierCode"] + " " + flight["flightNumber"]
        origin = flight["departure"]["iataCode"]
        destination = flight["arrival"]["iataCode"]
        arrival_time = datetime.fromisoformat(flight["arrival"]["at"]).strftime("%H:%M")
        departure_time = datetime.fromisoformat(flight["departure"]["at"]).strftime("%H:%M")
        
        flightTable += f"{flight_number:<8} {departure_date}  {origin}{destination:<12} {departure_time}-{arrival_time} ({duration})\n"

    return flightTable

def generateOffer(offerDetails):
    print("---------------------")
    print(offerDetails)

    hotelDetails = offerDetails["hotel"]
    AirportToHotelTransfer = offerDetails["AirportToHotelTransfer"]
    HotelToAirportTransfer = offerDetails["HotelToAirportTransfer"]

    # Generating the output strings
    #flights_string = generateFlightsString(dict(offers=[offerDetails]), usedForDraft=True)

    offerDraftText = "Pozdravljeni,\n\nHvala za povpraševanje. Glede na želje posredujem sledečo ponudbo:\n\n"

    offerDraftText += generateFlightTable(offerDetails) + "\n\n"

    pricePerPerson = float(offerDetails["price"]["grandTotal"])/float(offerDetails["passengers"])
    pricePerPerson = round(pricePerPerson, 2)
    
    offerDraftText += "Cena: " + str(pricePerPerson) + " " + offerDetails["price"]["billingCurrency"] + "/osebo - "
    
    if offerDetails['checkedBags'] >= 1:
        offerDraftText += f"(Vključena ročna prtljaga in {offerDetails['checkedBags']}x oddan kos do 23kg"
    else:
        offerDraftText += f"(Vključena zgolj ročna prtljaga"

    refundableMsgAdded = False
    for amenity in offerDetails["amenities"]:
        if (amenity["amenity_description"] == "REFUNDABLE TICKET" or amenity["amenity_description"] == "REFUND ANYTIME") and not refundableMsgAdded:
            refundableMsgAdded = True
            if amenity["included"] == True:
                if amenity["isChargeable"] == True:
                    offerDraftText += ", povračilo z odpovednimi stroški"
                else:
                    offerDraftText += ", povračilo za odpoved je možno"
            else:
                offerDraftText += ", povračilo za odpoved ni možno"

        if amenity["amenity_description"] == "CHANGEABLE TICKET":
            if amenity["included"] == True:
                if amenity["isChargeable"] == True:
                    offerDraftText += ", naknadne spremembe možne z doplačilom"
                else:
                    offerDraftText += ", naknadne spremembe možne"
            else:
                offerDraftText += ", naknadne spremembe niso možne"

    offerDraftText += ")\n\n"

    googlePlacebaseURL = "https://www.google.com/maps/search/?api=1&query=Google&query_place_id="
    if hotelDetails:
        offerDraftText += f"Predlagana namestitev:\n\n"
        offerDraftText += f"Ime hotela: {hotelDetails['hotelName']}\n"
        offerDraftText += f"Termin:\n od: {hotelDetails['checkInDate']}\n do: {hotelDetails['checkOutDate']}\n"
        offerDraftText += f"Kliknite za podrobnejši ogled: {googlePlacebaseURL + hotelDetails['googlePlaceID']}\n"
        offerDraftText += f"Namestitev v želenem terminu znaša skupaj za nočitve: {float(hotelDetails['price'])/float(offerDetails['passengers'])} {hotelDetails['currency']}/osebo"
    
        if AirportToHotelTransfer:
            offerDraftText += "\n\n"
            offerDraftText += f"Predlagan prevoz od letališča do namestitve:\n\n"
            offerDraftText += f"Opis prevoza: {AirportToHotelTransfer['carType']}\n"
            offerDraftText += f"Čas, ko Vas bodo pobrali: {AirportToHotelTransfer['startTime'].split('T')[1]}\n"
            offerDraftText += f"Celotni prevoz znaša: {AirportToHotelTransfer['price']}\n"

        if HotelToAirportTransfer:
            offerDraftText += "\n\n"
            offerDraftText += f"Predlagan prevoz od namestitve do letališča:\n\n"
            offerDraftText += f"Opis prevoza: {HotelToAirportTransfer['carType']}\n"
            offerDraftText += f"Čas, ko Vas bodo pobrali: {HotelToAirportTransfer['startTime'].split('T')[1]}\n"
            offerDraftText += f"Celotni prevoz znaša: {HotelToAirportTransfer['price']} {HotelToAirportTransfer['currency']}\n"

    return offerDraftText

def generateFlightsString(details, usedForDraft=False, email_comment_id=None):
    flights_string = ""

    for index, offer in enumerate(details["offers"]):
        if not usedForDraft:
            if index == 0:
                flights_string += f"Suggested offer:\n"
            elif index == 1:
                flights_string += f"Alternative offers:\n"
            flights_string += f"Offer {index+1}\n"
        for flight in offer["flights"]:
            departure_date = iso_to_custom_date(flight["departure"]["at"])
            duration = iso_to_hours_minutes(flight["duration"])
            flight_number = flight["carrierCode"] + " " + flight["flightNumber"]
            origin = flight["departure"]["iataCode"]
            destination = flight["arrival"]["iataCode"]
            arrival_time = datetime.fromisoformat(flight["arrival"]["at"]).strftime("%H:%M")
            departure_time = datetime.fromisoformat(flight["departure"]["at"]).strftime("%H:%M")
            
            flights_string += f"{flight_number:<8} {departure_date}  {origin}{destination:<12} {departure_time}-{arrival_time} ({duration})\n"
        
        flights_string += f"Checked bags per passenger: {offer['checkedBags']}\n"
        flights_string += "Number of passengers: " + str(offer["passengers"]) + "\n"
        pricePerPerson = float(offer["price"]["grandTotal"])/float(offer["passengers"])
        
        print(offer["amenities"])
        refundableMsgAdded = False
        for amenity in offer["amenities"]:
            if (amenity["amenity_description"] == "REFUNDABLE TICKET" or amenity["amenity_description"] == "CHANGEABLE TICKET") and not refundableMsgAdded:
                refundableMsgAdded = True
                if amenity["included"] == True:
                    if amenity["isChargeable"] == True:
                        flights_string += "Ticket is refundable with a fee\n"
                    else:
                        flights_string += "Ticket is refundable free of charge\n"
                else:
                    flights_string += "Ticket is not refundable\n"

            if amenity["amenity_description"] == "CHANGEABLE TICKET":
                if amenity["included"] == True:
                    if amenity["isChargeable"] == True:
                        flights_string += "Ticket is changeable with a fee\n"
                    else:
                        flights_string += "Ticket is changeable free of charge\n"
                else:
                    flights_string += "Ticket is not changeable\n"

        flights_string += "Price: " + str(pricePerPerson) + " " + offer["price"]["billingCurrency"] + "/person"
        if email_comment_id:
            flights_string += "\n"
            flights_string += getDeepLink(offer, email_comment_id)
        flights_string += "\n\n"
        
        if usedForDraft and index == 0:
            break

    return flights_string