from hs_api import count_tokens_for_file, load_api
    
api = load_api()

conversations = []
current_page = 300
while current_page >= 290:
    print(f"page {current_page}")
    convs = api.list_conversations(current_page)
    for c in convs:
        conversations.append(c)
    current_page -= 1
api.save_completions('first', conversations)

tokens = count_tokens_for_file('completions/first.jsonl')
print(f"File has {tokens // 1000}K tokens")

api.create_fine_tune('first')