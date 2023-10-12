import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import AIhelperEmail
import keys
import AIhelper
import AIrephraser
import requests
import AIregular

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
AIhelper_ = None
AIhelperEmail_ = None
AIrephraser_ = None
AIregular_ = None

@app.route('/get_answer_email', methods=['GET'])
def get_answer_email():
    sender_userID = request.args.get('sender_userID', type=str)
    sender_name = request.args.get('sender_name', type=str)
    card_id = request.args.get('card_id', type=str)
    contact_id = request.args.get('contact_id', type=str)
    badResponses = json.loads(request.args.get('badResponses', type=str))
    responseID = json.loads(request.args.get('responseID', type=str))
    explicit_question = json.loads(request.args.get('explicit_question', type=str))
    reply, memory = AIhelperEmail_.returnAnswer(sender_userID, sender_name, card_id, contact_id, badResponses, explicit_question)
    print("reply:\n", reply)

    answer = {"reply": reply, "context": memory, "responseID": responseID}
    return jsonify(answer)

@app.route('/get_answer', methods=['GET'])
def get_answer():
    sender_userID = request.args.get('sender_userID', type=str)
    recipient_userID = request.args.get('recipient_userID', type=str)
    badResponses = json.loads(request.args.get('badResponses', type=str))
    responseID = json.loads(request.args.get('responseID', type=str))
    explicit_question = json.loads(request.args.get('explicit_question', type=str))
    reply, memory = AIhelper_.returnAnswer(recipient_userID, sender_userID, badResponses, explicit_question)
    print("reply:\n", reply)

    answer = {"reply": reply, "context": memory, "responseID": responseID}
    return jsonify(answer)

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

@app.route('/rephrase', methods=['GET'])
def rephrase():
    message = request.args.get('message', type=str)
    prompt = request.args.get('prompt', type=str)

    rephrased_message = AIrephraser_.rephraseMessage(message, prompt)

    return jsonify(rephrased_message)

@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    print("get")
    short_lived_token = request.args.get('short_lived_token', type=str)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {short_lived_token}'
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
    AIhelper_ = AIhelper.AIhelper(keys.openAI_APIKEY)
    AIhelperEmail_ = AIhelperEmail.AIhelperEmail(keys.openAI_APIKEY)
    AIrephraser_ = AIrephraser.AIrephraser(keys.openAI_APIKEY)
    AIregular_ = AIregular.AIregular(keys.openAI_APIKEY)
    app.run(host='0.0.0.0', port=5000, debug=True)

    #while(1):
    #    query = str(input())
    #    print(lb.returnAnswer(query))