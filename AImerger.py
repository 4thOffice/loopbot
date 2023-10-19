import os
from langchain.schema import SystemMessage
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
import keys

class AImerger:
    def __init__(self, openAI_APIKEY):
        self.openAI_APIKEY = openAI_APIKEY
        os.environ['OPENAI_API_KEY'] = openAI_APIKEY
    
    def merge(self, answer1, answer2):
        
        system_prompt = SystemMessage(content="Lets think step by step. You are merging answers which you are given. All information from answer 1 and all information in answer 2 should be in your final output. Provide an output I can copy and paste. No aditional text.")
        
        prompt_change_message = "Answer number 1:\n"
                    
        prompt_change_message += answer1

        prompt_change_message += "Answer number 2:\n"
                    
        prompt_change_message += answer2
        
        human_message_template = HumanMessagePromptTemplate.from_template(prompt_change_message)
        
        chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_message_template])

            
        chain = LLMChain(
        llm=ChatOpenAI(temperature="0.0", model_name='gpt-3.5-turbo'),
        #llm=ChatOpenAI(temperature="0", model_name='gpt-4'),
        prompt=chat_prompt,
        verbose=True
        )
        merged_answer = chain.run({})

        return merged_answer

reph = AImerger(keys.openAI_APIKEY)
print(reph.merge("Please try resetting your account and upgrading Loop Email to the newest version.", "Hello. You should reset your account. Adittionaly you may want to disconnect your shared inbox and then reconnect it."))