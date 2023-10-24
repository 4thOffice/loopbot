import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import AIhelperEmail
import keys
import AIhelper
import AIrephraser
import requests
import AIregular
import userDataHandler
import AIclassificator
import sys
sys.path.append('./APIcalls')
import APIcalls.directchatHistory as directchatHistory

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
AIhelper_ = None
AIhelperEmail_ = None
AIrephraser_ = None
AIregular_ = None
userDataHandler_ = None
AIclassificator_ = None

@app.route('/get_answer_email', methods=['GET'])
def get_answer_email():
    sender_userID = request.args.get('sender_userID', type=str)
    sender_name = request.args.get('sender_name', type=str)
    card_id = request.args.get('card_id', type=str)
    contact_id = request.args.get('contact_id', type=str)
    badResponses = json.loads(request.args.get('badResponses', type=str))
    responseID = json.loads(request.args.get('responseID', type=str))
    reply, memory = AIhelperEmail_.returnAnswer(sender_userID, sender_name, card_id, contact_id, badResponses)
    print("reply:\n", reply)

    answer = {"reply": reply, "context": memory, "responseID": responseID}
    return jsonify(answer)

@app.route('/get_answer', methods=['GET'])
def get_answer():
    sender_userID = request.args.get('sender_userID', type=str)
    recipient_userID = request.args.get('recipient_userID', type=str)
    classified_issue = request.args.get('classified_issue', type=str)
    badResponses = json.loads(request.args.get('badResponses', type=str))
    responseID = json.loads(request.args.get('responseID', type=str))
    ResponseRecipientID = json.loads(request.args.get('ResponseRecipientID', type=str))
    reply = AIhelper_.returnAnswer(recipient_userID, sender_userID, classified_issue, badResponses)

    reply = AIhelper_.returnAnswer(recipient_userID, sender_userID, classified_issue, badResponses)

    print("reply:\n", reply)
    answer = {"reply": reply, "responseID": responseID, "ResponseRecipientID": ResponseRecipientID}
    
    return jsonify(answer)

@app.route('/check_for_new_comments', methods=['GET'])
def check_for_new_comments():
    sender_userID = request.args.get('sender_userID', type=str)
    recipient_userID = request.args.get('recipient_userID', type=str)
    oldComments = json.loads(request.args.get('oldComments', type=str))

    print("oldComments", oldComments)

    isNewData, newComments = AIhelper_.checkForNewComments(sender_userID, recipient_userID, oldComments)
    
    print("newComments", newComments)
    answer = {"isNewData": isNewData, "oldComments": newComments}
    
    return jsonify(answer)

@app.route('/add_file_to_faq', methods=['POST'])
def add_file_to_faq():
    uploaded_file = request.files['file']
    sender_userID = request.form['sender_userID']

    if uploaded_file:
        file_content = uploaded_file.read().decode('utf-8')
        userDataHandler_.addToUserDocument(sender_userID, file_content, uploaded_file.filename)
        return jsonify({"reply": "Document added to knowledge base."})
    else:
        return jsonify({"reply": "There was an error uploading document."})

@app.route('/handle_good_response', methods=['PUT'])
def handle_good_response():
    recipient_userID = request.args.get('recipient_userID', type=str)
    sender_userID = request.args.get('sender_userID', type=str)
    AIresponse = request.args.get('AIresponse', type=str)

    ret = AIhelper_.handleGoodResponse(sender_userID, recipient_userID, AIresponse)

    return jsonify(ret)

@app.route('/handle_bad_response', methods=['PUT'])
def handle_bad_response():
    recipient_userID = request.args.get('recipient_userID', type=str)
    sender_userID = request.args.get('sender_userID', type=str)
    AIresponse = request.args.get('AIresponse', type=str)

    ret = AIhelper_.handleBadResponse(sender_userID, recipient_userID, AIresponse)

    return jsonify(ret)

@app.route('/update_faq', methods=['PUT'])
def update_faq():
    sender_userID = request.args.get('sender_userID', type=str)
    AIresponse = request.args.get('AIresponse', type=str)
    classified_issue = request.args.get('classified_issue', type=str)
    FAQ_conversation_stage = request.args.get('FAQ_conversation_stage', type=int)
    user_input = request.args.get('user_input', type=str)

    print("FAQ_conversation_stage ", FAQ_conversation_stage)
    print("user_input ", user_input)
    print("AIresponse ", AIresponse)
    
    ret = AIhelper_.updateFAQ(sender_userID, AIresponse, classified_issue, FAQ_conversation_stage, user_input)

    return jsonify(ret)

