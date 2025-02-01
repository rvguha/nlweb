from http.server import HTTPServer, BaseHTTPRequestHandler, SimpleHTTPRequestHandler
import ssl
import os
from socketserver import ThreadingMixIn
import json
import time
import answer
import se_answer
import asyncio
import threading
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

class StreamingHandler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    
    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = os.getcwd() 
        super().__init__(*args, directory=directory, **kwargs)


    def do_GET(self):
        try:
            # Parse query parameters
            parsed_url = urlparse(self.path)
            query_str_parts = self.path.split("?")
            if parsed_url.path.find("html") != -1:
                print(f"Requested path: {self.path}")
                print(f"Looking in directory: {os.getcwd()}")
                return super().do_GET()
            if len(query_str_parts) < 2:
                self._handle_cors_preflight()
                return
             
            queryStr = query_str_parts[1]
            params = parse_qs(queryStr)
            
            # Extract parameters with defaults
            query = params['query'][0]
            site = params.get('site', ['imdb'])[0]
            model = params.get('model', ['gpt-4o-mini'])[0]
            embedding = params.get('embedding', ['small'])[0]
            prev = params.get('prev', [''])[0]
            item_to_remember = params.get('item_to_remember', [''])[0]
            num = params.get('num', ['10'])[0]

            self._start_sse_response()
            
            # Create an event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                if site == "seriouseats":
                    loop.run_until_complete(
                        se_answer.get_ranked_answers(query, site, model, embedding, prev, self, item_to_remember)
                    )
                else:
                    loop.run_until_complete(
                        answer.get_ranked_answers(query, site, model, embedding, prev, self, item_to_remember)
                    )
            finally:
                loop.close()

            self.wfile.write(("data: " + json.dumps({"message_type": "complete"}) + "\n\n").encode("utf-8"))
            self.wfile.flush()
            
        except Exception as e:
            print(f"Error handling request: {str(e)}")
            self.send_error(500, f"Internal server error: {str(e)}")

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def _handle_cors_preflight(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _start_sse_response(self):
        """Setup SSE response headers"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.flush()
        self.request.settimeout(None)

def run_server(port=8000, max_workers=10):
    server_address = ('0.0.0.0', port)
    try:
        httpd = ThreadedHTTPServer(server_address, StreamingHandler)
       # context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
      #  context.load_cert_chain(certfile="server.cert", keyfile="server.key")
    
        # Wrap the socket with SSL
       # httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
       # httpd.socket = ssl.wrap_socket(httpd.socket, server_side=True, certfile="server.cert", keyfile="server.key")
        print(f"Threaded server running on http://localhost:{port}")
        print(f"Server is using {max_workers} worker threads")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.socket.close()

if __name__ == '__main__':
    run_server()