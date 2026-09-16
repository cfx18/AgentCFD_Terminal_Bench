"""One-time mechanical source migration; NOT imported by the benchmark.

Copy tested transport plumbing, and extract the transitive pure-physics dependency
closure. Archived source remains byte-for-byte unchanged. No model/solver calls.
"""

import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys

PROJECT = Path(__file__).resolve().parents[1]
OLD = PROJECT / "agentcfd_bench_old"
NEW = PROJECT / "agentcfd_bench"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as out:
        out.write(text)


def transport():
    names = [
        "identity.py",
        "journal.py",
        "telemetry.py",
        "diagnostics.py",
        "provider_outcome.py",
        "live_transcript.py",
        "documentation.py",
        "documentation_service.py",
        "documentation_statistics.py",
        "adapters/native_responses.py",
        "adapters/codex_bridge.py",
        "adapters/request_queue.py",
        "adapters/response_stream.py",
        "adapters/subscription_auth.py",
        "adapters/codex_broker.py",
        "smoke/broker.py",
        "smoke/protocol.py",
    ]
    target = NEW / "harnesses/_transport"
    for name in names:
        text = (
            (OLD / name)
            .read_text()
            .replace("agentcfd_bench.", "agentcfd_bench.harnesses._transport.")
        )
        if name.endswith("subscription_auth.py"):
            text = text.replace(
                "from .codex_agent import CODEX", "from ...codex import CODEX"
            )
        write(target / name, text)
    for sub in ("", "adapters", "smoke"):
        write(
            target / sub / "__init__.py",
            '"""Preserved protocol plumbing; no legacy controller or task dispatch."""\n',
        )
    write(NEW / "records/transcript.py", (OLD / "live_transcript.py").read_text())


