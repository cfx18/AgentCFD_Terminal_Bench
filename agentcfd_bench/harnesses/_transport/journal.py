import json
import os
from pathlib import Path
from .identity import fingerprint

def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)

def read_receipt(path):
    path = Path(path)
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    if fingerprint(record["payload"]) != record["hash"]:
        raise ValueError("Native receipt integrity mismatch")
    return record["payload"]


class NativeJournal:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def read(self, name):
        return read_receipt(self.root / (name + ".json"))

    def write(self, name, data):
        with (self.root / (name + ".json")).open("x") as handle:
            handle.write(encode({"payload": data, "hash": fingerprint(data)}))
            handle.flush()
            os.fsync(handle.fileno())
        directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

