from WebServerHandler import ThreadedHTTPServer, StreamingHandler
import ssl
import retriever


def run_server(port=443, max_workers=10):
    server_address = ('0.0.0.0', port)
    try:
        retriever.search_db("test", "imdb")
        httpd = ThreadedHTTPServer(server_address, StreamingHandler)
        
        # More explicit SSL context setup
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2  # Enforce minimum TLS version
        context.maximum_version = ssl.TLSVersion.TLSv1_3  # Allow up to TLS 1.3
        context.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256')  # Specify secure ciphers
        context.load_cert_chain(certfile="fullchain.pem", keyfile="privkey.pem")
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Disable older TLS versions
        
        # Wrap the socket with SSL
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        print(f"Threaded server running on https://localhost:{port}")
        print(f"Server is using {max_workers} worker threads")
        httpd.serve_forever()
    except Exception as e:
        print(f"Failed to start server: {e}")
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.socket.close()


if __name__ == '__main__':
    run_server()
