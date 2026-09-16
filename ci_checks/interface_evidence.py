"""Distinguish a real upstream probe from user-selected LOCAL client tests."""
KIND = 'local-client-contract-not-provider-probe-v1'


def validate(mode, spec, result, *, tests=None):
    if not result or not result.get('passed') or result.get('benchmark_score') is not False:
        raise ValueError('Interface evidence has not passed')
    local = spec.get('kind') == KIND
    if local != (mode == 'local-only') or mode not in ('live-probe','local-only'):
        raise ValueError('Interface evidence mode differs from explicitly selected campaign condition')
    if not local:
        return
    identity = spec['harness_identity']
    if (identity.get('name') != 'codex' or identity.get('backend') != 'chatgpt-subscription'
            or identity.get('reasoning_effort') != 'xhigh'
            or result.get('provider_verified') is not False or result.get('model_requests_sent') != 0):
        raise ValueError('Local evidence must not claim live provider verification')
    required = {'gpt-6-astra':'test_real_astra_xhigh_client_tools_docs_isolation_and_resume',
                'gpt-5.6-sol':'test_real_xhigh_client_tools_docs_isolation_and_resume'}.get(spec['model']['name'])
    if required is None:
        raise ValueError('No reviewed local-client test for this model')
    if tests is not None:
        passed = {r['name'] for shard in tests['shards'] for r in shard['cases'] if r['status']=='pass'}
        hashes = [s['sha256'] for s in tests['shards']]
        if not tests['passed'] or required not in passed or spec.get('test_junit_sha256') != hashes:
            raise ValueError('Local interface evidence is not bound to successful exact-model CLI/isolation tests')


def create(project, experiment, output, junit, auth_home):
    """No credential read, request or CLI model turn: bind completed local tests."""
    from pathlib import Path
    from release_evidence import verify
    from agentcfd_bench.smoke.agent import harness_identity
    from agentcfd_bench.documentation import load
    from agentcfd_bench.adapters.subscription_auth import SubscriptionAuth
    from agentcfd_bench.journal import NativeJournal
    checks = verify(junit, project, subscription_xhigh=True)
    h = experiment['harness']
    catalog = SubscriptionAuth(auth_home).catalog(experiment['model']['name'], h['reasoning_effort'])
    identity = harness_identity('codex',Path(project).parent, model=experiment['model']['name'],
        fresh_action=True, documentation=load(experiment['documentation']), catalog=catalog, **h)
    spec = {'kind':KIND,'model':experiment['model'],'harness_identity':identity,
            'test_junit_sha256':[s['sha256'] for s in checks['shards']],
            'authorization':'Explicit user choice: no online smoke; start formal tasks after local tests.'}
    result = {'passed':True, 'benchmark_score':False,'provider_verified':False,'model_requests_sent':0,
              'meaning':'Actual Codex executable with fake local Responses; quota/access not probed.'}
    validate('local-only',spec,result,tests=checks)
    Path(output).mkdir(parents=True,exist_ok=False)
    journal = NativeJournal(output)
    journal.write('spec',spec)
    journal.write('result',result)
    return result
