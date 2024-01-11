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
import traceback

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
    emailText = subject + "\n\n" + plainText
    return getResponse(emailText, commentData, upsell, email_comment_id, verbose_checkpoint)

def getFlightOffer(cardID=None, authKey=None):
    print(cardID)
    commentData = classification.getFirstCommentData(cardID, authKey)
    if commentData["id"] is None:
        return({"parsedOffer": ("Failed to gather email data."), "details": None})

    emailText = classification.getCommentContent(commentData["id"], authKey)
    
    return getResponse(emailText, commentData, False)


def getResponse(emailText, commentData, upsell, email_comment_id=None, verbose_checkpoint=None, retries=0):
    answer = classification.classifyEmail(emailText)
    print("raw email text:", emailText)

    AIregular_ = AIregular.AIregular(keys.openAI_APIKEY)
    if answer:
        filesText = []
        filesPicture = []
        print(commentData["fileUrls"])
        for fileUrl in commentData["fileUrls"]:
            if isinstance(fileUrl, str) and fileUrl.startswith("data:"):
                filesPicture.append(fileUrl)
                continue

            if isinstance(fileUrl, bytes):
                file_content = fileUrl
                file_type = magic.from_buffer(fileUrl, mime=True)
            elif isinstance(fileUrl, tuple):
                # Union[Tuple[str, bytes], Tuple[str, bytes, Optional[str]]] -> filename, file_bytes, *mime_type
                file_content = fileUrl
                file_type = fileUrl[2] if len(fileUrl) == 3 and fileUrl[2] else magic.from_buffer(fileUrl[1], mime=True)
            else:
                response = requests.get(fileUrl)
                response.raise_for_status()
                file_content = io.BytesIO(response.content)
                file_type = magic.from_buffer(file_content.getvalue(), mime=True)

            if "image" in file_type:
                filesPicture.append(fileUrl)
            else:
                filesText.append(file_content)

        if len(filesPicture) > 0:
            if len(filesText) <= 0:
                flightDetailsImages = AIregular_.processImages(emailText, filesPicture, shortenedOutput=False, verbose_checkpoint=verbose_checkpoint)
                flightDetails = flightDetailsImages
            else:
                print("Asking picture specialized agent - ", str(len(filesPicture)) + " files")
                flightDetailsImages = AIregular_.processImages(emailText, filesPicture, shortenedOutput=True, verbose_checkpoint=verbose_checkpoint)
                verbose("Asking picture specialized agent with " + str(len(filesPicture)) + " files", verbose_checkpoint)

        if len(filesText) > 0 or len(filesPicture) == 0:
            print("Asking text specialized agent - ", str(len(filesText)) + " files")
            verbose("Asking text specialized agent with " + str(len(filesText)) + " files", verbose_checkpoint)
            if len(filesPicture) > 0:
                flightDetails = dataExtractor.askGPT(emailText, filesText, imageInfo=flightDetailsImages, verbose_checkpoint=verbose_checkpoint)
            else:
                flightDetails = dataExtractor.askGPT(emailText, filesText, verbose_checkpoint=verbose_checkpoint)

            if flightDetails == None:
                return({"parsedOffer": "Error requesting offers: Timeout while asking AI to extract data.", "details": None})

        print(f"data extracted from first extraction stage:\n {flightDetails}")
        verbose(f"data extracted from first extraction stage:\n {flightDetails}", verbose_checkpoint=verbose_checkpoint)
        intercontinentalText, travelClassText = getExtraInfo(flightDetails)
        details = flightSearch.getFlightOffer(flightDetails, verbose_checkpoint)

        if details["status"] == "ok" and details["data"] is None:
            return({"parsedOffer": f"{travelClassText}\n\nNo flights found", "details": None})
        elif details["status"] == "error":
            if retries > 0:
                return({"parsedOffer": f"{travelClassText}\n\n" + "Error requesting offers: " + details["data"], "details": None})
            else:
                print("Encountered an error, trying one more time...")
                verbose("Encountered an error, trying one more time...", verbose_checkpoint)
                return getResponse(emailText, commentData, upsell, email_comment_id=email_comment_id,
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
                        currency = offer["price"]["billingCurrency"]
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

                            upsellOffer = {"hotelDetails": hotelDetails, "AirportToHotelTransferDetails": AirportToHotelTransferDetails, "HotelToAirportTransferDetails": HotelToAirportTransferDetails}
                            upsellOffers.append(upsellOffer)

                        details["data"]["offers"][index]["upsellOffers"] = upsellOffers
                        upsellOffersPerCity[cityCode] = upsellOffers
            except Exception:
                print(traceback.print_exc())
                #dodaj prazen upsell v vsak offer
                for index, offer in (details["data"]["offers"]):
                    details["data"]["offers"][index]["upsellOffers"] = []
        else:
            for index, offer in enumerate(details["data"]["offers"]):
                details["data"]["offers"][index]["upsellOffers"] = []
        
        
        print("final offer details with amenities:\n", details["data"]["offers"])
        generatedOffer = offerGenerator.generateFlightsString({"offers": details["data"]["offers"]}, email_comment_id=email_comment_id)

        peopleString = ""
        if "people" in details["data"]:
            if details["data"]["people"]:
                peopleString += "Rezervacija za:\n"
            for person in details["data"]["people"]:
                peopleString += f"{person['first_name']} {person['last_name']}\n"

        print(offerGenerator.generateOffer(details["data"]["offers"][0]))


        print(details["data"])
        print("flight details gathered")
        
        return({"parsedOffer": f"{peopleString}\n{travelClassText}\n\n{generatedOffer}", "details": details["data"]})

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