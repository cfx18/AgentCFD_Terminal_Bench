"""No-network namespaces, immutable installed tools, anonymous working paths.

The native image is administrator-configured, never selected by a model. All
tools/libraries in that image are available. No dictionary contents are parsed.
"""

from dataclasses import dataclass
import os
from pathlib import Path

VENDOR = Path(
    "/usr/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl"
)
BWRAP = VENDOR / "codex-resources/bwrap"


@dataclass(frozen=True)
class Sandbox:
    foam_root: str | None = None
    bwrap: str = str(BWRAP)
    mpi: str = "sys-openmpi"
    memory_bytes: int = 4 * 1024**3
    file_bytes: int = 512 * 1024**2

    def command(self, work, argv, *, readonly=(), environment=None):
        if not argv or not all(
            isinstance(s, str) and s and "\0" not in s for s in argv
        ):
            raise ValueError("A nonempty command argument list is required")
        work = Path(work).resolve(strict=True)
        command = [
            self.bwrap,
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--cap-drop",
            "ALL",
            "--clearenv",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--symlink",
            "usr/bin",
            "/bin",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--dir",
            "/home",
            "--dir",
            "/home/agent",
            "--bind",
            str(work),
            "/work",
        ]
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/agent",
            "LANG": "C.UTF-8",
            "OMP_NUM_THREADS": "1",
        }
        if self.foam_root:
            foam = Path(self.foam_root).resolve(strict=True)
            command += ["--ro-bind", str(foam), "/opt/foam"]
            env.update(
                WM_PROJECT_DIR="/opt/foam",
                WM_PROJECT_VERSION="v2306",
                FOAM_ETC="/opt/foam/etc",
                FOAM_APPBIN="/opt/foam/bin",
                FOAM_LIBBIN="/opt/foam/lib",
                FOAM_MPI=self.mpi,
                WM_OPTIONS="linux64IccDPInt32Opt",
                PATH="/opt/foam/bin:/usr/bin:/bin",
                LD_LIBRARY_PATH=f"/opt/foam/lib/{self.mpi}:/opt/foam/lib:/opt/foam/deps:/opt/foam/lib/dummy",
            )
        for source, target in readonly:
            command += ["--ro-bind", str(Path(source).resolve(strict=True)), target]
        env.update(environment or {})  # trusted controller only
        for key, value in env.items():
            command += ["--setenv", key, value]
        return command + ["--chdir", "/work", "--", *argv]

    def probe(self):
        import subprocess, tempfile

        with tempfile.TemporaryDirectory(prefix="of-isolation-") as work:
            code = "import os,socket; assert not os.path.exists('/root'); assert not os.path.exists('/solution'); assert socket.if_nameindex()==[(1,'lo')]; print('isolated')"
            result = subprocess.run(
                self.command(work, ["/usr/bin/python3", "-c", code]),
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode:
                raise RuntimeError(
                    "Namespace isolation probe failed: " + result.stderr[-1000:]
                )
        return {
            "filesystem": "isolated",
            "network": "no_network",
            "foam_installed": bool(self.foam_root),
        }
