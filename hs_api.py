import requests
import json
import markdownify

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
        self.threads = self.threads.reverse()

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

    def list_conversations(self, page: int):
        res = _make_request_get(self.token, 'conversations', {
            "page": page,
            "embed": "threads"
        })
        if res.status_code != 200:
            raise res.text
        convs = []
        for c in json.loads(res.text)['_embedded']['conversations']:
            convs.append(Conversation(c))
        return convs
