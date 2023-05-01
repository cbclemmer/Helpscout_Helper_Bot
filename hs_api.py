import requests
import json
import markdownify
import re
import os

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

def _make_request_get(token, path: str, params):
    query = "?"
    first = True
    for k in params.keys():
        if not first:
            query += "&"
        else:
            first = False
        query += f"{k}={params[k]}"
    url = "https://api.helpscout.net/v2/" + path + query
    print(url)
    return requests.get(url, headers={
        "Authorization": f"Bearer {token}"
    })

class Thread:
    def __init__(self, data):
        self.id = data['id']
        self.body = ''
        if 'body' in data:
            self.body = self._sanitize(markdownify.markdownify(data['body'], heading_style="ATX"))
        self.action = ''
        if 'text' in data['action'].keys():
            self.action = data['action']['text']
        self.type = data['type']
        self.source = data['source']['via']

    def _sanitize(self, text: str) -> str:
        # replace links with "LINK"
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'LINK', text)
        # replace images with "PICTURE"
        text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'PICTURE', text)
        return text

    def to_string(self):
        return f"""
___________THREAD_______________
ID: {self.id}
Action: {self.action}
Type: {self.type}
Source: {self.source}
{self.body}
"""

class Conversation:
    def __init__(self, data):
        self.text = json.dumps(data)
        self.id = data['id']
        self.subject = data['subject']
        self.created = data['createdAt']
        self.status = data['status']
        self.threads = []
        for t in data['_embedded']['threads']:
            self.threads.append(Thread(t))
        self.threads.reverse()

    def to_string(self):
        threads = ""
        for t in self.threads:
            threads += t.to_string() + '\n'

        return f"""
______________CONVERSATION_____________
ID: {self.id}
Created: {self.created}
Status: {self.status}

{self.subject}
_____________________
{threads}
"""


class HelpscoutAPI:
    def __init__(self, token: str):
        self.token = token

    def save_conversation_list(self, page, conversations):
        folder = 'conversation_lists'
        if not os.path.exists(folder):
            os.makedirs(folder)
        file_name = f"{folder}/page_{page}.json"
        if os.path.exists(file_name):
            return
        with open(file_name, 'w') as f:
            f.writelines(json.dumps(conversations))

    def load_conversation_list(self, page):
        folder = 'conversation_lists'
        if not os.path.exists(folder):
            return None
        file_name = f"{folder}/page_{page}.json"
        if not os.path.exists(file_name):
            return None
        data = json.loads(open_file(file_name))
        ret_val = []
        for c in data:
            ret_val.append(Conversation(c))
        return ret_val

    def list_conversations(self, page: int):
        convs = self.load_conversation_list(page)
        if convs is None:
            print("API REQUEST")
            res = _make_request_get(self.token, 'conversations', {
                "page": page,
                "embed": "threads"
            })
            if res.status_code != 200:
                raise res.text
            convs = []
            data = json.loads(res.text)['_embedded']['conversations']
            self.save_conversation_list(page, data)
            for c in data:
                convs.append(Conversation(c))
        return convs
