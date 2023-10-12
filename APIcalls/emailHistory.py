import requests

def memoryPostProcess(comments, username=""):
    formatted_messages = []

    for message in comments:
        sender = message['sender']
        content = message['content']
        
        if username != "":
            if sender == username:
                formatted_messages.append(f'Me: \n{content}\n\n')
            else:
                formatted_messages.append(f'Recipient: \n{content}\n\n')
        else:
            formatted_messages.append(f'{sender}:\n {content}\n')

    result = '\n'.join(formatted_messages)
    return result

#Get user id  of a user you are impersonating in this contact
def getContactUserID(contactID, userID, sender_name, authkey):
    endpoint_url = 'https://api.intheloop.io/api/v1/contact/list'

    headers = {
        'accept': 'application/json',
        'Authorization': authkey,
        'Content-Type': 'application/json'
    }

    data = {
        "size": 1,
        "contactIds": [
            contactID
        ],
    }

    response = requests.get(endpoint_url, headers=headers, params=data)
    if response.status_code == 200:
        response = response.json()["resources"][0]
        print(response)
        if response["groupType"] == "PersonalInbox":
            allowedImpersonatedSender = response["allowedImpersonatedSenders"]["resources"][0]
            return (allowedImpersonatedSender["id"], allowedImpersonatedSender["name"])
        elif response["groupType"] == "SharedInbox":
            return (userID, sender_name)
        return None
    else:
        print(f"Error: {response.status_code} - {response.text}")

#get all emails by card ID
#copy id dobi comment chate, original id pa comment maile
def getEmailHistory(cardID, impersonated_userID, impersonated_username, authkey):
    endpoint_url = 'https://api.intheloop.io/api/v1/comment/list'

    headers = {
        'accept': 'application/json',
        'Authorization': authkey,
        'Content-Type': 'application/json'
    }

    data = {
        "offset": 0,
        "size": 1024,
        "sortOrder": "Ascending",
        "cardIds": [
            cardID + "-copy1T",
            cardID
        ],
        "authorizeCardIdsBeforeSearch": False,
        "cardTypes": "",
        "htmlFormat": "text/html"
    }

    response = requests.get(endpoint_url, headers=headers, params=data)
    if response.status_code == 200:
        comments = response.json()
        comments_return = []
        for comment in comments["resources"]:
            if comment["$type"] == "CommentMail":
                #print("comment mail")
                if comment["author"]["id"] == impersonated_userID:
                    print("Me")
                    comments_return.append({"sender": impersonated_username, "content": comment["snippet"]})
                else:
                    print("Recipient")
                    comments_return.append({"sender": comment["author"]["name"], "content": comment["snippet"]})

                print(comment["snippet"])
            #elif comment["$type"] == "CommentChat":
                #print("comment chat")

        return comments_return
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []
        
#userID, username = getContactUserID("CCr7jNfk92eIEmEGrRRfw_cbfVw0T", "user_24534935", "Niko Šneberger", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1X2lkIjoiMjQ1NjQ3NjkiLCJhdF9pZCI6IjI0NTY0NzY5XzY4Mjg5NTdlLTY2YTEtODU0YS1lYjk5LTIwY2U2NjkyYTdmNyIsImF1dGhfdHlwZSI6IjciLCJuYmYiOjE2OTY1NzQ0OTksImV4cCI6MTY5NzQzODQ5OSwiaWF0IjoxNjk2NTc0NDk5fQ.QOTuU8Fg4tVYf_6fvLrEP7YxaWePZju18biKmYCM7Og")
#print(userID)

#emailHistory = getEmailHistory("ACr7joNC3rF6x9kmwIFC2J-QUKA0T", userID, username, "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1X2lkIjoiMjQ1NjQ3NjkiLCJhdF9pZCI6IjI0NTY0NzY5XzY4Mjg5NTdlLTY2YTEtODU0YS1lYjk5LTIwY2U2NjkyYTdmNyIsImF1dGhfdHlwZSI6IjciLCJuYmYiOjE2OTY1NzQ0OTksImV4cCI6MTY5NzQzODQ5OSwiaWF0IjoxNjk2NTc0NDk5fQ.QOTuU8Fg4tVYf_6fvLrEP7YxaWePZju18biKmYCM7Og")
#print(emailHistory)