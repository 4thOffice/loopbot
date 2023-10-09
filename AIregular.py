import os
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
)
from langchain.chains import LLMChain
import os

class AIregular:
    def __init__(self, openAI_APIKEY):
        self.openAI_APIKEY = openAI_APIKEY
        os.environ['OPENAI_API_KEY'] = openAI_APIKEY
        self.chat_model = ChatOpenAI()

    def returnAnswer(self, userInput):
        prompt = "{message}"

        chat_prompt = ChatPromptTemplate.from_messages([prompt])

        chain = LLMChain(
        llm=ChatOpenAI(temperature="0.7", model_name='gpt-3.5-turbo'),
        prompt=chat_prompt,
        verbose=True
        )
        answer = chain.run({"message": userInput})

        return answer