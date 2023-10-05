import json

def append_json(new_data, file_data):
    file_data["responses"].append(new_data)
    return file_data

def write_json(data, filepath):
    with open(filepath, 'w') as file:
        file.write(json.dumps(data, indent=2))

def update_json(data, contextToSearch, AIresponse, score):
    for response in data['responses']:
        if response['context'] == contextToSearch:
            print("FOUND")
            response['AIresponse'] = AIresponse
            response['score'] = score 

    return data

def delete_from_json(data, contextToSearch):
    target_context = contextToSearch

    data['responses'] = [response for response in data['responses'] if response['context'] != target_context]

    return data