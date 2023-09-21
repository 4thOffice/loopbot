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

class LoopBot:

    prompt_starting = """Lets think step by step.

You are a helpful assistant answering questions about our platform "Loop Email".
    
User asked the following question: {human_input} 
        
Here are previous conversations with other users similar to the topic user asked about: {relavant_messages}.

Do NOT mention this previous conversations information.

Do NOT mention previous conversations with other users you have been provided. Act like you are customer support.

Answer should be formal and short.

If you do not know the answer, just say you do not know the answer.

Metadata description:
    context: conversation context
        
Chat history with this user: {chat_history}

Do NOT mention this Chat history information.

Do your best to answer the following user question: {human_input} correctly based on chat history with this user and previous similar conversations."""

    def __init__(self, openAI_APIKEY):
        global loader
        self.openAI_APIKEY = openAI_APIKEY

        os.environ['OPENAI_API_KEY'] = openAI_APIKEY

        underlying_embeddings = OpenAIEmbeddings()
        fs = LocalFileStore("./cache/")
        json_path='./jsons/split.json'
        self.memoryStorage = {}
        #self.memory = ConversationBufferMemory(memory_key="chat_history", input_key="human_input")


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
        #relavant_chats = db.similarity_search_with_score(input, k=3, search_type="hybrid")
        #relavant_chats = db.max_marginal_relevance_search_with_score_by_vector(underlying_embeddings.embed_query(input), 2)

        #print(relavant_chats)
        #print(relavant_chats)
        #printRelavantChats(relavant_chats)
        return relavant_chats

    def checkForOutdatedMemory(self):
        for userID in self.memoryStorage:
            timePassed = datetime.now() - self.memoryStorage[userID]["createdDatetime"]
            if (timePassed.total_seconds() / 60) > 60:
                del self.memoryStorage[userID]

    def getPrompt(self):
        return self.prompt_starting
    
    def returnAnswer(self, query, _prompt, userID):
        if userID not in self.memoryStorage:
            memory = ConversationBufferMemory(memory_key="chat_history", input_key="human_input")
            self.memoryStorage[userID] = {"memory": memory, "createdDatetime": datetime.now()}
        else:
            memory = self.memoryStorage[userID]["memory"]
        
        prompt = _prompt
        
        user_input = query

        print(memory)
        message_prompt = PromptTemplate(
        input_variables=["relavant_messages", "chat_history", "human_input"],
        template=prompt
        )
        
        #PRVA 2 RELAVANT CHATA STA OD USER INOUT IN ZADNJI JE OD USERINPUT + HISTORY

        relavantChatsQuery = self.findRelavantChats(user_input)
        relavantChatsHistory = self.findRelavantChats((("user question: " + user_input).join(memory.load_memory_variables({})["chat_history"].split("\n")[:4])))
        
        #Take 2 top results for query similarity search (if similarity not over threshold) and 1 for whole history similarity search
        relavantChats = []
        for comment in relavantChatsQuery:
            if len(relavantChats) >= 2:
                break
            if comment[1] < 0.4:
                relavantChats.append(comment)
        for comment in relavantChatsHistory:
            if len(relavantChats) >= 3:
                break
            relavantChats.append(comment)

        #print(memory.load_memory_variables({})["chat_history"])
        accurateEnough = False
        minimumScore = 0.25 #(L2 distance)
        for comment in relavantChats:
            if comment[1] <= minimumScore:
                accurateEnough = True
                break

        if accurateEnough:
            relavantChats_noscore = [relavantChat[0] for relavantChat in relavantChats]
            
            chain = LLMChain(
            llm=ChatOpenAI(temperature="0", model_name='gpt-3.5-turbo-16k'),
            #llm=ChatOpenAI(temperature="0", model_name='gpt-4'),
            prompt=message_prompt,
            memory=self.memoryStorage[userID]["memory"],
            verbose=False
            )
            reply = chain.run({"human_input": user_input, "relavant_messages": relavantChats_noscore})
        else:
            reply = "I do not know the answer to that."
        
        #print("-------------------------------------------------")
        #print(self.memory.load_memory_variables({})["chat_history"].split("\n")[:4])
        #print("------------------------------------------------")
        #print(reply)

        similarChats = []
        for comment in relavantChats:
            context = comment[0].metadata["context"].split("    ")
            similarChats.append({"context": context, "score": float(comment[1])})
            #print(context)

        #print(json.dumps(similarChats, indent=2, default=self.convert_to_serializable))
        reply = reply.replace("\n", "\\n")
        return reply, similarChats
