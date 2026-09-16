---
name: bridge-benchmark-harness
description: Configure and extend AgentCFD benchmark harness bridges for FoamClaw, Codex CLI, Claude Code, or Kimi Code, with explicit model identity, isolation checks, and no-cost interface tests.
---

# Bridge benchmark harnesses

Use this skill on the **host configuring the benchmark**, not inside the agent
being scored. Its files and the repository names are private setup material.

Read `references/bridges.md` for the selected harness before changing its adapter.
Locate the standalone project by its `agentcfd_bench/engine.py` and task manifest;
do not assume the old project's root is the runnable package.

## Configure

Run the bundled stdlib-only helper. It does not import legacy FoamClaw, read
credentials, install clients, launch models, or run OpenFOAM:

```bash
python /absolute/path/to/skill/scripts/configure.py configure \
  --project /absolute/path/to/AgentCFD_Terminal_Bench \
  --harness foamclaw --model Kimi-K3 --wire-api chat \
  --source /absolute/path/to/legacy/AgentCFD \
  --output /absolute/path/to/new-private-setup
python /absolute/path/to/skill/scripts/configure.py doctor \
  --setup /absolute/path/to/new-private-setup
```

Other choices: `codex`, `claude-code`, `kimi-code`. Model names are explicit;
never substitute one to make a connection work. The helper creates a configuration
bundle, source fingerprints, a copied experiment and an empty credential template.
It refuses to overwrite an existing directory. `doctor` exit 0 means static setup
integrity only; JSON contains blockers and `paid_ready: false` even on success.
Do not label configuration generation as a functioning adapter or runtime install.

New setups use `experiments/science-from-scratch-rounds-v2.json`: cumulative
provider calls bound model work; token/cost/model-time use is reported, not capped
by the benchmark. Preserve client/provider output settings, without injecting a
fixed ceiling. Keep network failure guards and native runtime safety limits.
Legacy capped configs/receipts remain historical; do not mix their results with
new-policy runs or silently change settings while resuming them.

## Implement a missing bridge

Use `agentcfd_bench.adapters.contract.Harness` and the existing `agent_factory`
injection in `engine.run/resume`. Keep the existing task/verifier unchanged. Map
the real harness's session, files, actions, stop signal, and **all** provider calls
into `PublicContext -> AgentTurn`. Do not replace its reasoning loop with a new
loop bearing the same name. Fake interface tests do not qualify a real client.

Configuration metadata is a setup lock, not yet scheduler-enforced harness identity.
Before adding a non-Codex paid CLI route, persist harness version/source digest,
prompt/tool/memory settings and model settings in experiment state and reports;
reject mismatches on resume. Do not reuse old runs or old qualification evidence.

For runtime installation, inspect the actual client/version first, use a dedicated
environment, and keep credentials in the host broker. Never run `latest` installs
or copy global login/session files into an evaluated workspace. Configuration
requests do not authorize paid calls, cluster jobs, global installs, or logins.

## Verify and hand off

Run the project tests, including actual CLI/local fake-API tests where sandbox
permissions permit. For a new bridge add: normal submission, malformed output,
native failure feedback, interrupted/unknown request, restored session, request
budget including retries, and attempts to read reference/config/host paths.
Check escaping child processes and unexpected network egress too.

Report separately: generated / client installed / contract tested / isolated /
native-qualified / paid tested. Include exact test outcomes and remaining gates.
Comparisons must distinguish a fixed-model harness experiment from whole-product
comparisons where different models/tools are used. See the reference for fair
FoamClaw settings. Never describe returned reasoning summaries as complete hidden
chain of thought or as proof that the agent cannot cheat.
