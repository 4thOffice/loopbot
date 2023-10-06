import sys
sys.path.append('./APIcalls')
import APIcalls.directchatHistory as directchatHistory
from langchain.docstore.document import Document
from langchain.evaluation import load_evaluator, EmbeddingDistance
from langchain.docstore.document import Document
import jsonOperations
import json


class UserFeedbackHandler:

    def __init__(self, feedbackBuffer):
        with open("./jsons/good_responses.json", 'r') as file:
            self.good_responses_json = json.load(file)
        with open("./jsons/bad_responses.json", 'r') as file:
            self.bad_responses_json = json.load(file)
        self.feedbackCounter = 0
        self.feedbackBuffer = feedbackBuffer


    def handleGoodResponse(self, recipient_userID, AIresponse, db_good_responses, db_bad_responses):
        context = directchatHistory.getAllComments(5, recipient_userID)
        contextLastTopic = directchatHistory.getLastTopic(context)

        if len(contextLastTopic) > 0:
            context = contextLastTopic
            
        context = directchatHistory.memoryPostProcess(context)
        context += "\n" + AIresponse

        good_responses = db_good_responses.similarity_search_with_score(context, k=1)
        
        #check if similar good responses already exist
        if good_responses[0][1] > 0.027:
            new_document = Document(page_content=context, metadata=dict(AIresponse=AIresponse, score=1))
            db_good_responses.add_documents([new_document])
            self.good_responses_json = jsonOperations.append_json({"context": context, "AIresponse": AIresponse, "score": 1}, self.good_responses_json)
        else:
            # ADD SCORE IN GOOD RESPONSES
            if(len(db_good_responses.docstore._dict) > 0):
                closestDoc = db_good_responses.search(context, k=1, search_type="similarity")
                print("diff", good_responses[0][1])
                for key, doc in db_good_responses.docstore._dict.copy().items():
                    if closestDoc[0].page_content == doc.page_content:
                        print("doc to update", doc, key)
                        contextTemp = doc.page_content
                        AIresponseTemp = doc.metadata["AIresponse"]
                        scoreTemp = doc.metadata["score"]

                        key_list=list(db_good_responses.index_to_docstore_id.keys())
                        val_list=list(db_good_responses.index_to_docstore_id.values())
                        ind=val_list.index(key)

                        db_good_responses.delete([db_good_responses.index_to_docstore_id[key_list[ind]]])
                        new_document = Document(page_content=contextTemp, metadata=dict(AIresponse=AIresponseTemp, score=scoreTemp+1))
                        db_good_responses.add_documents([new_document])
                        self.good_responses_json = jsonOperations.update_json(self.good_responses_json, contextTemp, AIresponseTemp, scoreTemp+1)

            if(len(db_bad_responses.docstore._dict) > 0):
                # SUBSTRACT SCORE IN BAD RESPONSES
                closestDoc = db_bad_responses.search(context, k=1, search_type="similarity")

                evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
                distance = evaluator.evaluate_string_pairs(
                    prediction=closestDoc[0].page_content, prediction_b=doc.page_content
                )

                if distance["score"] <= 0.4:    
                    for key, doc in db_bad_responses.docstore._dict.copy().items():
                        if closestDoc[0].page_content == doc.page_content:
                            print("doc to update", doc, key)
                            contextTemp = doc.page_content
                            AIresponseTemp = doc.metadata["AIresponse"]
                            scoreTemp = doc.metadata["score"]

                            if scoreTemp <= 0:
                                self.bad_responses_json = jsonOperations.delete_from_json(self.bad_responses_json, contextTemp)
                                continue

                            key_list=list(db_bad_responses.index_to_docstore_id.keys())
                            val_list=list(db_bad_responses.index_to_docstore_id.values())
                            ind=val_list.index(key)

                            db_bad_responses.delete([db_bad_responses.index_to_docstore_id[key_list[ind]]])
                            new_document = Document(page_content=contextTemp, metadata=dict(AIresponse=AIresponseTemp, score=scoreTemp-1))
                            db_bad_responses.add_documents([new_document])
                            self.bad_responses_json = jsonOperations.update_json(self.bad_responses_json, contextTemp, AIresponseTemp, scoreTemp-1)
                            
        if self.feedbackCounter > self.feedbackBuffer:
            self.write_jsons()
            self.feedbackCounter = 0
        else:
            self.feedbackCounter += 1
        
        return (AIresponse + " -> handeled as positive")
        
    def handleBadResponse(self, recipient_userID, AIresponse, db_good_responses, db_bad_responses):
        context = directchatHistory.getAllComments(5, recipient_userID)
        contextLastTopic = directchatHistory.getLastTopic(context)

        if len(contextLastTopic) > 0:
            context = contextLastTopic
            
        context = directchatHistory.memoryPostProcess(context)
        context += "\n" + AIresponse

        bad_responses = db_bad_responses.similarity_search_with_score(context, k=1)
        
        print("distance:", bad_responses[0][1])

        #check if similar good responses already exist
        if bad_responses[0][1] > 0.04:
            new_document = Document(page_content=context, metadata=dict(AIresponse=AIresponse, score=1))
            db_bad_responses.add_documents([new_document])

            self.bad_responses_json = jsonOperations.append_json({"context": context, "AIresponse": AIresponse, "score": 1}, self.bad_responses_json)
        else:
            if(len(db_bad_responses.docstore._dict) > 0):
                closestDoc = db_bad_responses.search(context, k=1, search_type="similarity")
                for key, doc in db_bad_responses.docstore._dict.copy().items():
                    if closestDoc[0].page_content == doc.page_content:
                        print("doc to update", doc, key)
                        contextTemp = doc.page_content
                        AIresponseTemp = doc.metadata["AIresponse"]
                        scoreTemp = doc.metadata["score"]

                        key_list=list(db_bad_responses.index_to_docstore_id.keys())
                        val_list=list(db_bad_responses.index_to_docstore_id.values())
                        ind=val_list.index(key)

                        db_bad_responses.delete([db_bad_responses.index_to_docstore_id[key_list[ind]]])
                        new_document = Document(page_content=contextTemp, metadata=dict(AIresponse=AIresponseTemp, score=scoreTemp+1))
                        db_bad_responses.add_documents([new_document])
                        self.bad_responses_json = jsonOperations.update_json(self.bad_responses_json, contextTemp, AIresponseTemp, scoreTemp+1)

            if len(db_good_responses.docstore._dict) > 0:
                # SUBSTRACT SCORE IN GOOD RESPONSES
                closestDoc = db_good_responses.search(context, k=1, search_type="similarity")

                evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
                distance = evaluator.evaluate_string_pairs(
                    prediction=closestDoc[0].page_content, prediction_b=doc.page_content
                )

                if distance["score"] <= 0.4:    
                    for key, doc in db_good_responses.docstore._dict.copy().items():
                        if closestDoc[0].page_content == doc.page_content:
                            print("doc to update", doc, key)
                            contextTemp = doc.page_content
                            AIresponseTemp = doc.metadata["AIresponse"]
                            scoreTemp = doc.metadata["score"]

                            if scoreTemp <= 0:
                                self.good_responses_json = jsonOperations.delete_from_json(self.good_responses_json, contextTemp)
                                continue

                            key_list=list(db_good_responses.index_to_docstore_id.keys())
                            val_list=list(db_good_responses.index_to_docstore_id.values())
                            ind=val_list.index(key)

                            db_good_responses.delete([db_good_responses.index_to_docstore_id[key_list[ind]]])
                            new_document = Document(page_content=contextTemp, metadata=dict(AIresponse=AIresponseTemp, score=scoreTemp-1))
                            db_good_responses.add_documents([new_document])
                            self.good_responses_json = jsonOperations.update_json(self.good_responses_json, contextTemp, AIresponseTemp, scoreTemp-1)
        
        if self.feedbackCounter > self.feedbackBuffer:
            self.write_jsons()
            self.feedbackCounter = 0
        else:
            self.feedbackCounter += 1
        
        return (AIresponse + "  -> handeled as negative")

    def write_jsons(self):
        jsonOperations.write_json(self.bad_responses_json, "./jsons/bad_responses.json")
        jsonOperations.write_json(self.good_responses_json, "./jsons/good_responses.json")