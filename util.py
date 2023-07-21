import json
import hashlib
import datetime

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()
    
def save_file(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(data)

def to_sha(s: str) -> str:
    return hashlib.sha256(bytes(json.dumps(s), 'utf-8')).hexdigest()

def get_pretty_date():
    return datetime.now().strftime("%B %d, %Y %H:%M:%S")