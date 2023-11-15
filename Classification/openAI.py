import time
from openai import OpenAI
import sys

import requests
sys.path.append("../")
import keys

def delete_assistant(assistant_id, api_key):
    url = f"https://api.openai.com/v1/assistants/{assistant_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v1"
    }
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print(f"Assistant with ID {assistant_id} has been deleted successfully.")
        return response.json()
    else:
        print(f"Failed to delete assistant with ID {assistant_id}. Status code: {response.status_code}, response: {response.text}")
        return None
    

def askGPT():
    client = OpenAI(api_key=keys.openAI_APIKEY)

    file = client.files.create(
    file=open("../8bhY-Vfvxuj7EQSavH3hPxpPcGuS-SfNMUT-0Ibeafk.png", "rb"),
    purpose='assistants'
    )

    # Add the file to the assistant
    textFileAssistant = client.beta.assistants.create(
    instructions="You are a helpful robot.",
    model="gpt-4-1106-preview",
    tools=[{"type": "retrieval"}],
    file_ids=[]
    )

    pictureFileAssistant = client.beta.assistants.create(
    instructions="You are a helpful robot.",
    model="gpt-4-1106-preview",
    tools=[{"type": "code_interpreter"}],
    file_ids=[]
    )

    thread = client.beta.threads.create(
    messages=[
        {
        "role": "user",
        "content": "I will give you an email. Tell me if it is a tender inquiry. It only counts as tender inquiry if person asks for a quote. Also look at attached files, if there are any, to help with decision.\n\nOnly say yes/no: Pozdravljeni, Prosim za ceno vozovnic. Hvala in lep pozdrav, Adin Bećirović",
        "file_ids": [file.id]
        }
    ]
    )

    run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=pictureFileAssistant.id
    )

    while True:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
        )
        print(run)
        print(run.status)

        if run.status == "completed":
            break
    
    print("completed")

    messages = client.beta.threads.messages.list(
    thread_id=thread.id
    )
    delete_assistant(textFileAssistant.id, keys.openAI_APIKEY)
    delete_assistant(pictureFileAssistant.id, keys.openAI_APIKEY)
    
    print(messages.data[0].content[0].text.value)

askGPT()
