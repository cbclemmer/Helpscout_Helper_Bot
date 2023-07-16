import os
import json
from time import time, sleep
from hs_api import load_api
from util import open_file, save_file, to_sha

lifetime = 8 * 60 * 60
heart_beat_time = 5 * 60

api = load_api()

responded_conversations_file = 'responded_conversations.json'
responded_conversations = { }
if os.path.exists(responded_conversations_file):
    responded_conversations = json.loads(open_file(responded_conversations_file))

print('Started Watcher')

start_time = time()
while time() - start_time < lifetime:
    convs = api.list_conversations(1, True, False)
    res_hash = to_sha(responded_conversations)
    for conv in convs:
        print(f'Found conversation: {conv.id}')
        hash = to_sha(conv.for_gpt())
        if conv.id in responded_conversations.keys() and responded_conversations[conv.id] == hash:
            continue
        print(f'New Conversation: {conv.id}')
        responded_conversations[conv.id] = hash
        api.recieve_conversation(conv)
        break

    if to_sha(responded_conversations) != res_hash:
        save_file(responded_conversations_file, json.dumps(responded_conversations))
    sleep(heart_beat_time)
