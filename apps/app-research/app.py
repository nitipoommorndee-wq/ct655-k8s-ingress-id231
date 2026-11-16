"""app-research : GET /research shows the research summary,
GET /edit shows the edit form and POST /edit saves it back to the data file."""
import html
import os
import shutil
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

DATA_FILE = os.environ.get("DATA_FILE", "/data/research.txt")
DEFAULT_FILE = os.environ.get("DEFAULT_FILE", "/app/research.txt")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "/research")

STYLE = """
  body { margin: 0; background: #f1f5f9; color: #0f172a;
         font-family: "Sarabun", "Thonburi", system-ui, sans-serif; line-height: 1.8; }
  main { max-width: 820px; margin: 32px auto; background: #fff; padding: 32px 40px;
         border-radius: 12px; box-shadow: 0 2px 10px rgba(15, 23, 42, .08); }
  h1 { font-size: 24px; line-height: 1.4; margin: 0 0 6px; }
  .sub { color: #64748b; font-size: 14px; margin-bottom: 20px; }
  p { margin: 0 0 14px; text-indent: 2em; text-align: justify; }
  input, textarea { width: 100%; box-sizing: border-box; font: inherit; padding: 10px;
         border: 1px solid #cbd5e1; border-radius: 8px; }
  textarea { height: 420px; line-height: 1.7; }
  label { display: block; font-weight: 600; margin: 14px 0 6px; }
  button { margin-top: 16px; background: #2563eb; color: #fff; border: 0; font: inherit;
         padding: 10px 28px; border-radius: 8px; cursor: pointer; }
  .ok { background: #dcfce7; color: #166534; padding: 10px 14px; border-radius: 8px; margin-bottom: 16px; }
  footer { color: #94a3b8; font-size: 13px; margin-top: 20px; }
"""


def load():
    if not os.path.exists(DATA_FILE):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        shutil.copy(DEFAULT_FILE, DATA_FILE)
    with open(DATA_FILE, encoding="utf-8") as f:
        title, _, body = f.read().partition("\n")
    return title.strip(), body.strip()


def save(title, body):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(title.strip() + "\n" + body.replace("\r\n", "\n").strip() + "\n")
    os.replace(tmp, DATA_FILE)


def page(title, inner):
    return (f'<!doctype html><html lang="th"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{STYLE}</style></head>"
            f"<body><main>{inner}<footer>app-research &middot; pod {html.escape(socket.gethostname())}"
            f"</footer></main></body></html>")


def view_page():
    title, body = load()
    paras = "".join(f"<p>{html.escape(p.strip())}</p>" for p in body.split("\n") if p.strip())
    return page("Research", f'<h1>{html.escape(title)}</h1><div class="sub">Research summary</div>{paras}')


def edit_page(saved=False):
    title, body = load()
    note = (f'<div class="ok">Saved. View it at <a href="{html.escape(PUBLIC_URL)}">'
            f"{html.escape(PUBLIC_URL)}</a></div>") if saved else ""
    form = (f'<h1>Edit research summary</h1><div class="sub">app-research /edit</div>{note}'
            f'<form method="post"><label>Title</label>'
            f'<input name="title" value="{html.escape(title, quote=True)}">'
            f'<label>Summary</label><textarea name="body">{html.escape(body)}</textarea>'
            f"<button type=\"submit\">Save</button></form>")
    return page("Edit research", form)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path == "/healthz":
            return self.send(200, "ok", "text/plain")
        if path == "/research":
            return self.send(200, view_page(), "text/html")
        if path == "/edit":
            return self.send(200, edit_page(), "text/html")
        self.send(404, "not found", "text/plain")

    def do_POST(self):
        path = urlsplit(self.path).path.rstrip("/")
        if path != "/edit":
            return self.send(404, "not found", "text/plain")
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
        title, body = form.get("title", [""])[0], form.get("body", [""])[0]
        if not title.strip() or not body.strip():
            return self.send(400, "title and body are required", "text/plain")
        save(title, body)
        self.send(200, edit_page(saved=True), "text/html")

    def send(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    load()
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
