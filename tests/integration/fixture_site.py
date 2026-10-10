from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HOME = """<html><body>
<h1 id="title">Welcome</h1>
<p id="visited"></p>
<input id="name"><button id="go">Go</button>
<p id="greeting"></p>
<p id="hidden" style="display:none">hidden</p>
<script>
document.getElementById('visited').textContent = localStorage.getItem('v') ? 'yes' : 'no';
localStorage.setItem('v', '1');
document.getElementById('go').onclick = () => {
  document.getElementById('greeting').textContent =
    'Hello, ' + document.getElementById('name').value;
};
console.log('page loaded');
</script></body></html>"""

_THIRD_PARTY = (
    '<html><body><h1 id="title">Third party</h1>'
    '<img src="http://localhost:__PORT__/pixel.png"></body></html>'
)

_WEBSOCKET = """<html><body><h1 id="title">Socket</h1>
<p id="closed" style="display:none">closed</p>
<script>
const socket = new WebSocket('ws://__HOST__:__PORT__/socket');
socket.onclose = () => { document.getElementById('closed').style.display = 'block'; };
</script></body></html>"""

_CONSOLE_ERROR = """<html><body><h1 id="title">Broken</h1>
<script>console.error('boom'); throw new Error('page-crash');</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        port = str(self.server.server_address[1])
        path = self.path
        if path == "/":
            self._html(200, _HOME)
        elif path == "/redirect-out":
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{port}/")
            self.end_headers()
        elif path == "/third-party":
            self._html(200, _THIRD_PARTY.replace("__PORT__", port))
        elif path in {"/websocket", "/websocket-same-host"}:
            host = "127.0.0.1" if path == "/websocket-same-host" else "localhost"
            self._html(200, _WEBSOCKET.replace("__HOST__", host).replace("__PORT__", port))
        elif path == "/slow":
            time.sleep(3)
            self._html(200, _HOME)
        elif path == "/console-error":
            self._html(200, _CONSOLE_ERROR)
        elif path == "/missing":
            self._html(404, "<html><body><h1 id='title'>Not found</h1></body></html>")
        else:
            self._html(404, "not found")

    def _html(self, status: int, body: str) -> None:
        payload = body.encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def fixture_site() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
