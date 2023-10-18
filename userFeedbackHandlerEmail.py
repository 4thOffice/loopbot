import sys
sys.path.append('./APIcalls')
import APIcalls.emailHistory as emailHistory
from langchain.docstore.document import Document
from langchain.evaluation import load_evaluator, EmbeddingDistance
from langchain.docstore.document import Document
import jsonOperations
import json
import databaseHandler

class UserFeedbackHandlerEmail:

    def __init__(self, feedbackBuffer):
        with open("./jsons/good_responses.json", 'r') as file:
            self.good_responses_json = json.load(file)
        with open("./jsons/bad_responses.json", 'r') as file:
            self.bad_responses_json = json.load(file)
        self.feedbackCounter = 0
        self.feedbackBuffer = feedbackBuffer


    def handleGoodResponse(self, sender_userID, sender_name, contactID, cardID, AIresponse, db_good_responses, db_bad_responses, authKey):

        impersonated_userID, impersonated_username = emailHistory.getContactUserID(contactID, sender_userID, sender_name, authKey)
        comments = emailHistory.getEmailHistory(cardID, impersonated_userID, impersonated_username, authKey)
        comments = comments[-5:]
        memory_anonymous = emailHistory.memoryPostProcess(comments, impersonated_username)
        context = memory_anonymous
        context += "\n" + AIresponse

        good_responses = db_good_responses["docs"].similarity_search_with_score(context, k=1)
        
        #check if similar good responses already exist
        if good_responses[0][1] > 0.027:
            print("add new")
            new_document = Document(page_content=context, metadata=dict(AIresponse=AIresponse, score=1))
            db_good_responses["docs"].add_documents([new_document])
            db_good_responses["json"] = jsonOperations.append_json({"context": context, "AIresponse": AIresponse, "score": 1}, db_good_responses["json"])
        else:
            # ADD SCORE IN GOOD RESPONSES
            if(len(db_good_responses["docs"].docstore._dict) > 0):
                closestDoc = db_good_responses["docs"].search(context, k=1, search_type="similarity")
                print("diff", good_responses[0][1])
                for key, doc in db_good_responses["docs"].docstore._dict.copy().items():
                    if closestDoc[0].page_content == doc.page_content:
                        #print("doc to update", doc, key)
                        contextTemp = doc.page_content
                        AIresponseTemp = doc.metadata["AIresponse"]
                        scoreTemp = doc.metadata["score"]

                        key_list=list(db_good_responses["docs"].index_to_docstore_id.keys())
                        val_list=list(db_good_responses["docs"].index_to_docstore_id.values())
                        ind=val_list.index(key)

                        db_good_responses["docs"].delete([db_good_responses["docs"].index_to_docstore_id[key_list[ind]]])
                        new_document = Document(page_content=contextTemp, metadata=dict(AIresponse=AIresponseTemp, score=scoreTemp+1))
                        db_good_responses["docs"].add_documents([new_document])
                        db_good_responses["json"] = jsonOperations.update_json(db_good_responses["json"], contextTemp, AIresponseTemp, scoreTemp+1)
                        print("update existing good")

            if(len(db_bad_responses["docs"].docstore._dict) > 0):
                # SUBSTRACT SCORE IN BAD RESPONSES
                closestDoc = db_bad_responses["docs"].search(context, k=1, search_type="similarity")

                evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
                distance = evaluator.evaluate_string_pairs(
                    prediction=closestDoc[0].page_content, prediction_b=doc.page_content
                )

                if distance["score"] <= 0.4:    
                    for key, doc in db_bad_responses["docs"].docstore._dict.copy().items():
                        if closestDoc[0].page_content == doc.page_content:
                            #print("doc to update", doc, key)
                            contextTemp = doc.page_content
                            AIresponseTemp = doc.metadata["AIresponse"]
                            scoreTemp = doc.metadata["score"]

                            if scoreTemp <= 0:
                                db_bad_responses["json"] = jsonOperations.delete_from_json(db_bad_responses["json"], contextTemp)
                                continue

                            key_list=list(db_bad_responses["docs"].index_to_docstore_id.keys())
                            val_list=list(db_bad_responses["docs"].index_to_docstore_id.values())
                            ind=val_list.index(key)

                            db_bad_responses["docs"].delete([db_bad_responses["docs"].index_to_docstore_id[key_list[ind]]])
                            new_document = Document(page_content=contextTemp, metadata=dict(AIresponse=AIresponseTemp, score=scoreTemp-1))
                            db_bad_responses["docs"].add_documents([new_document])
                            db_bad_responses["json"] = jsonOperations.update_json(db_bad_responses["json"], contextTemp, AIresponseTemp, scoreTemp-1)
                            print("update existing bad")

        if self.feedbackCounter > self.feedbackBuffer:
            self.write_jsons(sender_userID, db_bad_responses["json"], db_good_responses["json"])
            self.feedbackCounter = 0
        else:
            self.feedbackCounter += 1
        
        return (AIresponse + " -> handeled as positive")
        
    def handleBadResponse(self, sender_userID, sender_name, contactID, cardID, AIresponse, db_good_responses, db_bad_responses, authKey):
        impersonated_userID, impersonated_username = emailHistory.getContactUserID(contactID, sender_userID, sender_name, authKey)
        comments = emailHistory.getEmailHistory(cardID, impersonated_userID, impersonated_username, authKey)
        comments = comments[-5:]
        memory_anonymous = emailHistory.memoryPostProcess(comments, impersonated_username)
        context = memory_anonymous
        context += "\n" + AIresponse

        print("anonymous memory: ", memory_anonymous)

        """
        bad_responses = db_bad_responses["docs"].similarity_search_with_score(context, k=1)
        
        print("distance:", bad_responses[0][1])

        #check if similar good responses already exist
        if bad_responses[0][1] > 0.04:
            new_document = Document(page_content=context, metadata=dict(AIresponse=AIresponse, score=1))
            db_bad_responses["docs"].add_documents([new_document])

            db_bad_responses["json"] = jsonOperations.append_json({"context": context, "AIresponse": AIresponse, "score": 1}, db_bad_responses["json"])
        else:
            if(len(db_bad_responses["docs"].docstore._dict) > 0):
                closestDoc = db_bad_responses["docs"].search(context, k=1, search_type="similarity")
                for key, doc in db_bad_responses["docs"].docstore._dict.copy().items():
                    if closestDoc[0].page_content == doc.page_content:
                        contextTemp = doc.page_content
                        AIresponseTemp = doc.metadata["AIresponse"]
                        scoreTemp = doc.metadata["score"]

                        key_list=list(db_bad_responses["docs"].index_to_docstore_id.keys())
                        val_list=list(db_bad_responses["docs"].index_to_docstore_id.values())
                        ind=val_list.index(key)

                        db_bad_responses["docs"].delete([db_bad_responses["docs"].index_to_docstore_id[key_list[ind]]])
                        new_document = Document(page_content=contextTemp, metadata=dict(AIresponse=AIresponseTemp, score=scoreTemp+1))
                        db_bad_responses["docs"].add_documents([new_document])
                        db_bad_responses["json"] = jsonOperations.update_json(db_bad_responses["json"], contextTemp, AIresponseTemp, scoreTemp+1)

            if len(db_good_responses["docs"].docstore._dict) > 0:
                # SUBSTRACT SCORE IN GOOD RESPONSES
                closestDoc = db_good_responses["docs"].search(context, k=1, search_type="similarity")

                evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
                distance = evaluator.evaluate_string_pairs(
                    prediction=closestDoc[0].page_content, prediction_b=doc.page_content
                )

                if distance["score"] <= 0.4:    
                    for key, doc in db_good_responses["docs"].docstore._dict.copy().items():
                        if closestDoc[0].page_content == doc.page_content:
                            #print("doc to update", doc, key)
                            contextTemp = doc.page_content
                            AIresponseTemp = doc.metadata["AIresponse"]
                            scoreTemp = doc.metadata["score"]

                            if scoreTemp <= 0:
                                db_good_responses["json"] = jsonOperations.delete_from_json(db_good_responses["json"], contextTemp)
                                continue

                            key_list=list(db_good_responses["docs"].index_to_docstore_id.keys())
                            val_list=list(db_good_responses["docs"].index_to_docstore_id.values())
                            ind=val_list.index(key)

                            db_good_responses["docs"].delete([db_good_responses["docs"].index_to_docstore_id[key_list[ind]]])
                            new_document = Document(page_content=contextTemp, metadata=dict(AIresponse=AIresponseTemp, score=scoreTemp-1))
                            db_good_responses["docs"].add_documents([new_document])
                            db_good_responses["json"] = jsonOperations.update_json(db_good_responses["json"], contextTemp, AIresponseTemp, scoreTemp-1)
        
        if self.feedbackCounter > self.feedbackBuffer:
            self.write_jsons(sender_userID, db_bad_responses["json"], db_good_responses["json"])
            self.feedbackCounter = 0
        else:
            self.feedbackCounter += 1"""
        
        return (AIresponse + "  -> handeled as negative")

    def write_jsons(self, user_id, bad_responses_json, good_responses_json):
        print("SHOULD WRITE")
        #jsonOperations.write_json(self.bad_responses_json, "./jsons/bad_responses.json")
        databaseHandler.insert_json_data(user_id, "bad_responses_email", bad_responses_json)
        #jsonOperations.write_json(self.good_responses_json, "./jsons/good_responses.json")
        databaseHandler.insert_json_data(user_id, "good_responses_email", good_responses_json)