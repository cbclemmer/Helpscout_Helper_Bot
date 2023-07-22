import os
import json
import datetime
import time
from typing import List

import openai
import tiktoken
from util import save_file, open_file

class GptCompletion:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        openai.api_key = self.api_key
        self.total_tokens = 0
        self.encoding = tiktoken.encoding_for_model("davinci")

    def complete(self, prompt: str, config: dict = {}):
        messages = []
        prompt_tokens = self.encoding.encode(prompt)
        if len(prompt_tokens) > 2000:
            print(f'Too many tokens: {len(prompt_tokens)} tokens')
            return messages
        try:
            defaultConfig = {
                "model": self.model,
                "prompt": prompt,
                "max_tokens": 150,
                "n": 1,
                "stop": None,
                "temperature": 0.5
            }

            defaultConfig.update(config)
            res = openai.Completion.create(**defaultConfig)
            messages = []
            for c in res.choices:
                messages.append(c.text.strip())
            self.total_tokens += res.usage.total_tokens
        except Exception as e:
            print(e)
        return messages

class Prompt:
    title: str
    text: str
    url: str

    def __init__(self, title: str, text: str, url: str):
        self.title = title
        self.text = text
        self.url = url

class Summary(Prompt):
    def __init__(self, title: str, text: str, url: str):
        super().__init__(title, text, url)

class Message:
    role: str
    content: str

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class Conversation:
    messages: List[Message]

    def __init__(self, messages: List[Message]):
        self.messages = messages

    def to_object(self):
        messages = []
        for m in self.messages:
            messages.append({
                "role": m.role,
                "content": m.content
            })
        return messages
    
class GptChat:
    def __init__(self, system_prompt_file: str) -> None:
        self.system_prompt = open_file(system_prompt_file)
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.system_prompt_tokens = len(self.encoding.encode(self.system_prompt))
        self.messages = []
        self.conversations = []
        self.reset_chat()
        self.total_tokens = 0

    def save_completions(self, file_name):
        if len(self.conversations) == 0:
            return
        text = ''
        for completion in self.conversations:
            text += json.dumps(completion.to_object()) + '\n'
        today = datetime.date.today().strftime("%Y-%m-%d-%H-%M")

        if not os.path.exists('completions'):
            os.mkdir('completions')
        save_file(f'completions/{file_name}_{today}.json', text)

    def add_message(self, message: str, role: str):
        self.messages.append(Message(role, message))

    def reset_chat(self):
        if len(self.messages) > 1:
            self.conversations.append(Conversation(self.messages))
        self.messages = [ ]
        self.add_message(self.system_prompt, "system")

    def get_message_tokens(self) -> int:
        message_tokens = 0
        for m in self.messages:
            message_tokens += len(self.encoding.encode(m.content))
        return message_tokens

    def send(self, message: str, max_tokens=100) -> str:
        message_tokens = self.get_message_tokens()
        message_tokens += len(self.encoding.encode(message))
        print(f"Sending chat with {message_tokens} tokens")
        
        if message_tokens >= 4096 - 200:
            raise "Chat Error too many tokens"
        
        self.add_message(message, "user")
        
        defaultConfig = {
            "model": 'gpt-3.5-turbo',
            "max_tokens": max_tokens,
            "messages": Conversation(self.messages).to_object(),
            "temperature": 0.5
        }

        try:
            res = openai.ChatCompletion.create(**defaultConfig)
        except:
            print('Error when sending chat, retrying in one minute')
            time.sleep(60)
            self.messages = self.messages[:-1]
            self.send(message, max_tokens)
        msg = res.choices[0].message.content.strip()
        print(f"GPT API responded with {res.usage.completion_tokens} tokens")
        self.add_message(msg, "assistant")
        self.total_tokens += res.usage.total_tokens
        return msg