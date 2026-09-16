"""Author-only flow mesh study. Real OpenFOAM, zero model/API requests.

One native operation at a time; a restart observes the same durable operation.
The full source snapshot, inputs, recipe and policy are saved before execution.
Failures and inconclusive controls remain visible; this never publishes tasks.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from agentcfd_bench.free_mesh_flow import (
    VERSION, TASKS, snapshot, compare, proposed_policy, probe_points,
    flux_observations, scalar_balance, FlowAcceptance, observations as complete_observations,
)
from agentcfd_bench.free_mesh_flow_reference import AuthorFlowTask, fabricate_measurements, public_materials
from agentcfd_bench.identity import fingerprint
from agentcfd_bench.journal import NativeJournal
from agentcfd_bench.runtime import cluster_service
from run_codex_science import ObserveNative


def emit(kind, **row):
    print(json.dumps({'time': datetime.now(timezone.utc).isoformat(), 'kind': kind,
                      **row}, ensure_ascii=False), flush=True)


def prepare(task_id, output, *, native=False, seconds=1800, selected=None, numerics='original'):
    task = AuthorFlowTask(task_id, numerics=numerics)
    root = Path(output)/task_id
    journal = NativeJournal(root)
    plan = {'version': VERSION, 'task': task.binding, 'config': task.config,
            'profile': task.profile, 'policy': proposed_policy(task.profile),
            'fixed_probe_points_m': probe_points(task_id),
            'controls': {name: fingerprint(files) for name, files in task.controls.items()},
            'native_seconds_limit': seconds, 'model_calls': 0, 'paid_ready': False}
    if journal.read('plan') is None:
        package = Path(__file__).resolve().parents[1]
        source = {path.relative_to(package).as_posix(): path.read_text()
                  for base in (package/'agentcfd_bench', package/'ci_checks')
                  for path in sorted(base.rglob('*.py')) if '__pycache__' not in path.parts}
        journal.write('source-snapshot', {'source': source, 'hash': fingerprint(source)})
        journal.write('plan', plan)
        journal.write('control-inputs', task.controls)
    elif journal.read('plan') != plan or journal.read('control-inputs') != task.controls:
        raise ValueError('Author inputs/recipe/policy changed: use a new immutable evidence directory')
    if not native:
        emit('flow_prepared', task=task_id, controls=list(task.controls), model_calls=0)
        return {'prepared': True, 'paid_ready': False}
    service = ObserveNative(cluster_service(root/'native', task=task, author_seconds=seconds))
    outcomes = {}
    for index, (name, files) in enumerate(task.controls.items(), 1):
        if selected and name not in selected:
            continue
        emit('flow_control_started', task=task_id, control=name, run_id=f'r-{index:06d}',
             input_hash=fingerprint(files), model_calls=0)
        result = service.execute(f'r-{index:06d}', files, seconds)
        observed = None
        error = None
        if result['verdict'] == 'pass':
            try:
                observed = snapshot(result['artifacts'], task.profile)
            except (ValueError, KeyError, RuntimeError) as exc:
                error = {'type': type(exc).__name__, 'message': str(exc)}
        row = {'control': name, 'native_verdict': result['verdict'],
               'stage': result['stage'], 'reason': result['reason'],
               'native_seconds': result['native_seconds'], 'result_hash': fingerprint(result),
               'input_hash': fingerprint(files), 'observation': observed, 'observation_error': error}
        prior = journal.read('observation-'+name)
        if prior is None:
            journal.write('observation-'+name, row)
        elif prior != row:
            raise ValueError('Observation changed; retain original and audit with an explicit new analysis version')
        outcomes[name] = row
        emit('flow_control_completed', task=task_id, control=name, native_verdict=result['verdict'],
             stage=result['stage'], native_seconds=result['native_seconds'],
             observed_cells=observed['cell_count'] if observed else None,
             steady_converged=observed['steady_converged'] if observed else None,
             last_residual=observed['max_last_initial_residual'] if observed else None,
             observation_error=error)
    return outcomes


def supplemental_phi(output, task_id):
    """Explicit offline import from an already completed trusted author download.

    Historical artifact allowlists omitted phi although OpenFOAM wrote it. This
    records those extra raw bytes and their provenance without rerunning a solve
    or overwriting the original native result. Only a completed/released native
    operation may supply the supplement. New studies register phi at launch.
    """
    root = Path(output)/task_id
    journal = NativeJournal(root)
    plan = journal.read('plan')
    controls = journal.read('control-inputs')
    if not plan or not controls:
        raise ValueError('Author source receipts are missing')
    from agentcfd_bench.journal import read_receipt
    result = {}
    for index, name in enumerate(controls, 1):
        # JSON encoding sorts dictionary keys. Resolve the run by input hash,
        # never assume the serialized key order equals dispatch order.
        matches = []
        for path in sorted((root/'native/runs').glob('r-*')):
            native = read_receipt(path/'result.json')
            if native and native['input_hash'] == fingerprint(controls[name]):
                matches.append((path, native))
        if len(matches) != 1 or matches[0][1]['verdict'] != 'pass':
            continue
        run, native = matches[0]
        if read_receipt(run/'released.json') != {'released': True}:
            raise ValueError('Cannot import artifacts from an unresolved native operation')
        handle = read_receipt(run/'handle.json')
        import re
        if not re.fullmatch(r'[a-f0-9]{32,64}', handle['operation_id']):
            raise ValueError('Unsafe native download handle')
        download = root/'native/transport'/handle['operation_id']/'download'
        from agentcfd_bench.runtime import sanitized
        verified = {}
        for path, content in native['artifacts'].items():
            if path.endswith('.log'):
                continue
            file = download/path
            if (file.is_symlink() or file.parent.is_symlink() or not file.is_file()
                    or sanitized(file.read_text()) != content):
                raise ValueError('Downloaded native fields disagree with original committed evidence: '+path)
            verified[path] = fingerprint(content)
        integrity = {'source_result_hash': fingerprint(native),
                     'source_artifact_hash': native['artifact_hash'],
                     'downloaded_original_fields_verified': verified,
                     'all_original_field_bytes_match': True}
        prior_integrity = journal.read('supplemental-integrity-'+name)
        if prior_integrity is None:
            journal.write('supplemental-integrity-'+name, integrity)
        elif prior_integrity != integrity:
            raise ValueError('Native download integrity record changed')
        extra = {}
        for file in sorted(download.glob('*/phi')):
            if (file.is_symlink() or file.parent.is_symlink() or not file.is_file()
                    or file.stat().st_size > 16*1024*1024):
                raise ValueError('Unsafe native supplemental artifact')
            if re.fullmatch(r'[0-9.eE+\-]+', file.parent.name):
                extra[file.relative_to(download).as_posix()] = file.read_text()
        if not extra:
            raise ValueError('Completed native download contains no phi')
        receipt = {'purpose': 'offline_author_native_phi_import_not_a_new_execution',
                   'source_run': str(run), 'source_result_hash': fingerprint(native),
                   'source_artifact_hash': native['artifact_hash'],
                   'source_operation_id': handle['operation_id'], 'artifacts': extra,
                   'artifact_hash': fingerprint(extra)}
        old = journal.read('supplemental-phi-'+name)
        if old is None:
            journal.write('supplemental-phi-'+name, receipt)
        elif old != receipt:
            raise ValueError('Native supplemental evidence changed')
        result[name] = receipt
    return result


def recorded_native(root, files):
    from agentcfd_bench.journal import read_receipt
    found = [row for path in sorted((Path(root)/'native/runs').glob('r-*/result.json'))
             if (row := read_receipt(path)) and row['input_hash'] == fingerprint(files)]
    if len(found) != 1:
        return None
    return found[0]


def supplemental_mesh(output, task_id):
    """Import retained generated topology from completed/released native runs.

    This is separately bound evidence, not a rewritten native artifact record.
    The complete current mesh allowlist is recorded, including owner/neighbour.
    """
    from agentcfd_bench.journal import read_receipt
    from agentcfd_bench.runtime import sanitized
    root = Path(output)/task_id
    journal = NativeJournal(root)
    controls = journal.read('control-inputs')
    written = {}
    for name, files in controls.items():
        native = recorded_native(root, files)
        if not native or native['verdict'] != 'pass':
            continue
        runs = [path for path in (root/'native/runs').glob('r-*')
                if (row := read_receipt(path/'result.json')) and fingerprint(row) == fingerprint(native)]
        if len(runs) != 1:
            raise ValueError('Supplement requires one exact original native result')
        run = runs[0]
        if read_receipt(run/'released.json') != {'released': True}:
            raise ValueError('Supplement requires completed resource release')
        handle = read_receipt(run/'handle.json')
        download = root/'native/transport'/handle['operation_id']/'download'
        verified = {}
        for path, content in native['artifacts'].items():
            if path.endswith('.log'):
                continue
            actual = ('constant/polyMesh/'+path[5:]) if path.startswith('mesh/') else path
            source = download/actual
            if source.is_symlink() or source.parent.is_symlink() or not source.is_file() or sanitized(source.read_text()) != content:
                raise ValueError('Retained native download disagrees with original artifact: '+path)
            verified[path] = fingerprint(content)
        extra = {}
        for item in ('points', 'faces', 'boundary', 'owner', 'neighbour'):
            source = download/'constant/polyMesh'/item
            if source.is_symlink() or source.parent.is_symlink() or not source.is_file() or source.stat().st_size > 16*1024*1024:
                raise ValueError('Missing/unsafe retained generated mesh: '+item)
            extra['mesh/'+item] = source.read_text()
        evidence = {'purpose': 'offline_completed_author_mesh_import_not_a_new_execution',
                    'source_run': str(run), 'source_result_hash': fingerprint(native),
                    'source_artifact_hash': native['artifact_hash'],
                    'source_operation_id': handle['operation_id'],
                    'downloaded_original_fields_verified': verified,
                    'all_original_field_bytes_match': True,
                    'artifacts': extra, 'artifact_hash': fingerprint(extra)}
        prior = journal.read('supplemental-mesh-'+name)
        if prior is None:
            journal.write('supplemental-mesh-'+name, evidence)
        elif prior != evidence:
            raise ValueError('Generated-mesh supplement cannot overwrite prior evidence')
        written[name] = fingerprint(evidence)
    return written


def author_view(journal, name, native):
    """Compose an explicit derived view while keeping the original result bound."""
    source_hash = fingerprint(native)
    artifacts = dict(native['artifacts'])
    supplements = []
    for kind in ('phi', 'mesh'):
        extra = journal.read('supplemental-'+kind+'-'+name)
        if not extra:
            continue
        if extra['source_result_hash'] != source_hash or extra['source_artifact_hash'] != native['artifact_hash']:
            raise ValueError('Supplement belongs to another native result')
        if fingerprint(extra['artifacts']) != extra['artifact_hash']:
            raise ValueError('Supplement artifact evidence changed')
        integrity = journal.read('supplemental-integrity-'+name) if kind == 'phi' else extra
        if not integrity or integrity['source_result_hash'] != source_hash or integrity['all_original_field_bytes_match'] is not True:
            raise ValueError('Supplement lacks original-field integrity verification')
        for path, content in extra['artifacts'].items():
            if path in artifacts and artifacts[path] != content:
                raise ValueError('Supplement attempts to change existing native artifact')
            artifacts[path] = content
        supplements.append('supplemental-'+kind+'-'+name)
    return ({**native, 'source_native_result_hash': source_hash,
             'author_supplements': supplements, 'artifacts': artifacts,
             'artifact_hash': fingerprint(artifacts)} if supplements else native)


def export_resolved_mesh_materials(task_id, evidence, destination, *, numerics='original'):
    """Freeze a NEW author-review version after two resolved meshes qualify.

    The original preregistered three-positive-mesh study is preserved, including
    a rejected coarse mesh. This explicitly different review is not rewritten as
    an original all-positive outcome and never registers/launches a scored task.
    """
    task = AuthorFlowTask(task_id, numerics=numerics)
    journal = NativeJournal(Path(evidence)/task_id)
    rows = assess(task_id, evidence, numerics=numerics)
    required = ('missing_velocity_rejected', 'medium_fine_mesh_agreement',
                'wrong_physics_runs_but_fails_observations',
                'independent_mass_conservation_qualified', 'forged_report_rejected')
    required += ('three_meshes_residual_converged',) if task.profile['physics']['time']['kind'] == 'steady' else (
        'time_refinement_agreement',)
    if task_id == 's-105':
        required += ('scalar_source_diffusion_storage_balance_qualified',)
    if not all(rows['checks'].get(name) is True for name in required):
        raise ValueError('Author controls do not yet support a resolved-mesh release candidate')
    controls = journal.read('control-inputs')
    native = recorded_native(journal.root, controls['fine'])
    native = author_view(journal, 'fine', native)
    complete, conservation = complete_observations(native['artifacts'], task.profile)
    qualification = {'version': 'resolved-two-mesh-author-review-v2',
        'basis': 'fine_primary_medium_independent_coarse_failure_preserved',
        'source_original_assessment': rows,
        'required_checks': list(required), 'passed': True, 'paid_ready': False,
        'coarse_study_retained': True, 'coarse_accepted': rows['checks']['coarse_mesh_also_accepted'],
        'reference_result_hash': fingerprint(native),
        'source_native_result_hash': native.get('source_native_result_hash', fingerprint(native)),
        'policy_unchanged': proposed_policy(task.profile), 'native_model_requests': 0}
    baseline = {'version': VERSION, 'profile_hash': fingerprint(task.profile), 'qualified': True,
                'snapshot': complete, 'conservation': conservation, 'qualification': qualification}
    acceptance = FlowAcceptance(task.profile, task.reference_mesh, baseline)
    evaluation = acceptance.evaluate({'measurements': acceptance.extract(native['artifacts'])}, native)
    if evaluation['verdict'] != 'pass':
        raise ValueError('Frozen fine reference does not pass the actual current acceptance implementation')
    files = public_materials(task.profile, baseline)
    recommended = json.loads(json.dumps(task.config))
    recommended['metadata']['native_mesh_geometry'] = True
    for name, value in (
        ('solution/profile.json', task.profile), ('solution/baseline.json', baseline),
        ('solution/reference-inputs.json', controls['fine']), ('solution/control-inputs.json', controls),
        ('environment/acceptance-policy.json', proposed_policy(task.profile)),
        ('author-qualification.json', qualification), ('recommended-native-config.json', recommended)):
        files[name] = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)+'\n'
    files['tests/acceptance.py'] = '''from pathlib import Path
from agentcfd_bench.free_mesh_flow import create
_acceptance = create(Path(__file__).resolve().parents[1])
safety_inputs = _acceptance.safety_inputs
physics_contract = _acceptance.physics_contract
parse_action = _acceptance.parse_action
extract = _acceptance.extract
evaluate = _acceptance.evaluate
validate_measurements = _acceptance.validate_measurements
'''
    files['solution/reference.py'] = '''import json
from pathlib import Path
from agentcfd_bench.free_mesh_flow_reference import fabricate_measurements
ROOT = Path(__file__).resolve().parent
def _read(): return json.loads((ROOT/'control-inputs.json').read_text())
def reference_files(): return _read()['fine']
def alternative_mesh(): return _read()['medium']
def qualification_controls():
    rows = _read()
    return {'valid': rows['fine'], 'invalid': rows['missing_velocity'],
            'wrong_physics': rows['wrong_physics'], 'invalid_stage': 'startup'}
'''
    candidate = Path(__file__).resolve().parents[1]/'tasks/releases/free-mesh-v1'/task_id
    for path in sorted((candidate/'geometry').glob('*')):
        if path.is_file():
            files[path.relative_to(candidate).as_posix()] = path.read_text()
    target = Path(destination)/task_id
    target.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        path = target/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as output:
            output.write(content)
    return {'path': str(target), 'author_qualified': True, 'paid_ready': False,
            'files_hash': fingerprint(files), 'task_id': task_id}


def assess(task_id, output, *, numerics='original'):
    """Read receipts only: never run a missing native control during reporting."""
    from types import SimpleNamespace
    from agentcfd_bench.journal import read_receipt
    task = AuthorFlowTask(task_id, numerics=numerics)
    report_root = Path(output)/task_id
    journal = SimpleNamespace(root=report_root,
        read=lambda name: read_receipt(report_root/(name+'.json')))
    saved = {name: journal.read('observation-'+name) for name in task.controls}
    observations = {name: row['observation'] if row else None for name, row in saved.items()}
    checks = {'all_three_meshes_completed': all(observations[n] for n in ('coarse', 'medium', 'fine')),
              'missing_velocity_rejected': bool(saved['missing_velocity']
                    and saved['missing_velocity']['native_verdict'] == 'fail'
                    and saved['missing_velocity']['stage'] == 'startup')}
    distances = {}
    if observations['fine']:
        for name in ('coarse', 'medium', 'wrong_physics', 'half_time_step'):
            if observations.get(name):
                distances[name] = compare(observations[name], observations['fine'], task.profile)
    checks['medium_fine_mesh_agreement'] = bool(distances.get('medium')) and all(
        row['relative_rms'] <= row['limit_rms']*.5 and row['relative_max'] <= row['limit_max']*.5
        for row in distances.get('medium', {}).values())
    checks['coarse_mesh_also_accepted'] = bool(distances.get('coarse')) and all(
        row['passed'] for row in distances.get('coarse', {}).values())
    checks['wrong_physics_runs_but_fails_observations'] = bool(distances.get('wrong_physics')) and any(
        not row['passed'] for row in distances.get('wrong_physics', {}).values())
    if task.profile['physics']['time']['kind'] == 'steady':
        checks['three_meshes_residual_converged'] = all(observations[n]
            and observations[n]['steady_converged'] and observations[n]['max_last_initial_residual'] <= 1e-5
            for n in ('coarse', 'medium', 'fine'))
    else:
        temporal = (compare(observations['half_time_step'], observations['medium'], task.profile)
                    if observations.get('half_time_step') and observations['medium'] else {})
        distances['time_refinement_vs_medium'] = temporal
        checks['time_refinement_agreement'] = bool(temporal) and all(
            row['relative_rms'] <= row['limit_rms']*.5 and row['relative_max'] <= row['limit_max']*.5
            for row in temporal.values())
    conservation = {}
    native_rows = {}
    original_inputs = journal.read('control-inputs') or {}
    for name, observed in observations.items():
        if not observed or name not in original_inputs:
            continue
        native = recorded_native(journal.root, original_inputs[name])
        if not native:
            continue
        native = author_view(journal, name, native)
        native_rows[name] = native
        try:
            flux = flux_observations(native['artifacts'], task.profile, observed['end'])
            if task_id == 's-105':
                flux['scalar_balance'] = scalar_balance(native['artifacts'], task.profile,
                                                         observed['end'], observed, flux)
                flux['scalar_balance_complete'] = True
                flux.pop('scalar_balance_missing_terms', None)
            conservation[name] = flux
        except (ValueError, KeyError) as exc:
            conservation[name] = {'error': str(exc)}
    checks['independent_mass_conservation_qualified'] = all(
        conservation.get(name, {}).get('mass_closed') is True for name in ('coarse', 'medium', 'fine'))
    if task_id == 's-105':
        checks['scalar_source_diffusion_storage_balance_qualified'] = all(
            conservation.get(name, {}).get('scalar_balance', {}).get('balance_closed') is True
            for name in ('coarse', 'medium', 'fine'))
    checks['forged_report_rejected'] = False
    if observations['fine'] and 'fine' in native_rows:
        # This unpublished in-memory baseline exists ONLY for the author forgery
        # control; author_mesh_study_passed/paid_ready remain independent gates.
        try:
            complete, _ = complete_observations(native_rows['fine']['artifacts'], task.profile)
            baseline = {'profile_hash': fingerprint(task.profile), 'version': VERSION,
                        'qualified': True, 'snapshot': complete}
            acceptance = FlowAcceptance(task.profile, task.reference_mesh, baseline)
            forged = acceptance.evaluate({'measurements': fabricate_measurements(
                complete['measurements'])}, native_rows['fine'])
            checks['forged_report_rejected'] = forged['checks']['report_matches_artifacts'] is False
        except (ValueError, KeyError, RuntimeError):
            pass
    return {'task_id': task_id, 'version': VERSION, 'paid_ready': False,
            'author_mesh_study_passed': all(checks.values()), 'checks': checks,
            'distances': distances, 'conservation': conservation,
            'controls': {name: ({k: v for k, v in row.items() if k != 'observation'}
                        | {'cell_count': row['observation']['cell_count'] if row['observation'] else None})
                        if row else None for name, row in saved.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks', nargs='+', choices=TASKS, default=list(TASKS))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--seconds', type=int, default=1800)
    parser.add_argument('--controls', nargs='+')
    parser.add_argument('--numerics', choices=('original', 'stable-v2', 'aligned-v3', 'linear-tight-v4'), default='original')
    parser.add_argument('--report', action='store_true')
    parser.add_argument('--import-completed-phi', action='store_true')
    parser.add_argument('--import-completed-mesh', action='store_true')
    parser.add_argument('--export-materials', type=Path)
    args = parser.parse_args()
    for task in args.tasks:
        if args.import_completed_phi:
            supplemental_phi(args.output, task)
        if args.import_completed_mesh:
            supplemental_mesh(args.output, task)
        if not args.report:
            prepare(task, args.output, native=args.native, seconds=args.seconds, selected=args.controls,
                    numerics=args.numerics)
        result = assess(task, args.output, numerics=args.numerics)
        emit('flow_author_assessment', **result)
        if args.export_materials:
            emit('flow_materials_exported', **export_resolved_mesh_materials(
                task, args.output, args.export_materials, numerics=args.numerics))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
