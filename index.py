from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode())
            except:
                self.wfile.write(b"<h1>AURORA SUSU LIVE</h1><a href='/login.html'>Login</a>")
            return
        if "login" in path:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            try:
                with open("login.html", "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode())
            except:
                self.wfile.write(b"<h1>Login admin / admin123</h1>")
            return
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "AURORA Running", "path": path}).encode())

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True}).encode())
