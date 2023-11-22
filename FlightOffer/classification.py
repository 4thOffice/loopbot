#get all emails by card ID
#copy id dobi comment chate, original id pa comment maile
import re
import sys
import json
import openai
import requests
import os
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import keys

def cut_string_at_keyword(input_string, keyword_list):
    position = len(input_string)
    for keyword in keyword_list:
        index = input_string.find(keyword)
        if index != -1 and index < position:
            position = index
    
    cut_string = input_string[position:]
    return cut_string

def normalize_newlines(text, max_newlines=2):
    """Normalizes the number of newlines in text to have at most 'max_newlines' newlines in a row."""
    lines = text.splitlines()
    normalized_lines = []
    current_newlines = 0

    for line in lines:
        if line.strip():  # If the line has content, reset newline counter and keep the line.
            normalized_lines.append(line.strip())
            current_newlines = 0
        else:  # If the line is blank, increment the newline counter if it's less than 'max_newlines'.
            current_newlines += 1
            if current_newlines <= max_newlines:
                normalized_lines.append('')

    return '\n'.join(normalized_lines)

def parseHtml(commentContent):
    html_tag_pattern = re.compile(r'<[^>]*>|<!--(.*?)-->', re.DOTALL)
    clean_text = re.sub(html_tag_pattern, '', commentContent)
    clean_text = clean_text.replace("&nbsp;", "")
    clean_text = clean_text.replace("nbsp;", "")
    return normalize_newlines(clean_text, max_newlines=2)

def getFiles(attachments, commentContent):
    returnFileUrls = []
    signature = ""
    signature = cut_string_at_keyword(commentContent, ["LP", "lep pozdrav", "Lep pozdrav", "lp", "pozdrav"])
    for attachment in attachments:
        if attachment["id"] not in signature:
            returnFileUrls.append(attachment["urlLink"])
    return {"fileUrls": returnFileUrls}

def getCommentContent(commentID, authkey):
    endpoint_url = 'https://api.intheloop.io/api/v1/comment/' + commentID + '/preview'

    headers = {
        'accept': 'application/json',
        'Authorization': authkey,
        'Content-Type': 'application/json'
    }

    response = requests.get(endpoint_url, headers=headers)
    if response.status_code == 200:
        comment = response.json()
        commentText = comment["html"]
        html_tag_pattern = re.compile(r'<[^>]*>|<!--(.*?)-->', re.DOTALL)
        clean_text = re.sub(html_tag_pattern, '', commentText)
        clean_text = clean_text.replace("&nbsp;", "")
        clean_text = clean_text.replace("nbsp;", "")
        return normalize_newlines(clean_text, max_newlines=2)

    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []
    
#Get first email in email thread
def getFirstCommentData(cardID, authkey):
    endpoint_url = 'https://api.intheloop.io/api/v1/comment/list'

    headers = {
        'accept': 'application/json',
        'Authorization': authkey,
        'Content-Type': 'application/json'
    }

    data = {
        "offset": 0,
        "size": 10,
        "sortOrder": "Ascending",
        "cardIds": [
            cardID + "-copy1T",
            cardID
        ],
        "authorizeCardIdsBeforeSearch": False,
        "cardTypes": "",
        "htmlFormat": "text/html",
        "includeSignedLinks": True
    }

    response = requests.get(endpoint_url, headers=headers, params=data)
    if response.status_code == 200:
        comments = response.json()
        for comment in comments["resources"]:
            if comment["$type"] == "CommentMail":
                fileUrls = []
                attachments = comment["attachments"]["resources"]
                signature = ""
                if "content" in comment["body"]:
                    signature = cut_string_at_keyword(comment["body"]["content"], ["LP", "lep pozdrav", "Lep pozdrav", "lp", "pozdrav"])
                for attachment in attachments:
                    if attachment["id"] not in signature:
                        fileUrls.append(attachment["urlLink"])
                return {"id": comment["id"], "fileUrls": fileUrls}
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {"id": None, "fileUrls": []}

def classifyEmail(text):
    openai.api_key = keys.openAI_APIKEY

    user_msg = "I will give you an email. Tell me if it is a flight tender inquiry. It only counts as flight tender inquiry if person asks for a quote for a flight (hotels dont count) and if at least some flights details are provided.\nOnly say yes/no:\n\n" + text

    response = openai.chat.completions.create(
                                            model="gpt-3.5-turbo-16k",
                                            messages=[{"role": "user", "content": user_msg}]
                                            )
    
    answer = response.choices[0].message.content.lower()
    print("answer:", answer)
    
    if "yes" in answer:
        return True
    return False