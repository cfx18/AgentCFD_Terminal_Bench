"""Host-only, append-at-source I/O transcripts. No model calls or log replay.

JSONL is the machine-readable capture; Markdown is appended in the same call.
Neither is the scheduler's state source or a replacement for raw receipts.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import select
import threading
import uuid
import warnings


LABELS = {
    "native_request": "原生工具请求：命令／参数／日志查询",
    "native_response": "原生工具响应：真实状态／日志／输出路径",
    "native_tool_error": "执行接口拒绝或基础设施错误",
    "prompt": "发送给 Agent 的提示词",
    "agent_context": "调度器交给 Harness 的上下文（实际提示词另记）",
    "client_event": "Harness 输出：消息／动作／工具观察",
    "client_stderr": "Harness 标准错误（不等于任务失败）",
    "provider_request": "模型请求已准备，等待上游结果",
    "provider_response": "上游回复已捕获（尚不代表工具已执行）",
    "provider_stream": "上游流事件（不是另一轮调用）",
    "provider_stream_partial": "未完成的上游流片段",
    "provider_delivery": "向 Harness 写入响应的结果",
    "provider_error": "接口／适配异常",
    "docs_request": "文档查询：路径与关键词／文档 ID",
    "docs_response": "文档返回的原始知识（不代表 Agent 已采用）",
    "docs_delivery": "文档响应交付记录",
    "web_retrieval": "联网查询／阅读：关键词、URL 与上游实际返回的检索记录",
    "web_request": "联网查询请求",
    "web_error": "联网查询异常",
    "process_started": "Harness 进程启动",
    "process_exit": "观察到的 Harness 退出结果",
    "client_result": "Harness 完成与接口错误汇总",
    "submission": "捕获的提交文件与提交状态",
    "feedback": "验收方产生的公开反馈（待下一次提示词发送）",
    "evaluation": "验收结果（仅供专家，不额外传给 Agent）",
    "native_result": "执行方返回的结果与输出",
    "native_error": "原生执行／证据回收异常（非模型答案错误）",
    "failure_checkpoint": "中断时保存的工作区与会话（不是有效提交）",
    "provider_continuation": "人工确认后的新续接（原请求仍保留未知）",
    "controller": "控制器状态／恢复观察",
}

HEADER = """# 实时 I/O 记录

本文件在事件发生时追加，不是结束后导出。时间为宿主捕获时间（UTC）。
只展示可捕获的输出，不补写隐含思考；响应存在不等于工具已执行，返回资料不等于已被采用。
同一次交互可能同时有上游与 Harness 两层记录；source 用于关联，不能按段落数计算模型调用。
未出现响应或退出记录的请求仍是等待中／结果未知，不推定成功或自动重发。
原始日志和状态库仍单独保留。本阅读记录不要求哈希，也不挂载给被测 Agent。

