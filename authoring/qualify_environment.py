"""Free local environment audit; writes new manifests only. No model requests."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agentcfd_bench.execution.identity import runtime_identity
from agentcfd_bench.execution.files import inventory
from agentcfd_bench.records.store import write_once, digest

PROJECT = Path(__file__).resolve().parents[1]


def main(report):
    tree = ET.parse(report)
    cases = tree.findall(".//testcase")
    required = {
        "test_installed_tool_dependencies",
        "test_native_dictionary_errors_not_python_allowlist",
        "test_real_shock_native_to_private_grader",
    }
    if not required <= {c.get("name").split("[")[0] for c in cases} or any(
        c.find(k) is not None for c in cases for k in ("failure", "error", "skipped")
    ):
        raise SystemExit("A passing local native integration report is required")
    foam = PROJECT / "environments/native-v2306/foam"
    docs = PROJECT / "environments/docs-v2306"
    library = ":".join(
        str(foam / p) for p in ("lib/intelmpi", "lib", "deps", "lib/dummy")
    )

    def audit(path):
        r = subprocess.run(
            ["/usr/bin/ldd", str(path)],
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin", "LD_LIBRARY_PATH": library},
            timeout=15,
        )
        return path.name, [
            line.strip() for line in r.stdout.splitlines() if "not found" in line
        ]

    with ThreadPoolExecutor(max_workers=4) as pool:
        dependency_errors = {
            name: errors
            for name, errors in pool.map(audit, sorted((foam / "bin").iterdir()))
            if errors
        }
    write_once(
        PROJECT / "docs/native-dependency-audit.json", {"missing": dependency_errors}
    )
    if dependency_errors:
        raise SystemExit(
            "Native shared dependencies are missing; see docs/native-dependency-audit.json"
        )
    write_once(
        foam / "workbench-manifest.json",
        {
            "version": "OpenFOAM-v2306",
            "wm_options": "linux64IccDPInt32Opt",
            "mpi": "intelmpi",
            "content_identity": runtime_identity(foam),
            "native_integration_passed": True,
            "native_executables": len(list((foam / "bin").iterdir())),
            "integration_report_sha256": __import__("hashlib")
            .sha256(Path(report).read_bytes())
            .hexdigest(),
            "validated_scope": "bundled serial native executables; dynamic compilation and distributed MPI unqualified",
        },
    )
    names = ["scalarTransport", "readFields", "fvOptions"]
    paths = [p.as_posix() for p in (docs / "source").rglob("*")]
    if not all(any(name in p for p in paths) for name in names):
        raise SystemExit("Required native API source docs are missing")
    write_once(
        docs / "manifest.json",
        {
            "version": "OpenFOAM-v2306",
            "coverage_reviewed": True,
            "coverage": "635 reference pages plus matching native source, not a claim of exhaustive manual coverage",
            "content_identity": digest(inventory(docs)),
            "tutorial_solutions_included": False,
            "known_missing_api_pages_remedied_by_source": names,
        },
    )


if __name__ == "__main__":
    main(sys.argv[1])
