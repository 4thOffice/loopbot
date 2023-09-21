import math
import os
import requests
import models.comment as comment
import json
import keys
import sys

os.environ['OPENAI_API_KEY'] = keys.openAI_APIKEY
loopbotID = "user_1552217"
authkey = keys.authKey
fromYear = 2021
offsetHistoryId = ""
dataPerEmail = []

#hardcoded messages to ignore -> system messages
messagestoExclude= ["Wohoo! Your account was successfully upgraded to a pro plan. We can't wait to see what Loop will do for you and your team.",
                    "Hi there! Your free trial has now come to an end. Please upgrade to a paid plan to continue using Loop. We have pricing plans that suit all types of teams. Subscribe here.",
                    "has just joined Loop Email. Say Hi!",
                    "Your account has been changed to a sponsored account.",
                    "Your account has been changed to a free trial. We'd love to hear any feedback as you're testing out Loop.",
                    "thrilled to have you on board!",
                    "Wohoo! Your account was successfully upgraded to a paid plan. We can't wait to see what Loop will do for you and your team.",
                    "Let us know how you get on with trying out Loop.",
                    "Let us know how you get on with trying out Loop. Remember, I'm here to support you throughout your journey",
                    "Your free trial has ended",
                    "Your account was successfully",
                    "successfully added you to the reporting and personal rules early beta programs",
                    "free trial",
                    "upgraded to a paid plan",
                    "why not download Loop to give us a try",
                    "Checking in to see how the trial is going."]

def checkIfSystemMessage(commentToCheck):
    if "tags" in commentToCheck and "tags" in commentToCheck["tags"] and "resources" in commentToCheck["tags"]["tags"]:
        for tag in commentToCheck["tags"]["tags"]["resources"]:
            if tag["id"] == "SYSTEMMESSAGE":
                return True

    for sysMsg in messagestoExclude:
        if sysMsg in commentToCheck["snippet"]:
            return True
    return False

#get last historySize comments of a conversation with userID
def getComments(historySize, userID, historyID):
        
        endpoint_url = 'https://api.intheloop.io/api/v1/search/list'

        headers = {
            'accept': 'application/json',
            'Authorization': authkey,
            'Content-Type': 'application/json'
        }

        data = {
            "$type": "SearchQueryComment",
            "size": historySize,
            "historyId": historyID,
            "historyStartDate": "2021-01-01T00:00:00.021Z",
            "sortOrder": "Ascending",
            "sortType": "ModifiedDate",
            "commonCommentConditions": {
                "cardTypes": ["CardChat"],
                "contactIds": [userID] 
            },
            "groupComments": False
        }

        response = requests.post(endpoint_url, headers=headers, json=data)
        
        loopbot_responded = False
        if response.status_code == 200:
            commentsJson = []
            for item in response.json()["resources"]: #for each comment in a conversation
                if item["attachments"]["size"] > 0 or checkIfSystemMessage(item): #if comment is an image or doesnt have a "comment" field?, skip it
                    continue

                datetime_string = item["created"]
                year = datetime_string.split("-")[0]
                if int(year) < fromYear:
                    continue

                commentID = item["id"]
                commentMessage = item["snippet"]
                quoteCommentID = None
                if "quoteCommentId" in item:
                    quoteCommentID = item["quoteCommentId"]
                else:
                    quoteCommentID = "none"
                
                if item["author"]["id"] == loopbotID:
                    sender = "our response"
                    loopbot_responded = True
                else:
                    sender = "their message"

                commentInstance = comment.comment(commentID, sender, quoteCommentID, datetime_string, commentMessage)
                commentsJson.append(commentInstance.__dict__) #LIST OF JSONS FOR EACH COMMENT in a conversation
            
            if loopbot_responded == False:
                commentsJson.clear()
            return commentsJson
        else:
            print(f"Error: {response.status_code} - {response.text}")


