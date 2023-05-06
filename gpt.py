import openai

class GptCompletion:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        openai.api_key = self.api_key
        self.total_tokens = 0

    def complete(self, prompt: str, config: dict = {}):
        defaultConfig = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": 150,
            "n": 1,
            "stop": None,
            "temperature": 0.8
        }

        defaultConfig.update(config)
        res = openai.Completion.create(**defaultConfig)
        messages = []
        for c in res.choices:
            messages.append(c.text.strip())
        self.total_tokens += res.usage.total_tokens
        return messages