import os
import time
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
import keys
import Auxiliary.verbose_checkpoint

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
        prompt=chat_prompt
        )
        answer = chain.run({"message": userInput})

        return answer
    
    def returnDocAnswer(self, userInput, textFiles=[], imageFiles=[]):
        client = OpenAI_()

        for index, file_ in enumerate(textFiles):
            textFiles[index] = client.files.create(
            file=file_,
            purpose='assistants'
            ).id

        fileAssistant = client.beta.assistants.create(
        instructions="You are a helpful robot.",
        model="gpt-4-1106-preview",
        tools=[{"type": "retrieval"}],
        file_ids=[]
        )

        if len(imageFiles) > 0:
            output_vision = self.processImages(userInput, imageFiles)
            if len(textFiles) <= 0:
                return output_vision
            
        if len(textFiles) > 0:
            content_text = "Answer the following prompt based on text documents attached to this message.\nPrompt: " + userInput
            if len(imageFiles) > 0:
                content_text += "\n\nAditional important information from attached files you dont have direct access to, which you should take into consideration when coming up with an answer:\n" + output_vision
        else:
            content_text = userInput
            if len(imageFiles) > 0:
                content_text += "\n\nAditional important information from attached files you dont have direct access to, which you should take into consideration when coming up with an answer:\n" + output_vision

        thread = client.beta.threads.create(
        messages=[
            {
            "role": "user",
            "content": content_text,
            "file_ids": textFiles
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

        for file_ in textFiles:
            apiDataHandler.delete_file(file_, keys.openAI_APIKEY)

        return answer
    
    def processImages(self, emailText, imageFiles, shortenedOutput=False, verbose_checkpoint=None):
        client = OpenAI_()
        
        if not shortenedOutput:
            content_text = """Extract ALL flight details from the text which I will give you. Extract ALL of the following data:
                - currency
                - number of passangers (MUST ALWAYS include in output)
                - maximum number of connections
                - requested airlines with codes
                - travel class
                - whether near airports should be included as departure options
                - amount of checked bags per person (MUST ALWAYS include in output)
                - insurance for the risk of cancellation (say "no" if not specified otherwise)
                - changeable ticket (say "no" if not specified otherwise)
                - list of full names of people for whom ticket reservations has to be made (only if explicitly mentioned or inferred) (only for selected flight option)

            In the text which you will be given, person is asking for offers for one or more flight options that are usually round-trip if not specified otheriwse.
            Select only one flight option and extract data for each itinerary of this specific flight option. There should be only 2 itineraries. One for outbound and one for return. Use connection points.
            Keep in mind that outbound and return itineraries can sometimes be detected by looking at travel dates.
            For each flight itinerary extract the following data:
                - origin location name and IATA 3-letter code
                - alternative origin locations names and IATA 3-letter codes (only for this specific itinerary)
                - destination location name and IATA 3-letter code
                - alternative destination locations names and IATA 3-letter codes (only for this specific itinerary)
                - included connection points names and IATA 3-letter codes
                - travel class
                - departure date
                - exact departure time (must be in HH:MM:SS format)
                - exact arrival time (must be in HH:MM:SS format)
                //Extract the following time parameters from flight timing information written in the text you will be given. You can also leave them empty if not mentioned at all. Convert each time request to to proper time parameters. For example "departure in the evening" should be earliest departure time: 18:00:00 and latest departure time: 23:59:59
                - earliest departure time (must be in HH:MM:SS format) //earlist possible time to depart
                - latest departure time (must be in HH:MM:SS format) //latest possible time to depart
                - earliest arrival time (must be in HH:MM:SS format) //earlist possible time to arrive
                - latest arrival time (must be in HH:MM:SS format) //latest possible time to arrive
                - flight numbers for this itinerary
            \n\n"""
            
            """ - other requests regarding time of departure/arrival (do not leave out any provided information)"""
            """
            Timeframe definitions: 
                - morning: from 05:00:00 to 12:00:00
                - evening: from 18:00:00 to 23:59:59
                - afternoon: from 12:00:00 to 23:59:59
                - middle of the day: from 10:00:00 to 14:00:00
            \n\n"""
            #content_text += emailText
            content_text += "Extract ALL flight details from the text which I will give you. Extract data like origin, destionation, dates, timeframes, requested connection points (if specified explicitly) and ALL other flight information.\n\nProvide an answer without asking me any further questions.\n\nText to extract details from:\n\n" + emailText
            content_text += "\n\nDo not forget to extract data from images. If you cant extract any data from images, then extract only from the text which you were given."
        else:
            content_text = "Extract ALL flight details from the images which I will give you.\nExtract data like origin, destionation, dates, timeframes, requested connection points (if specified explicitly) and absolutely ALL other flight information.\n\nProvide an answer without asking me any further questions. It is completely possible that images do not have any flight information, in that case, just summarize the image text."

        print("--------------------------------------")
        print(f"content_text:\n{content_text}")
        print("--------------------------------------")
        messages = [
            {
            "role": "user",
            "content": [
                {"type": "text", "text": content_text},
            ],
            }
        ]

        for imageFile in imageFiles:
            img = {
                "type": "image_url",
                "image_url": {
                    "url": imageFile,
                },
            }
            messages[0]["content"].append(img)

        response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=messages,
        max_tokens=4096,
        )

        if response.choices[0].finish_reason == "length":
            print("WARNING: picture specialized agent exceeded maximum amount of tokens!")
            Auxiliary.verbose_checkpoint.verbose("WARNING: picture specialized agent exceeded maximum amount of tokens!", verbose_checkpoint)
        #print("data extracted from image process:", response.choices[0].message.content)
        return response.choices[0].message.content
    
    #AIregular_ = AIregular(keys.openAI_APIKEY)
#AIregular_.processImages("what is in these images?", ["https://i.gyazo.com/52237d1ce662e613af2950c3a351a6c8.jpg", "https://i.gyazo.com/98ca775b51faa2a19fa6d7fbf588e5e3.png"])
#with open("Nabavno.pdf", 'rb') as file:
#    AIregular_.returnDocAnswer(userInput="Summarize everything that is attached to this message.", textFiles=[file], imageFiles=["https://i.gyazo.com/52237d1ce662e613af2950c3a351a6c8.jpg", "https://i.gyazo.com/98ca775b51faa2a19fa6d7fbf588e5e3.png"])