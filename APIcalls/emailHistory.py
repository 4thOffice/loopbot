import requests

#Get user id  of a user you are impersonating in this contact
def getContactUserID(contactID, userID, authkey):
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
        if response["groupType"] == "PersonalInbox":
            return response["allowedImpersonatedSenders"]["resources"][0]["id"]
        elif response["groupType"] == "SharedInbox":
            return userID
        return None
    else:
        print(f"Error: {response.status_code} - {response.text}")

#get all emails by card ID
#copy id dobi comment chate, original id pa comment maile
def getEmailHistory(cardID, impersonated_userID, authkey):
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
        for comment in comments["resources"]:
            if comment["$type"] == "CommentMail":
                print("comment mail")
                if comment["author"]["id"] == impersonated_userID:
                    print("Me")
                else:
                    print("Recipient")
                print(comment["snippet"])
            elif comment["$type"] == "CommentChat":
                print("comment chat")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        
userID = getContactUserID("CCr7jNfk92eIEmEGrRRfw_cbfVw0T", "user_24534935", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1X2lkIjoiMjQ1NjQ3NjkiLCJhdF9pZCI6IjI0NTY0NzY5XzY4Mjg5NTdlLTY2YTEtODU0YS1lYjk5LTIwY2U2NjkyYTdmNyIsImF1dGhfdHlwZSI6IjciLCJuYmYiOjE2OTY1NzQ0OTksImV4cCI6MTY5NzQzODQ5OSwiaWF0IjoxNjk2NTc0NDk5fQ.QOTuU8Fg4tVYf_6fvLrEP7YxaWePZju18biKmYCM7Og")
print(userID)

getEmailHistory("ACr7joNC3rF6x9kmwIFC2J-QUKA0T", userID, "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1X2lkIjoiMjQ1NjQ3NjkiLCJhdF9pZCI6IjI0NTY0NzY5XzY4Mjg5NTdlLTY2YTEtODU0YS1lYjk5LTIwY2U2NjkyYTdmNyIsImF1dGhfdHlwZSI6IjciLCJuYmYiOjE2OTY1NzQ0OTksImV4cCI6MTY5NzQzODQ5OSwiaWF0IjoxNjk2NTc0NDk5fQ.QOTuU8Fg4tVYf_6fvLrEP7YxaWePZju18biKmYCM7Og")
