import os
import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        if 'code' in query_params:
            code = query_params['code'][0]
            print(f"Received code: {code}")
            with open('code.txt', 'w') as f:
                f.writelines(code)
            print("State file written")
        else:
            return

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Client Authorized")

def get_token(hs_id, hs_secret):
    auth_token = ''
    if not os.path.exists('token.json'):
        server_address = ('', 3000)
        httpd = HTTPServer(server_address, MyHTTPRequestHandler)
        print(f"Server listening on port {server_address[1]}")

        pid = os.fork()
        if pid == 0:
            httpd.handle_request()
            httpd.server_close()
            print('Closing server')
        else:
            os.system(f'firefox https://secure.helpscout.net/authentication/authorizeClientApplication?client_id={hs_id}&state={hs_secret}')
            os._exit(pid)
        code = open_file('code.txt')
        os.remove('code.txt')
        
        token = requests.post('https://api.helpscout.net/v2/oauth2/token', data={
            "code": code,
            "client_id": hs_id,
            "client_secret": hs_secret,
            "grant_type": "authorization_code"
        }).text
        
        with open('token.json', 'w') as f:
            f.writelines(token)
        auth_token = json.loads(token)['access_token']
    else:
        auth_token = json.loads(open_file('token.json'))['access_token']
    
    print("Authentication Successful")
    
    return auth_token