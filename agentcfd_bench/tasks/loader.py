from dataclasses import dataclass
from pathlib import Path
import json
import shutil

from ..execution.files import inventory
from ..records.store import digest


@dataclass(frozen=True)
class Task:
    root: Path
    task_id: str
    identity: str

    @classmethod
    def load(cls, root):
        root = Path(root).resolve(strict=True)
        meta = json.loads((root / "task.json").read_text())
        if meta["schema"] != "openfoam-task-v3":
            raise ValueError("Unsupported task schema")
        for path in (
            "public/instruction.md",
            "public/observations.md",
            "private/reference.json",
            "private/grading.json",
        ):
            if not (root / path).is_file():
                raise ValueError("Task file missing: " + path)
        return cls(root, meta["id"], digest(inventory(root)))

    def public_prompt(self):
        return (
            (self.root / "public/instruction.md").read_text()
            + "\n\n"
            + (self.root / "public/observations.md").read_text()
        )

    def public_to(self, destination):
        if self.identity != digest(inventory(self.root)):
            raise ValueError("Task changed after registration")
        shutil.copytree(self.root / "public", destination)

    def private(self):
        if self.identity != digest(inventory(self.root)):
            raise ValueError("Task changed after registration")
        return (
            json.loads((self.root / "private/reference.json").read_text()),
            json.loads((self.root / "private/grading.json").read_text()),
        )
