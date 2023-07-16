import json
from flask import Flask, request, jsonify

from hs_api import load_api

app = Flask(__name__)

api = load_api()

@app.route('/', methods=['POST'])
def process_data():
    data = request.get_json()
    with open('messages.jsonl', 'a') as f:
        f.write(json.dumps(data))
    api.recieve_message(data)
    return jsonify({ 'responded': True }), 200

if __name__ == '__main__':
    app.run(port=5500)