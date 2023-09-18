import json
from dateutil import parser

f = open('chatsBigCollection.json')

relavanceTimeLimit = 72 #48 hours, load all comments that are at most this far apart from each other

data = json.load(f)

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


subConversations = {}#conversations split into different topics
convIndex = 0
for i, conversation in enumerate(data):
    conversationData = data[conversation]
    print("Splitting conversation:", str(i+1) + "/" + str(len(data)))

    msgIndex = 0
    conv = []
    while msgIndex < len(conversationData)-1:
        msg = conversationData[msgIndex]
        msgNext = conversationData[msgIndex+1]

        conv.append(msg)
        if getTimeDifference(msg["datetime"], msgNext["datetime"]) > relavanceTimeLimit:
            #print("split")
            subConversations["conversation" + str(convIndex)] = conv
            convIndex += 1
            conv = []

        msgIndex += 1
    
    if getTimeDifference(conversationData[msgIndex-1]["datetime"], conversationData[msgIndex]["datetime"]) > relavanceTimeLimit:
        conv = [conversationData[msgIndex]]
    else:
        conv.append(conversationData[msgIndex])
    
    subConversations["conversation" + str(convIndex)] = conv  
    convIndex += 1    

json_string = json.dumps(subConversations, indent=2)
f = open("split.json", "w")
#print(chatData)
f.write(json_string)
f.close()

