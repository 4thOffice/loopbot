import datetime
import io
import re
import typing
import os
import sys
import requests
from Auxiliary.generateErrorID import generate_error_id
import classification
import dataExtractor
import magic
import flightSearch
import offerGenerator
from Auxiliary.verbose_checkpoint import verbose
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import AIregular
import keys
import traceback
import uuid
from exceptions import Timeout
import getParametersJson
import base64

current_directory = os.path.dirname(os.path.realpath(__file__))
hotel_offer_path = os.path.join(current_directory, 'HotelOffer')
sys.path.append(hotel_offer_path)
from HotelOffer import hotelSearch, googleAPI

current_directory = os.path.dirname(os.path.realpath(__file__))
transfer_offer_path = os.path.join(current_directory, 'TransferOffer')
sys.path.append(transfer_offer_path)
from TransferOffer import transferSearch


def getFlightOfferAutomation(attachments, subject, htmlEmailtext, plainText, email_comment_id, variables, verbose_checkpoint: typing.Callable[[str], None] = None):
    verbose("TravelAI module started.", verbose_checkpoint)
    automatic_order = False
    upsell = True
    if "No upsell" in variables:
        upsell = False
        verbose(f"No upsell variable {variables['No upsell']}", verbose_checkpoint)
    if "Order" in variables:
        automatic_order = variables["Order"]
        verbose(f"Order variable {variables['Order']}", verbose_checkpoint)

    try:
        print("attachments: ", attachments)
        commentData = classification.getFiles(attachments, htmlEmailtext, verbose_checkpoint)
        emailText = subject + "\n\n" + plainText
        response = getResponse(emailText, commentData, upsell, automatic_order, email_comment_id, verbose_checkpoint)
    except Exception as e:
        traceback_msg = traceback.format_exc()
        error_id = generate_error_id()
        print(f"Error ID: {error_id}")
        print(traceback_msg) 
        verbose(f"Error ID: {error_id}", verbose_checkpoint)
        verbose(traceback_msg, verbose_checkpoint)
        response = {"parsedOffer": ("Error requesting offers - Error ID: " + error_id), "details": None}
    
    return response

def getFlightOffer(cardID=None, authKey=None):
    print(cardID)
    commentData = classification.getFirstCommentData(cardID, authKey)
    if commentData["id"] is None:
        return({"parsedOffer": ("Failed to gather email data."), "details": None})

    emailText = classification.getCommentContent(commentData["id"], authKey)
    
    try:
        response = getResponse(emailText, commentData, False, False)
    except Exception as e:
        traceback_msg = traceback.format_exc()
        error_id = generate_error_id()
        print(f"Error ID: {error_id}")
        print(traceback_msg)
        response = {"parsedOffer": ("Error requesting offers - Error ID: " + error_id), "details": None}

    return response

def getUnstructuredData(AIregular_, commentData, emailText, verbose_checkpoint=None):
    filesText = []
    filesPicture = []

    print(commentData["fileUrls"])
    #verbose(commentData["fileUrls"], verbose_checkpoint)
    for fileUrl in commentData["fileUrls"]:
        #verbose(f"fileUrl: {fileUrl}", verbose_checkpoint)
        if isinstance(fileUrl, str) and fileUrl.startswith("data:"):
            verbose("1", verbose_checkpoint)
            #verbose(f"1: {fileUrl}", verbose_checkpoint)
            #file_content = io.StringIO(fileUrl)
            header, base64_str = fileUrl.split(",", 1)
            image_bytes = base64.b64decode(base64_str)
            file_content = io.BytesIO(image_bytes)
            filesPicture.append(file_content)
            continue

        if isinstance(fileUrl, bytes):
            verbose("2", verbose_checkpoint)
            file_content = io.BytesIO(fileUrl)
            file_type = magic.from_buffer(fileUrl, mime=True)
            #verbose(f"2: {file_content} {file_type}", verbose_checkpoint)
        elif isinstance(fileUrl, tuple):
            verbose("3", verbose_checkpoint)
            # Union[Tuple[str, bytes], Tuple[str, bytes, Optional[str]]] -> filename, file_bytes, *mime_type
            file_content = io.BytesIO(fileUrl[1])
            file_type = fileUrl[2] if len(fileUrl) == 3 and fileUrl[2] else magic.from_buffer(fileUrl[1], mime=True)
            #verbose(f"3: {file_content} {file_type}", verbose_checkpoint)
        else:
            verbose("4", verbose_checkpoint)
            response = requests.get(fileUrl)
            response.raise_for_status()
            file_content = io.BytesIO(response.content)
            file_type = magic.from_buffer(file_content.getvalue(), mime=True)
            #verbose(f"4: {file_content} {file_type}", verbose_checkpoint)

        if "image" in file_type:
            verbose("5", verbose_checkpoint)
            response = requests.get(fileUrl)
            response.raise_for_status()
            file_content = io.BytesIO(response.content)
            filesPicture.append(file_content)
            #verbose(f"5: {file_content}", verbose_checkpoint)
        else:
            verbose("6", verbose_checkpoint)
            filesText.append(file_content)
            #verbose(f"6: {file_content}", verbose_checkpoint)
    
    #verbose(f"filesText: {filesText}", verbose_checkpoint)
    #verbose(f"filesPicture: {filesPicture}", verbose_checkpoint)
    flightDetails = dataExtractor.askGPT(emailText, filesText, filesPicture, verbose_checkpoint=verbose_checkpoint)

    if flightDetails == None:
        raise Timeout()

    print(f"data extracted from first extraction stage:\n {flightDetails}")
    verbose(f"data extracted from first extraction stage:\n {flightDetails}", verbose_checkpoint=verbose_checkpoint)

    return flightDetails
    

