from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import loopBot
import keys

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://192.168.124.75:3000"}})
lb = None

@app.route('/get_answer', methods=['GET'])
def get_answer():
    query = request.args.get('query', type=str)
    prompt = request.args.get('prompt', type=str)
    print("query:\n", query)
    reply, similarChats = lb.returnAnswer(query, prompt)
    print("reply:\n", reply)

    return_data = {"reply": reply, "similarChats": similarChats}
    return jsonify(return_data)

@app.route('/get_prompt', methods=['GET'])
def get_prompt():
    prompt = lb.getPrompt()
    print("prompt:\n", prompt)
    return prompt

    #return get_normal_transactions(starting_block, wallet_address, API_KEY, endpoint)


if __name__ == '__main__':
    lb = loopBot.LoopBot(keys.openAI_APIKEY)
    app.run(debug=True)

    #while(1):
    #    query = str(input())
    #    print(lb.returnAnswer(query))