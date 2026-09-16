from pathlib import Path
import ast

from setuptools import find_packages


def test_archive_is_not_a_new_runtime_dependency_or_wheel_package():
    root = Path(__file__).resolve().parents[1]
    packages = find_packages(str(root), include=["agentcfd_bench", "agentcfd_bench.*"])
    assert "agentcfd_bench" in packages
    assert all("old" not in name for name in packages)
    for path in (root / "agentcfd_bench").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(
                    ("agentcfd_bench_old", "scripts", "ci_checks")
                )
