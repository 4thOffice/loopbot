import base64
import contextlib
import io
import json
import mimetypes
import time
import httpx
from openai import OpenAI
import sys
import openai
import requests
import os
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import keys
import apiDataHandler
import exceptions
from contextlib import ExitStack
import Auxiliary.verbose_checkpoint
from datetime import datetime
import magic

custom_mime_map = {
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/pdf': '.pdf',
    'text/plain': '.txt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    'application/json': '.json',
    'application/msword': '.doc',
    'image/png': '.png',
    'image/jpg': '.jpg',
    'image/jpeg': '.jpeg',
    'image/jpeg': '.gif',
    'image/.webp': '.webp'
}

supported_file_types = [".txt", ".doc", ".docx", ".pdf", ".json", ".pptx"]

@contextlib.contextmanager
def get_open_ai_client(api_key=None,  timeout=60):
    with httpx.Client(timeout=60) as client:
        yield OpenAI(api_key=api_key, http_client=client)
        
class AiAssistantManager:
    def __init__(self, content_text, filesText, filesPicture):
        self.content_text = content_text
        self.filesText = filesText
        self.filesPicture = filesPicture

    def __enter__(self):
        with get_open_ai_client(api_key=keys.openAI_APIKEY) as client:

            self.textFileAssistant = client.beta.assistants.create(
            instructions="You are a helpful robot who extracts flight details from text.",
            model="gpt-4o",
            tools=[{"type": "file_search"}]
            )

            attachments = []
            content = []
            for fileID in self.filesText:
                attachments.append({ "file_id": fileID, "tools": [{"type": "file_search"}] })

            content.append({"type": "text", "text": self.content_text})
            for index, imgFile in enumerate(self.filesPicture):
                file_type = magic.from_buffer(imgFile.getvalue(), mime=True)
                file_extension = mimetypes.guess_extension(file_type) or custom_mime_map.get(file_type, '')
                print("filetypes", file_extension)
                imgID = client.files.create(
                file=(f"img.{file_extension}", imgFile),
                purpose='assistants'
                ).id
                self.filesPicture[index] = imgID
                content.append({"type": "image_file", "image_file": {"file_id": imgID, "detail": "high"}})

            self.thread = client.beta.threads.create(
            messages=[
                {
                "role": "user",
                "content": content,
                "attachments": attachments
                }
            ]
            )
        
        return self.textFileAssistant, self.thread

    def __exit__(self, exc_type, exc_value, traceback):
        apiDataHandler.delete_assistant(self.textFileAssistant.id, keys.openAI_APIKEY)
        for file_ in self.filesPicture:
            apiDataHandler.delete_file(file_, keys.openAI_APIKEY)
        for file_ in self.filesText:
            apiDataHandler.delete_file(file_, keys.openAI_APIKEY)

