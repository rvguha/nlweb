from http.server import HTTPServer, BaseHTTPRequestHandler, SimpleHTTPRequestHandler
import ssl
import os
from socketserver import ThreadingMixIn
import json
import time
from baseHandler import BaseNLWebHandler
import asyncio
import threading
from urllib.parse import parse_qs, urlparse
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import traceback
from concurrent.futures import ThreadPoolExecutor
import utils
from recipe import RecipeHandler
from latam import LatamHandler
from imdb2 import Imdb2Handler
from zillow import ZillowHandler        
from backcountry_product import BCProductHandler

# Configure logging
def setup_logging():
    """Configure the logging system with both file and console handlers"""
    log_formatter = logging.Formatter(
        '%(asctime)s [%(threadName)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
    )
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/webserver.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress HTTP request logging
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('http.client').setLevel(logging.WARNING)
    
    return root_logger

logger = setup_logging()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("ThreadedHTTPServer initialized")

class StreamingHandler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    
    def __init__(self, *args, directory=None, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        if directory is None:
            directory = os.getcwd()
            self.logger.debug(f"No directory specified, using current working directory: {directory}")
        super().__init__(*args, directory=directory, **kwargs)
        self.logger.info(f"StreamingHandler initialized with directory: {directory}")

    def siteToClass(self, site):
        self.logger.debug(f"Converting site '{site}' to handler class")
        item_type = utils.siteToItemType(site)
        if site == "imdb2" or site == "imdb":
            self.logger.debug("Selected ImdbHandler for imdb")
            return Imdb2Handler
        elif site == "bc_product":
            self.logger.debug("Selected BCProductHandler for backcountry")
            return BCProductHandler
        elif site == "zillow":
            self.logger.debug("Selected ZillowHandler for zillow")
            return ZillowHandler
        elif site == "latam_recipes":
            self.logger.debug("Selected LatamHandler for latam_recipes")
            return LatamHandler
        elif item_type == "Recipe":
            self.logger.debug("Selected RecipeHandler for Recipe item type")
            return RecipeHandler
        else:
            self.logger.debug("Selected BaseNLWebHandler as default")
            return BaseNLWebHandler

    def do_GET(self):
        request_id = f"req_{int(time.time()*1000)}"
        self.logger.info(f"[{request_id}] Received GET request for path: {self.path}")
        
        try:
            # Parse query parameters
            parsed_url = urlparse(self.path)
            query_str_parts = self.path.split("?")
            
            if (parsed_url.path.find("html") != -1) or (parsed_url.path.find("png") != -1):
                self.logger.debug(f"[{request_id}] Handling static file request for: {self.path}")
                self.logger.debug(f"[{request_id}] Current working directory: {os.getcwd()}")
                return super().do_GET()
                
            if len(query_str_parts) < 2:
                self.logger.debug(f"[{request_id}] No query parameters found, handling CORS preflight")
                self._handle_cors_preflight()
                return
             
            queryStr = query_str_parts[1]
            params = parse_qs(queryStr)
            
            # Log all received parameters
            self.logger.info(f"[{request_id}] Received parameters: {params}")
            
            # Extract parameters with defaults
            query = params['query'][0]
            site = params.get('site', ['imdb'])[0]
            model = params.get('model', ['gpt-4o-mini'])[0]
            prev = params.get('prev', [''])[0]
            num = params.get('num', ['10'])[0]
            query_id = params.get('query_id', [''])[0]
            context_url = params.get('context_url', [''])[0]
            self.logger.debug(f"[{request_id}] Starting SSE response")
            self._start_sse_response()
            
            # Create an event loop for this thread
            self.logger.debug(f"[{request_id}] Creating new event loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                handlerClass = self.siteToClass(site)
                self.logger.info(f"[{request_id}] Processing query with handler: {handlerClass.__name__}")
                loop.run_until_complete(
                    self.handle_query(site, query, prev, model, query_id, context_url)
                )
            finally:
                self.logger.debug(f"[{request_id}] Closing event loop")
                loop.close()

        except Exception as e:
            self.logger.error(f"[{request_id}] Error handling request: {str(e)}")
            self.logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
            try:
                self.logger.debug(f"[{request_id}] Sending error response")
                try:
                    self.send_response(500)
                    self.send_header('Content-Type', 'text/plain')
                    self.send_header('Connection', 'close')
                    self._send_cors_headers()
                    self.end_headers()
                    error_msg = f"Internal server error: {str(e)}".encode('utf-8')
                    self.wfile.write(error_msg)
                    self.wfile.flush()
                except (ssl.SSLError, BrokenPipeError, ConnectionResetError) as ssl_err:
                    self.logger.error(f"[{request_id}] Failed to send error response due to SSL/connection error: {ssl_err}")
                    try:
                        self.connection.close()
                    except:
                        pass
            except Exception as final_err:
                self.logger.critical(f"[{request_id}] Critical error during error handling: {final_err}")
                try:
                    self.connection.close()
                except:
                    pass
                return
    
    async def handle_query(self, site, query, prev, model, query_id, context_url):
        request_id = f"query_{int(time.time()*1000)}"
        self.logger.info(f"[{request_id}] Starting query handling for site: {site}, query_id: {query_id}")
        
        try:
            handlerClass = self.siteToClass(site)
            self.logger.debug(f"[{request_id}] Created handler instance: {handlerClass.__name__}")
            
            handler = handlerClass(site, query, prev, model, http_handler=self, query_id=query_id, context_url=context_url)
            self.logger.debug(f"[{request_id}] Getting ranked answers")
            
            await handler.getRankedAnswers()
            self.logger.debug(f"[{request_id}] Completed getting ranked answers")
            
            await self.write_stream({"message_type": "complete"})
            self.logger.info(f"[{request_id}] Query handling completed successfully")
        except Exception as e:
            self.logger.error(f"[{request_id}] Error in handle_query: {str(e)}")
            self.logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
            raise
    
    async     def write_stream(self, message):
        """
        Asynchronously write a message to the SSE stream.
        
        Args:
            message (str): Message to write to the stream
        """
        try:
            data = f"data: {json.dumps(message)}\n\n"
            self.wfile.write(data.encode('utf-8'))
            self.wfile.flush()
            await asyncio.sleep(0)
        except (ssl.SSLError, BrokenPipeError, ConnectionResetError) as e:
            self.logger.error(f"Connection error while writing to stream: {str(e)}")
            try:
                self.connection.close()
            except:
                pass
            raise
        except Exception as e:
            self.logger.error(f"Error writing to stream: {str(e)}")
            raise

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def _handle_cors_preflight(self):
        self.logger.debug("Handling CORS preflight request")
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
        self.request.settimeout(10)