def physics():
    cache, selected, imports = {}, {}, {}

    def module(name):
        if name in cache:
            return cache[name]
        text = (OLD / (name.replace(".", "/") + ".py")).read_text()
        tree = ast.parse(text)
        definitions = {}
        aliases = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                definitions[node.name] = node
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for target in (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                ):
                    if isinstance(target, ast.Name):
                        definitions[target.id] = node
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    aliases[alias.asname or alias.name.split(".")[0]] = (
                        node,
                        None,
                        alias.name,
                    )
            elif isinstance(node, ast.ImportFrom):
                base = name.split(".")[: -node.level] if node.level else []
                source = ".".join(
                    base + ((node.module or "").split(".") if node.module else [])
                )
                for alias in node.names:
                    aliases[alias.asname or alias.name] = (
                        node,
                        source if node.level else None,
                        alias.name,
                    )
        cache[name] = (text, definitions, aliases)
        return cache[name]

    def need(name, symbol):
        text, defs, aliases = module(name)
        if symbol in aliases:
            node, source, original = aliases[symbol]
            imports.setdefault(name, set()).add(node)
            if source is not None:
                candidate = ".".join(x for x in (source, original) if x)
                if (OLD / (candidate.replace(".", "/") + ".py")).exists():
                    return  # module attributes are traversed below
                need(source, original)
            return
        if symbol not in defs:
            return
        node = defs[symbol]
        if node in selected.setdefault(name, set()):
            return
        selected[name].add(node)
        for item in ast.walk(node):
            if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Load):
                need(name, item.id)
            if (
                isinstance(item, ast.Attribute)
                and isinstance(item.value, ast.Name)
                and item.value.id in aliases
            ):
                parent, source, original = aliases[item.value.id]
                if source is not None:
                    candidate = ".".join(x for x in (source, original) if x)
                    if (OLD / (candidate.replace(".", "/") + ".py")).exists():
                        need(candidate, item.attr)
            if isinstance(item, ast.ImportFrom) and item.level:
                source = ".".join(
                    name.split(".")[: -item.level] + (item.module or "").split(".")
                )
                for alias in item.names:
                    need(source, alias.name)

    for symbol in ("snapshot", "compare", "diagnostics", "schema", "POLICY"):
        need("accepted_reference", symbol)
    # Retain only needed aliases from each import statement (not unused author modules).
    target = NEW / "grading/physics"
    for name in sorted(set(selected) | set(imports)):
        text, defs, aliases = module(name)
        nodes = sorted(selected.get(name, set()), key=lambda n: n.lineno)
        used = {
            n.id
            for node in nodes
            for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
        }
        headers = []
        for node in sorted(imports.get(name, set()), key=lambda n: n.lineno):
            filtered = [
                a for a in node.names if (a.asname or a.name.split(".")[0]) in used
            ]
            if filtered:
                cloned = (
                    ast.Import(filtered)
                    if isinstance(node, ast.Import)
                    else ast.ImportFrom(node.module, filtered, node.level)
                )
                headers.append(ast.unparse(cloned))
        body = "\n\n".join(ast.get_source_segment(text, node) for node in nodes)
        write(
            target / (name.replace(".", "/") + ".py"),
            '"""Pure numeric extraction/comparison migrated from '
            + name
            + '; no runtime policy."""\n'
            + "\n".join(headers)
            + "\n\n"
            + body
            + "\n",
        )
    for sub in ("", "foam"):
        write(
            target / sub / "__init__.py",
            '"""Frozen numerical definitions, independent of execution and harness."""\n',
        )


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "transport":
        transport()
    elif mode == "physics":
        physics()
    elif mode == "inventory":
        files = {
            p.relative_to(OLD).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in OLD.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        write(
            PROJECT / "docs/archive-v2-inventory.json",
            json.dumps(files, sort_keys=True, indent=2) + "\n",
        )
    elif mode == "decorators":
        # Mechanical correction: get_source_segment starts after decorator lines.
        for path in (NEW / "grading/physics").rglob("*.py"):
            original = OLD / path.relative_to(NEW / "grading/physics")
            if not original.exists():
                continue
            decorators = {
                n.name: "\n".join("@" + ast.unparse(d) for d in n.decorator_list) + "\n"
                for n in ast.parse(original.read_text()).body
                if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.decorator_list
            }
            content = path.read_text()
            for name, prefix in decorators.items():
                for token in ("class " + name + ":", "def " + name + "("):
                    if "\n" + token in content:
                        content = content.replace("\n" + token, "\n" + prefix + token)
            path.write_text(content)
    elif mode == "tasks":
        for task in ("s-202", "s-203", "s-204", "s-205"):
            source = PROJECT / "tasks/releases/expert-output-v1" / task
            target = PROJECT / "tasks/releases/workbench-v3" / task
            write(
                target / "task.json",
                json.dumps(
                    {
                        "schema": "openfoam-task-v3",
                        "id": task,
                        "source": "expert-output-v1",
                    },
                    indent=2,
                )
                + "\n",
            )
            for name in ("instruction.md", "observations.md"):
                write(target / "public" / name, (source / name).read_text())
            shutil.copytree(source / "geometry", target / "public/geometry")
            write(
                target / "private/reference.json",
                (source / "solution/accepted-target.json").read_text(),
            )
            write(
                target / "private/grading.json",
                json.dumps(
                    {
                        "policy": "accepted-gt-v1",
                        "convergence_rules": [],
                        "convergence_status": "diagnostic_only_until_expert_thresholds_are_registered",
                        "reference_revision": "unchanged_expert_output_v1",
                    },
                    indent=2,
                )
                + "\n",
            )
    elif mode == "docs":
        corpus = json.loads(
            (PROJECT / "resources/openfoam-v2306-reference-v1/corpus.json").read_text()
        )
        for page in corpus["pages"]:
            write(
                PROJECT / "environments/docs-v2306/manual" / (page["id"] + ".md"),
                "# "
                + page["title"]
                + "\n\nSource: "
                + page["url"]
                + "\n\n"
                + page["text"]
                + "\n",
            )
    else:
        raise SystemExit("transport | physics | inventory")
