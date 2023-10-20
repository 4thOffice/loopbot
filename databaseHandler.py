import sqlite3
import json

json_content_template = """{
  "responses": [
    {
      "context": "",
      "AIresponse": "",
      "score": 0
    }
  ]
}
"""

faq_content_template = """{
  "responses": [
    {
      "issue": "",
      "answer": ""
    }
  ]
}
"""


conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

# Retrieve JSON data for a user and data_name
def add_user_json_data(user_id, file_name, file_content=None):
    cursor.execute('''
        SELECT json_content FROM user_data
        WHERE user_id = ? AND file_name = ?
    ''', (user_id, file_name))
    existing_row = cursor.fetchone()

    print("filename: ", file_name)
    print("filecontent: ", file_content)
    if existing_row:
        # If the row exists, retrieve and print JSON data
        retrieved_data = json.loads(existing_row[0])
        print('Retrieved JSON data:', retrieved_data)
        return retrieved_data
    else:
        # If the row does not exist, insert a new row and print None
        print('No data found for user_id:', user_id, 'and file_name:', file_name)
        if file_content:
            json_template = file_content
        elif file_name == "faq":
            json_template = json.loads(faq_content_template)
        else:
            json_template = json.loads(json_content_template)
            
        insert_json_data(user_id, file_name, json_template)

# Insert JSON data for the user
def insert_json_data(user_id, file_name, json_content):
    cursor.execute('''
        SELECT * FROM user_data
        WHERE user_id = ? AND file_name = ?
    ''', (user_id, file_name))
    
    existing_row = cursor.fetchone()
    
    if existing_row:
        # If the row exists, update it
        print("existing row ", user_id, file_name, json_content)
        cursor.execute('''
            UPDATE user_data
            SET json_content = ?
            WHERE user_id = ? AND file_name = ?
        ''', (json.dumps(json_content), user_id, file_name))
    else:
        # If the row does not exist, insert a new row
        cursor.execute('''
            INSERT INTO user_data (user_id, file_name, json_content)
            VALUES (?, ?, ?)
        ''', (user_id, file_name, json.dumps(json_content)))
    conn.commit()

def get_unique_user_ids():
    cursor.execute('''
        SELECT DISTINCT user_id FROM user_data
    ''')
    unique_user_ids = [row[0] for row in cursor.fetchall()]
    return unique_user_ids

def get_user_json_data(user_id):
    cursor.execute('''
        SELECT file_name, json_content FROM user_data
        WHERE user_id = ?
    ''', (user_id,))
    user_data = cursor.fetchall()
    json_data = {}
    
    for row in user_data:
        file_name, json_content = row
        json_data[file_name] = json.loads(json_content)
    
    return json_data