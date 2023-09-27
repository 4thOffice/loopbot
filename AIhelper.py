import json
import os
import numpy as np
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

class AIhelper:

    prompt_loopbot = """Lets think step by step.

I am answering questions about our platform "Loop Email".
    
Here are previous conversations with other users that MAY be similar to the topic user asked about: {relavant_messages}.

Answer should be formal and short.

Chat history with this user: {memory}

User last said: {human_input}

Provide me with an answer I can send next based on chat history with this user."""


    prompt_regular_user = """Lets think step by step.
    
Here are previous conversations with other users that MAY be similar to the topic user asked about: {relavant_messages}.

Chat history with this user: {memory}

User last said: {human_input}

Reply to the user."""


    def __init__(self, openAI_APIKEY):
        global loader
        self.openAI_APIKEY = openAI_APIKEY

        os.environ['OPENAI_API_KEY'] = openAI_APIKEY

        underlying_embeddings = OpenAIEmbeddings()
        fs = LocalFileStore("./cache_loopbot_conversations/")
        json_path='./jsons/split.json'
        self.memoryStorage = {}
        
        #EMBEDDING PROCESS
        cached_embedder = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, fs, namespace=underlying_embeddings.model
        )

        loader = loader.JSONLoader(file_path=json_path)
        documents = loader.load()
        self.db = FAISS.from_documents(documents, cached_embedder)

        print("Finished embbeding")


    #print relavant information about a query
    def printRelavantChats(relavant_chats):
        for i, comment in enumerate(relavant_chats):
            print("Conversation context:", i, "score:", comment[1])

            context = comment[0].metadata["context"].split("    ")
            for txt in context:
                print(txt)

    #find relavant information abotu a query
    def findRelavantChats(self, input):
        relavant_chats = self.db.similarity_search_with_score(input, k=3)

        return relavant_chats
    
    def handleGoodResponse(self, context, AIresponse):
        return (AIresponse + " -> handeled as positive")
    
    def handleBadResponse(self, context, AIresponse):
        return (AIresponse + "  -> handeled as negative")

    def returnAnswer(self, recipient_userID, sender_userID):
        regular_user = True
        if sender_userID == "user_1552217":
            regular_user = False

        comments = directchatHistory.getAllComments(1000, recipient_userID)

        if len(comments) == 0:
            return "Hello!"
        
        memory = directchatHistory.memoryPostProcess(comments)
        
        if not regular_user:
            prompt = self.prompt_loopbot
        else:
            prompt = self.prompt_regular_user
        
        if comments[-1]["sender"] == "their message":
            user_input = comments[-1]["content"]
        else:
            return "Wait for user to reply."
        
        message_prompt = PromptTemplate(
        input_variables=["human_input", "relavant_messages", "memory"],
        template=prompt
        )
        
        #PRVA 2 RELAVANT CHATA STA OD USER INOUT IN ZADNJI JE OD USERINPUT + HISTORY
        if not regular_user:
            relavantChatsQuery = self.findRelavantChats(user_input)
            relavantChatsHistory = self.findRelavantChats(memory)
            print(relavantChatsHistory)
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

            relavantChats_noscore = [relavantChat[0] for relavantChat in relavantChats]
        
        else:
            relavantChats_noscore = "No relavant conversations"

        chain = LLMChain(
        llm=ChatOpenAI(temperature="0", model_name='gpt-3.5-turbo-16k'),
        #llm=ChatOpenAI(temperature="0", model_name='gpt-4'),
        prompt=message_prompt,
        verbose=True
        )
        reply = chain.run({"human_input": user_input, "relavant_messages": relavantChats_noscore, "memory": memory})

        """similarChats = []
        for comment in relavantChats:
            context = comment[0].metadata["context"].split("    ")
            similarChats.append({"context": context, "score": float(comment[1])})
            #print(context)"""

        reply = reply.replace("\n", "\\n")
        return reply, memory

#lb = AIhelper(keys.openAI_APIKEY)
#print(lb.returnAnswer("is there vpn?", lb.getPrompt(), "user_13"))