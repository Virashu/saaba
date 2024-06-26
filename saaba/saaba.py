"""Main file"""

from __future__ import annotations

__all__ = ["App"]

import json
import logging
import typing as t
from http.server import BaseHTTPRequestHandler, HTTPServer
from mimetypes import guess_type
from os.path import exists
from typing import Any, Callable

from .containers import Request, Response
from .typing import RouteCallable, RouteDecorator
from .utils import read_file

logger = logging.getLogger(__name__)

http_server_logger = logging.getLogger("http.server")


class App:
    "App"

    def __init__(self) -> None:
        class _Server(BaseHTTPRequestHandler):
            saaba_parent_app: "App | None" = None

            # pylint: disable=invalid-name,missing-function-docstring
            def do_GET(self) -> None:
                if self.saaba_parent_app is None:
                    return
                self.saaba_parent_app.handle_get(self)

            # pylint: disable=invalid-name,missing-function-docstring
            def do_POST(self) -> None:
                if self.saaba_parent_app is None:
                    return
                self.saaba_parent_app.handle_post(self)

            # Original method just throws it into stderr instead of using logging module
            # :(
            # pylint: disable=redefined-builtin
            def log_message(self, format: str, *args: t.Any) -> None:
                http_server_logger.info(format, *args)

        self.routes: dict[str, dict[str, Callable[..., Any]]] = {
            "get": {},
            "post": {},
        }
        self._static_dict: dict[str, str] = {}
        self._server = _Server
        self._server.saaba_parent_app = self
        self._server_instance: HTTPServer

    def handle_get(self, server: BaseHTTPRequestHandler):
        """GET request handler

        Called from child"""
        path: str = server.path
        client: tuple[str, int] = server.client_address
        query: dict[str, Any] = {}

        if "?" in path:
            url, query_string = path.split("?")

            for x in query_string.split("&"):
                key, value = x.split("=")
                query[key] = value
        else:
            url = path

        if url.rstrip("/") in self.routes["get"]:
            # Found in direct routes

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
            logger.info("GET %s", url.rstrip("/"))

            server.send_response(response.status)

            for key, value in response.headers.items():
                server.send_header(key, value)

            server.end_headers()

            server.wfile.write(bytes(response.data, "utf-8"))

        elif self.is_static(url):
            # Found in static routes
            abspath = self.find_static(self._static_dict, server.path)
            abspath.replace("../", "")

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
        """POST request handler"""
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
        self._server_instance = HTTPServer((ip, port), self._server)
        if callback is not None:
            callback()

        self._server_instance.serve_forever()

    def stop(self) -> None:
        """Stop the app"""
        self._server_instance.shutdown()

    def route(self, methods: list[str], path: str) -> RouteDecorator:
        """Set route"""

        def decorator(func: RouteCallable) -> RouteCallable:
            for method in methods:
                self.routes[method.lower()][path.rstrip("/")] = func
            return func

        return decorator

    def get(self, path: str) -> RouteDecorator:
        """Set route"""

        return self.route(["get"], path)

    def post(self, path: str) -> RouteDecorator:
        """Set route"""

        return self.route(["post"], path)

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
