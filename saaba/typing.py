__all__ = ["RouteCallable", "RouteDecorator"]

from typing import Any, Callable, TypeAlias

from .containers import Request, Response

RouteCallable: TypeAlias = Callable[[Request, Response], Any]
RouteDecorator: TypeAlias = Callable[[RouteCallable], RouteCallable]
