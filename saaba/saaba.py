"""Main file"""

__all__ = ["App", "Request", "Response"]

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from mimetypes import guess_type
from os.path import exists
from typing import Callable, Self, Any
from dataclasses import dataclass


from .utils import read_file


@dataclass
class Request:
    """Request class

    Contains request info"""

    url: str
    path: str
    query: dict[str, Any] | None
    body: dict[str, Any] | None
    client: tuple[str, int]


class Response:
    """Response class

    Used to modify response data"""

    def __init__(self) -> None:
        self.headers: dict[str, Any] = {
            "Content-type": "text/html",
            "Access-Control-Allow-Origin": "*",
        }
        self.data: Any = ""
        self.status = 200

    def send(self, data: dict[Any, Any] | str) -> Self:
        """Send data"""
        if isinstance(data, dict):
            content_type = "application/json"
            data = json.dumps(data)
        else:
            content_type = "text/html"
        self.headers["Content-type"] = content_type
        self.data = data
        return self

    def add(self, data: dict[Any, Any] | str) -> Self:
        """Add data"""
        content_type = self.headers["Content-type"]
        if isinstance(data, dict):
            if self.data:
                if content_type == "application/json":
                    data_merge = json.loads(self.data)
                    data |= data_merge
                else:
                    return self

            data = json.dumps(data)
        self.data += data
        return self

    def set_status(self, value: int) -> Self:
        """Set response code"""
        self.status = value
        return self

    def set_headers(self, value: dict[str, str]) -> Self:
        """Set headers"""
        self.headers |= value
        return self


class App:
    "App"

    def __init__(self) -> None:
        class _Server(BaseHTTPRequestHandler):
            _parent_app: "App | None" = None

            def do_GET(self):
                if self._parent_app is None:
                    return
                self._parent_app.handle_get(self)

            def do_POST(self):
                if self._parent_app is None:
                    return
                self._parent_app.handle_post(self)

        self.routes: dict[str, dict[str, Callable[..., Any]]] = {
            "get": {},
            "post": {},
        }
        self._static_dict: dict[str, str] = {}
        self._server = _Server
        self._server._parent_app = self

    def handle_get(self, server: BaseHTTPRequestHandler):
        """GET request handler.

        Called from child"""
        if server.path.rstrip("/") in self.routes["get"]:
            # Found in direct routes
            path = server.path
            client = server.client_address
            query = {}

            if "?" in path:
                url, query_string = path.split("?")

                for x in query_string.split("&"):
                    key, value = x.split("=")
                    query[key] = value
            else:
                url = path

            request = Request(
                path=path,
                client=client,
                url=url,
                query=query,
                body=None,
            )
            response = Response()

            # Call user function
            self.routes["get"][url.rstrip("/")](request, response)

            server.send_response(response.status)

            for key, value in response.headers.items():
                server.send_header(key, value)

            server.end_headers()

            server.wfile.write(bytes(response.data, "utf-8"))

        elif self.is_static(server.path):
            # Found in static routes
            abspath = self.find_static(self._static_dict, server.path)

            if abspath.endswith("/"):
                abspath += "index.html"

            if not exists(abspath):
                server.send_response(404)
                server.end_headers()
                return

            content = read_file(abspath)

            server.send_response(200)

            content_type, _ = guess_type(abspath)
            if not content_type:
                raise ValueError(f"Unknown MIME type for {abspath}")
            server.send_header("Content-type", content_type)
            server.send_header("Access-Control-Allow-Origin", "*")
            server.end_headers()

            server.wfile.write(bytes(content, "utf-8"))

        else:
            # Not found in direct/static routes
            server.send_response(404)
            server.send_header("Content-type", "text/html")
            server.end_headers()
            server.wfile.write(bytes("<h1>File not found</h1>", "utf-8"))

    def handle_post(self, server: BaseHTTPRequestHandler) -> None:
        if server.path.rstrip("/") in self.routes["post"]:
            # Found in direct routes
            path = server.path
            url = path
            client = server.client_address

            body_raw: str = ""

            while not body_raw.count("{") or body_raw.count("{") != body_raw.count("}"):
                body_raw += server.rfile.read(1).decode()

            body = json.loads(body_raw)

            request = Request(
                path=path,
                client=client,
                url=url,
                query=None,
                body=body,
            )
            response = Response()

            # Call user function
            self.routes["post"][server.path.rstrip("/")](request, response)

            server.send_response(response.status)

            for key, value in response.headers.items():
                server.send_header(key, value)

            server.end_headers()

            server.wfile.write(bytes(response.data, "utf-8"))

        else:
            # Not found in direct routes
            server.send_response(404)
            server.send_header("Content-type", "text/html")
            server.end_headers()
            server.wfile.write(bytes("<h1>File not found</h1>", "utf-8"))

    def listen(
        self, ip: str, port: int, callback: Callable[..., None] | None = None
    ) -> None:
        """Start the app"""
        web_server = HTTPServer((ip, port), self._server)
        if callback is not None:
            callback()

        web_server.serve_forever()

    def route(
        self, method, path
    ) -> Callable[
        [Callable[[Request, Response], Any]], Callable[[Request, Response], Any]
    ]:
        """Set route"""

        def decorator(func: Callable[[Request, Response], Any]):
            self.routes[method][path.rstrip("/")] = func
            return func

        return decorator

    def get(
        self, path: str
    ) -> Callable[
        [Callable[[Request, Response], Any]], Callable[[Request, Response], Any]
    ]:
        """Set route"""

        return self.route("get", path)

    def post(
        self, path: str
    ) -> Callable[
        [Callable[[Request, Response], Any]], Callable[[Request, Response], Any]
    ]:
        """Set route"""

        return self.route("post", path)

    def static(self, url: str, path: str) -> None:
        """Set static route"""
        self._static_dict[url] = path

    def is_static(self, url: str) -> bool:
        """Check if url can be resolved with static"""
        return any((url.startswith(x) for x in self._static_dict))

    def find_static(self, static: dict[str, str], path: str) -> str:
        """returns final path"""
        f = filter(path.startswith, static.keys())
        s = sorted(f, key=lambda a: len(a.split("/")))
        return path.replace(s[-1], static[s[-1]])
