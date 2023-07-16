import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from hs_api import load_api

api = load_api()

def process_data(data_string):
    data = json.loads(data_string)
    with open('messages.jsonl', 'a') as f:
        f.write(json.dumps(data))
    api.recieve_message(data)
    return jsonify({ 'responded': True }), 200

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        process_data(post_data)

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Hello, world!\n')

def run_server(port):
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f'Starting server on port {port}...')
    httpd.serve_forever()

run_server(5500)
