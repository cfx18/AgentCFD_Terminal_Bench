"""Explicit real-client tool/docs probe; never a scored physics trial."""
import argparse
import json
from pathlib import Path

from agentcfd_bench.documentation import load
from agentcfd_bench.journal import NativeJournal
from agentcfd_bench.models import PublicContext
from agentcfd_bench.smoke.agent import Agent, factory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', choices=['codex', 'foamclaw', 'claude-code', 'kimi-code'], default='codex')
    parser.add_argument('--env-file')
    parser.add_argument('--auth-home')
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--max-calls', type=int, default=6)
    parser.add_argument('--allow-paid', action='store_true')
    args = parser.parse_args(argv)
    if not args.allow_paid:
        parser.error('Explicit --allow-paid required')
    if not 1 <= args.max_calls <= 32:
        parser.error('Interface probe requires 1..32 explicitly recorded model calls')
    from agentcfd_bench.spec import load_experiment
    experiment = load_experiment(args.experiment)
    extra = experiment.get('harness', {})
    if extra.get('backend') == 'chatgpt-subscription':
        if args.harness != 'codex':
            parser.error('Subscription authentication requires the Codex harness')
        if args.env_file:
            parser.error('Do not load an API credential in subscription mode')
        from agentcfd_bench.adapters.subscription_auth import SubscriptionAuth
        extra = {**extra, 'auth': SubscriptionAuth(args.auth_home)}
        endpoint = key = None
    else:
        if (args.harness != 'codex' and experiment['model']['name'] != 'Kimi-K3'
                and not (args.harness == 'kimi-code' and experiment['model']['name'] == 'kimi-k3')):
            parser.error('Non-Codex bridges require the explicit Kimi-K3 model')
        if not args.env_file or args.auth_home:
            parser.error('Custom API mode requires --env-file only')
        from dotenv import dotenv_values
        values = dotenv_values(args.env_file)
        endpoint = values.get('SCIENCE_API_BASE') or values.get('OPENAI_BASE_URL')
        key = values.get('SCIENCE_API_KEY') or values.get('OPENAI_API_KEY')
        if not endpoint or not key:
            parser.error('Explicit provider URL and credential required')
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    journal = NativeJournal(root)
    docs = load(experiment['documentation'])
    from agentcfd_bench.documentation import PROMPT
    instruction = ('This is a local tool interface check, not a CFD benchmark. '
        'Use your file/shell tools to search the available manual for viscosity. '
        'Then create /work/system/interface-check.json containing the JSON object {"ok":true}, '
        'read it back using a JSON parser to verify the object, and finish. '
        'JSON whitespace, formatting and a trailing newline are irrelevant; do not compare raw bytes. '
        'No OpenFOAM run or '
        'science-action submission is requested. Do not investigate host files.\n' + PROMPT)
    create = factory(root/'agent', args.harness, endpoint=endpoint, credential=key,
                  legacy=Path(__file__).resolve().parents[2], seconds=600,
                  documentation=docs, model=experiment['model']['name'], **extra)
    agent = create(None)
    journal.write('spec', {'kind':'actual-client-interface-not-model-score', 'max_provider_calls':args.max_calls,
                          'model':experiment['model'], 'harness_identity':agent.identity,
                          'documentation':experiment['documentation']})
    try:
        turn = agent.step(PublicContext(instruction, {}, (), args.max_calls, 1))
        try:
            correct = json.loads(turn.files.get('system/interface-check.json','')) == {'ok':True}
        except ValueError:
            correct = False
        doc_usage = (turn.usage or {}).get('documentation') or {}
        docs_used = doc_usage.get('queries', 0) > 0
        result = {'passed':bool(correct and docs_used and turn.submitted and not turn.input_error),
                  'documentation_queried':docs_used,
                  'calls':turn.model_calls, 'usage':turn.usage, 'benchmark_score':False}
    except Exception as exc:
        result = {'passed':False, 'benchmark_score':False, 'type':type(exc).__name__,
                  'calls':getattr(exc,'model_calls',None),
                  'failure_details':getattr(exc,'failure_details',None)}
    finally:
        agent.close()
    journal.write('result', result)
    print(json.dumps(result,indent=2),flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
