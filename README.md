# loopbot

AI loopbot

logic behind the bot:
Get all userIDs with which loopbot has talked to, load all chat data for each conversation from those userIDs,
turn this conversations data to json, split this json by topic and create new json, vectorize, embbed and store data,
get user query, perform similarity search on the stored data, give openAI model most similar previous conversations.

Run instructions:

1. Set up keys.py with variables: openAI_APIKEY = "" (openAI API key), authKey = "" (bearer for loopbot)
2. python chat.py - create a json of all chat data
3. python conversationSplitter.py - create a json of all chat data split into seperate topics
4. python loopBot.py - run the AI
