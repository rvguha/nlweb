from WebServerHandler import ThreadedHTTPServer, StreamingHandler
import retriever
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

def run_server(port=8000, max_workers=10):
    server_address = ('0.0.0.0', port)
    try:
        retriever.search_db("test", "all")
        print("initialized retriever")
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