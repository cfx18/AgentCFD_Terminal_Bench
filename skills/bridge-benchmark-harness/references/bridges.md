# Bridge boundaries and source map

## Two interfaces, not interchangeable

Harbor's **dataset adapter** converts tasks. Its **agent integration** uses
`BaseAgent` (`setup`, async `run`) or `BaseInstalledAgent` for headless clients.
`AgentFactory.create_agent_from_config` accepts a custom import path.
Official source/docs: https://www.harborframework.com/docs/agents

Our standalone project uses `engine.run(experiment, root, agent_factory, service)`
and `engine.resume(root, agent_factory, service)`. A factory receives the public
artifact directory and returns `step(PublicContext) -> AgentTurn`, `close()`.
`adapters/contract.py` documents this structural interface. `__main__.py` still
only dispatches the Codex paid factory; arbitrary Python factories are trusted
host code, not automatically sandboxed plugins.

Harbor 0.22.0 locally includes Codex, Claude Code, Kimi Code and Kimi CLI adapters.
They are useful reusable client implementations but **do not by themselves** map
our repeated service submissions, host receipts and budget protocol. Do not put
our task folder into stock `harbor run` and claim protocol equivalence.

## Codex

Reuse `agentcfd_bench/codex.py:factory`, `adapters/codex_agent.py:CodexAgent`,
`codex_broker.py` and `codex_bridge.py`. Broker credentials stay on the host.
Runtime needs the pinned vendored CLI, bubblewrap, and the existing cluster service.
The helper does not install any of them. Existing tests:
`tests/test_science_codex_integration.py`, `tests/test_codex_broker_compatibility.py`,
`tests/test_process_interruption.py`, `tests/test_migration_recovery.py`.
Official noninteractive mode: https://developers.openai.com/codex/noninteractive/
CLI JSON events are not the task's numeric report format; both need validation.

## FoamClaw

Inspect the selected source, not an unrelated similarly named directory:

- `foamclaw/core/react.py:ReActEngine.__init__/run`: injectable LLM, tools, memory;
  action-memory mode, executor push and argument repair change behavior.
- `foamclaw/core/llm.py:LLMClient.chat/_add_usage`: usage can be absent; the current
  usage counter is not authoritative dispatch accounting. SDK retries also count.
- `foamclaw/tools/registry.py:ToolRegistry`: inject only benchmark-approved tools.
- `foamclaw/core/memory.py`: freeze the actual memory configuration/version.

Reuse the real engine in a dedicated worker. Do not import it into the scorer or
mount the whole old repository: imports use `config.settings`, which may load a
real environment file. Package reviewed source/dependencies only. Bridge filesystem
tools to the anonymous workdir; bridge solver requests to the benchmark service,
never unrestricted host `run_solver`. Submission must be an explicit operation;
returning a prose summary does not mean submit.

For a **controlled-tools track**, no reference/tutorial-copy/retrieval/cross-task
memory tools. Same public task, model, provider, feedback and budget; freeze all
remaining prompt/memory/executor-push/repair settings. A disabled feature must be
reported, e.g. `foamclaw-controlled`, not marketed as default FoamClaw. For a
**native-product track**, keep each product's native features and report the
differences; do not attribute its score solely to harness intelligence.

No production FoamClaw worker is implemented by this configuration skill. Its
source check is AST-only and explicitly not an import, model call or isolation test.

## Claude Code

Reuse/reference Harbor `agents/installed/claude_code.py`; inspect its installed
version, setup, output parsing and resume implementation. Official headless docs:
https://code.claude.com/docs/en/headless . Native print mode supports structured
events but its Anthropic protocol is **not** the current Responses broker.
Implement/count the correct transport and test failure events as well as exit code.
Do not assume an arbitrary OpenAI-compatible model works through that protocol.
Configuration currently records intent only; no standalone paid adapter exists.

## Kimi Code versus Kimi CLI

Harbor has two distinct implementations. `agents/installed/kimi_code.py` installs
`@moonshot-ai/kimi-code`; `kimi_cli.py` is the separate Python client. Both may
occupy a command named `kimi`. Do not identify the product from executable name
alone or apply Python print-mode flags to the Node client without checking.
Sources: https://github.com/MoonshotAI/kimi-code and
https://github.com/MoonshotAI/kimi-cli . Record package identity, version and actual
supported headless/session flags. The `kimi-code` helper profile deliberately
does not select Kimi CLI as a fallback. No standalone paid adapter exists yet.

## Common acceptance gates

On one minimal public task: successful submit, nonzero native exit, malformed
output, interrupted request with unknown outcome, and restart after a saved exit
receipt. Preserve original logs, session IDs, input hashes and dispatch counts.
Unknown provider outcomes are not free retries. Every bridge must hide host
credentials, references, scores, judge code and other tasks. A tools allowlist or
JSON output schema is not an OS sandbox. Bind all settings to the run before
comparing scores, and retain failures rather than shrinking the denominator.
