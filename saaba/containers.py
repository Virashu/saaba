from __future__ import annotations

__all__ = ["Request", "Response"]

import json
from dataclasses import dataclass
from typing import Any


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

    def send(self, data: dict[Any, Any] | str) -> Response:
        """Send data"""
        if isinstance(data, dict):
            content_type = "application/json"
            data = json.dumps(data)
        else:
            content_type = "text/html"
        self.headers["Content-type"] = content_type
        self.data = data
        return self

    def add(self, data: dict[Any, Any] | str) -> Response:
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

    def set_status(self, value: int) -> Response:
        """Set response code"""
        self.status = value
        return self

    def set_headers(self, value: dict[str, str]) -> Response:
        """Set headers"""
        self.headers |= value
        return self