"""
{
  "queryText": "",
  "size": 40,
  "sortOrder": "Descending",
  "sortType": "ModifiedDate",
  "$type": "SearchQueryConversation",
  "showInView": {
    "view": "LoopInbox",
    "filter": "Chats"
  },
  "channelIds": []
}
"""

#get user ID for each conversation
def getConversations(historySize):
    global offsetHistoryId
    print("Gathering user IDs...")

    endpoint_url = 'https://api.intheloop.io/api/v1/conversation/list'

    headers = {
        'accept': 'application/json',
        'Authorization': authkey,
        'Content-Type': 'application/json'
    }

    data = {
        "queryText": "",
        "size": historySize,
        "historyId": offsetHistoryId,
        "sortOrder": "Descending",
        "sortType": "ModifiedDate",
        "$type": "SearchQueryConversation",
        "showInView": {
            "view": "LoopInbox",
            "filter": "Chats"
        },
        "conversationDateFrom": "2021-01-01T00:00:00.021Z",
        "channelIds": []
    }

    response = requests.post(endpoint_url, headers=headers, json=data)
    
    if response.status_code == 200:
        userIDs = []
        userEmails = []
        items = response.json()["resources"]
        if len(items) <= 0: #if empty response
            return []
        
        for item in items:
            try:
                #check if not group:
                if item["sharedTags"]["parent"]["$type"] == "ResourceBase" and item["cardId"].startswith("CC_"):
                    userID1 = item["snippet"]["sender"]["id"]
                    userEmail = "-"
                    if(userID1 == loopbotID):
                        userID2 = item["toList"]["resources"][0]["id"]
                        userEmail = item["toList"]["resources"][0]["email"]
                        userIDs.append(userID2)
                        userEmails.append(userEmail)
                    else:
                        userEmail = item["snippet"]["sender"]["email"]
                        userIDs.append(userID1)
                        userEmails.append(userEmail)
            except:
                print("Error while gathering userID")
        offsetHistoryId = response.json()["offsetHistoryId"]
        print("Finished gathering user IDs.")
        return [userIDs, userEmails]
    else:
        print(f"Error: {response.status_code} - {response.text}")
    

#Returns json file of all
def getAllChatData(amountOfConversations, amountOfcomments, chunkSize):
    allComments = {}

    for groupIndex in range(0, math.ceil(amountOfConversations/chunkSize)):
        conversationsReturned = getConversations(min(chunkSize, amountOfConversations - (groupIndex*chunkSize)))

        if len(conversationsReturned) < 2:
            print("Finished gathering all chat data for group ", groupIndex, "...")
            break
        userIDs = conversationsReturned[0]
        userEmails = conversationsReturned[1]

        if len(userIDs) <= 0:
            print("Finished gathering all chat data for group ", groupIndex, "...")
            break
        print("Gathering all chat data for group ", groupIndex, "...")
        for i, userID in enumerate(userIDs):
            print("gathering chat data for user: ", groupIndex*chunkSize + i)
            comments = getComments(amountOfcomments, userID, "")
            if len(comments) > 0: #only add conversation to the final list if it includes non-system comments
                #allComments[userEmails[i]] = comments
                dataPerEmail.append((userEmails[i], len(comments)))
                allComments["conversation" + str(groupIndex*chunkSize + i)] = comments

        print("Finished gathering all chat data for group ", groupIndex, "...")

    json_string = json.dumps(allComments, indent=2) 
    #print(json_string)
    print("Finished gathering all chat data.")
    return json_string


if __name__ == "__main__":
    chatData = getAllChatData(10000, 1000, 1000)

    f = open("./jsons/chats.json", "w")
    #print(chatData)
    f.write(chatData)
    f.close()

    with open('dataPerEmail.txt', 'w') as fp:
        for item in dataPerEmail:
            # write each item on a new line
            fp.write("email: " + item[0] + " | comment count: " + str(item[1]) + "\n")