import io
import json
import time
from openai import OpenAI
import sys
import openai
import requests
import os
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import keys
import apiDataHandler
    
def askGPT(emailText, files, imageInfo=[]):
    client = OpenAI(api_key=keys.openAI_APIKEY)

    for index, file_ in enumerate(files):
        files[index] = client.files.create(
        file=file_,
        purpose='assistants'
        ).id

    # Add the file to the assistant
    textFileAssistant = client.beta.assistants.create(
    instructions="You are a helpful robot who extracts flight details from email.",
    model="gpt-4-1106-preview",
    tools=[{"type": "retrieval"}],
    file_ids=[]
    )

    if len(files) > 0:
        content_text = """Extract ALL flight details from the email which I will give you. Extract the following data:
        - currency
        - number of adult passangers
        - number of child passangers
        - maximum number of connections
        - requested airlines with codes
        - travel class.

        For each flight segment extract the following data:
        - origin location names and IATA 3-letter codes
        - alternative origin locations names and IATA 3-letter codes (only for this specific segment)
        - destination locationname and IATA 3-letter code
        - alternative destination locations names and IATA 3-letter codes (only for this specific segment)
        - included connection points names and IATA 3-letter codes
        - departure date
        - exact departure time
        - earliest departure time
        - latest departure time
        - exact arrival time
        - earliest arrival time
        - latest arrival time
        
        Email (in text format) to extract details from:\n\n"""
        content_text += emailText
        #content_text = "Extract ALL flight details from the email which I will give you. Extract data like origin, destionation, dates, timeframes, requested connection points (if specified explicitly) and ALL other flight information. Also, if there are any documents attached, read them too, they provide aditional information. You MUST read every single one of the attached documents, as they all include critical information.\n\nProvide an answer without asking me any further questions.\n\nEmail (in text format) to extract details from:\n\n" + emailText
        if len(imageInfo) > 0:
            content_text += "\n\nAlso take this important extra information about this email into consideration:\n" + imageInfo
    else:
        content_text = "Extract ALL flight details from the email which I will give you. Extract data like origin, destionation, dates, timeframes, requested connection points (if specified explicitly) and ALL other flight information.\n\nProvide an answer without asking me any further questions.\n\nEmail (in text format) to extract details from:\n\n" + emailText
    
    thread = client.beta.threads.create(
    messages=[
        {
        "role": "user",
        "content": content_text,
        "file_ids": files
        }
    ]
    )

    assistant_id=textFileAssistant.id

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
    apiDataHandler.delete_assistant(textFileAssistant.id, keys.openAI_APIKEY)

    for file_ in files:
        apiDataHandler.delete_file(file_, keys.openAI_APIKEY)

    return answer

def isIntercontinentalFlight(emailText):
        openai.api_key = keys.openAI_APIKEY
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": ("I will provide you an email text about flight tender inquiry. I want you to tell me if it is a request for a intercontinental flight. A flight is intercontinental if it flies from one continent to another.\n\nEmail text:\n" + emailText + "\n\nOutput should be ONLY yes/no.")}
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