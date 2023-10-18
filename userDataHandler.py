import databaseHandler
import loader
from langchain.vectorstores.faiss import FAISS
from langchain.embeddings import OpenAIEmbeddings, CacheBackedEmbeddings
from langchain.storage import LocalFileStore

class UserDataHandler:
    def __init__(self):
        underlying_embeddings = OpenAIEmbeddings()
        self.user_data = {}
        self.fs = LocalFileStore("./cache/")

        userIDS = databaseHandler.get_unique_user_ids()
        for userID in userIDS:
            self.user_data[userID] = {}
            json_data = databaseHandler.get_user_json_data(userID)
            
            for json_type in json_data:
                cached_user_embedder = CacheBackedEmbeddings.from_bytes_store(
                    underlying_embeddings, self.fs, namespace=userID + "-" + json_type
                )
                
                loader_ = loader.JSONLoader(file_path="")
                if json_type == "faq":
                    documents = loader_.loadFAQ(json_data[json_type])
                else:
                    documents = loader_.loadResponses(json_data[json_type])
                self.user_data[userID][json_type] = {"docs": FAISS.from_documents(documents, cached_user_embedder), "json": json_data[json_type]}


        print(self.user_data)

    def checkUserData(self, userID):
        if userID not in self.user_data:
            self.user_data[userID] = {}
            databaseHandler.add_user_json_data(userID, "good_responses")
            databaseHandler.add_user_json_data(userID, "bad_responses")
            databaseHandler.add_user_json_data(userID, "good_responses_email")
            databaseHandler.add_user_json_data(userID, "bad_responses_email")
            databaseHandler.add_user_json_data(userID, "faq")

            json_data = databaseHandler.get_user_json_data(userID)
            
            underlying_embeddings = OpenAIEmbeddings()

            for json_type in json_data:
                cached_embedder_good = CacheBackedEmbeddings.from_bytes_store(
                    underlying_embeddings, self.fs, namespace=userID + "-" + json_type
                )

                loader_ = loader.JSONLoader(file_path="")
                if json_type == "faq":
                    documents = loader_.loadFAQ(json_data[json_type])
                else:
                    documents = loader_.loadResponses(json_data[json_type])
                self.user_data[userID][json_type] = {"docs": FAISS.from_documents(documents, cached_embedder_good), "json": json_data[json_type]}
