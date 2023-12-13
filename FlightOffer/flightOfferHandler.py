import datetime
import io
import re
import typing
import os
import sys
import requests
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

current_directory = os.path.dirname(os.path.realpath(__file__))
hotel_offer_path = os.path.join(current_directory, 'HotelOffer')
sys.path.append(hotel_offer_path)
from HotelOffer import hotelSearch, googleAPI

current_directory = os.path.dirname(os.path.realpath(__file__))
transfer_offer_path = os.path.join(current_directory, 'TransferOffer')
sys.path.append(transfer_offer_path)
from TransferOffer import transferSearch


def getFlightOfferAutomation(attachments, subject, htmlEmailtext, plainText, email_comment_id, upsell=False, verbose_checkpoint: typing.Callable[[str], None] = None):
    print("attachments: ", attachments)
    commentData = classification.getFiles(attachments, htmlEmailtext, verbose_checkpoint)
    emailText = "Subject: " + subject + "\n" + plainText
    return getResponse(emailText, commentData, upsell, email_comment_id, verbose_checkpoint)

def getFlightOffer(cardID=None, authKey=None):
    print(cardID)
    commentData = classification.getFirstCommentData(cardID, authKey)
    if commentData["id"] is None:
        return({"parsedOffer": ("Failed to gather email data."), "details": None})

    emailText = classification.getCommentContent(commentData["id"], authKey)
    
    return getResponse(emailText, commentData, True)


