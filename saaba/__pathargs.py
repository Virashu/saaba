import re
from typing import Any

format = "users/{user}/messages/{message}"
query = "users/virashu/messages/mondays"


def find_vars(_format: str, _query: str) -> dict[str, Any] | None:
    re_format = re.sub(r"{(\w+)}", r"(?P<\1>\\w+)", _format)

    pattern = re.compile(re_format)

    if match := pattern.match(_query):
        return match.groupdict()

    return None


print(find_vars(format, query))
