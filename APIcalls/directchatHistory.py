import sys
sys.path.append('..')
import keys
import requests
import keys
import sys
import json
from dateutil import parser

#authkey = keys.authKey

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
                    "Checking in to see how the trial is going.",
                    "Welcome to Loop!",
                    "Your account was changed to a sponsored account"]

#returns tiem difference in hours
def getTimeDifference(msg1time, msg2time):
    date1 = parser.parse(msg1time)
    date2 = parser.parse(msg2time)

    if date1 >= date2:
        time_difference = date1 - date2
    else:
        time_difference = date2 - date1

    seconds = time_difference.total_seconds()
    hours = seconds / (60 * 60)

    return hours

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
def getAllComments(historySize, userID, authkey):
    endpoint_url = 'https://api.intheloop.io/api/v1/search/list'

    headers = {
        'accept': 'application/json',
        'Authorization': authkey,
        'Content-Type': 'application/json'
    }

    data = {
        "$type": "SearchQueryComment",
        "size": historySize,
        "historyId": "",
        "sortOrder": "Descending",
        "sortType": "ModifiedDate",
        "commonCommentConditions": {
            "cardTypes": ["CardChat"],
            "contactIds": [userID] 
        },
        "groupComments": False
    }

    response = requests.post(endpoint_url, headers=headers, json=data)
    if response.status_code == 200:
        comments = []
        for item in response.json()["resources"]: #for each comment in a conversation
            if item["attachments"]["size"] > 0 or checkIfSystemMessage(item): #if comment is an image or doesnt have a "comment" field?, skip it
                continue

            commentMessage = item["snippet"]
            creationTime = item["created"]

            if item["author"]["id"] != userID:
                sender = "my response"
            else:
                sender = "their message"

            comment = {"sender": sender, "content": commentMessage, "creationTime": creationTime}
            comments.append(comment)
            
        comments.reverse()
        return comments
    else:
        print(f"Error: {response.status_code} - {response.text}")

#get comments of the last topic in a comment set
def getLastTopic(comments):
    timeDifferenceThreshold = 72 #in hours
    commentsInTopic = []

    i = len(comments)-1
    while i >= 1:
        comment = comments[i]
        commentPrior = comments[i-1]
        if getTimeDifference(comment["creationTime"], commentPrior["creationTime"]) > timeDifferenceThreshold:
            commentsInTopic.append(comment)
            break
        commentsInTopic.append(comment)
        i -= 1
    
    if len(comments) == 1:
        commentsInTopic.append(comments[0])
    elif comments[1] in commentsInTopic and getTimeDifference(comments[0]["creationTime"], comments[1]["creationTime"]) < timeDifferenceThreshold:
        commentsInTopic.append(comments[0])

    commentsInTopic.reverse()

    print("comments in topic: ", commentsInTopic)
    return commentsInTopic

def memoryPostProcess(comments):
    formatted_messages = []

    for message in comments:
        sender = message['sender']
        content = message['content']
        
        if sender == 'my response':
            formatted_messages.append(f'AI: {content}')
        elif sender == 'their message':
            formatted_messages.append(f'user: {content}')

    result = '\n'.join(formatted_messages)
    return result

def memoryPostProcessForStorage(comments):
    formatted_messages = []

    for message in comments:
        sender = message['sender']
        content = message['content']
        
        if sender == 'my response':
            formatted_messages.append(f'AI: {content}')
        elif sender == 'their message':
            formatted_messages.append(f'user: {content}')

    result = '\n'.join(formatted_messages)
    return result

#allComments = getAllComments(50, "user_1552217")
#print(allComments)
#lastTopic = getLastTopic(allComments)
#print(lastTopic)