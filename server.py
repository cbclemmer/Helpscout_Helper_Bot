import json
import os
from flask import Flask, request, jsonify

from hs_api import HelpscoutAPI
from get_token import get_token

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()
    
if not os.path.exists('config.json'):
    raise "Error: Config not found"

config = json.loads(open_file('config.json'))
hs_id = config["helpscout_id"]
hs_secret = config["helpscout_secret"]
openai_token = config["openai_key"]

token = get_token(hs_id, hs_secret)

api = HelpscoutAPI(token, openai_token, 'davinci')

app = Flask(__name__)

@app.route('/', methods=['POST'])
def process_data():
    data = request.get_json()
    with open('messages.jsonl', 'a') as f:
        f.write(json.dumps(data))
    api.recieve_message(data)

if __name__ == '__main__':
    app.run(port=5500)