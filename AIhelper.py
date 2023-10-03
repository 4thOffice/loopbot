import json
import os
import numpy as np
import json
from langchain.schema import SystemMessage
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import BaseOutputParser
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
import loader
from langchain.memory import ConversationBufferMemory
from langchain.storage import LocalFileStore
from langchain.embeddings import OpenAIEmbeddings, CacheBackedEmbeddings
from datetime import datetime
import sys
sys.path.append('./APIcalls')
import APIcalls.directchatHistory as directchatHistory
from langchain.docstore.document import Document
from langchain.evaluation import load_evaluator, EmbeddingDistance

class AIhelper:

    prompt_loopbot = """Lets think step by step.

You are answering questions about our platform "Loop Email".
    
Here are relavant conversations with other people with similar topic:
{relavant_messages}.

Answer should be formal and short."""


    prompt_regular_user = """Lets think step by step.

You are talking to a user.
I want you to reply to a user based on the following information:
    
{relavant_messages}

"""


    def __init__(self, openAI_APIKEY):
        global loader
        self.openAI_APIKEY = openAI_APIKEY

        os.environ['OPENAI_API_KEY'] = openAI_APIKEY

        underlying_embeddings = OpenAIEmbeddings()
        fs = LocalFileStore("./cache_loopbot_conversations/")
        json_path='./jsons/split.json'
        
        #EMBEDDING PROCESS
        cached_embedder = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, fs, namespace=underlying_embeddings.model
        )

        loader_ = loader.JSONLoader(file_path=json_path)
        documents = loader_.load()
        self.db_loopbot_data = FAISS.from_documents(documents, cached_embedder)

        print("Finished embbeding loopbot data")


        #GOOD RESPONSES EMBEDDING 
        fs = LocalFileStore("./cache_good_responses/")
        json_path='./jsons/good_responses.json'
        cached_embedder_good = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, fs, namespace=underlying_embeddings.model
        )

        loader_ = loader.JSONLoader(file_path=json_path)
        documents = loader_.loadResponses()
        self.db_good_responses = FAISS.from_documents(documents, cached_embedder_good)

        print("Finished embbeding good responses data")

        # BAD RESPONSES EMBEDDING 
        fs = LocalFileStore("./cache_bad_responses/")
        json_path='./jsons/bad_responses.json'
        cached_embedder_bad = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, fs, namespace=underlying_embeddings.model
        )

        loader_ = loader.JSONLoader(file_path=json_path)
        documents = loader_.loadResponses()
        self.db_bad_responses = FAISS.from_documents(documents, cached_embedder_bad)

        print("Finished embbeding good responses data")

    def write_json(self, new_data, filepath):
        with open(filepath,'r+') as file:
            file_data = json.load(file)
            file_data["responses"].append(new_data)
            file.seek(0)
            json.dump(file_data, file, indent = 2)

    #print relavant information about a query
    def printRelavantChats(relavant_chats):
        for i, comment in enumerate(relavant_chats):
            print("Conversation context:", i, "score:", comment[1])

            context = comment[0].metadata["context"].split("    ")
            for txt in context:
                print(txt)

    #find relavant information abotu a query
    def findRelavantChats(self, input):
        relavant_chats = self.db_loopbot_data.similarity_search_with_score(input, k=3)

        return relavant_chats
    
    def findResponses(self, recipient_userID):
        context = directchatHistory.getAllComments(5, recipient_userID)
        contextLastTopic = directchatHistory.getLastTopic(context)

        if len(contextLastTopic) > 0:
            context = contextLastTopic

        lastMsg1 = context[-1]["content"]
        
        context = directchatHistory.memoryPostProcess(context)

        goodResponses = self.db_good_responses.similarity_search_with_score(context, k=3)
        badResponses = self.db_bad_responses.similarity_search_with_score(context, k=3)

        responsesGood = []
        print("good:")
        for response in goodResponses:
            print("score", response[1])
            print("data", response[0])
            if response[1] <= 0.07:
                print("lastMsg1: ", lastMsg1)
                lastMsg2 = response[0].page_content.split("\n")[-2]
                print("lastMsg2: ", lastMsg2)
 
                evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
                distance = evaluator.evaluate_string_pairs(
                    prediction=lastMsg1, prediction_b=lastMsg2
                )

                print("distance: ", distance["score"])

                if distance["score"] < 0.2:
                    responsesGood.append(response[0].metadata["AIresponse"])

        responsesBad = []
        print("bad:")
        for response in badResponses:
            print("score", response[1])
            print("data", response[0])
            if response[1] <= 0.07:
                responsesBad.append(response[0].metadata["AIresponse"])
            
        return responsesGood, responsesBad

    def handleGoodResponse(self, recipient_userID, AIresponse):
        context = directchatHistory.getAllComments(5, recipient_userID)
        contextLastTopic = directchatHistory.getLastTopic(context)

        if len(contextLastTopic) > 0:
            context = contextLastTopic
            
        context = directchatHistory.memoryPostProcess(context)
        context += "\n" + AIresponse

        good_responses = self.db_good_responses.similarity_search_with_score(context, k=1)
        
        #check if similar good responses already exist
        if good_responses[0][1] > 0.04:
            new_document = Document(page_content=context, metadata=dict(AIresponse=AIresponse))
            self.db_good_responses.add_documents([new_document])

            self.write_json({"context": context, "AIresponse": AIresponse}, "./jsons/good_responses.json")

        return (AIresponse + " -> handeled as positive")
    
    def handleBadResponse(self, recipient_userID, AIresponse):

        context = directchatHistory.getAllComments(5, recipient_userID)
        contextLastTopic = directchatHistory.getLastTopic(context)

        if len(contextLastTopic) > 0:
            context = contextLastTopic
            
        context = directchatHistory.memoryPostProcess(context)
        context += "\n" + AIresponse

        bad_responses = self.db_bad_responses.similarity_search_with_score(context, k=1)
        
        print("distance:", bad_responses[0][1])

        #check if similar good responses already exist
        if bad_responses[0][1] > 0.04:
            new_document = Document(page_content=context, metadata=dict(AIresponse=AIresponse))
            self.db_bad_responses.add_documents([new_document])

            self.write_json({"context": context, "AIresponse": AIresponse}, "./jsons/bad_responses.json")

        return (AIresponse + "  -> handeled as negative")

    def returnAnswer(self, recipient_userID, sender_userID, badResponsesPrevious):
        conversationBuffer = ConversationBufferMemory()
        
        regular_user = True
        if sender_userID == "user_1552217":
            regular_user = False

        comments = directchatHistory.getAllComments(10, recipient_userID)

        for message in comments:
            sender = message['sender']
            content = message['content']
            if sender == "my response":
                conversationBuffer.chat_memory.add_ai_message(content)
            else:
                conversationBuffer.chat_memory.add_user_message(content)

        if len(comments) == 0:
            return "Hello!", ""
        
        memory = directchatHistory.memoryPostProcess(comments)
        
        if not regular_user:
            prompt = self.prompt_loopbot
        else:
            prompt = self.prompt_regular_user
        
        if comments[-1]["sender"] == "their message":
            user_input = comments[-1]["content"]
        else:
            return "Wait for user to reply.", ""
        
        #PRVA 2 RELAVANT CHATA STA OD USER INOUT IN ZADNJI JE OD USERINPUT + HISTORY
        if not regular_user:
            relavantChatsQuery = self.findRelavantChats(user_input)
            relavantChatsHistory = self.findRelavantChats(memory)

            #Take 2 top results for query similarity search (if similarity not over threshold) and 1 for whole history similarity search
            relavantChats = []
            for comment in relavantChatsQuery:
                if len(relavantChats) >= 1:
                    break
                if comment[1] < 0.4:
                    relavantChats.append(comment)
            for comment in relavantChatsHistory:
                if len(relavantChats) >= 3:
                    break
                relavantChats.append(comment)

            #relavantChats_noscore = [relavantChat[0].metadata["context"] for relavantChat in relavantChats]
            relavantChats_noscore = ""
            for index, relavantChat in enumerate(relavantChats):
                relavantChats_noscore += f"\nConversation {index}:\n"
                relavantChats_noscore += relavantChat[0].metadata["context"]
        
        else:
            relavantChats_noscore = ""

        goodResponses, badResponses = self.findResponses(recipient_userID)
        
        system_prompt = SystemMessage(content="You are a chatbot having a conversation with a human.")

        if len(goodResponses) > 0:
            system_prompt.content = system_prompt.content + """

Use the following reply options as starting point: \n"""
            for index, response in enumerate(goodResponses, start=1):
                system_prompt.content += f"- {response}\n"

        if len(badResponses) > 0 or len(badResponsesPrevious) > 0:

            system_prompt.content = system_prompt.content + """

DO NOT use the following replies. They are examples of BAD replies. Come up with something totally different from these: \n"""
            for index, response in enumerate(badResponses + badResponsesPrevious, start=1):
                system_prompt.content += f"- {response}\n"

        prompt = prompt + """

Answer to this message from user: """ + user_input + """

Reply to the user last messages best as you can based on chat history and examples of bad replies you have been provided. Also take information from relavant conversations You have been provided. Only provide a reply to user's last message. Provide a message I can copy and paste - no explaination or chat history and unneccessary content. Give a reply that is different from bad reply examples"""
        
        print(conversationBuffer.load_memory_variables({}))

        message_prompt = PromptTemplate(
        input_variables=["relavant_messages"],
        template=prompt
        )

        # Create a human message template
        human_message_template = HumanMessagePromptTemplate.from_template(prompt)

        # Create a chat prompt template from the system message, chat history placeholder, and human message template
        chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_message_template])

            
        chain = LLMChain(
        llm=ChatOpenAI(temperature="1.0", model_name='gpt-3.5-turbo-16k'),
        #llm=ChatOpenAI(temperature="0", model_name='gpt-4'),
        prompt=chat_prompt,
        memory=conversationBuffer,
        verbose=True
        )
        reply = chain.run({"relavant_messages": str(relavantChats_noscore)})

        reply = reply.replace("\n", "\\n")
        return reply, memory
    

#lb = AIhelper(keys.openAI_APIKEY)
#print(lb.returnAnswer("is there vpn?", lb.getPrompt(), "user_13"))