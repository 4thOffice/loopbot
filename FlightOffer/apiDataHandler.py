import requests
import sys
sys.path.append("../")
import keys

def list_files(api_key):
    url = "https://api.openai.com/v1/files"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # If call is successful, return the list of assistants
        return response.json()["data"]
    else:
        raise Exception(f"Failed to fetch assistants, status code: {response.status_code}")

def delete_file(file_id, api_key):
    url = f"https://api.openai.com/v1/files/{file_id}"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print(f"File with ID {file_id} has been deleted successfully.")
        return response.json()
    else:
        raise Exception(f"Failed to fetch assistants, status code: {response.status_code}")
    
def list_assistants(api_key):
    url = "https://api.openai.com/v1/assistants"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "assistants=v1"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # If call is successful, return the list of assistants
        return response.json()["data"]
    else:
        raise Exception(f"Failed to fetch assistants, status code: {response.status_code}")


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

def delete_all_assistants():
    assistants = list_assistants(keys.openAI_APIKEY)
    for assistant in assistants:
        delete_assistant(assistant["id"], keys.openAI_APIKEY)

def delete_all_files():
    files = list_files(keys.openAI_APIKEY)
    for file_ in files:
        delete_file(file_["id"], keys.openAI_APIKEY)

#delete_all_assistants()
#delete_all_files()