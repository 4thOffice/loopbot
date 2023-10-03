import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import keys
import AIhelper
import AIrephraser

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
AIhelper_ = None
AIrephraser_ = None

@app.route('/get_answer', methods=['GET'])
def get_answer():
    sender_userID = request.args.get('sender_userID', type=str)
    recipient_userID = request.args.get('recipient_userID', type=str)
    badResponses = json.loads(request.args.get('badResponses', type=str))

    reply, memory = AIhelper_.returnAnswer(recipient_userID, sender_userID, badResponses)
    print("reply:\n", reply)

    answer = {"reply": reply, "context": memory}
    return jsonify(answer)

@app.route('/handle_good_response', methods=['PUT'])
def handle_good_response():
    recipient_userID = request.args.get('recipient_userID', type=str)
    AIresponse = request.args.get('AIresponse', type=str)

    ret = AIhelper_.handleGoodResponse(recipient_userID, AIresponse)

    return jsonify(ret)

@app.route('/handle_bad_response', methods=['PUT'])
def handle_bad_response():
    recipient_userID = request.args.get('recipient_userID', type=str)
    AIresponse = request.args.get('AIresponse', type=str)

    ret = AIhelper_.handleBadResponse(recipient_userID, AIresponse)

    return jsonify(ret)

@app.route('/rephrase', methods=['GET'])
def rephrase():
    message = request.args.get('message', type=str)
    prompt = request.args.get('prompt', type=str)

    rephrased_message = AIrephraser_.rephraseMessage(message, prompt)

    return jsonify(rephrased_message)


if __name__ == '__main__':
    AIhelper_ = AIhelper.AIhelper(keys.openAI_APIKEY)
    AIrephraser_ = AIrephraser.AIrephraser(keys.openAI_APIKEY)
    app.run(host='0.0.0.0', port=5000, debug=True)

    #while(1):
    #    query = str(input())
    #    print(lb.returnAnswer(query))