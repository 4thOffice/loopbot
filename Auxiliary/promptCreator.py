from langchain.schema import SystemMessage
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


prompt_loopbot = """Lets think step by step.

You are answering questions about our platform "Loop Email".
    
Here are relavant conversations with other people with similar topic:
{relavant_messages}.\n"""


prompt_regular_user = """Lets think step by step.

You are talking to a user.
{relavant_messages}
"""

prompt_loopbot_email = """Lets think step by step.
{relavant_messages}"""

prompt_regular_user_email = """Lets think step by step.
{relavant_messages}
"""

def createPrompt(goodResponses, badResponses, badResponsesPrevious, relavantInfo, user_input, loopbotMode):
        if loopbotMode:
            prompt = prompt_loopbot
        else:
            prompt = prompt_regular_user

        system_prompt = SystemMessage(content="You are a chatbot having a conversation with a human. You should decide whether to ask a troubleshoot question or provide a solution if you have enough data.\n")

        if len(goodResponses) > 0:
            prompt += "\nHere are some old conversations with other users that may be relavant: \n"
            for index, response in enumerate(goodResponses, start=1):
                prompt += f"Conversation {index}:\n {response}\n"

        if len(relavantInfo) > 0:
             prompt += ("\nThe following information sources might be of help as well:\n" + relavantInfo + "\n\n")

        prompt = prompt + """

Reply to the user's following message: """ + user_input + """

Reply should be formal and short and ready to copy and paste.
Your output should ONLY be the reply text I can copy and paste and NO other text.

Reply to the human LAST message best as you can based on chat history. Also take information from relavant conversations You have been provided. Only provide a reply to human's last message. Provide a message I can copy and paste - no explaination or chat history and unneccessary content. Reply should be in the same language as user's message."""
        
        # Create a human message template
        human_message_template = HumanMessagePromptTemplate.from_template(prompt)

        # Create a chat prompt template from the system message, chat history placeholder, and human message template
        chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_message_template])

        return chat_prompt

def createPromptEmail(goodResponses, badResponses, badResponsesPrevious, loopbotMode, username, emailMemory):
        if loopbotMode:
            prompt = prompt_loopbot_email
        else:
            prompt = prompt_regular_user_email

        prompt = prompt + "\nI will give you the following email conversation history:\n\n" + emailMemory

        system_prompt = SystemMessage(content="You are answering an email." + """ My name is: """ + username)

        if len(goodResponses) > 0:
            system_prompt.content = system_prompt.content + "\nHere are some old conversations with other users that may be relavant: \n"
            for index, response in enumerate(goodResponses, start=1):
                system_prompt.content += f"- {response}\n"

        if len(badResponses) > 0 or len(badResponsesPrevious) > 0:

            system_prompt.content = system_prompt.content + "\nDO NOT use the following replies. They are examples of BAD replies. Think from a different perspective and come up with something content-wise totally different from these: \n"
            for index, response in enumerate(badResponses + badResponsesPrevious, start=1):
                system_prompt.content += f"- {response}\n"
        
        prompt = prompt + "\n\nProvide me with an email I can send as a reply to the recipient(s) last email. Use the same language. Do not include subject. Use my name in signature."
        
        # Create a human message template
        human_message_template = HumanMessagePromptTemplate.from_template(prompt)

        # Create a chat prompt template from the system message, chat history placeholder, and human message template
        chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_message_template])

        return chat_prompt