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
            self.body = markdownify.markdownify(data['body'], heading_style="ATX")
        self.action = ''
        if 'text' in data['action'].keys():
            self.action = data['action']['text']
        self.type = data['type']
        self.source = data['source']['via']

    def _sanitize(self, text: str) -> str:
        # replace links with "LINK"
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'LINK', text)
        text = re.sub(r'https?:\/\/[^\s]*', r'LINK', text)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', r'LINK', text)
        # replace images with "PICTURE"
        text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'PICTURE', text)
        text = re.sub(r'\+\d{1,3}\s\d{1,3}\s\d{1,4}\s\d{1,10}', r'PHONE_NUMBER', text)
        text = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', r'IP', text)
        # text = re.sub(r'https?:\/\/[^\s]*\/login[^\s]*', r'LOGIN', text)
        # text = re.sub(r'https?:\/\/[^\s]*\/instructor[^\s]*', r'INSTRUCTOR_SITE_LINK', text)
        # text = re.sub(r'https?:\/\/scormfly[^\s]*', r'SCORMFLY_LINK', text)
        # text = re.sub(r'\b\d{1,5}\s[a-zA-Z0-9\s]*[.,]?\s[a-zA-Z]{2,}\b', r'ADDRESS', text)
        # text = re.sub(r'^.*This communication.*\n?', '', text, flags=re.MULTILINE)
        # text = re.sub(r'^.*This email and any attachments.*\n?', '', text, flags=re.MULTILINE)
        # text = re.sub(r'\b[A-Z][a-z]+\s([A-Z]\.\s)?[A-Z][a-z]+\b', r'NAME', text)
        return text

    def for_gpt(self):
        s = "###THREAD\n"
        s += f"Type: {self.type}\n"
        s += f"Source: {self.source}\n"
        if self.action != "":
            s += f"Action: {self.action}\n"
        if self.body != "":
            s += f"Body:\n{self._sanitize(self.body)}\n"
        return s

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

    def for_gpt(self):
        threads = ""
        for t in self.threads:
            if t.type == "lineitem":
                continue
            threads += t.for_gpt() + '\n'

        return f"""
###CONVERSATION
Subject: {self.subject}

{threads}
"""

    def to_string(self):
        threads = ""
        for t in self.threads:
            threads += t.to_string() + '\n'

        return f"""
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
