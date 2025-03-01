import os
import json
import time
import asyncio
from urllib.parse import parse_qs, urlparse
from datetime import datetime
import traceback
from utils import siteToClass
import ssl



class HandleRequest():
    protocol_version = 'HTTP/1.1'
    
    def __init__(self, method, path, headers, query_params, body, send_response, send_chunk_wrapper):
        self.method = method
        self.path = path
        self.headers = headers
        self.query_params = query_params
        self.body = body
        self.send_response = send_response
        self.send_chunk_wrapper = send_chunk_wrapper
        self.connection = None  # Added to maintain compatibility with error handlers
        self.connection_alive = True  # Flag to track connection state

    async def do_GET(self):
        request_id = f"req_{int(time.time()*1000)}"
        print(f"[{request_id}] Received GET request for path: {self.path}")
        try:
            # Parse query parameters                 
            # Extract parameters with defaults
            query = self.query_params.get('query', [''])
            site = self.query_params.get('site', ['imdb'])
            model = self.query_params.get('model', ['gpt-4o-mini'])
            prev = self.query_params.get('prev', [''])
            num = self.query_params.get('num', ['10'])
            query_id = self.query_params.get('query_id', [''])
            context_url = self.query_params.get('context_url', [''])
            
            try:
                await self._start_sse_response()
                
                if not self.connection_alive:
                    print(f"[{request_id}] Connection lost before starting query handling")
                    return
                    
                handlerClass = siteToClass(site)
                await self.handle_query(site[0] if isinstance(site, list) else site,
                                       query[0] if isinstance(query, list) else query,
                                       prev[0] if isinstance(prev, list) else prev,
                                       model[0] if isinstance(model, list) else model,
                                       query_id[0] if isinstance(query_id, list) else query_id,
                                       context_url[0] if isinstance(context_url, list) else context_url)
            except (ssl.SSLError, BrokenPipeError, ConnectionResetError) as conn_err:
                print(f"[{request_id}] Connection error during request handling: {str(conn_err)}")
                self.connection_alive = False
                # Connection errors are expected and don't need to generate an error response
                return
            except Exception as inner_e:
                if self.connection_alive:
                    print(f"[{request_id}] Error during request handling: {str(inner_e)}")
                    error_msg = f"Error processing request: {str(inner_e)}"
                    await self.send_error_response(500, error_msg)
                else:
                    print(f"[{request_id}] Error after connection was already lost: {str(inner_e)}")
                return

        except Exception as e:
            print(f"[{request_id}] Critical error in do_GET: {str(e)}")
            print(f"[{request_id}] Traceback: {traceback.format_exc()}")
            try:
                if self.connection_alive:
                    await self.send_error_response(500, f"Internal server error: {str(e)}")
            except Exception as final_err:
                print(f"[{request_id}] Failed to send error response: {str(final_err)}")
    
    async def send_error_response(self, status_code, message):
        """Send error response to client if connection is still alive"""
        try:
            headers = {
                'Content-Type': 'text/plain',
                'Connection': 'close'
            }
            headers.update(self._get_cors_headers())
            
            await self.send_response(status_code, headers)
            await self.send_chunk_wrapper.write({"error": message}, end_response=True)
        except (ssl.SSLError, BrokenPipeError, ConnectionResetError) as ssl_err:
            self.connection_alive = False
            print(f"Connection lost while sending error response: {str(ssl_err)}")
        except Exception as e:
            print(f"Critical error during error handling: {str(e)}")
    
    async def handle_query(self, site, query, prev, model, query_id, context_url):
        request_id = f"query_{int(time.time()*1000)}"
        print(f"[{request_id}] Starting query handling for site: {site}, query_id: {query_id}")
        
        try:
            handlerClass = siteToClass(site)
            print(f"[{request_id}] Created handler instance: {handlerClass.__name__}")
            
            handler = handlerClass(site, query, prev, model, http_handler=self, query_id=query_id, context_url=context_url)
            print(f"[{request_id}] Getting ranked answers")
            
            await handler.getRankedAnswers()
            
            if self.connection_alive:
                print(f"[{request_id}] Completed getting ranked answers")
                await self.write_stream({"message_type": "complete"})
                print(f"[{request_id}] Query handling completed successfully")
            else:
                print(f"[{request_id}] Connection already closed, skipping completion message")
        except (ssl.SSLError, BrokenPipeError, ConnectionResetError) as conn_err:
            print(f"[{request_id}] Connection lost during query handling: {str(conn_err)}")
            self.connection_alive = False
            # This is expected and we should just exit gracefully
        except Exception as e:
            print(f"[{request_id}] Error in handle_query: {str(e)}")
            print(f"[{request_id}] Traceback: {traceback.format_exc()}")
            if self.connection_alive:
                try:
                    await self.write_stream({"message_type": "error", "error": str(e)})
                except:
                    print(f"[{request_id}] Failed to send error message")
                    self.connection_alive = False
    
    async def write_stream(self, message):
        """
        Asynchronously write a message to the SSE stream.
        
        Args:
            message (str): Message to write to the stream
        """
        if not self.connection_alive:
            return
            
        try:
            await self.send_chunk_wrapper.write(message)
            await asyncio.sleep(0)  # Yield control to allow other tasks to run
        except (ssl.SSLError, BrokenPipeError, ConnectionResetError) as e:
            self.connection_alive = False
            print(f"Connection lost while writing to stream: {str(e)}")
            # Don't re-raise - consumer should check connection_alive flag
        except Exception as e:
            print(f"Error writing to stream: {str(e)}")
            self.connection_alive = False
            # Don't re-raise - consumer should check connection_alive flag

    def _get_cors_headers(self):
        """Return CORS headers as a dictionary"""
        return {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    async def _handle_cors_preflight(self):
        print("Handling CORS preflight request")
        headers = self._get_cors_headers()
        await self.send_response(200, headers)

    async def _start_sse_response(self):
        """Setup SSE response headers"""
        try:
            headers = {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
            headers.update(self._get_cors_headers())
            await self.send_response(200, headers)
        except (ssl.SSLError, BrokenPipeError, ConnectionResetError) as e:
            self.connection_alive = False
            print(f"Connection lost before sending headers: {str(e)}")
            raise  # Re-raise to caller