import requests
import json
import markdownify
from typing import List
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
        # text = re.sub(r'\[(.*?)\]\((.*?)\)', r'LINK', text)
        # text = re.sub(r'https?:\/\/[^\s]*', r'LINK', text)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', r'LINK', text)
        text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'PICTURE', text)
        text = re.sub(r'\+\d{1,3}\s\d{1,3}\s\d{1,4}\s\d{1,10}', r'PHONE_NUMBER', text)
        text = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', r'IP', text)
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
    text: str
    id: str
    subject: str
    created: str
    status: str
    threads: List[Thread]

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

    def get_completions(self):
        completions = []
        current_prompt = ''
        first = True
        for t in self.threads:
            if t.type == "lineitem":
                continue
            if t.source == "user" and not first:
                completions.append({
                    "prompt": current_prompt + '\n\n######\n\n',
                    "completion": t.for_gpt() + '\n\n######\n\n'
                })
            first = False
            current_prompt += t.for_gpt() + '\n'
        return completions

class HelpscoutAPI:
    def __init__(self, token: str):
        self.token = token

    def save_conversation_list(self, file_name, conversations: List[Conversation]) -> None:
        folder = 'conversation_lists'
        if not os.path.exists(folder):
            os.makedirs(folder)
        path = f"{folder}/{file_name}.json"
        if os.path.exists(path):
            raise f"Error file {file_name} already exists"
        with open(path, 'w') as f:
            f.writelines(json.dumps(conversations))

    def load_conversation_list(self, file_name) -> List[Conversation]:
        folder = 'conversation_lists'
        if not os.path.exists(folder):
            return None
        path = f"{folder}/{file_name}.json"
        if not os.path.exists(path):
            return None
        data = json.loads(open_file(path))
        ret_val = []
        for c in data:
            ret_val.append(Conversation(c))
        return ret_val

    def list_conversations(self, page: int) -> List[Conversation]:
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
    
    def save_completions(self, file_name: str, convs: List[Conversation]) -> None:
        completions = []
        for c in convs:
            comps = c.get_completions()
            for comp in comps: 
                completions.append(comp)
        folder = 'completions'
        if not os.path.exists(folder):
            os.makedirs(folder)
        path = f"{folder}/{file_name}.jsonl"
        if os.path.exists(path):
            raise f"Error file {file_name} already exists"
        with open(path, 'w') as f:
            for comp in completions:
                f.write(json.dumps(comp) + '\n')
        print(f"Completions for {file_name} written to file")