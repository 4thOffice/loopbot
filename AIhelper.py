import os
import time
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
import loader
from langchain.memory import ConversationBufferMemory
from langchain.storage import LocalFileStore
from langchain.embeddings import OpenAIEmbeddings, CacheBackedEmbeddings
import sys
sys.path.append('./APIcalls')
import APIcalls.directchatHistory as directchatHistory
from langchain.evaluation import load_evaluator, EmbeddingDistance
import promptCreator
from langchain.vectorstores.faiss import FAISS
import userFeedbackHandler
import json

class AIhelper:

    feedbackHandler = None

    def __init__(self, openAI_APIKEY, userDataHandler):
        global loader
        self.openAI_APIKEY = openAI_APIKEY

        os.environ['OPENAI_API_KEY'] = openAI_APIKEY

        with open('whitelist.json', 'r') as file:
            self.whitelist = json.load(file)

        underlying_embeddings = OpenAIEmbeddings()

        #LOOPBOT CONVERSATIONS EMBEDDING
        self.fs = LocalFileStore("./cache/")
        json_path='./jsons/split.json'
        
        cached_embedder = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, self.fs, namespace=underlying_embeddings.model
        )

        loader_ = loader.JSONLoader(file_path=json_path)
        documents = loader_.load()
        self.db_loopbot_data = FAISS.from_documents(documents, cached_embedder)

        print("Finished embbeding loopbot data")

        self.userDataHandler_ = userDataHandler
        self.feedbackHandler = userFeedbackHandler.UserFeedbackHandler(feedbackBuffer=2)

    #print relavant information about a query
    def printRelavantChats(relavant_chats):
        for i, comment in enumerate(relavant_chats):
            print("Conversation context:", i, "score:", comment[1])

            context = comment[0].metadata["context"].split("    ")
            for txt in context:
                print(txt)

    #find relavant information abotu a query
    def findRelavantChats(self, input):
        start_time1 = time.time()
        relavant_chats = self.db_loopbot_data.similarity_search_with_score(input, k=3)
        start_time2 = time.time()
        print("relavant chat finding duration:", start_time2-start_time1)
        return relavant_chats

    def findAnswerFAQ(self, sender_userID, classified_issue):
        similar_faq_entry = self.userDataHandler_.user_data[sender_userID]["faq"]["docs"].similarity_search_with_score(classified_issue, k=1)
        print("similar faq entry: ", similar_faq_entry)
        if similar_faq_entry[0][1] < 0.3:
            return similar_faq_entry[0][0].metadata["answer"]

        print("similar_faq_entry ", similar_faq_entry)

    def findResponses(self, sender_userID, recipient_userID, authkey):
        context = directchatHistory.getAllComments(5, recipient_userID, authkey)
        contextLastTopic = directchatHistory.getLastTopic(context)

        if len(contextLastTopic) > 0:
            context = contextLastTopic

        lastMsg1 = context[-1]["content"]
        
        context = directchatHistory.memoryPostProcess(context)

        self.userDataHandler_.checkUserData(sender_userID)

        goodResponses = self.userDataHandler_.user_data[sender_userID]["good_responses"]["docs"].similarity_search_with_score(context, k=3)
        badResponses = self.userDataHandler_.user_data[sender_userID]["bad_responses"]["docs"].similarity_search_with_score(context, k=3)


        print(goodResponses)

        responsesGood = []
        print("good:")
        for response in goodResponses:
            print("score", response[1])
            print("data", response[0])
            if response[1] <= 0.21:
                print("lastMsg1: ", lastMsg1)
                lastMsg2 = response[0].page_content.split("\n")[-1]
                lastMsg2 = lastMsg1.replace("AI:", "")
                lastMsg2 = lastMsg1.replace("user:", "")

                print("lastMsg2: ", lastMsg2)
 
                evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
                distance = evaluator.evaluate_string_pairs(
                    prediction=lastMsg1, prediction_b=lastMsg2
                )

                print("distance: ", distance["score"])

                if distance["score"] < 0.21:
                    responsesGood.append(response[0].metadata["AIresponse"])

        responsesBad = []
        print("bad:")
        for response in badResponses:
            print("score", response[1])
            print("data", response[0])
            if response[1] <= 0.15:
                responsesBad.append(response[0].metadata["AIresponse"])
            
        return responsesGood, responsesBad

    def handleGoodResponse(self, sender_userID, recipient_userID, AIresponse):
        authKey = self.whitelist[sender_userID]
        self.userDataHandler_.checkUserData(sender_userID)
        self.feedbackHandler.handleGoodResponse(sender_userID, recipient_userID, AIresponse, self.userDataHandler_.user_data[sender_userID]["good_responses"], self.userDataHandler_.user_data[sender_userID]["bad_responses"], authKey)
        return (AIresponse + " -> handeled as positive")
    
    def handleBadResponse(self, sender_userID, recipient_userID, AIresponse):
        authKey = self.whitelist[sender_userID]
        self.userDataHandler_.checkUserData(sender_userID)
        self.feedbackHandler.handleBadResponse(sender_userID, recipient_userID, AIresponse, self.userDataHandler_.user_data[sender_userID]["good_responses"], self.userDataHandler_.user_data[sender_userID]["bad_responses"], authKey)
        return (AIresponse + "  -> handeled as negative")

    def updateFAQ(self, sender_userID, recipient_userID, AIresponse, classified_issue, type_):
        self.userDataHandler_.checkUserData(sender_userID)
        self.feedbackHandler.handleUpdateFaq(sender_userID, AIresponse, self.userDataHandler_.user_data[sender_userID]["faq"], classified_issue, type_)
        return (AIresponse + "  -> updated FAQ")
    
    def getAuthkey(self, sender_userID):
        return self.whitelist[sender_userID]

    def returnAnswer(self, recipient_userID, sender_userID, classified_issue, badResponsesPrevious):
        start_time1 = time.time()

        conversationBuffer = ConversationBufferMemory()
        
        authKey = self.getAuthkey(sender_userID)

        recipient_userID = directchatHistory.getRecipientUserIdFromCardId(sender_userID, recipient_userID, authKey)

        regular_user = True
        if sender_userID == "user_1552217" or sender_userID == "user_24564769":
            regular_user = False

        comments = directchatHistory.getAllComments(10, recipient_userID, authKey)
        print(comments)
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
        
        concreteAnswer = self.findAnswerFAQ(sender_userID, classified_issue)

        if concreteAnswer and concreteAnswer != "":
            return concreteAnswer, memory
        
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
                print(comment)
                if len(relavantChats) >= 1:
                    break
                if comment[1] < 0.4:
                    relavantChats.append(comment)
            for comment in relavantChatsHistory:
                print(comment)
                if len(relavantChats) >= 3:
                    break
                relavantChats.append(comment)

            #relavantChats_noscore = [relavantChat[0].metadata["context"] for relavantChat in relavantChats]
            relavantChats_noscore = ""
            for index, relavantChat in enumerate(relavantChats):
                relavantChats_noscore += f"\nConversation {index}:\n"
                relavantChats_noscore += relavantChat[0].metadata["context"]
                #relavantChats_noscore += relavantChat[0].page_content
        else:
            relavantChats_noscore = ""

        goodResponses, badResponses = self.findResponses(sender_userID, recipient_userID, authKey)
        
        chat_prompt = promptCreator.createPrompt(goodResponses, badResponses, badResponsesPrevious, user_input, not regular_user)
        
        print("chat history ", conversationBuffer)

        end_time1 = time.time()
        start_time2 = time.time()
        chain = LLMChain(
        llm=ChatOpenAI(temperature="1.0", model_name='gpt-3.5-turbo-16k'),
        #llm=ChatOpenAI(temperature="1.0", model_name='gpt-4'),
        prompt=chat_prompt,
        memory=conversationBuffer,
        verbose=True
        )
        reply = chain.run({"relavant_messages": str(relavantChats_noscore)})

        end_time2 = time.time()

        elapsed_time = end_time1 - start_time1
        print(f"Time taken to execute preprocess steps: {elapsed_time:.6f} seconds")

        elapsed_time = end_time2 - start_time2
        print(f"Time taken to execute CHATGPT API call: {elapsed_time:.6f} seconds")
        reply = reply.replace("\n", "\\n")
        return reply, memory
    

#lb = AIhelper(keys.openAI_APIKEY)
#print(lb.returnAnswer("is there vpn?", lb.getPrompt(), "user_13"))