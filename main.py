import json
import os
from get_token import get_token

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()
    
if not os.path.exists('config.json'):
    raise "Error: Config not found"

config = json.loads(open_file('config.json'))
hs_id = config["helpscout_id"]
hs_secret = config["helpscout_secret"]

code = get_token(hs_id, hs_secret)