@app.route('/show_faq', methods=['PUT'])
def show_faq():
    sender_userID = request.args.get('sender_userID', type=str)
    FAQShowStage = request.args.get('FAQShowStage', type=int)
    user_input = request.args.get('user_input', type=str)
    
    ret = AIhelper_.showFAQ(sender_userID, FAQShowStage, user_input)

    return jsonify(ret)



@app.route('/handle_good_response_email', methods=['PUT'])
def handle_good_response_email():
    sender_userID = request.args.get('sender_userID', type=str)
    sender_name = request.args.get('sender_name', type=str)
    card_id = request.args.get('card_id', type=str)
    contact_id = request.args.get('contact_id', type=str)
    AIresponse = request.args.get('AIresponse', type=str)

    ret = AIhelperEmail_.handleGoodResponse(sender_userID, sender_name, contact_id, card_id, AIresponse)

    return jsonify(ret)

@app.route('/handle_bad_response_email', methods=['PUT'])
def handle_bad_response_email():
    sender_userID = request.args.get('sender_userID', type=str)
    sender_name = request.args.get('sender_name', type=str)
    card_id = request.args.get('card_id', type=str)
    contact_id = request.args.get('contact_id', type=str)
    AIresponse = request.args.get('AIresponse', type=str)

    ret = AIhelperEmail_.handleBadResponse(sender_userID, sender_name, contact_id, card_id, AIresponse)

    return jsonify(ret)

@app.route('/rephrase', methods=['GET'])
def rephrase():
    message = request.args.get('message', type=str)
    prompt = request.args.get('prompt', type=str)
    prompt_mode = request.args.get('prompt_mode', type=str)
    ResponseRecipientID = json.loads(request.args.get('ResponseRecipientID', type=str))
    
    if prompt_mode == "custom":
        rephrased_message = AIrephraser_.change_message(message, prompt)
    elif prompt_mode == "preset":
        rephrased_message = AIrephraser_.rephraseMessage(message, prompt)

    answer = ({"rephrased_message": rephrased_message, "ResponseRecipientID": ResponseRecipientID})
    return jsonify(answer)

@app.route('/classify', methods=['GET'])
def classify():
    sender_userID = request.args.get('sender_userID', type=str)
    recipient_userID = request.args.get('recipient_userID', type=str)

    authKey = AIhelper_.getAuthkey(sender_userID)
    comments = directchatHistory.getAllComments(20, recipient_userID, authKey)
    lastTopic = directchatHistory.getLastTopic(comments)
    processedLastTopic = directchatHistory.memoryPostProcess(lastTopic)

    classified_issue = AIclassificator_.classify(processedLastTopic)

    return jsonify({"classified_issue": classified_issue})

@app.route('/check_intent', methods=['GET'])
def check_intent():
    text = request.args.get('text', type=str)
    state = request.args.get('state', type=str)
    
    intent = AIclassificator_.check_intent(text, state)
    print("intent: ", intent["intent"])
    return jsonify(intent)


@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    print("get")
    auth_header = request.headers.get('Authorization')

    # Check if Authorization header is present
    if auth_header is None:
        return jsonify({"error": "Missing Authorization header"}), 401  # Unauthorized status code

    # Extract the Bearer token from the Authorization header
    try:
        _, token = auth_header.split(' ')
    except ValueError:
        return jsonify({"error": "Invalid Authorization header"}), 401  # Unauthorized status code

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.get('https://api.intheloop.io/api/v1/user', headers=headers)

    responseJson = response.json()
    print("userID ", responseJson["id"])
    print("userID ", responseJson["name"])
    return jsonify({"id": responseJson["id"], "username": responseJson["name"]}) #tole naredi da vrne tuple id, name -> spremeni v get_user_info -> spremeni na drugi strani in si shrani name in ga podaj v getansweremail


@app.route('/get_answer_regular', methods=['GET'])
def get_answer_regular():
    user_input = request.args.get('user_input', type=str)
    reply = AIregular_.returnAnswer(user_input)

    return jsonify(reply)

if __name__ == '__main__':
    userDataHandler_ = userDataHandler.UserDataHandler()
    AIhelper_ = AIhelper.AIhelper(keys.openAI_APIKEY, userDataHandler_)
    AIhelperEmail_ = AIhelperEmail.AIhelperEmail(keys.openAI_APIKEY, userDataHandler_)
    AIrephraser_ = AIrephraser.AIrephraser(keys.openAI_APIKEY)
    AIregular_ = AIregular.AIregular(keys.openAI_APIKEY)
    AIclassificator_ = AIclassificator.AIclassificator(keys.openAI_APIKEY)
    app.run(host='0.0.0.0', port=5000, debug=True)

    #while(1):
    #    query = str(input())
    #    print(lb.returnAnswer(query))