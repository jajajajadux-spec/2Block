"""Loopback-only development server. Replace the HTTP layer before public hosting."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from packages.common.protocol import SERVER
from .world import GAMES, Store

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "web"
STATIC = {"/": (WEB / "index.html", "text/html; charset=utf-8"),
          "/style.css": (WEB / "style.css", "text/css; charset=utf-8"),
          "/app.js": (WEB / "app.js", "text/javascript; charset=utf-8"),
          "/downloads/2Block-Setup.exe": (ROOT / "dist" / "2Block-Setup.exe", "application/octet-stream")}
STATIC["/play"] = (WEB / "game" / "index.html", "text/html; charset=utf-8")
for name in ("client.js", "renderer.js", "math.js", "game.css"):
    STATIC["/game/" + name] = (WEB / "game" / name,
                              "text/css; charset=utf-8" if name.endswith(".css") else "text/javascript; charset=utf-8")


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address=("127.0.0.1", 8765)):
        super().__init__(address, Handler)
        self.store = Store()


class Handler(BaseHTTPRequestHandler):
    server_version = "2Block/dev"

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, fmt, *args):
        # Do not log join URIs, session tokens or request bodies.
        pass

    def reply(self, status, payload, content_type="application/json"):
        body = json.dumps(payload).encode() if content_type == "application/json" else payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; "
                         "style-src 'self'; connect-src 'self'; object-src 'none'; "
                         "base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self, post=False):
        try:
            # Host validation also prevents DNS rebinding against the local runtime.
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                self.reply(403, {"error": "Open the portal using its 127.0.0.1 address"})
                return
            origin = self.headers.get("Origin")
            expected = f"http://127.0.0.1:{self.server.server_port}"
            if ((origin is not None and origin != expected)
                    or self.headers.get("Sec-Fetch-Site") == "cross-site"):
                self.reply(403, {"error": "Cross-origin requests are not accepted"})
                return
            path = urlsplit(self.path).path
            if post:
                if self.headers.get_content_type() != "application/json":
                    self.reply(415, {"error": "Send application/json"})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192 or self.headers.get("Transfer-Encoding"):
                    self.reply(413, {"error": "Invalid request size"})
                    return
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
                token = self.headers.get("Authorization", "").removeprefix("Bearer ")
                with self.server.store.lock:
                    store = self.server.store
                    if path == "/api/launches":
                        result = store.create_launch(data)
                    elif path == "/api/join":
                        result = store.join(data)
                    elif path == "/api/step":
                        result = store.step(token, data)
                    elif path == "/api/action":
                        result = store.action(token, data)
                    elif path == "/api/leave":
                        store.session(token)
                        del store.sessions[token]
                        result = {"ok": True}
                    else:
                        self.reply(404, {"error": "Unknown endpoint"})
                        return
                self.reply(200, result)
            elif path == "/api/games":
                self.reply(200, {"games": GAMES})
            elif path == "/api/config":
                self.reply(200, {"server": SERVER, "windowsInstaller":
                                "/downloads/2Block-Setup.exe" if STATIC["/downloads/2Block-Setup.exe"][0].is_file() else None})
            elif path.startswith("/api/launches/"):
                with self.server.store.lock:
                    result = self.server.store.launch_status(path.removeprefix("/api/launches/"))
                self.reply(200, result)
            elif path in STATIC and STATIC[path][0].is_file():
                file, mime = STATIC[path]
                self.reply(200, file.read_bytes(), mime)
            else:
                self.reply(404, {"error": "Not found"})
        except PermissionError as error:
            self.reply(401, {"error": str(error)})
        except (ValueError, UnicodeError) as error:
            self.reply(400, {"error": str(error)})
        except (TimeoutError, BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch(post=True)


def main():
    with Server() as server:
        print(f"2Block portal and runtime: {SERVER}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()

