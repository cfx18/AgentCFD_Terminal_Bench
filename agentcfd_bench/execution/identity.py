"""Content identity of administrator-installed runtime, excluding its own manifest."""

from pathlib import Path
from .files import inventory
from ..records.store import digest, read


def runtime_identity(root):
    files = inventory(root)
    files.pop("workbench-manifest.json", None)
    return digest(files)


def verify_runtime(root, expected=None):
    value = read(Path(root) / "workbench-manifest.json")
    if expected is not None and value != expected:
        raise ValueError("Native runtime manifest changed")
    if value.get("content_identity") != runtime_identity(root):
        raise ValueError("Native runtime contents changed")
    return value
