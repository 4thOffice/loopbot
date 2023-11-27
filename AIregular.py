import os
import time
from langchain import OpenAI
from openai import OpenAI as OpenAI_
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
)
import sys
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import keys
from langchain.chains import LLMChain
import os
import FlightOffer.apiDataHandler as apiDataHandler

class AIregular:
    def __init__(self, openAI_APIKEY):
        self.openAI_APIKEY = openAI_APIKEY
        os.environ['OPENAI_API_KEY'] = openAI_APIKEY
        self.chat_model = ChatOpenAI()

    def returnAnswer(self, userInput, files_=[]):
        prompt = "{message}"

        chat_prompt = ChatPromptTemplate.from_messages([prompt])

        chain = LLMChain(
        llm=ChatOpenAI(temperature="0.7", model_name='gpt-3.5-turbo'),
        prompt=chat_prompt,
        verbose=True
        )
        answer = chain.run({"message": userInput})

        return answer
    
    def returnDocAnswer(self, userInput, files=[]):
        client = OpenAI_()

        for index, file_ in enumerate(files):
            files[index] = client.files.create(
            file=file_,
            purpose='assistants'
            ).id

        fileAssistant = client.beta.assistants.create(
        instructions="You are a helpful robot.",
        model="gpt-4-1106-preview",
        tools=[{"type": "retrieval"}, {"type": "code_interpreter"}],
        file_ids=[]
        )

        if len(files) > 0:
            content_text = "Answer the following prompt based on documents attached to this message.\nPrompt: " + userInput

        thread = client.beta.threads.create(
        messages=[
            {
            "role": "user",
            "content": content_text,
            "file_ids": files
            }
        ]
        )

        assistant_id=fileAssistant.id

        run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
        )

        while True:
            time.sleep(3)
            run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
            )
            print(run)
            print(run.status)

            if run.status == "failed":
                return "There was an error extracting data."
            if run.status == "completed":
                break
        
        print("Done")

        messages = client.beta.threads.messages.list(
        thread_id=thread.id
        )
        print("Answer:\n", messages.data[0].content[0].text.value)
        answer = messages.data[0].content[0].text.value
        apiDataHandler.delete_assistant(fileAssistant.id, keys.openAI_APIKEY)

        for file_ in files:
            apiDataHandler.delete_file(file_, keys.openAI_APIKEY)

        return answer