# loopbot

Run instructions:

1. Set up keys.py in root directory with variables: openAI_APIKEY = "" (openAI API key), authKey = "" (bearer for loopbot)
2. Set up whitelist.json in root directory:
   {
   "user_id_1": "{Authorization token}",
   "user_id_2": "{Authorization token}",
   ...
   }
3. loopbot> python chat.py - create a json of all loopbot chat data
4. loopbot> python conversationSplitter.py - create a json of all chat data split into seperate topics
5. loopbot> python AIserver.py - run backend server
