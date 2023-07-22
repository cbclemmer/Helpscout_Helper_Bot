import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from hs_api import load_api

api = load_api()

def process_data(data_string):
    print('Recieved Data')
    data = json.loads(data_string)
    with open('raw_recieve.txt', 'a') as f:
        f.write(data_string + '\n\n\n\n\n\n')
    with open('messages.jsonl', 'a') as f:
        f.write(json.dumps(data) + '\n')
    api.recieve_message(data)

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            process_data(post_data)
        except Exception as e:
            print(e)
        finally:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('success'.encode())

def run_server(port):
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f'Starting server on port {port}...')
    httpd.serve_forever()

run_server(5500)
