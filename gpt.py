import openai

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