import io
import json
import requests
import classification
import dataExtractor
import magic
import flightSearch

with open('../whitelist.json', 'r') as file:
    whitelist = json.load(file)

def getFlightOffer(cardID, authKey):
    commentData = classification.getFirstCommentData(cardID, authKey)
    emailText = classification.getCommentContent(commentData["id"], authKey)
    answer = classification.classifyEmail(emailText)
    print(emailText)
    print(answer)

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

        print("Not a tender enquiry" + str(details["price"]))
        return("flight details gathered" + str(details["price"]))

    else:
        print("Not a tender enquiry")
        return("Not a tender enquiry")

#authKey = whitelist["user_1552217"]
#getFlightOffer("DCwm6ekeYTewrKkymigycY4PBIA0T")