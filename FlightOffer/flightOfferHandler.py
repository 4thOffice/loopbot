import io
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

def getFlightOfferAutomation(attachments, subject, htmlEmailtext, plainText, verbose_checkpoint: typing.Callable[[str], None] = None):
    commentData = classification.getFiles(attachments, htmlEmailtext, verbose_checkpoint)
    emailText = "Subject: " + subject + "\n" + plainText
    return getResponse(emailText, commentData, verbose_checkpoint)

def getFlightOffer(cardID=None, authKey=None):
    print(cardID)
    
    commentData = classification.getFirstCommentData(cardID, authKey)
    if commentData["id"] is None:
        return({"parsedOffer": ("Failed to gather email data."), "details": None})

    emailText = classification.getCommentContent(commentData["id"], authKey)
    
    return getResponse(emailText, commentData)


def getResponse(emailText, commentData, verbose_checkpoint=None, retries=0):
    answer = classification.classifyEmail(emailText)
    print("raw email text:", emailText)

    AIregular_ = AIregular.AIregular(keys.openAI_APIKEY)
    if answer:
        filesText = []
        filesPicture = []
        file_content = None
        print(commentData["fileUrls"])
        for fileUrl in commentData["fileUrls"]:
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
            prompt = "Extract ALL flight details from the email and attached images which I will give you. Extract data like origin, destionation, dates, timeframes, requested connection points (if specified explicitly) and ALL other flight information.\n\nDo not forget to extract data from images too. Email:\n" + emailText
            flightDetailsImages = AIregular_.processImages(prompt, filesPicture)
            verbose("Asking picture specialized agent with " + str(len(filesPicture)) + " files", verbose_checkpoint)
            if len(filesText) <= 0:
                flightDetails = flightDetailsImages
        if len(filesText) > 0 or len(filesPicture) == 0:
            print("Asking text specialized agent - ", str(len(filesText)) + " files")
            if len(filesPicture) > 0:
                flightDetails = dataExtractor.askGPT(emailText, filesText, imageInfo=flightDetailsImages)
            else:
                flightDetails = dataExtractor.askGPT(emailText, filesText)
            verbose("Asking text specialized agent with " + str(len(filesPicture)) + " files", verbose_checkpoint)

        details = flightSearch.getFlightOffer(flightDetails, verbose_checkpoint)
        if details["status"] == "ok" and details["data"] is None:
            return({"parsedOffer": "[TravelAI Success]\n\nNo flights found", "details": None})
        elif details["status"] == "error":
            if retries > 0:
                return({"parsedOffer": "[TravelAI Error]\n\n" + details["data"], "details": None})
            else:
                print("Encountered an error, trying one more time...")
                return getResponse(emailText, commentData, verbose_checkpoint, retries=1)
        
        #generatedOffer = offerGenerator.generateOffer(emailText, details)
        generatedOffer = offerGenerator.generateFlightsString(details["data"])
        
        print("flight details gathered")
        return({"parsedOffer": "[TravelAI Success]\n\n" + generatedOffer, "details": details["data"]})

    else:
        print("Not a flight tender inquiry")
        return({"parsedOffer": "[TravelAI Success]\n\n" + "Not a flight tender inquiry", "details": None})

#authKey = whitelist["user_1552217"]
#getFlightOffer("DCwm6ekeYTewrKkymigycY4PBIA0T", authKey)