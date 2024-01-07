"""Utilities"""

__all__ = ["read_file", "get_path"]


def read_file(path: str) -> str:
    """Macro to read file"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_path(file: str) -> str:
    """Get absolute path using `__file__`"""
    return file.replace("\\", "/").rsplit("/", 1)[0]
