import asyncio
import json
import urllib.parse
import os
import sys
import time
import retriever
from StreamingWrapper import HandleRequest


async def handle_client(reader, writer, fulfill_request):
    """Handle a client connection by parsing the HTTP request and passing it to fulfill_request."""
    request_id = f"client_{int(time.time()*1000)}"
    connection_alive = True
    
    try:
        # Read the request line
        request_line = await reader.readline()
        if not request_line:
            print(f"[{request_id}] Empty request line, closing connection")
            connection_alive = False
            return
            
        request_line = request_line.decode('utf-8').rstrip('\r\n')
        words = request_line.split()
        if len(words) < 2:
            # Bad request
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await writer.drain()
            connection_alive = False
            return
            
        method, path = words[0], words[1]
        print(f"[{request_id}] Received {method} request for {path}")
        
        # Parse headers
        headers = {}
        while True:
            try:
                header_line = await reader.readline()
                if not header_line or header_line == b'\r\n':
                    break
                    
                hdr = header_line.decode('utf-8').rstrip('\r\n')
                if ":" not in hdr:
                    continue
                name, value = hdr.split(":", 1)
                headers[name.strip().lower()] = value.strip()
            except (ConnectionResetError, BrokenPipeError) as e:
                print(f"[{request_id}] Connection lost while reading headers: {str(e)}")
                connection_alive = False
                return
        
        # Parse query parameters
        if '?' in path:
            path, query_string = path.split('?', 1)
            query_params = {}
            try:
                # Parse query parameters into a dictionary of lists
                for key, values in urllib.parse.parse_qs(query_string).items():
                    query_params[key] = values
            except Exception as e:
                print(f"[{request_id}] Error parsing query parameters: {str(e)}")
                query_params = {}
        else:
            query_params = {}
        
        # Read request body if Content-Length is provided
        body = None
        if 'content-length' in headers:
            try:
                content_length = int(headers['content-length'])
                body = await reader.read(content_length)
            except (ValueError, ConnectionResetError, BrokenPipeError) as e:
                print(f"[{request_id}] Error reading request body: {str(e)}")
                connection_alive = False
                return
        
        # Create a streaming response handler
        async def send_response(status_code, response_headers, end_response=False):
            """Send HTTP status and headers to the client."""
            nonlocal connection_alive
            
            if not connection_alive:
                return
                
            try:
                status_line = f"HTTP/1.1 {status_code}\r\n"
                writer.write(status_line.encode('utf-8'))
                
                # Send headers
                for header_name, header_value in response_headers.items():
                    header_line = f"{header_name}: {header_value}\r\n"
                    writer.write(header_line.encode('utf-8'))
                
                # End headers
                writer.write(b"\r\n")
                await writer.drain()
                
                # Signal that we've sent the headers
                send_response.headers_sent = True
                send_response.ended = end_response
            except (ConnectionResetError, BrokenPipeError) as e:
                print(f"[{request_id}] Connection lost while sending response headers: {str(e)}")
                connection_alive = False
            except Exception as e:
                print(f"[{request_id}] Error sending response headers: {str(e)}")
                connection_alive = False
        
        # Create a streaming content sender
        async def send_chunk(chunk, end_response=False):
            """Send a chunk of data to the client."""
            nonlocal connection_alive
            
            if not connection_alive:
                return
                
            if not hasattr(send_response, 'headers_sent') or not send_response.headers_sent:
                print(f"[{request_id}] Headers must be sent before content")
                return
                
            if hasattr(send_response, 'ended') and send_response.ended:
                print(f"[{request_id}] Response has already been ended")
                return
                
            try:
                if chunk:
                    if isinstance(chunk, str):
                        writer.write(chunk.encode('utf-8'))
                    else:
                        writer.write(chunk)
                    await writer.drain()
                
                send_response.ended = end_response
            except (ConnectionResetError, BrokenPipeError) as e:
                print(f"[{request_id}] Connection lost while sending chunk: {str(e)}")
                connection_alive = False
            except Exception as e:
                print(f"[{request_id}] Error sending chunk: {str(e)}")
                connection_alive = False
        
        # Call the user-provided fulfill_request function with streaming capabilities
        if connection_alive:
            try:
                await fulfill_request(
                    method=method,
                    path=urllib.parse.unquote(path),
                    headers=headers,
                    query_params=query_params,
                    body=body,
                    send_response=send_response,
                    send_chunk=send_chunk
                )
            except Exception as e:
                print(f"[{request_id}] Error in fulfill_request: {str(e)}")
                if connection_alive and not (hasattr(send_response, 'headers_sent') and send_response.headers_sent):
                    try:
                        # Send a 500 error if headers haven't been sent yet
                        error_headers = {
                            'Content-Type': 'text/plain',
                            'Connection': 'close'
                        }
                        await send_response(500, error_headers)
                        await send_chunk(f"Internal server error: {str(e)}".encode('utf-8'), end_response=True)
                    except:
                        pass
        
    except Exception as e:
        print(f"[{request_id}] Critical error handling request: {str(e)}")
    finally:
        # Close the connection in a controlled manner
        try:
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            print(f"[{request_id}] Connection closed")
        except Exception as e:
            print(f"[{request_id}] Error closing connection: {str(e)}")
            
