import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from mimetypes import guess_type
from os.path import exists
from typing import Callable, Self, Any
import abc


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


__all__ = ["App"]

DIRNAME = __file__.replace("\\", "/").rsplit("/", 1)[0]


class Request:
    __slots__ = ["path", "client"]


class Response:
    @abc.abstractmethod
    def send(self, data: str | dict[Any, Any]) -> Self:
        """Send data"""

    @abc.abstractmethod
    def status(self, value: int) -> Self:
        """Set response code"""

    @abc.abstractmethod
    def headers(self, value: dict[str, str]) -> Self:
        """Set headers"""

    @abc.abstractmethod
    def add(self, data: str | dict[Any, Any]) -> Self:
        """Add data"""


class _Server(BaseHTTPRequestHandler):
    def do_GET(self):
        ...

    def do_POST(self):
        ...


class App:
    def __init__(self) -> None:
        self.routes: dict[str, Callable[..., Any]] = {}
        self._static_dict: dict[str, str] = {}

    def listen(
        self, ip: str, port: int, callback: Callable[..., None] | None = None
    ) -> None:
        _routes_arg = self.routes
        _static_arg = self._static_dict
        _find_static_arg = self.find_static

        def do_GET(self: BaseHTTPRequestHandler):
            nonlocal _routes_arg, _static_arg, _find_static_arg

            if self.path.rstrip("/") in _routes_arg:
                _req = Request()
                _res = Response()

                _req.path = self.path
                _req.client = self.client_address

                response: dict[str, Any] = {
                    "data": "",
                    "headers": {
                        "Content-type": "text/html",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "status": 200,
                }

                def _send(data: dict[Any, Any] | str) -> Response:
                    if isinstance(data, dict):
                        content_type = "application/json"
                        data = json.dumps(data)
                    else:
                        content_type = "text/html"
                    response["headers"]["Content-type"] = content_type
                    response["data"] = data
                    return _res

                def _add(data: dict[Any, Any] | str) -> Response:
                    content_type = response["headers"]["Content-type"]
                    if isinstance(data, dict):
                        if response["data"]:
                            if content_type == "application/json":
                                data_merge = json.loads(response["data"])
                                data |= data_merge
                            else:
                                return _res

                        data = json.dumps(data)
                    response["data"] += data
                    return _res

                def _status(value: int) -> Response:
                    response["status"] = value
                    return _res

                def _set_headers(value: dict[str, str]) -> Response:
                    response["headers"] |= value
                    return _res

                _res.send = _send
                _res.status = _status
                _res.headers = _set_headers
                _res.add = _add

                _routes_arg[self.path.rstrip("/")](_req, _res)

                self.send_response(response["status"])

                for key, value in response["headers"].items():
                    self.send_header(key, value)

                self.end_headers()

                self.wfile.write(bytes(response["data"], "utf-8"))

            elif any((self.path.startswith(x) for x in _static_arg.keys())):
                abspath = _find_static_arg(_static_arg, self.path)

                if abspath.endswith("/"):
                    abspath += "index.html"

                if not exists(abspath):
                    self.send_response(404)
                    self.end_headers()
                    return

                content = read_file(abspath)

                self.send_response(200)

                content_type, _ = guess_type(abspath)
                if not content_type:
                    raise ValueError(f"Unknown MIME type for {abspath}")
                self.send_header("Content-type", content_type)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                self.wfile.write(bytes(content, "utf-8"))

            else:
                self.send_response(404)

                self.send_header("Content-type", "text/html")
                self.end_headers()

                self.wfile.write(bytes("<h1>File not found</h1>", "utf-8"))

        _Server.do_GET = do_GET
        _Server.do_POST = do_GET

        web_server = HTTPServer((ip, port), _Server)
        if callback is not None:
            callback()
        web_server.serve_forever()

    def get(
        self, path: str
    ) -> Callable[
        [Callable[[Request, Response], Any]], Callable[[Request, Response], Any]
    ]:
        def decorator(func: Callable[[Request, Response], Any]):
            self.routes[path.rstrip("/")] = func  # deepcopy(func)
            return func

        return decorator

    def static(self, path: str, localdir: str) -> None:
        self._static_dict[path] = localdir

    def find_static(self, static: dict[str, str], path: str) -> str:
        """returns final path"""
        f = filter(path.startswith, static.keys())
        s = sorted(f, key=lambda a: len(a.split("/")))
        return path.replace(s[-1], static[s[-1]])


if __name__ == "__main__":
    app = App()

    @app.get("/api")
    def _(req: Request, res: Response):
        res.send('API<br><a href="/"><-</a>')
        res.add("<style>*{font-family:'Fira Code';}</style>")
        res.add(f"{req.path}")

    try:
        app.listen("0.0.0.0", 8888)
    except KeyboardInterrupt:
        ...
