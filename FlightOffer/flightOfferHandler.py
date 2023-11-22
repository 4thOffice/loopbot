import io
import json
import requests
import classification
import dataExtractor
import magic
import flightSearch
import offerGenerator

def getFlightOfferAutomation(attachments, subject, htmlEmailtext, plainText):
    commentData = classification.getFiles(attachments, htmlEmailtext)
    emailText = "Subject: " + subject + "\n" + plainText
    return getResponse(emailText, commentData)

def getFlightOffer(cardID=None, authKey=None):
    print(cardID)
    
    commentData = classification.getFirstCommentData(cardID, authKey)
    if commentData["id"] is None:
        return({"parsedOffer": ("Failed to gather email data."), "details": None})

    emailText = classification.getCommentContent(commentData["id"], authKey)
    
    return getResponse(emailText, commentData)


def getResponse(emailText, commentData, retries=0):
    answer = classification.classifyEmail(emailText)
    print("raw email text:", emailText)

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
                filesPicture.append(file_content)
            else:
                filesText.append(file_content)

        if len(filesPicture) > 0:
            print("Asking picture specialized agent - ", str(len(filesPicture)) + " files")
            flightDetails = dataExtractor.askGPT(emailText, filesPicture, hasImages=True)
        if len(filesText) > 0 or len(filesPicture) == 0:
            print("Asking text specialized agent - ", str(len(filesText)) + " files")
            flightDetails = dataExtractor.askGPT(emailText, filesText, hasImages=False)

        details = flightSearch.getFlightOffer(flightDetails)
        if details["status"] == "ok" and details["data"] is None:
            return({"parsedOffer": "[FlightOfferAgentAI]\n\nNo flights found", "details": None})
        elif details["status"] == "error":
            if retries > 0:
                return({"parsedOffer": "[FlightOfferAgentAI]\n\n" + details["data"], "details": None})
            else:
                print("Encountered an error, trying one more time...")
                return getResponse(emailText, commentData, retries=1)
        
        #generatedOffer = offerGenerator.generateOffer(emailText, details)
        generatedOffer = offerGenerator.generateFlightsString(details["data"])
        
        print("flight details gathered")
        return({"parsedOffer": "[FlightOfferAgentAI]\n\n" + generatedOffer, "details": details["data"]})

    else:
        print("Not a flight tender enquiry")
        return({"parsedOffer": "[FlightOfferAgentAI]\n\n" + "Not a flight tender enquiry", "details": None})

#authKey = whitelist["user_1552217"]
#getFlightOffer("DCwm6ekeYTewrKkymigycY4PBIA0T", authKey)