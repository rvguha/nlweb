from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import answer
import asyncio
from urllib.parse import parse_qs
hostName = "localhost"
serverPort = 8080

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        queryStr = self.path.split("?")[1]
        params = parse_qs(queryStr)
        query = params['query'][0]
        site = params['site'][0] if 'site' in params else 'imdb'
        model = params['model'][0] if 'model' in params else 'gpt-4o-mini'
        embedding = params['embedding'][0] if 'embedding' in params else 'small'
        prev = params['prev'][0] if 'prev' in params else ''
        num = params['num'][0] if 'num' in params else 10

        results = asyncio.run(answer.get_ranked_answers(query, site, model, embedding, prev, num))
        # Convert results to JSON string before sending
        json_results = json.dumps(results)
     #   print(json_results)
        self.wfile.write(json_results.encode("utf-8"))
        print("wrote")
       # self.wfile.write(bytes("\n\n", "utf-8"))

if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")