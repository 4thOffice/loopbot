import sqlite3
import json
from anytree import Node
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

def serialize_node(node):
    serialized_node = {
        "name": node.name,
        "type": node.type,  # Add the "type" field to the serialized data
        "answers": {key: serialize_node(value) for key, value in node.answers.items()}
    }
    return serialized_node

def deserialize_node(json_data, parent=None):
    name = json_data["name"]
    node_type = json_data.get("type")  # Extract the "type" field from JSON data
    node = Node(name, parent=parent, answers={}, type=node_type)
    if "answers" in json_data:
        answers = json_data["answers"]
        for key, child_data in answers.items():
            node.answers[key] = deserialize_node(child_data, parent=node)
    return node

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

def insert_last_comment(user_id, recipient_userID, last_comment):
    cursor.execute('''
        SELECT * FROM last_comments
        WHERE user_id = ? AND recipient_user_id = ?
    ''', (user_id, recipient_userID,))
    
    existing_row = cursor.fetchone()
    
    if existing_row:
        # If the row exists, update it
        print("existing row ", user_id, last_comment)
        cursor.execute('''
            UPDATE last_comments
            SET last_comment = ?
            WHERE user_id = ? AND recipient_user_id = ?
        ''', (json.dumps(last_comment), user_id, recipient_userID,))
    else:
        # If the row does not exist, insert a new row
        cursor.execute('''
            INSERT INTO last_comments (user_id, recipient_user_id, last_comment)
            VALUES (?, ?, ?)
        ''', (user_id, recipient_userID, json.dumps(last_comment),))
    conn.commit()

def get_user_last_comment(user_id, recipient_userID):
    cursor.execute('''
        SELECT last_comment FROM last_comments
        WHERE user_id = ? AND recipient_user_id = ?
    ''', (user_id, recipient_userID,))
    last_comment = cursor.fetchone()

    if last_comment:
        # Fetch the first element from the row (assuming there is only one column in the result)
        last_comment_text = last_comment[0]
        return json.loads(last_comment_text)
    else:
        return None
    
def insert_decision_tree(user_id, decision_tree, decision_tree_name):

    serialized_root = serialize_node(decision_tree)
    json_decision_tree = json.dumps(serialized_root, indent=2)

    cursor.execute('''
        SELECT * FROM decision_trees
        WHERE user_id = ? AND decision_tree_name = ?
    ''', (user_id, decision_tree_name,))
    
    existing_row = cursor.fetchone()
    
    if existing_row:
        # If the row exists, update it
        print("existing row ", user_id, decision_tree_name)
        cursor.execute('''
            UPDATE decision_trees
            SET decision_tree = ?
            WHERE user_id = ? AND decision_tree_name = ?
        ''', (json_decision_tree, user_id, decision_tree_name,))
    else:
        # If the row does not exist, insert a new row
        cursor.execute('''
            INSERT INTO decision_trees (user_id, decision_tree_name, decision_tree)
            VALUES (?, ?, ?)
        ''', (user_id, decision_tree_name, json_decision_tree,))
    conn.commit()

def get_decision_tree(user_id, decision_tree_name):
    cursor.execute('''
        SELECT decision_tree FROM decision_trees
        WHERE user_id = ? AND decision_tree_name = ?
    ''', (user_id, decision_tree_name,))
    decision_tree = cursor.fetchone()

    if decision_tree:
        # Fetch the first element from the row (assuming there is only one column in the result)
        decision_tree_text = decision_tree[0]

        parsed_data = json.loads(decision_tree_text)
        deserialized_root = deserialize_node(parsed_data)

        return deserialized_root
    else:
        return None