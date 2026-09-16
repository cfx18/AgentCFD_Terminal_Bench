"""Read archived evidence only. Never submit jobs, invoke models or grade agents.

Execution completion and suitability as a free-mesh reference are different.
Residuals below a limit alone never qualify steady physics or mesh independence.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def check_receipt(outer, expected_inputs):
    if not isinstance(outer, dict) or set(outer) != {'payload', 'hash'}:
        raise ValueError('Missing native evidence envelope')
    value = outer['payload']
    if fingerprint(value) != outer['hash']:
        raise ValueError('Native receipt integrity mismatch')
    if not isinstance(value.get('artifacts'), dict):
        raise ValueError('Native artifacts missing')
    if value.get('artifact_hash') != fingerprint(value['artifacts']):
        raise ValueError('Native artifact integrity mismatch')
    if value.get('input_hash') != fingerprint(expected_inputs):
        raise ValueError('Reference inputs differ from native execution')
    return value


def steady_evidence(log, limits):
    """Inspect the LAST iteration's INITIAL equation residuals (not linear solve residuals).

    Values are not mixed across iterations. Multiple solves in the final block
    are reported separately; taking their maximum is an audit warning, not a
    reimplementation of a solver's convergence algorithm.
    """
    blocks = list(re.finditer(r'^Time = ([^\s]+)\s*$', log, re.M))
    if not blocks:
        raise ValueError('Native iteration evidence missing')
    final = log[blocks[-1].end():]
    number = float(blocks[-1][1])
    if not math.isfinite(number) or number <= 0:
        raise ValueError('Invalid native iteration')
    residuals = {}
    for field, initial, linear_final in re.findall(
            r'^.*?Solving for ([A-Za-z][A-Za-z0-9_]*), Initial residual = ([^,\s]+), '
            r'Final residual = ([^,\s]+)', final, re.M):
        pair = {'initial': float(initial), 'linear_final': float(linear_final)}
        if any(not math.isfinite(v) or v < 0 for v in pair.values()):
            raise ValueError('Invalid native residual')
        residuals.setdefault(field, []).append(pair)
    exceeded = {field: {'limit': bound, 'max_initial': max(v['initial'] for v in residuals[field])}
                for field, bound in limits.items() if field in residuals
                and max(v['initial'] for v in residuals[field]) > bound}
    missing = sorted(set(limits)-set(residuals))
    messages = re.findall(r'^SIMPLE solution converged in [^\n]+$', log, re.M)
    return {'final_iteration': number, 'last_iteration_residuals': residuals,
            'declared_limits_exceeded': exceeded, 'missing_residual_fields': missing,
            'solver_convergence_messages': messages,
            'free_mesh_reference_qualified': False,
            'reason': 'steady_reference_not_established' if exceeded or missing or not messages
                      else 'convergence_signal_only_mesh_and_physical_controls_still_required'}


def audit(project):
    project = Path(project)
    rows = {}
    for task in ('s-202', 's-204'):
        source_path = project/'tasks'/task/'solution/source'/(task+'.json')
        inputs = json.loads(source_path.read_text())['active_inputs']
        relative = 'runs/fable-edge-originals-002/'+task+'/result.json'
        raw = (project/relative).read_bytes()
        native = check_receipt(json.loads(raw), inputs)
        log = native['artifacts'].get('solver.log')
        if not isinstance(log, str) or not log:
            raise ValueError('Solver log missing')
        row = {'source': relative, 'source_sha256': hashlib.sha256(raw).hexdigest(),
               'input_hash': fingerprint(inputs), 'receipt_and_artifacts_verified': True,
               'native_verdict': native.get('verdict'), 'native_reason': native.get('reason'),
               'free_mesh_reference_qualified': False}
        if task == 's-204':
            row.update(steady_evidence(log, {'p_rgh': 1e-4, 'h': 1e-4, 'k': 1e-3, 'omega': 1e-3}))
            row['limitations'] = ['U equation residual not covered by this narrow audit',
                                   'No heat balance or mesh convergence qualification']
        else:
            times = re.findall(r'^Time = ([^\s]+)\s*$', log, re.M)
            row['final_time'] = float(times[-1]) if times else None
            row['reason'] = 'transient_execution_only_no_free_mesh_heat_balance_qualification'
        rows[task] = row
    return {'version': 'free-mesh-source-audit-v1', 'tasks': rows,
            'model_requests_sent': 0, 'native_jobs_started': 0, 'paid_ready': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, help='New evidence file; refuses overwrite')
    args = parser.parse_args()
    value = audit(args.project)
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as handle:
            handle.write(text)
    print(text, end='')


if __name__ == '__main__':
    main()