async def start_server(host='0.0.0.0', port=8000, fulfill_request=None, use_https=False, 
                 ssl_cert_file=None, ssl_key_file=None):
    """
    Start the HTTP/HTTPS server with the provided request handler.
    """
    import ssl
    
    if fulfill_request is None:
        raise ValueError("fulfill_request function must be provided")
    
    ssl_context = None
    if use_https:
        if not ssl_cert_file or not ssl_key_file:
            raise ValueError("SSL certificate and key files must be provided for HTTPS")
        
        # Create SSL context - using configuration from working code
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
        ssl_context.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256')
        ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        
        try:
            ssl_context.load_cert_chain(ssl_cert_file, ssl_key_file)
        except (ssl.SSLError, FileNotFoundError) as e:
            raise ValueError(f"Failed to load SSL certificate: {e}")
    
    # Start server with or without SSL
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, fulfill_request), 
        host, 
        port,
        ssl=ssl_context
    )
    
    addr = server.sockets[0].getsockname()
    protocol = "HTTPS" if use_https else "HTTP"
    url_protocol = "https" if use_https else "http"
    print(f'Serving {protocol} on {addr[0]} port {addr[1]} ({url_protocol}://{addr[0]}:{addr[1]}/) ...')
    retriever.initialize()
    async with server:
        await server.serve_forever()


class SendChunkWrapper:
    def __init__(self, send_chunk):
        self.send_chunk = send_chunk
        self.closed = False

    async def write(self, chunk, end_response=False):
        if self.closed:
            return
            
        try:
            if isinstance(chunk, dict):
                message = f"data: {json.dumps(chunk)}\n\n"
                await self.send_chunk(message, end_response)
            else:
                await self.send_chunk(chunk, end_response)
                
            if end_response:
                self.closed = True
        except (ConnectionResetError, BrokenPipeError) as e:
            self.closed = True
            # Don't re-raise, just note that the connection is closed
        except Exception as e:
            print(f"Error in SendChunkWrapper.write: {str(e)}")
            self.closed = True

    async def write_stream(self, message, end_response=False):
        if self.closed:
            return
            
        try:
            data_message = f"data: {json.dumps(message)}\n\n"
            await self.send_chunk(data_message, end_response)
            if end_response:
                self.closed = True
        except (ConnectionResetError, BrokenPipeError) as e:
            self.closed = True
        except Exception as e:
            print(f"Error in write_stream: {str(e)}")
            self.closed = True


async def fulfill_request(method, path, headers, query_params, body, send_response, send_chunk):
    '''
    Process an HTTP request and stream the response back.
    
    Args:
        method (str): HTTP method (GET, POST, etc.)
        path (str): URL path
        headers (dict): HTTP headers
        query_params (dict): URL query parameters
        body (bytes or None): Request body
        send_response (callable): Function to send response headers
        send_chunk (callable): Function to send response body chunks
    '''
    if (path.find("html") != -1) or (path.find("png") != -1):
        await send_static_file(path, send_response, send_chunk)
        return
    if (path.find("ask") != -1):
        send_chunk_wrapper = SendChunkWrapper(send_chunk)
        # send_response(200)
        hr = HandleRequest(method, path, headers, query_params, body, send_response, send_chunk_wrapper)
        await hr.do_GET()

async def send_static_file(path, send_response, send_chunk):
    # Map file extensions to MIME types
    mime_types = {
        '.html': 'text/html',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.css': 'text/css',
        '.js': 'application/javascript'
    }

    # Get file extension and corresponding MIME type
    file_ext = os.path.splitext(path)[1].lower()
    content_type = mime_types.get(file_ext, 'application/octet-stream')

    try:
        # Remove leading slash and sanitize path
        safe_path = os.path.normpath(path.lstrip('/'))
        
        # Try to open and read the file
        with open(safe_path, 'rb') as f:
            content = f.read()
            
        # Send successful response with proper headers
        await send_response(200, {'Content-Type': content_type, 'Content-Length': str(len(content))})
        await send_chunk(content, end_response=True)
        
    except FileNotFoundError:
        # Send 404 if file not found
        await send_response(404, {'Content-Type': 'text/plain'})
        error_msg = f"File not found: {path}".encode('utf-8')
        await send_chunk(error_msg, end_response=True)
        
    except Exception as e:
        # Send 500 for other errors
        await send_response(500, {'Content-Type': 'text/plain'})
        error_msg = f"Internal server error: {str(e)}".encode('utf-8')
        await send_chunk(error_msg, end_response=True)

if __name__ == "__main__":
    if (len(sys.argv) > 1 and sys.argv[1] == "https"):
        asyncio.run(start_server(
            fulfill_request=fulfill_request,
            use_https=True,
            ssl_cert_file='fullchain.pem',  # Changed to match working code
            ssl_key_file='privkey.pem',     # Changed to match working code
            port=443
        ))
    else:
        asyncio.run(start_server(port=8000, fulfill_request=fulfill_request))