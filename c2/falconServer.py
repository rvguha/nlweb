import falcon.asgi
import asyncio
import random
import json
import uvicorn
from datetime import datetime

active_clients = 0

class NLWebResource:

    def __init__(self):
        print("StreamResource initialized")
        
    async def on_get(self, req, resp):
        """Handle GET requests for streaming data"""
        global active_clients
        active_clients += 1
        
        # Set streaming response headers
        resp.content_type = 'text/event-stream'
        resp.set_header('Cache-Control', 'no-cache')
        resp.set_header('Connection', 'keep-alive')
        
        # Create an asynchronous generator for streaming

        def write_back(data):
            yield f"data: {json.dumps(data)}\n\n".encode('utf-8')

        async def event_stream_generator():
            count = 0
            try:
                while True:
                    count += 1
                    # Create a sample data point
                    timestamp = datetime.now().timestamp()
                    data = {
                        'id': count,
                        'timestamp': timestamp,
                        'value': random.randint(1, 100),
                        'message': f'Event #{count}'
                    }
                    
                    # Format as Server-Sent Events (SSE)
                    yield f"data: {json.dumps(data)}\n\n".encode('utf-8')
                    
                    # Pause between events (non-blocking)
                    await asyncio.sleep(1)
            finally:
                # Decrement active client count when connection closes
                global active_clients
                active_clients -= 1
        
        # Use the generator to stream the response
        resp.stream = event_stream_generator()


class HeartbeatResource:
    async def on_get(self, req, resp):
        """Simple endpoint to check if the server is alive"""
        resp.media = {'status': 'alive', 'timestamp': datetime.now().timestamp()}
        resp.status = falcon.HTTP_200


class StatsResource:
    async def on_get(self, req, resp):
        """Return stats about the server"""
        resp.media = {'active_clients': active_clients}
        resp.status = falcon.HTTP_200


class ClientPageResource:
    async def on_get(self, req, resp):
        try:
            # Read the HTML file from the 'html' directory
            with open('html/index.html', 'r') as f:
                html_content = f.read()
            
            resp.content_type = 'text/html'
            resp.text = html_content
            resp.status = falcon.HTTP_200
        except FileNotFoundError:
            resp.text = "Error: HTML file not found in the 'html' directory"
            resp.status = falcon.HTTP_404
        except Exception as e:
            resp.text = f"Error loading HTML file: {str(e)}"
            resp.status = falcon.HTTP_500

     
# Create the Falcon ASGI application
app = falcon.asgi.App()

# Add routes
app.add_route('/ask', NLWebResource())
app.add_route('/heartbeat', HeartbeatResource())
app.add_route('/stats', StatsResource())
app.add_route('/html', ClientPageResource())

if __name__ == '__main__':
    # Start the ASGI server with Uvicorn
    print('Starting Falcon ASGI streaming server on http://localhost:8000')
    uvicorn.run(app, host='0.0.0.0', port=8000)