"""Serial native release gates after final-source tests; no model calls.

Reuse the five original positives, execute registered negative/numerical controls,
then the frozen explicit-default coefficient controls. Re-entry observes the same
NativeService operations. It never creates replacement runs for uncertain exits.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def effective_coefficients(log, expected):
    from agentcfd_bench.foam.parsed import read, scalar
    blocks = re.findall(r'(?m)^\s*kEpsilonCoeffs\s*\{([^{}]*)\}', log)
    if len(blocks) != 1:
        raise ValueError('One native effective-coefficient block required')
    values = read('kEpsilonCoeffs {'+blocks[0]+'}')['kEpsilonCoeffs']
    if set(values) != set(expected):
        raise ValueError('Native coefficient keys differ from preregistration')
    parsed = {key:scalar(value) for key,value in values.items()}
    if any(parsed[k] != Decimal(expected[k]) for k in expected):
        raise ValueError('Effective native coefficient differs from registered default')
    return {key:str(value) for key,value in parsed.items()}


def observe(operation, *, seconds=600):
    from agentcfd_bench.runtime import Pending
    deadline = time.monotonic()+seconds
    while True:
        try:
            return operation()
        except (Pending, RuntimeError) as exc:
            # Only explicitly unresolved operations/known Slurm queue states.
            # All other exceptions retain evidence and stop for investigation.
            if not isinstance(exc, Pending) and '|PENDING|' not in str(exc):
                raise
            if time.monotonic() >= deadline:
                raise
            print(json.dumps({'event':'observing_existing_native_operation','reason':str(exc)}),flush=True)
            time.sleep(10)


def run(args):
    from agentcfd_bench.journal import NativeJournal, read_receipt
    from agentcfd_bench.identity import fingerprint
    from agentcfd_bench.qualification import qualify, require_qualified, protocol_identity, _positive_import
    from agentcfd_bench.runtime import cluster_service
    from agentcfd_bench.task_package import load_task
    from agentcfd_bench.foam.science_metrics import snapshot
    from agentcfd_bench.reporting import atomic

    tests, registration, originals, output = [Path(v).resolve() for v in
        (args.tests,args.preregistration,args.originals,args.output)]
    if not output.is_relative_to(PROJECT/'runs'):
        raise ValueError('Use a separate release evidence directory under runs/')
    passed, test_spec = [read_receipt(tests/(name+'.json')) for name in ('summary','spec')]
    assert passed['kind'] == 'final_deployed_source_regression'
    assert passed['collected'] == passed['passed'] > 0
    assert passed['failed_reports'] == passed['skipped_reports'] == passed['pytest_exit'] == 0
    assert passed['source_files_unchanged'] and passed['candidate_matches'] and passed['runner_unchanged']
    assert passed['actual_client_tests_enabled'] and passed['old_run_resume_rejected']
    assert not passed['forbidden_attempts']
    registered = read_receipt(registration)
    assert registered['kind'] == 'preregistered_supplemental_native_controls_not_executed'
    def sources_unchanged():
        actual = {str(p.relative_to(PROJECT)):sha(p)
                  for folder in ('agentcfd_bench','tests','tasks','resources','experiments')
                  for p in (PROJECT/folder).rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts}
        assert test_spec['source_files'] == actual, 'Final tested source changed'
        assert sha(Path(__file__)) == driver_hash, 'Qualification driver changed while running'
    driver_hash = sha(Path(__file__))
    sources_unchanged()
    tasks = {name:load_task(name) for name in passed['protocol_hashes']}
    assert {name:protocol_identity(task=task) for name,task in tasks.items()} == passed['protocol_hashes']
    for control in registered['controls']:
        task = tasks[control['task']['id']]
        assert task.binding == control['task']
        assert protocol_identity(task=task) == control['candidate_protocol_hash']
        assert fingerprint(task.reference().reference_files()) == control['reference_input_hash']
        assert fingerprint(control['control_inputs']) == control['control_input_hash']
        assert _positive_import(task) == control['original_positive']
        assert task.acceptance()._acceptance.policy == control['quantitative_policy']
        assert [[label,list(argv)] for label,argv in task.execution.commands] == control['commands']
    journal = NativeJournal(output)
    spec = {'kind':'deployed_release_native_qualification','driver_sha256':driver_hash,
            'tests_sha256':sha(tests/'summary.json'), 'test_spec_sha256':sha(tests/'spec.json'),
            'preregistration_sha256':sha(registration), 'protocol_hashes':passed['protocol_hashes'],
            'originals':str(originals), 'standard_tasks':list(tasks),
            'supplemental_tasks':[v['task']['id'] for v in registered['controls']],
            'new_paid_requests':0,'original_reference_reruns':0}
    if journal.read('spec') is None:
        journal.write('spec',spec)
        journal.write('driver-source',{'source':Path(__file__).read_text(),'sha256':driver_hash})
    assert journal.read('spec') == spec, 'Do not reuse evidence with changed inputs or driver'
    standard, supplemental = {}, {}
    def progress():
        atomic(output/'progress.json',json.dumps({'time':datetime.now(timezone.utc).isoformat(),
            'standard':standard,'supplemental':supplemental,'new_paid_requests':0},indent=2)+'\n')
    for name, task in tasks.items():
        sources_unchanged()
        path = output/name
        service = cluster_service(path/'native',task=task)
        value = observe(lambda:qualify(path,service,task=task,positive_source=originals/name))
        standard[name] = {'passed':value['passed'],'checks':value['checks']}
        progress()
        print(json.dumps({'event':'standard_task_qualified','task':name,**standard[name]}),flush=True)
        if not value['passed']:
            raise ValueError('Standard qualification failed; no threshold changes or replacement controls')
        assert require_qualified(path,task=task) == value
    for control in registered['controls']:
        name = control['task']['id']
        task, path = tasks[name], output/'explicit-defaults'/name
        sources_unchanged()
        private = NativeJournal(path)
        service = cluster_service(path/'native',task=task)
        native = observe(lambda:service.execute('r-000001',control['control_inputs'],control['native_seconds_limit']))
        assert native['task'] == task.binding
        assert native['input_hash'] == control['control_input_hash']
        assert read_receipt(service.root/'r-000001/released.json') == {'released':True}
        acceptance = task.acceptance()
        evaluation, coefficients, equal_fields = {'verdict':'not_evaluated'}, None, None
        if native['verdict'] == 'pass':
            coefficients = effective_coefficients(native['artifacts']['solver.log'],control['expected_effective_coefficients'])
            # Author-only qualification measurements; never a synthetic model report.
            observed = snapshot(native['artifacts'],acceptance._acceptance.profile)
            evaluation = acceptance.evaluate({'measurements':observed['measurements']},native)
            equal_fields = observed['fields'] == acceptance._acceptance.baseline['snapshot']['fields']
        value = {'task':task.binding,'protocol_hash':protocol_identity(task=task),
                 'native_result_hash':fingerprint(native),'control_input_hash':control['control_input_hash'],
                 'native_verdict':native['verdict'],'effective_coefficients':coefficients,
                 'evaluation':evaluation,'exact_same_final_fields_diagnostic':equal_fields,
                 'passed':native['verdict']=='pass' and evaluation['verdict']=='pass' and coefficients is not None,
                 'new_model_requests':0,'not_a_model_report':True}
        if private.read('assessment') is None:
            private.write('assessment',value)
        assert private.read('assessment') == value
        supplemental[name] = {'passed':value['passed'],'exact_same_final_fields_diagnostic':equal_fields}
        progress()
        print(json.dumps({'event':'supplemental_task_qualified','task':name,**supplemental[name]}),flush=True)
        if not value['passed']:
            raise ValueError('Supplemental qualification failed; preserve evidence for review')
    sources_unchanged()
    result = {**spec,'standard':standard,'supplemental':supplemental,
              'qualified':all(x['passed'] for x in list(standard.values())+list(supplemental.values()))}
    if journal.read('result') is None:
        journal.write('result',result)
    assert journal.read('result') == result
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('tests','preregistration','originals','output'):
        parser.add_argument('--'+key,required=True)
    parser.add_argument('--execute-native',action='store_true')
    args = parser.parse_args()
    if not args.execute_native:
        parser.error('Explicit --execute-native required; no paid model calls are made')
    print(json.dumps(run(args),ensure_ascii=False,indent=2),flush=True)
