"""Utilities"""


def read_file(path: str) -> str:
    """Macro to read file"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
