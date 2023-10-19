import os
from langchain.schema import SystemMessage
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
import spacy
from spacy.matcher import Matcher
import keys

class AIclassificator:

    faq_patterns = [
        [{"LOWER": "faq"}],
        [{"LOWER": "frequently"}, {"LOWER": "asked"}, {"LOWER": "questions"}],
        [{"LOWER": "how"}, {"LOWER": "do"}, {"LOWER": "i"}, {"LOWER": "find"}, {"LOWER": "faq"}]
    ]

    replaceEntryFAQ = [
        [{"LOWER": "replace"}, {"LOWER": "existing"}, {"LOWER": "faq"}, {"LOWER": "entry"}, {"LOWER": "with"}, {"LOWER": "new"}],
        [{"LOWER": "replace"}, {"LOWER": "faq"}, {"LOWER": "entry"}, {"LOWER": "with"}, {"LOWER": "new"}],
        [{"LOWER": "replace"}, {"LOWER": "it"}, {"LOWER": "with"}, {"LOWER": "new"}],
        [{"LOWER": "swap"}, {"LOWER": "out"}, {"LOWER": "existing"}, {"LOWER": "faq"}, {"LOWER": "entry"}, {"LOWER": "with"}, {"LOWER": "new"}],
        [{"LOWER": "swap"}],
        [{"LOWER": "replace"}],
        [{"LOWER": "use"}, {"LOWER": "new"}],
    ]

    keepEntryFAQ =[
        [{"LOWER": "keep"}, {"LOWER": "existing"}, {"LOWER": "faq"}, {"LOWER": "entry"}],
        [{"LOWER": "keep"}, {"LOWER": "it"}, {"LOWER": "as"}, {"LOWER": "is"}],
        [{"LOWER": "leave"}, {"LOWER": "existing"}, {"LOWER": "faq"}, {"LOWER": "entry"}],
        [{"LOWER": "stick"}, {"LOWER": "with"}, {"LOWER": "current"}, {"LOWER": "faq"}, {"LOWER": "entry"}],
        [{"LOWER": "stick"}, {"LOWER": "with"}, {"LOWER": "current"}, {"LOWER": "faq"}, {"LOWER": "entry"}],
        [{"LOWER": "do"}, {"LOWER": "not"}, {"LOWER": "replace"}],
        [{"LOWER": "keep"}, {"LOWER": "old"}],
        [{"LOWER": "use"}, {"LOWER": "old"}],
        [{"LOWER": "keep"}],
    ]

    def __init__(self, openAI_APIKEY):
        self.openAI_APIKEY = openAI_APIKEY
        os.environ['OPENAI_API_KEY'] = openAI_APIKEY
        self.nlp = spacy.load("en_core_web_sm")
        
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
    
    def getUserIntent(self, user_input, usecase):
        doc = self.nlp(user_input.lower())

        if usecase == "show_faq":
            matcher = Matcher(self.nlp.vocab)
            patterns = self.faq_patterns

            for pattern in patterns:
                print(pattern)
                matcher.add("FAQ_PATTERN", [pattern])

            matches = matcher(doc)
            
            if any(matches):
                return "show_faq"
            return "other_intent"
        

        elif usecase == "entry_faq":
            patterns = self.keepEntryFAQ
            patterns = self.replaceEntryFAQ
            matcherReplace = Matcher(self.nlp.vocab)
            matcherKeep = Matcher(self.nlp.vocab)
            
            for pattern in self.replaceEntryFAQ:
                matcherReplace.add("REPLACE_FAQ_PATTERN", [pattern])
            
            for pattern in self.keepEntryFAQ:
                matcherKeep.add("KEEP_FAQ_PATTERN", [pattern])

            matches = matcherReplace(doc)
            if any(matches):
                return "replace_entry"
            
            matches = matcherKeep(doc)
            if any(matches):
                return "keep_entry"

            return "other_intent"

"""
reph = AIclassificator(keys.openAI_APIKEY)
print(reph.getUserIntent("Replace", "entry_faq"))
print(reph.getUserIntent("you should replace", "entry_faq"))
print(reph.getUserIntent("keep", "entry_faq"))
print(reph.getUserIntent("i wnat to replace it with new one", "entry_faq"))
print(reph.getUserIntent("new", "entry_faq"))
print(reph.getUserIntent("Keep existing faq entry", "entry_faq"))"""