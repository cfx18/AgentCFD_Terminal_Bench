"""Filesystem containment only: no OpenFOAM syntax or tool allowlists."""

import hashlib
import os
from pathlib import Path
import shutil
import stat


def inventory(root, max_bytes=2 * 1024**3):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Expected a real directory")
    result, size = {}, 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            if (Path(directory) / name).is_symlink():
                raise ValueError(
                    "Directory symlink cannot leave the submitted filesystem"
                )
        for name in sorted(files):
            path = Path(directory) / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError(
                    "Only regular, non-linked submitted files are accepted"
                )
            size += info.st_size
            if size > max_bytes:
                raise ValueError("Workspace disk quota exceeded")
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
            result[path.relative_to(root).as_posix()] = h.hexdigest()
    return result


def snapshot(source, destination):
    before = inventory(source)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    source_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in before:
            out = destination / name
            out.parent.mkdir(parents=True, exist_ok=True)
            directory = os.dup(source_fd)
            try:
                parts = name.split("/")
                for part in parts[:-1]:
                    child = os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=directory,
                    )
                    os.close(directory)
                    directory = child
                fd = os.open(
                    parts[-1],
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=directory,
                )
                with os.fdopen(fd, "rb") as stream:
                    info = os.fstat(stream.fileno())
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                        raise ValueError("Submitted file changed type while copying")
                    with out.open("xb") as target:
                        shutil.copyfileobj(stream, target)
                out.chmod(
                    stat.S_IMODE(info.st_mode) & 0o777
                )  # scripts stay executable; no setuid bits
            finally:
                os.close(directory)
    finally:
        os.close(source_fd)
    if inventory(source) != before or inventory(destination) != before:
        raise RuntimeError("Workspace changed while snapshotting")
    return before
