import keys
import os
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


os.environ['OPENAI_API_KEY'] = keys.openAI_APIKEY
underlying_embeddings = OpenAIEmbeddings()
fs = LocalFileStore("./cache/")
json_path='split.json'
memory = ConversationBufferMemory(memory_key="chat_history", input_key="human_input")


#EMBEDDING PROCESS
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings, fs, namespace=underlying_embeddings.model
)

loader = loader.JSONLoader(file_path=json_path)
documents = loader.load()
db = FAISS.from_documents(documents, cached_embedder)
print("Finished embbeding")

#print relavant information about a query
def printRelavantChats(relavant_chats):
    for i, comment in enumerate(relavant_chats):
        print("Conversation context:", i, "score:", comment[1])

        context = comment[0].metadata["context"].split("    ")
        for txt in context:
            print(txt)

#find relavant information abotu a query
def findRelavantChats(input):
    relavant_chats = db.similarity_search_with_score(input, k=3)
    #relavant_chats = db.similarity_search_with_score(input, k=3, search_type="hybrid")
    #relavant_chats = db.max_marginal_relevance_search_with_score_by_vector(underlying_embeddings.embed_query(input), 2)

    #print(relavant_chats)
    print(relavant_chats)
    #printRelavantChats(relavant_chats)
    return relavant_chats

while(1):
    user_input = str(input())

    message_prompt = PromptTemplate(
    input_variables=["relavant_messages", "chat_history", "human_input"],
    template="You are a helpful assistant answering questions about our platform " + "Loop Email" + """". User asked the following question: {human_input} 
    Here are previous conversations with other users similar to the topic user asked about: {relavant_messages}.

    Do NOT mention relavant_messages you have been provided. Act like you are customer support.

    Do NOT say if the issue is known or not and if our team is working/investigating on it. Just provide a helpful answer.

    Answer should be formal and short.

    If you do not know the answer, just say you do not know the answer.

    Metadata description:
    context: conversation context
    
    Previous conversation with this user: {chat_history}

    Do your best to answer correctly based on chat history and previous similar conversations.
    """
    )
    
    #relavantChats = findRelavantChats(user_input)
    relavantChats = findRelavantChats(user_input + "  " + memory.load_memory_variables({})["chat_history"])
    
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
        memory=memory,
        verbose=False
        )
        reply = chain.run({"human_input": user_input, "relavant_messages": relavantChats_noscore})
        print("------------------------------------------------")
        print(reply)
    else:
        print("I do not know the answer to that. We will take a look at this.")
