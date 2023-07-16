import os
import json
import hashlib
from time import time, sleep
from hs_api import load_api
from util import open_file, save_file

lifetime = 8 * 60 * 60
heart_beat_time = 5 * 60

api = load_api()

responded_conversations_file = 'responded_conversations.json'
responded_conversations = { }
if os.path.exists(responded_conversations_file):
    responded_conversations = json.loads(open_file(responded_conversations_file))

start_time = time()
while time() - start_time < lifetime:
    convs = api.list_conversations(1)
    res_hash = hashlib.sha256(json.dumps(responded_conversations)).hexdigest()
    for conv in convs:
        hash = hashlib.sha256(conv.for_gpt()).hexdigest()
        if conv.id in responded_conversations.keys() and responded_conversations[conv.id] == hash:
            continue
        print(f'New Conversation: {conv.id}')
        responded_conversations[conv.id] = hash
        api.recieve_conversation(conv)
	break

    if hashlib.sha256(json.dumps(responded_conversations)).hexdigest() != res_hash:
        save_file(responded_conversations_file, json.dumps(responded_conversations))
    sleep(heart_beat_time)