def getResponse(emailText, commentData, upsell, automatic_order, email_comment_id=None, verbose_checkpoint=None, retries=0):
    answer = classification.classifyEmail(emailText)
    print("raw email text:", emailText)
    verbose(f"raw email text:\n{emailText}", verbose_checkpoint)

    AIregular_ = AIregular.AIregular(keys.openAI_APIKEY)
    if answer:
        try:
            unstructuredData = getUnstructuredData(AIregular_, commentData, emailText, verbose_checkpoint)
        except Timeout as ce:
            return({"parsedOffer": "Error requesting offers - Timeout while asking AI to extract data.", "details": None})
        
        intercontinentalText, travelClassText = getExtraInfo(unstructuredData)

        try:
            structuredData = getParametersJson.extractSearchParameters(unstructuredData, 250, verbose_checkpoint)
            print("structured data:\n", structuredData)
        except Exception as e:
            traceback_msg = traceback.format_exc()
            error_id = generate_error_id()
            print(f"Exception {e=} while trying to extract search parameters into json. Error ID: {error_id} {unstructuredData=}")
            print(traceback_msg) 
            verbose(f"Exception {e=} while trying to extract search parameters into json. Error ID: {error_id} {unstructuredData=}", verbose_checkpoint)
            verbose(traceback_msg, verbose_checkpoint)
            return({"parsedOffer": (f"{travelClassText}\n\n" + "Error requesting offers - Error ID: " + generate_error_id()), "details": None})

        ama_Client_Ref = str(uuid.uuid4())
        details = flightSearch.getFlightOffer(structuredData, automatic_order, ama_Client_Ref, verbose_checkpoint)

        if details["status"] == "ok" and details["data"] is None:
            return({"parsedOffer": f"{travelClassText}\n\nNo flights found", "details": None})
        elif details["status"] == "error":
            if retries > 0:
                print(f"Error requesting offers - {details['data']}")
                verbose(f"Error requesting offers - {details['data']}", verbose_checkpoint)
                return({"parsedOffer": f"{travelClassText}\n\n" + "Error requesting offers - " + details["data"], "details": None})
            else:
                print("Encountered an error, trying one more time...")
                verbose("Encountered an error, trying one more time...", verbose_checkpoint)
                return getResponse(emailText, commentData, upsell, automatic_order, email_comment_id=email_comment_id,
                                   verbose_checkpoint=verbose_checkpoint, retries=1)
        
        #generatedOffer = offerGenerator.generateOffer(emailText, details)

        upsellOffersPerCity = {}
        if upsell:
            try:
                for index, offer in enumerate(details["data"]["offers"]):
                    geoCode = offer["geoCode"]
                    cityCode = offer["cityCode"]
                    airportName = offer["airportName"]
                    print("geoCode:", geoCode)
                    print("cityCode:", cityCode)
                    print("airportName:", airportName)
                    
                    del offer["cityCode"]
                    del offer["geoCode"]
                    del offer["airportName"]

                    if cityCode in upsellOffersPerCity:
                        details["data"]["offers"][index]["upsellOffers"] = upsellOffersPerCity[cityCode]
                    else:
                        checkInDate = offer["flights"][0]["arrival"]["at"]
                        checkInDate = datetime.datetime.strptime(checkInDate, '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
                        checkoutDate = offer["flights"][-1]["departure"]["at"]
                        checkoutDate = datetime.datetime.strptime(checkoutDate, '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
                        adults = int(offer["passengers"])
                        currency = offer["fares"][0]["price"]["billingCurrency"]
                        airportGooglePlaceID = googleAPI.get_place_id(geoCode["latitude"], geoCode["longitude"], 10, airportName)
                        
                        upsellOffers = []
                        for i in range(3):
                            hotelDetails = None
                            try:
                                hotelDetails = hotelSearch.getHotelOffer({"cityCode": cityCode, "latitude": geoCode["latitude"], "longitude": geoCode["longitude"], "checkInDate": checkInDate, "checkOutDate": checkoutDate, "adults": adults, "currency": currency, "stars": i+3})
                                if not hotelDetails["hotelName"]:
                                    raise Exception
                                
                                print("HOTEL SUCCESSFUL")
                            except Exception:
                                print(traceback.print_exc())
                                verbose(traceback.format_exc(), verbose_checkpoint=verbose_checkpoint)
                                continue
                            
                            transferStartTime = ""
                            transferStartBackTime = ""
                            LocationCode = ""
                            for flight in offer["flights"]:
                                if flight["iteraryNumber"] == 0:
                                    transferStartTime = flight["arrival"]["at"]
                                    LocationCode = flight["arrival"]["iataCode"]
                                elif flight["iteraryNumber"] == 1 and not transferStartBackTime:
                                    transferStartBackTime = flight["departure"]["at"]

                            datetime_obj = datetime.datetime.fromisoformat(transferStartBackTime)
                            one_hour_less = datetime_obj - datetime.timedelta(hours=2)
                            transferStartBackTime = one_hour_less.strftime("%Y-%m-%dT%H:%M:%S")

                            AirportToHotelTransferDetails = None
                            HotelToAirportTransferDetails = None
                            try:
                                AirportToHotelTransferDetails = transferSearch.getTransferOffer(airportGooglePlaceID, hotelDetails["googlePlaceID"], LocationCode, adults, transferStartTime, currency)
                                HotelToAirportTransferDetails = transferSearch.getTransferOffer(hotelDetails["googlePlaceID"], airportGooglePlaceID, LocationCode, adults, transferStartBackTime, currency)
                                print("TRANSFER SUCESSFUL")
                                print(AirportToHotelTransferDetails)
                                print(HotelToAirportTransferDetails)
                                
                            except Exception:
                                print("Failed gathering transfer offers")
                                print(traceback.print_exc())
                                verbose(traceback.format_exc(), verbose_checkpoint=verbose_checkpoint)

                            upsellOffer = {"hotelDetails": hotelDetails, "AirportToHotelTransferDetails": AirportToHotelTransferDetails, "HotelToAirportTransferDetails": HotelToAirportTransferDetails}
                            upsellOffers.append(upsellOffer)

                        details["data"]["offers"][index]["upsellOffers"] = upsellOffers
                        upsellOffersPerCity[cityCode] = upsellOffers
            except Exception:
                traceback.print_exc()
                verbose(f'{details["data"]["offers"]=}\n{traceback.format_exc()}', verbose_checkpoint=verbose_checkpoint)
                #dodaj prazen upsell v vsak offer
                for index, offer in enumerate(details["data"]["offers"]):
                    details["data"]["offers"][index]["upsellOffers"] = []
        else:
            for index, offer in enumerate(details["data"]["offers"]):
                details["data"]["offers"][index]["upsellOffers"] = []
        
        print("final offer details with amenities:\n", details["data"]["offers"])
        generatedOffer = offerGenerator.generateFlightsString({"offers": details["data"]["offers"]}, email_comment_id=email_comment_id, verbose_checkpoint=verbose_checkpoint)

        peopleString = ""
        if "people" in details["data"] and details["data"]["offers"][0]["order_reference"]:
            if details["data"]["people"]:
                peopleString += "Reservation for:\n"
            for person in details["data"]["people"]:
                peopleString += f"{person['first_name']} {person['last_name']}\n"
            if details["data"]["people"]:
                peopleString += "\n"

        #print(offerGenerator.generateOffer(details["data"]["offers"][0]))

        print(details["data"])
        print("flight details gathered")
        
        if len(details["data"]["offers"][0]["flights"]) == 1 and details["data"]["offers"][0]["flights"][0]["departure"]["iataCode"] == "LJU" and details["data"]["offers"][0]["flights"][0]["arrival"]["iataCode"] == "CDG":
            return({"parsedOffer": "AI could not provide an offer for this inquiry.", "details": None})
        else:
            return({"parsedOffer": f"{peopleString}{travelClassText}\n\n{generatedOffer}", "details": details["data"]})

    else:
        print("Not a flight tender inquiry")
        return({"parsedOffer": f"Not a flight travel request", "details": None})

def getExtraInfo(emailText):
    intercontinentalText = ""
    isIntercontinental = dataExtractor.isIntercontinentalFlight(emailText)
    if isIntercontinental:
        intercontinentalText = "[code][[/code]INTERCONTINENTAL FLIGHT[code]][/code]"

    travelClassText = ""
    travelClass = dataExtractor.getTravelClass(emailText)
    if travelClass != "":
        if "ECONOMY" in travelClass:
            travelClassText = "Suggested offers (economy requested) per person:"
        elif "BUSINESS" in travelClass:
            travelClassText = travelClassText = "Suggested offers (business requested) per person:"
        elif "FIRST" in travelClass:
            travelClassText = travelClassText = "Suggested offers (first class requested) per person:"
        else:
            travelClassText = "Suggested offers (economy requested) per person:"
    else: 
        travelClassText = "Suggested offers (economy requested) per person:"

    return intercontinentalText, travelClassText

#authKey = whitelist["user_1552217"]
#getFlightOffer("DCwm6ekeYTewrKkymigycY4PBIA0T", authKey)