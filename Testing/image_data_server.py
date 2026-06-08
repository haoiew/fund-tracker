import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

IMAGE_PATH = r"D:\Users\138721\Pictures\微信图片_20260605164756_452_131.jpg"
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        with open(IMAGE_PATH, "rb") as f:
            data_url = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")
        payload = json.dumps({"dataUrl": data_url, "length": len(data_url)}).encode("utf-8")
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
