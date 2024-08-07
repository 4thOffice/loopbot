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
from travelModels import OfferResult
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
import flightSortin

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
        response = OfferResult("", None)
    
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
        response = OfferResult("", None)

    return {"parsedOffer": response.loop_chat_message, "details": response.offer_details}

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
            verbose("Error requesting offers - Timeout while asking AI to extract data.", verbose_checkpoint)
            return OfferResult("", None)
        
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
            return OfferResult("", None)

        ama_Client_Ref = str(uuid.uuid4())
        
        # details = flightSortin.callFlightApis(structuredData, automatic_order, ama_Client_Ref, verbose_checkpoint)
        details = flightSearch.getFlightOffer(structuredData, automatic_order, ama_Client_Ref, verbose_checkpoint)
        

        if details["status"] == "ok" and details.data is None:
            verbose(f"{travelClassText}\n\nNo flights found", verbose_checkpoint)
            return OfferResult("", None)
        elif details["status"] == "error":
            if retries > 0:
                print(f"Error requesting offers - {details['data']}")
                verbose(f"Error requesting offers - {details['data']}", verbose_checkpoint)
                return OfferResult("", None)
            else:
                print("Encountered an error, trying one more time...")
                verbose("Encountered an error, trying one more time...", verbose_checkpoint)
                return getResponse(emailText, commentData, upsell, automatic_order, email_comment_id=email_comment_id,
                                   verbose_checkpoint=verbose_checkpoint, retries=1)
        

    
        
        print("final offer details with amenities:\n", details.data.flightOffers)
        generatedOffer = offerGenerator.generateFlightsString({"offers": details.data.flightOffers}, email_comment_id=email_comment_id, verbose_checkpoint=verbose_checkpoint)

        peopleString = ""
        if hasattr(details.data, "people"):
            if details.data.people:
                peopleString += "Reservation for:\n"
            people_list = getattr(details.data.people, 'people', [])
            for person in people_list:
                peopleString += f"{person['first_name']} {person['last_name']}\n"
            if people_list:
                peopleString += "\n"

        #print(offerGenerator.generateOffer(details["data"]["offers"][0]))

        print(details.data)
        print("flight details gathered")
        
        if len(details.data.flightOffers[0].flights) == 1 and details.data.flightOffers[0].flights[0]["departure"]["iataCode"] == "LJU" and details.data.flightOffers[0].flights[0]["arrival"]["iataCode"] == "CDG":
            verbose("AI could not provide an offer for this inquiry.", verbose_checkpoint)
            return OfferResult("", None)
        else:
            return OfferResult(f"{peopleString}{travelClassText}\n\n{generatedOffer}", details["data"])

    else:
        print("Not a flight travel request")
        verbose("Not a flight travel request", verbose_checkpoint)
        return OfferResult("", None)

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