def askGPT(emailText, filesText, filesPicture, verbose_checkpoint=None):
    with get_open_ai_client(api_key=keys.openAI_APIKEY) as client:
        for index, file_ in enumerate(filesText):
            file_type = magic.from_buffer(file_.getvalue(), mime=True)
            file_extension = mimetypes.guess_extension(file_type) or custom_mime_map.get(file_type, '')
            print("filetypes", file_extension)
            if file_extension in supported_file_types:
                filesText[index] = client.files.create(
                file=(f"document.{file_extension}", file_),
                purpose='assistants'
                ).id
            else:
                filesText.pop(index)

        current_date_time = datetime.now()
        formatted_current_date = current_date_time.strftime("%dth of %B %Y")
        
        content_text = f"""Extract ALL flight details from the text which I will give you. Extract ALL of the following data:
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

        """Timeframe definitions: 
            - morning: from 06:00:00 to 12:00:00
            - evening: from 18:00:00 to 23:59:59
            - afternoon: from 12:00:00 to 18:00:00
            - middle of the day: from 10:00:00 to 14:00:00
        \n\n"""
        #content_text += emailText

        filesPromptText = ""
        if len(filesText) > 0 or len(filesPicture) > 0:
            filesPromptText = "Also, if there are any documents attached, read them too, they provide aditional information. You MUST read every single one of the attached documents (if they are any), as they all include critical information."

        print("filesPromptText", filesPromptText)
        content_text += "Extract ALL flight details from the text which I will give you. Extract data like origin, destionation, dates, timeframes, requested connection points (if specified explicitly) and ALL other flight information. " + filesPromptText + "\n\nProvide an answer without asking me any further questions." + ("" if filesPromptText else " Ignore files if you didn't find any.") + "\n\nText to extract details from:\n\n" + emailText
            #content_text = "Extract ALL flight details from the email which I will give you. Extract data like origin, destionation, dates, timeframes, requested connection points (if specified explicitly) and ALL other flight information. Also, if there are any documents attached, read them too, they provide aditional information. You MUST read every single one of the attached documents, as they all include critical information.\n\nProvide an answer without asking me any further questions.\n\nEmail (in text format) to extract details from:\n\n" + emailText

        print("--------------------------------------")
        print(f"content_text_docs:\n{content_text}")
        print("--------------------------------------")
        #content_text += "\n\nIf there is a specific flight written, say that it is a preffered option."
        
        with AiAssistantManager(content_text, filesText, filesPicture) as (assistant, thread):
            answer = None
            try:
                answer = runThread(assistant, thread, client, verbose_checkpoint)
            except exceptions.stuck as e:
                print(f"Caught an exception: {e}")
                try:
                    answer = runThread(assistant, thread, client, verbose_checkpoint)
                except exceptions.stuck as e:
                    return None
                
            return answer

def runThread(assistant, thread, client, verbose_checkpoint=None):
    assistant_id=assistant.id

    run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant_id
    )

    i = 0
    while True:
        time.sleep(3)
        run = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
        )
        print(run)
        print(run.status)

        if run.last_error == "rate_limit_exceeded":
            print("WARNING: text specialized agent exceeded maximum amount of tokens!")
            Auxiliary.verbose_checkpoint.verbose("WARNING: text specialized agent exceeded maximum amount of tokens!", verbose_checkpoint)
        if run.status == "failed":
            return "There was an error extracting data."
        if run.status == "expired":
            return "There was an error extracting data."
        if run.status == "cancelled":
            return "There was an error extracting data."
        if run.status == "completed":
            break

        if i >= 100:
            raise exceptions.stuck("no response")

        i += 1

    print("Done")

    messages = client.beta.threads.messages.list(
    thread_id=thread.id
    )
    #print("Extracted non-structured data:\n", messages.data[0].content[0].text.value)
    answer = messages.data[0].content[0].text.value
    return answer

def extractCities(emailText):
        openai.api_key = keys.openAI_APIKEY
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": ("Lets think step by step.\nI will provide you an email text about flight tender inquiry. There will be origin and destination locations of the flight mentioned. Tell me what the initial origin location and final destination of the flight is. (connection flight locations dont count)\n\nEmail text:\n" + emailText)}
            ],
            temperature=0.0
        )

        if response.choices:
            res = (response.choices[0].message.content).lower()
            return res
        else:
            return False
        
def isIntercontinentalFlight(emailText):
        locations = extractCities(emailText)
        print(locations)

        openai.api_key = keys.openAI_APIKEY
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": ("Lets think step by step.\nI will give you 2 locations. Think about in which continents each of these locations are. I want you to tell me if these 2 locations are on different continents. \n\nEmail text:\n" + locations + "\n\nOutput should be ONLY yes/no and NO other text!!. (yes if they are on different continents and no if they are on the same continent)")}
            ],
            temperature=0.0
        )

        if response.choices:
            res = (response.choices[0].message.content).lower()
            print(res)
            if "yes" in res:
                return True
            else:
                return False
        else:
            return False
        
def getTravelClass(emailText):
        openai.api_key = keys.openAI_APIKEY
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": ("I will provide you an email text about flight tender inquiry. I want you to tell me what travel class customer is requesting. Choose one of these options: [ECONOMY, BUSINESS, FIRST]\n\nEmail text:\n" + emailText + "\n\nOutput should be ONLY travel class inside brackets and NO other text - like this: {ECONOMY}")}
            ],
            temperature=0.0
        )

        if response.choices:
            res = (response.choices[0].message.content).upper()
            print(res)
            return res
        else:
            return "ECONOMY"