import json
import os
import time
from anyio import Path
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
        [{"LOWER": "show"}, {"LOWER": "faq"}],
        [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "faq"}],
        [{"LOWER": "give"}, {"LOWER": "faq"}],
        [{"LOWER": "print"}, {"LOWER": "faq"}],
        [{"LOWER": "show"}, {"LOWER": "faq"}],
        [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "faq"}],
        [{"LOWER": "give"}, {"LOWER": "faq"}],
        [{"LOWER": "print"}, {"LOWER": "faq"}],
        [{"LOWER": "frequently"}, {"LOWER": "asked"}, {"LOWER": "questions"}],
        [{"LOWER": "how"}, {"LOWER": "do"}, {"LOWER": "i"}, {"LOWER": "find"}, {"LOWER": "faq"}]
    ]

    showTopicsPattern = [
        [{"LOWER": "show"}, {"LOWER": "topics"}],
        [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "topics"}],
        [{"LOWER": "give"}, {"LOWER": "topics"}],
        [{"LOWER": "print"}, {"LOWER": "topics"}],
        [{"LOWER": "show"}, {"LOWER": "topic"}],
        [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "topic"}],
        [{"LOWER": "give"}, {"LOWER": "topics"}],
        [{"LOWER": "print"}, {"LOWER": "topic"}],
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

    addResponseFAQ = [
        [{"LOWER": "add"}, {"LOWER": "response"}, {"LOWER": "to"}, {"LOWER": "faq"}, {"LOWER": "entry"}],
        [{"LOWER": "add"}, {"LOWER": "to"}, {"LOWER": "faq"}],
        [{"LOWER": "add"}, {"LOWER": "faq"}],
        [{"LOWER": "append"}, {"LOWER": "to"}, {"LOWER": "faq"}],
        [{"LOWER": "append"}, {"LOWER": "response"}, {"LOWER": "to"}, {"LOWER": "faq"}, {"LOWER": "entry"}],
        [{"LOWER": "insert"}, {"LOWER": "response"}, {"LOWER": "into"}, {"LOWER": "faq"}, {"LOWER": "entry"}],
        [{"LOWER": "update"}, {"LOWER": "faq"}, {"LOWER": "entry"}, {"LOWER": "with"}, {"LOWER": "response"}],
        [{"LOWER": "write"}, {"LOWER": "answer"}, {"LOWER": "for"}, {"LOWER": "faq"}, {"LOWER": "entry"}],
        [{"LOWER": "new"}, {"LOWER": "response"}, {"LOWER": "for"}, {"LOWER": "faq"}, {"LOWER": "entry"}],
    ]

    showAnswerForIssue = [
        [{"LOWER": "show"}],
        [{"LOWER": "show:"}],
        [{"LOWER": "give"}, {"LOWER": "me"}, {"LOWER": "answer"}],
        [{"LOWER": "provide"}, {"LOWER": "answer"}, {"LOWER": "for"}],
    ]

    addFileToKnowledgeBase = [
        [{"LOWER": "add"}],
        [{"LOWER": "use"}],
        [{"LOWER": "knowledgebase"}],
        [{"LOWER": "add"}, {"LOWER": "to"}, {"LOWER": "knowledgebase"}],
        [{"LOWER": "add"}, {"LOWER": "to"}],
        [{"LOWER": "remember"}],
    ]

    endConversation = [
        [{"LOWER": "end"}, {"LOWER": "conversation"}],
        [{"LOWER": "conversation"}, {"LOWER": "end"}],
    ]

    deleteEntryFAQ = [
        [{"LOWER": "delete"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}],
        [{"LOWER": "remove"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}],
        [{"LOWER": "delete"}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}, {"LOWER": "from"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}],
        [{"LOWER": "remove"}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}, {"LOWER": "from"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}],
        [{"LOWER": "discard"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}],
        [{"LOWER": "discard"}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}, {"LOWER": "from"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}],
        [{"LOWER": "forget"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}],
        [{"LOWER": "forget"}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}, {"LOWER": "from"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}],
        [{"LOWER": "erase"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}],
        [{"LOWER": "erase"}, {"LOWER": {"IN": ["entry", "issue", "answer"]}}, {"LOWER": "from"}, {"LOWER": {"IN": ["faq", "issue", "answer"]}}],
        [{"LOWER": "delete"}],
        [{"LOWER": "remove"}]
    ]
    

    def __init__(self, openAI_APIKEY):
        self.openAI_APIKEY = openAI_APIKEY
        os.environ['OPENAI_API_KEY'] = openAI_APIKEY
        self.nlp = spacy.load("en_core_web_sm")
    
    def check_intent(self, text, state):
        if state == "conversation":
            intent = self.getUserIntent(text, "add_to_faq")
            if intent == "add_to_faq":
                return {"intent": intent}
        
            intent = self.getUserIntent(text, "show_faq")
            if intent == "show_faq":
                return {"intent": intent}
            
            intent = self.getUserIntent(text, "show_topics")
            if intent == "show_topics":
                return {"intent": intent}
        
            intent = self.getUserIntent(text, "end_conversation")
            if intent == "end_conversation":
                return {"intent": intent}
            
            return {"intent": "other_intent"}
        
        elif state == "entry_faq":
            intent = self.getUserIntent(text, "add_to_faq")
            if intent == "add_to_faq":
                return {"intent": intent}

            return {"intent": "other_intent"}
        
        elif state == "faq_answer_command":
            intent = self.getUserIntent(text, "get_answer_faq")
            if intent == "get_answer_faq":
                return {"intent": intent}
        
            intent = self.getUserIntent(text, "delete_entry_faq")
            if intent == "delete_entry_faq":
                return {"intent": intent}
            return {"intent": "other_intent"}
        
        elif state == "add_file_to_knowledgebase":
            intent = self.getUserIntent(text, "add_file_to_knowledgebase")
            if intent == "add_file_to_knowledgebase":
                return {"intent": intent}
            return {"intent": "other_intent"}
        
        return {"intent": "other_intent"}


    
    def classify(self, context, classList=[]):

        if len(context) <= 0:
            return ""
        
        system_prompt = SystemMessage(content="You are identifying the issue customer is having problems with from chat conversation history you are provided with. You MUST provide only a raw short issue name. Nothing else.")
        
        prompt_change_message = """Lets think step by step.

Which problem is customer to which our support agent is chatting with experiencing?"""

        if len(classList) > 0:
            prompt_change_message += "You can choose from these issue options:\n" + "\n".join(classList) + "\n"

        prompt_change_message += """Classify the text below (output should be only a problem name and be very specific):\n"""

        print(context)       
        prompt_change_message += context.replace('{', '{{').replace('}', '}}')

        human_message_template = HumanMessagePromptTemplate.from_template(prompt_change_message)
        
        chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_message_template])

            
        chain = LLMChain(
        llm=ChatOpenAI(temperature="0.0", model_name='gpt-3.5-turbo'),
        #llm=ChatOpenAI(temperature="0", model_name='gpt-4'),
        prompt=chat_prompt,
        verbose=True
        )
        classification = chain.run({})

        return classification
    
    def getLastTopicsClassifications(self, context, classListPath):
        if len(context) <= 0:
            return ""
        
        with open(classListPath, 'r') as file:
            data = json.load(file)

        classList = data['issues']
        system_prompt = SystemMessage(content="You are identifying 3 issues user is having problems with from chat conversation history you are provided with. You MUST provide only a raw short issue name of these 3 identified issues. Nothing else.")
        
        prompt_change_message = """Lets think step by step.

Which problems is user to which our AI support agent is chatting with experiencing?\n"""

        if len(classList) > 0:
            prompt_change_message += "You can choose from these issue options:\n" + "\n".join(classList) + "\n\n"

        prompt_change_message += """Classify the text below (output should be only a problem name and be very specific):\n"""

        print(context)       
        prompt_change_message += context.replace('{', '{{').replace('}', '}}')

        human_message_template = HumanMessagePromptTemplate.from_template(prompt_change_message)
        
        chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_message_template])

            
        chain = LLMChain(
        llm=ChatOpenAI(temperature="0.0", model_name='gpt-3.5-turbo'),
        #llm=ChatOpenAI(temperature="0", model_name='gpt-4'),
        prompt=chat_prompt,
        verbose=True
        )
        #try:
        classification = chain.run({})  # Adding 4 seconds timeout
        #except TimeoutError:
        #    print("Classification timed out after 4 seconds.")
        #    classification = "Timeout Error"
        return classification
    
    def getUserIntent(self, user_input, usecase):
        doc = self.nlp(user_input.lower())

        if usecase == "show_faq":
            matcher = Matcher(self.nlp.vocab)
            patterns = self.faq_patterns

            for pattern in patterns:
                matcher.add("FAQ_PATTERN", [pattern])

            matches = matcher(doc)
            
            if any(matches):
                return "show_faq"
            return "other_intent"
        
        elif usecase == "add_to_faq":
            matcher = Matcher(self.nlp.vocab)
            patterns = self.addResponseFAQ

            for pattern in patterns:
                print(pattern)
                matcher.add("FAQ_PATTERN", [pattern])

            matches = matcher(doc)
            
            if any(matches):
                return "add_to_faq"
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
        
        elif usecase == "get_answer_faq":
            matcher = Matcher(self.nlp.vocab)
            patterns = self.showAnswerForIssue

            for pattern in patterns:
                print(pattern)
                matcher.add("GET_ANSWER_PATTERN", [pattern])

            matches = matcher(doc)
            
            if any(matches):
                return "get_answer_faq"
            return "other_intent"
        
        elif usecase == "delete_entry_faq":
            matcher = Matcher(self.nlp.vocab)
            patterns = self.deleteEntryFAQ

            for pattern in patterns:
                print(pattern)
                matcher.add("DELETE_ENTRY_PATTERN", [pattern])

            matches = matcher(doc)
            
            if any(matches):
                return "delete_entry_faq"
            return "other_intent"
        
        elif usecase == "add_file_to_knowledgebase":
            matcher = Matcher(self.nlp.vocab)
            patterns = self.addFileToKnowledgeBase

            for pattern in patterns:
                print(pattern)
                matcher.add("ADD_FILE_PATTERN", [pattern])

            matches = matcher(doc)
            
            if any(matches):
                return "add_file_to_knowledgebase"
            return "other_intent"
        
        elif usecase == "end_conversation":
            matcher = Matcher(self.nlp.vocab)
            patterns = self.endConversation

            for pattern in patterns:
                print(pattern)
                matcher.add("END_CONVERSATION_PATTERN", [pattern])

            matches = matcher(doc)
            
            if any(matches):
                return "end_conversation"
            return "other_intent"
        
        elif usecase == "show_topics":
            matcher = Matcher(self.nlp.vocab)
            patterns = self.showTopicsPattern

            for pattern in patterns:
                print(pattern)
                matcher.add("SHOW_TOPICS_PATTERN", [pattern])

            matches = matcher(doc)
            
            if any(matches):
                return "show_topics"
            return "other_intent"

    def getTopics(self, conversationsJson):
        with open(conversationsJson, 'r') as file:
            # Load the JSON data into a Python object
            data = json.load(file)

        topics = []
        for conversationIndex, conversation in enumerate(data):
            conversationData = data[conversation]
            if conversationIndex > 950:
                if conversationIndex % 50 == 0:
                    print("issues till now: ", topics)
            
                #if conversationIndex >= 50:
                #    return topics
                time.sleep(2)
                print("index: ", conversationIndex)
                context = ""
                for msgIndex, msg in enumerate(conversationData):
                    ID = msg['id']

                    if msg["sender"] == "our response":
                        sender = "Support agent"
                    else:
                        sender = "Customer"

                    commentQuotedID = msg['commentQuotedID']
                    message = msg['message']
                    sequenceNumber = msgIndex
                    conversationID = conversation

                    context += sender + ":\n" + message + "\n\n"
                try:
                    topic = self.classify(context)
                    print("got topic")
                except:
                    print("continued")
                    continue
                print(topic)
                topics.append(topic)

        return topics
    
#reph = AIclassificator(keys.openAI_APIKEY)
#print(reph.getTopics("./jsons/split.json"))
#print(reph.classify("i have a problem with my email not showing up.", ["Email delivery issues", "connectivity issues", "optimization issues"]))

"""
reph = AIclassificator(keys.openAI_APIKEY)
print(reph.getUserIntent("Replace", "entry_faq"))
print(reph.getUserIntent("you should replace", "entry_faq"))
print(reph.getUserIntent("keep", "entry_faq"))
print(reph.getUserIntent("i wnat to replace it with new one", "entry_faq"))
print(reph.getUserIntent("new", "entry_faq"))
print(reph.getUserIntent("Keep existing faq entry", "entry_faq"))"""