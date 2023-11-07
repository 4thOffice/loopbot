import json
import time
import openai
import keys
# Set your OpenAI API key
openai.api_key = keys.openAI_APIKEY

# Define the conversation
conversation = """
Customer:
I do not see my emails. I am a new customer

Support agent:
Can you send me a screenshot of the issue?

Customer:
Here it is

Support agent:
Have you connected your personal inbox?

Customer:
Huh, not sure. How do I do this?

Support agent:
to connect your personal inbox, please click on + on the sidebar next to "personal inboxes" section.

Customer:
Ok, I did it. Now I see a spinner, no emails

Support agent:
Wait a minute, and they will show up after some time

Customer:
Ah yes, I can see them now"""

def extractQuestions(conversation):
    prompt = "Extract important questions, which support agent can ask and will help categorize this issue if it appears next time, from this support conversation. Make sure that questions are posed in such way that support agent can ask the customer, so they shouldnt be in first person. Questions are not stated explicitly neccessarily:"

    system_msg = "You will be extracting questions from a conversation. Extract only up to a point where first customer issue has been solved. Format should be just questions and every question in new line."

    user_msg = prompt + "\n\n" + conversation

    response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                            messages=[{"role": "system", "content": system_msg},
                                            {"role": "user", "content": user_msg}])
    questionsExtracted = response["choices"][0]["message"]["content"]
    #print(questionsExtracted)

    # Split the conversation into lines and extract questions
    lines = questionsExtracted.split('\n')
    questions = [line.strip('- ').strip()[:-1] for line in lines if line.startswith('- ') or line.startswith('-') or line.startswith('')]

    # Print the extracted questions
    #for question in questions:
    #    print(question)

    return questions

def extractKeywords(conversation):
    prompt = "Extract important keywords, which will help categorize this issue if it appears next time, from this support conversation:"

    system_msg = "You will be extracting keywords from a conversation. Extract only a few keywords that you think are very important. Keywords should describe context of a customer, for example: IOS user, desktop user, new user, error etc. Format should be just keywords and every keyword in new line."

    user_msg = prompt + "\n\n" + conversation

    response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                            messages=[{"role": "system", "content": system_msg},
                                            {"role": "user", "content": user_msg}])
    keywordsExtracted = response["choices"][0]["message"]["content"]
    #print(keywordsExtracted)

    # Split the conversation into lines and extract questions
    lines = keywordsExtracted.split('\n')
    keywords = [line.strip('- ').strip() for line in lines if line.startswith('- ') or line.startswith('-') or line.startswith('')]

    # Print the extracted questions
    #for keyword in keywords:
        #print(keyword)

    return keywords


def getKeywords(conversationsJson):
    with open(conversationsJson, 'r') as file:
        # Load the JSON data into a Python object
        data = json.load(file)

    keywords = []
    for conversationIndex, conversation in enumerate(data):
        conversationData = data[conversation]
        if conversationIndex > 70:
            if conversationIndex % 20 == 0:
                print("issues till now: ", keywords)
        
            #if conversationIndex >= 70:
            #    return keywords
            time.sleep(5)
            print("index: ", conversationIndex)
            context = ""
            for msgIndex, msg in enumerate(conversationData):
                ID = msg['id']

                if msg["sender"] == "our response":
                    sender = "Support agent"
                else:
                    sender = "Customer"

                commentQuotedID = msg['commentQuotedID']
                message = msg['message']
                sequenceNumber = msgIndex
                conversationID = conversation

                context += sender + ":\n" + message + "\n\n"
            try:
                keyword = extractKeywords(context)
                print("got keyword")
            except:
                print("continued")
                continue
            print(keyword)
            keywords.append(keyword)

    return keywords

print(getKeywords("./jsons/split.json"))
#print(extractQuestions(conversation))
#print(extractKeywords(conversation))