"""app-api : GET /api/<text> shows <text> in big letters at the centre of the page."""
import html
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

PAGE = """<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>app-api</title>
<style>
  html, body {{ height: 100%; margin: 0; }}
  body {{ display: flex; align-items: center; justify-content: center;
         background: #0f172a; color: #f8fafc; font-family: system-ui, sans-serif; }}
  h1 {{ font-size: clamp(48px, 14vw, 220px); margin: 0; padding: 0 4vw;
       text-align: center; word-break: break-word; line-height: 1.15; }}
  footer {{ position: fixed; bottom: 12px; left: 0; right: 0; text-align: center;
           font-size: 14px; color: #94a3b8; }}
</style></head>
<body><h1>{text}</h1><footer>app-api &middot; pod {pod}</footer></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/healthz":
            return self.send(200, "ok", "text/plain")
        if not path.startswith("/api"):
            return self.send(404, "not found", "text/plain")
        text = unquote(path[len("/api"):].strip("/")) or "/api/<text>"
        body = PAGE.format(text=html.escape(text), pod=html.escape(socket.gethostname()))
        self.send(200, body, "text/html")

    def send(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
