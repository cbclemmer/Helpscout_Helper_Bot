import json
import os
from hs_api import HelpscoutAPI, count_tokens_for_file
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
conversations = []
current_page = 300
while current_page >= 290:
    print(f"page {current_page}")
    convs = api.list_conversations(current_page)
    for c in convs:
        conversations.append(c)
    current_page -= 1
api.save_completions('first', conversations)

tokens = count_tokens_for_file('completions/first.jsonl')
print(f"File has {tokens // 1000}K tokens")

api.create_fine_tune('first')