import os
from langchain.schema import SystemMessage
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain

class AIclassificator:
    def __init__(self, openAI_APIKEY):
        self.openAI_APIKEY = openAI_APIKEY
        os.environ['OPENAI_API_KEY'] = openAI_APIKEY
    
    def classify(self, context):

        if len(context) <= 0:
            return ""
        
        system_prompt = SystemMessage(content="You are identifying the issue user is having problems with from chat conversation history you are provided with. You MUST provide only a raw short issue name. Nothing else.")
        
        prompt_change_message = """Lets think step by step.

Which problem is user you are chatting with experiencing?
Classify the text below (output should be only a problem name and be very specific):\n"""
                    
        prompt_change_message += context
        
        human_message_template = HumanMessagePromptTemplate.from_template(prompt_change_message)
        
        chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_message_template])

            
        chain = LLMChain(
        llm=ChatOpenAI(temperature="0.0", model_name='gpt-3.5-turbo-16k'),
        #llm=ChatOpenAI(temperature="0", model_name='gpt-4'),
        prompt=chat_prompt,
        verbose=True
        )
        classification = chain.run({})

        return classification

#reph = AIclassificator(keys.openAI_APIKEY)
#print(reph.classify(""))