"""


def _clean(value, secrets):
    if isinstance(value, dict):
        return {
            k: (
                "[REDACTED]"
                if str(k).lower()
                in (
                    "authorization",
                    "api_key",
                    "access_token",
                    "refresh_token",
                    "id_token",
                )
                else _clean(v, secrets)
            )
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_clean(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[REDACTED]")
    return value


def _markdown(event):
    payload = event["payload"]
    if event["kind"] == "prompt":
        text, language = payload["text"], "text"
    elif event["kind"] == "client_stderr":
        text, language = payload["text"], "text"
    else:
        text, language = json.dumps(payload, ensure_ascii=False, indent=2), "json"
    fence = "`" * max(
        3, 1 + max((len(m.group()) for m in re.finditer(r"`+", text)), default=0)
    )
    label = LABELS.get(event["kind"], event["kind"])
    body = f"{fence}{language}\n{text}\n{fence}\n\n"
    if event["kind"] == "provider_stream":
        # Preserve every delta without thousands of expanded JSON snippets.
        label += (
            " · " + str(payload.get("type", "raw")) if isinstance(payload, dict) else ""
        )
        body = (
            "<details><summary>展开原始流事件</summary>\n\n" + body + "</details>\n\n"
        )
    return (
        f"## {event['captured_at']} · {label}\n\n" f"来源：{event['source']}\n\n{body}"
    )


class Transcript:
    def __init__(self, root, *, source="controller", secrets=()):
        self.root = Path(root)
        self.source = source
        self.secrets = tuple(s for s in secrets if isinstance(s, str) and s)

    def child(self, source):
        return Transcript(
            self.root, source=f"{self.source}/{source}", secrets=self.secrets
        )

    def problem(self, stage, exc):
        """Recording failures stay visible but never reinterpret a model answer."""
        error = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": self.source,
            "stage": stage,
            "error_type": type(exc).__name__,
        }
        try:
            with (self.root / "transcript-errors.jsonl").open("a") as out:
                out.write(json.dumps(error) + "\n")
                out.flush()
                os.fsync(out.fileno())
        except OSError:
            pass
        # stderr also survives when this disk cannot accept any more writes.
        try:
            warnings.warn(
                "Transcript capture incomplete: " + json.dumps(error), RuntimeWarning
            )
        except Warning:
            pass

    def emit(self, kind, payload):
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            # Shared by engine, broker and pipe reader threads; also serializes
            # separate writer instances after an explicit controller resume.
            with (self.root / "transcript.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                event = {
                    "event_id": uuid.uuid4().hex,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "source": self.source,
                    "kind": kind,
                    "payload": _clean(payload, self.secrets),
                }
                encoded = json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n"
                rendered = _markdown(event)
                with (self.root / "transcript.jsonl").open("a") as out:
                    out.write(encoded)
                    out.flush()
                    os.fsync(out.fileno())
                with (self.root / "transcript.md").open("a") as out:
                    if out.tell() == 0:
                        out.write(HEADER)
                    out.write(rendered)
                    out.flush()
                    os.fsync(out.fileno())
            return True
        except (OSError, TypeError, ValueError) as exc:
            self.problem("append", exc)
            return False


class StreamCapture:
    """Observe complete SSE events as they arrive, without changing wire bytes."""

    def __init__(self, transcript):
        self.transcript, self.pending = transcript, b""

    def feed(self, chunk):
        self.pending += chunk
        while True:
            match = re.search(rb"\r?\n\r?\n", self.pending)
            if match is None:
                break
            raw, self.pending = (
                self.pending[: match.start()],
                self.pending[match.end() :],
            )
            text = raw.decode("utf-8", errors="replace")
            data = "\n".join(
                line[5:].lstrip(" ")
                for line in text.splitlines()
                if line.startswith("data:")
            )
            try:
                value = json.loads(data)
            except ValueError:
                value = {"raw_event": text}
            self.transcript.emit("provider_stream", value)

    def finish(self):
        if self.pending:
            self.transcript.emit(
                "provider_stream_partial",
                {"text": self.pending.decode("utf-8", errors="replace")},
            )
            self.pending = b""


@contextmanager
def capture_pipe(path, transcript, *, kind="client_event"):
    """Tee child output while it runs; preserve the existing raw bytes exactly.

    The child receives an external FD, so Popen.communicate still owns only stdin
    and waiting/timeout handling, not a second competing stdout reader.
    """
    read_fd, write_fd = os.pipe()
    stop = threading.Event()

    def line(raw):
        text = raw.decode("utf-8", errors="replace")
        try:
            value = json.loads(text) if kind == "client_event" else {"text": text}
        except ValueError:
            value = {"type": "unparsed_client_output", "text": text}
        transcript.emit(kind, value)

    def pump():
        pending = b""
        try:
            with (
                os.fdopen(read_fd, "rb", buffering=0) as source,
                Path(path).open("xb") as raw,
            ):
                while True:
                    ready, _, _ = select.select([source], [], [], 0.1)
                    if not ready:
                        if stop.is_set():
                            # Usually EOF is observed instead. A descendant may
                            # still hold the pipe: make that evidence gap visible.
                            transcript.problem("pipe_not_closed", RuntimeError())
                            break
                        continue
                    chunk = os.read(source.fileno(), 65536)
                    if not chunk:
                        break
                    raw.write(chunk)
                    raw.flush()
                    pending += chunk
                    while b"\n" in pending:
                        completed, pending = pending.split(b"\n", 1)
                        line(completed)
                if pending:
                    line(pending)
                os.fsync(raw.fileno())
        except Exception as exc:
            transcript.problem("pipe_capture", exc)

    thread = threading.Thread(target=pump, daemon=True)
    thread.start()
    try:
        yield write_fd
    finally:
        os.close(write_fd)
        stop.set()
        thread.join(timeout=5)
        if thread.is_alive():
            transcript.problem("pipe_reader_join", TimeoutError())