def getResponse(emailText, commentData, upsell, email_comment_id=None, verbose_checkpoint=None, retries=0):
    answer = classification.classifyEmail(emailText)
    print("raw email text:", emailText)

    AIregular_ = AIregular.AIregular(keys.openAI_APIKEY)
    if answer:
        filesText = []
        filesPicture = []
        file_content = None
        print(commentData["fileUrls"])
        for fileUrl in commentData["fileUrls"]:
            if fileUrl.startswith("data:"):
                filesPicture.append(fileUrl)
                continue
            response = requests.get(fileUrl)
            response.raise_for_status()
            file_content = io.BytesIO(response.content)
            file_type = magic.from_buffer(file_content.getvalue(), mime=True)
            if "image" in file_type:
                filesPicture.append(fileUrl)
            else:
                filesText.append(file_content)

        if len(filesPicture) > 0:
            print("Asking picture specialized agent - ", str(len(filesPicture)) + " files")
            prompt = "Extract ALL flight details from the email and attached images which I will give you. Extract data like origin, destionation, dates, timeframes, requested connection points (if specified explicitly) and ALL other flight information.\n\nDo not forget to extract data from images too. If you cant extract any data from the image, then extract only from email. Email:\n" + emailText
            flightDetailsImages = AIregular_.processImages(prompt, filesPicture)
            verbose("Asking picture specialized agent with " + str(len(filesPicture)) + " files", verbose_checkpoint)
            if len(filesText) <= 0:
                flightDetails = flightDetailsImages
        if len(filesText) > 0 or len(filesPicture) == 0:
            print("Asking text specialized agent - ", str(len(filesText)) + " files")
            verbose("Asking text specialized agent with " + str(len(filesPicture)) + " files", verbose_checkpoint)
            if len(filesPicture) > 0:
                flightDetails = dataExtractor.askGPT(emailText, filesText, imageInfo=flightDetailsImages)
            else:
                flightDetails = dataExtractor.askGPT(emailText, filesText)

            if flightDetails == None:
                return({"parsedOffer": f"[code][[/code]TravelAI Error[code]][/code]\n\n" + "Timeout while asking AI to extract data.", "details": None})

        intercontinentalText, travelClassText = getExtraInfo(flightDetails)
        details = flightSearch.getFlightOffer(flightDetails, verbose_checkpoint)

        if details["status"] == "ok" and details["data"] is None:
            return({"parsedOffer": f"[code][[/code]TravelAI Success[code]][/code]\n{intercontinentalText}\n{travelClassText}\n\nNo flights found", "details": None})
        elif details["status"] == "error":
            if retries > 0:
                return({"parsedOffer": f"[code][[/code]TravelAI Error[code]][/code]\n{intercontinentalText}\n{travelClassText}\n\n" + details["data"], "details": None})
            else:
                print("Encountered an error, trying one more time...")
                verbose("Encountered an error, trying one more time...", verbose_checkpoint)
                return getResponse(emailText, commentData, upsell, verbose_checkpoint=verbose_checkpoint, retries=1)
        
        #generatedOffer = offerGenerator.generateOffer(emailText, details)

        if upsell:
            try:
                for index, offer in enumerate(details["data"]["offers"]):
                    geoCode = offer["geoCode"]
                    airportName = offer["airportName"]
                    print("geoCode:", geoCode)
                    print("airportName:", airportName)
                    
                    del offer["airportName"]
                    del offer["geoCode"]

                    checkInDate = offer["flights"][0]["arrival"]["at"]
                    checkInDate = datetime.datetime.strptime(checkInDate, '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
                    checkoutDate = offer["flights"][-1]["departure"]["at"]
                    checkoutDate = datetime.datetime.strptime(checkoutDate, '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
                    adults = int(offer["passengers"])
                    currency = offer["price"]["billingCurrency"]

                    hotelDetails = None
                    try:
                        hotelDetails = hotelSearch.getHotelOffer({"latitude": geoCode["latitude"], "longitude": geoCode["longitude"], "checkInDate": checkInDate, "checkOutDate": checkoutDate, "adults": adults, "currency": currency})

                        airportGooglePlaceID = googleAPI.get_place_id(geoCode["latitude"], geoCode["longitude"], 10, airportName)
                    except Exception:
                        details["data"]["offers"][index]["hotel"] = None
                        details["data"]["offers"][index]["AirportToHotelTransfer"] = None
                        details["data"]["offers"][index]["HotelToAirportTransfer"] = None
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

                    try:
                        AirportToHotelTransferDetails = transferSearch.getTransferOffer(airportGooglePlaceID, hotelDetails["googlePlaceID"], LocationCode, adults, transferStartTime)
                        HotelToAirportTransferDetails = transferSearch.getTransferOffer(hotelDetails["googlePlaceID"], airportGooglePlaceID, LocationCode, adults, transferStartBackTime)
                    except Exception:
                        AirportToHotelTransferDetails = None
                        AirportToHotelTransferDetails = None
                        
                    print("TRANSFER DETAILS")
                    print(AirportToHotelTransferDetails)
                    print(HotelToAirportTransferDetails)

                    details["data"]["offers"][index]["hotel"] = hotelDetails
                    details["data"]["offers"][index]["AirportToHotelTransfer"] = AirportToHotelTransferDetails
                    details["data"]["offers"][index]["HotelToAirportTransfer"] = HotelToAirportTransferDetails
            except Exception:
                details["data"]["offers"][index]["hotel"] = None
                details["data"]["offers"][index]["AirportToHotelTransfer"] = None
                details["data"]["offers"][index]["HotelToAirportTransfer"] = None
        else:
            for index, offer in enumerate(details["data"]["offers"]):
                details["data"]["offers"][index]["hotel"] = None
                details["data"]["offers"][index]["AirportToHotelTransfer"] = None
                details["data"]["offers"][index]["HotelToAirportTransfer"] = None


        generatedOffer = offerGenerator.generateFlightsString({"offers": details["data"]["offers"]}, email_comment_id=email_comment_id)
        print(offerGenerator.generateOffer(details["data"]["offers"][0]))

        print("flight details gathered")
        return({"parsedOffer": f"[code][[/code]TravelAI Success[code]][/code]\n{intercontinentalText}\n{travelClassText}\n\n" + generatedOffer, "details": details["data"]})

    else:
        print("Not a flight tender inquiry")
        return({"parsedOffer": f"[code][[/code]TravelAI Success[code]][/code]\n\n" + "Not a flight tender inquiry", "details": None})

def getExtraInfo(emailText):
    intercontinentalText = ""
    isIntercontinental = dataExtractor.isIntercontinentalFlight(emailText)
    if isIntercontinental:
        intercontinentalText = "[code][[/code]INTERCONTINENTAL FLIGHT[code]][/code]"

    travelClassText = ""
    travelClass = dataExtractor.getTravelClass(emailText)
    if travelClass != "":
        if "ECONOMY" in travelClass:
            travelClassText = "[code][[/code]ECONOMY[code]][/code]"
        elif "BUSINESS" in travelClass:
            travelClassText = travelClassText = "[code][[/code]BUSINESS[code]][/code]"
        elif "FIRST" in travelClass:
            travelClassText = travelClassText = "[code][[/code]FIRST[code]][/code]"
        else:
            travelClassText = "[code][[/code]ECONOMY[code]][/code]"
    else: 
        travelClassText = "[code][[/code]ECONOMY[code]][/code]"

    return intercontinentalText, travelClassText

#authKey = whitelist["user_1552217"]
#getFlightOffer("DCwm6ekeYTewrKkymigycY4PBIA0T", authKey)