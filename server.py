"""Serve the imported FocusMate prototype without exposing workspace files."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


INDEX = Path(__file__).with_name("index.html")


class PrototypeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.serve_page()

    def do_HEAD(self):
        self.serve_page(head_only=True)

    def serve_page(self, head_only=False):
        path = urlsplit(self.path).path
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if path not in ("/", "/index.html"):
            self.send_error(404)
            return
        page = INDEX.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(page)


if __name__ == "__main__":
    print("FocusMate running on port 5000", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 5000), PrototypeHandler).serve_forever()