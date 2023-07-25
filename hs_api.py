import requests
import json
import markdownify
from typing import List
import re
import os
import tiktoken
from datetime import datetime
from gpt import GptCompletion, GptChat
import shutil
from get_token import get_token
from util import open_file, get_pretty_date, save_file

def refresh_token():
    print('Token Expired, Refreshing token')
    if not os.path.exists('token.json'):
        raise Exception('Token File does not exist, please manually authenticate')
    token_data = json.loads(open_file('token.json'))
    config = json.loads(open_file('config.json'))
    res = requests.post('https://api.helpscout.net/v2/oauth2/token', data={
        "refresh_token": token_data['refresh_token'],
        "client_id": config['helpscout_id'],
        "client_secret": config['helpscout_secret'],
        "grant_type": 'refresh_token'
    })
    if res.status_code != 200:
        raise Exception(f'Error refreshing token, please manually authenticate\n{res.content.decode()}')
    data = res.json()
    save_file('token.json', json.dumps(data))
    print('Token refreshed successfully')
    return data['access_token']

def count_tokens_for_file(filepath: str):
    objects = open_file(filepath).split('\n')
    encoding = tiktoken.encoding_for_model('text-davinci-003')
    total_tokens = 0
    print(f"File contains {len(objects)} completions")
    for o in objects:
        data = {}
        try:
            data = json.loads(o)
        except:
            continue
        total_tokens += len(encoding.encode(data["prompt"]))
        total_tokens += len(encoding.encode(data["completion"]))
    return total_tokens

class Thread:
    def __init__(self, data):
        self.id = data['id']
        self.body = ''
        if 'body' in data:
            self.body = markdownify.markdownify(data['body'], heading_style="ATX")
        self.action = ''
        if 'action' in data.keys() and 'text' in data['action'].keys():
            self.action = data['action']['text']
        self.type = data['type']
        self.source = data['source']['via']
        self.user = self.source
        if 'email' in data['createdBy']:
            email = data['createdBy']['email']
            if email is not None and len(email) > 0:
                self.user = email[:email.index('@')]

    def _sanitize(self, text: str) -> str:
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'LINK', text)
        text = re.sub(r'https?:\/\/[^\s]*', r'LINK', text)
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
User: {self.user}
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
        self.data = json.dumps(data)
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
    def __init__(self, hs_token: str, openai_token: str, model: str):
        self.token = hs_token
        if os.path.exists('fine_tune.json'):
            model = json.loads(open_file('fine_tune.json'))['model']
        print('Using model: ' + model)
        self.complete = GptCompletion(openai_token, model)

    def save_conversation_list(self, file_name, conversations: List[Conversation]) -> None:
        folder = 'conversation_lists'
        if not os.path.exists(folder):
            os.makedirs(folder)
        path = f"{folder}/{file_name}.json"
        if os.path.exists(path):
            print(f"Error: file {file_name} already exists")
            return
        with open(path, 'w') as f:
            f.writelines(json.dumps(conversations))

    def _make_request_get(self, path: str, params):
        query = "?"
        first = True
        for k in params.keys():
            if not first:
                query += "&"
            else:
                first = False
            query += f"{k}={params[k]}"
        url = "https://api.helpscout.net/v2/" + path + query
        print(f'GET: {url}')
        res =  requests.get(url, headers={
            "Authorization": f"Bearer {self.token}"
        })
        if res.status_code == 401:
            self.token = refresh_token()
            self._make_request_get(path, params)
        return res

    def _make_request_post(self, path: str, params):
        url = "https://api.helpscout.net/v2/" + path
        print(f'POST: {url}')
        res = requests.post(url, 
            headers={ "Authorization": f"Bearer {self.token}" }, 
            json=params
        )
        if res.status_code == 401:
            self.token = refresh_token()
            self._make_request_post(path, params)
        return res

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

    def list_conversations(self, page: int, open_conv: bool, use_cache: bool = True) -> List[Conversation]:
        convs = None
        if use_cache:	
            convs = self.load_conversation_list(page)
        if convs is None:
            print(f"Listing conversations page: {page}")
            res = self._make_request_get('conversations', {
                "page": page,
                "embed": "threads",
                "status": "open" if open_conv else "closed"
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
        print(f"Saving {len(convs)} conversations")
        print(f"Saving {len(completions)} completions")
        with open(path, 'w') as f:
            for comp in completions:
                f.write(json.dumps(comp) + '\n')
        print(f"Completions for {file_name} written to file")

    def send_note(self, conv_id: str, text: str):
        print(f'Sending Note for conv: {conv_id}')
        self._make_request_post(f'conversations/{conv_id}/notes', {
            "text": text
        })

    def process_user_message(self, conversation: Conversation):
        print(f'Processing user message for conversation {conversation.id}')
        message = conversation.threads[-1].body.lower()
        if '@scoutbot' not in message:
            return
        if 'good bot' in message:
            return self.process_good_bot(conversation, message)
        if 'summarize' in message:
            return self.summarize_conversation(conversation)
        
    def summarize_conversation(self, conversation: Conversation):
        conv_str = conversation.for_gpt()
        chat = GptChat('summarize.prompt')
        try:
            msg = chat.send(conv_str, 300).replace('\n', '<br>\n')
            self.send_note(conversation.id, f'<h2>Scout Bot 🤖</h2><p><b>I summarized the conversation for you:</b></p><p>{msg}</p>')
        except Exception as e:
            print(e)
            return
        print(f'{get_pretty_date()}: Summarized conversation {conversation.id}')
        chat.save_completions(f'summarize_{conversation.id}')

    def process_good_bot(self, conversation: Conversation, message: str):
        if 'good bot' not in message or message.source != 'user':
            return
        selected_message = -1
        try:
            selected_message = int(message[-1])
        except:
            return
        if selected_message == -1 or selected_message > 3 or selected_message < 1:
            return
        last_thread = conversation.threads[-2]
        last_message = last_thread.body
        message_text = last_message.split('BOT: message')[selected_message][1:]
        last_thread.body = message_text
        conversation.threads = conversation.threads[:-2]
        conversation.threads.append(last_thread)
        completion = conversation.get_completions()[-1]
        with open('completions/fine_tune_queue.jsonl', 'a') as f:
            f.write(json.dumps(completion))
        with open('log.txt', 'a') as f:
            f.write(f'{get_pretty_date()}: Feedback recieved for response {selected_message} on conversation {conversation.id}')

    def recieve_message(self, data: object):
        conversation = Conversation(data)
        self.recieve_conversation(conversation)

    def recieve_conversation(self, conversation: Conversation):
        print('Recieved Conversation')
        last_thread = conversation.threads[-1]
        if last_thread.source == 'user' and last_thread.type != 'lineitem':
            self.process_user_message(conversation)
            return
        return # Disable responses for now
        print('Responding to Conversation')
        prompt = conversation.for_gpt()
        completions = self.complete.complete(prompt, {
            "n": 3,
            "max_tokens": 150
        })
        print('Got completion')
        idx = 1
        note = ''
        stop_token = '\n\n######\n\n'
        for c in completions:
            if stop_token in c:
                c = c.split(stop_token)[0]
            c = c.replace('\n', '<br>\n')
            note += f"""<br><br>
<h1>BOT: message</h1>
{c}<br>
            """
            idx += 1
        self.send_note(conversation.id, note)
        with open('log.txt', 'a') as f:
            now = datetime.now()
            pretty_datetime = now.strftime("%B %d, %Y %H:%M:%S")
            f.write(f'{pretty_datetime}: Sent note on conversation {conversation.id}\n')

    def create_fine_tune(self, filename: str):
        os.environ('OPENAI_API_KEY=' + self.complete.api_key)
        path = f'completions/{filename}.jsonl'
        os.system(f"openai api fine_tunes.create -t {path} -m {self.complete.model} --n_epochs 1")
        now = datetime.now()
        with open('log.txt', 'a') as f:
            tokens = count_tokens_for_file(path)
            pretty_datetime = now.strftime("%B %d, %Y %H:%M:%S")
            f.write(f'{pretty_datetime}: Fine tune started, ran with {tokens} tokens')

        shutil.move(path, f'completions/{now.strftime("%Y_%m_%dT%H_%M_%S")}_fine_tune.jsonl')

def load_api():
    if not os.path.exists('config.json'):
        raise "Error: Config not found"
    config = json.loads(open_file('config.json'))
    hs_id = config["helpscout_id"]
    hs_secret = config["helpscout_secret"]
    openai_token = config["openai_key"]
    fine_tune_id = 'davinci'
    if 'fine_tune_id' in config:
        fine_tune_id = config['fine_tune_id']

    token = get_token(hs_id, hs_secret)

    api = HelpscoutAPI(token, openai_token, fine_tune_id)
    return api
