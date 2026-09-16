"""Author-only isolated thermal mesh/physics studies, zero model calls.

This writes evidence, not a paid-ready flag or a released task. Completed native
operations are reclaimed by their existing journal; unknown starts are observed.
"""
import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

from agentcfd_bench.edge_tasks import observe
from agentcfd_bench.execution_spec import EDGE_RECIPES, EDGE_REGIONS, ExecutionSpec
from agentcfd_bench.free_mesh_thermal_reference import controls
from agentcfd_bench.free_mesh_thermal import CRITERIA
from agentcfd_bench.identity import fingerprint
from agentcfd_bench.journal import NativeJournal, read_receipt
from agentcfd_bench.runtime import cluster_service
from agentcfd_bench.task_package import load_task


def summarize_recorded(task_root, output):
    """Read completed native evidence; no SSH, solver, requests or hidden retries."""
    from agentcfd_bench.author_evidence import completed_operation
    from agentcfd_bench.free_mesh_thermal import (snapshot, wall_heat_observations, compare_spatial,
        conjugate_energy_balance,thermal_transport_balance)
    task_root=Path(task_root);task_id=task_root.name
    if task_id not in ('s-202','s-203'):
        raise ValueError('Summary root must name the thermal task')
    journal=NativeJournal(output);rows=[];spatial={}
    for root in sorted(task_root.iterdir()):
        native=root/'native/runs/r-000001'
        if not native.is_dir():
            continue
        if not (native/'result.json').is_file():
            rows.append({'control':root.name,'lifecycle':'running','verdict':'not_evaluated'})
            continue
        evidence=completed_operation(native)
        n=evidence['native_result'];artifacts=dict(n['artifacts'])
        row={'control':root.name,'lifecycle':'completed','native_verdict':n['verdict'],
             'native_stage':n['stage'],'native_seconds':n['native_seconds'],
             'source_evidence':{k:v for k,v in evidence.items() if k!='native_result'},
             'native_field_hash':fingerprint({k:v for k,v in artifacts.items() if not k.endswith('.log')})}
        # The first C/V-only study predates the public phi export. Its isolated
        # transport downloaded the complete original case. Import these files
        # into a NEW author analysis record, never mutate the old native result.
        supplements={}
        end='100' if task_id=='s-202' else '1.5'
        for name in ([r+'/phi' for r in EDGE_REGIONS[:2]] if task_id=='s-202' else ['phi']):
            key=end+'/'+name
            if key in artifacts:
                continue
            candidates=list(root.glob('native/transport/*/download/'+key))
            if len(candidates)==1 and candidates[0].is_file() and not candidates[0].is_symlink():
                text=candidates[0].read_text()
                artifacts[key]=text
                supplements[key]={'source':str(candidates[0]),'content_hash':fingerprint(text)}
        row['supplemental_author_downloads']=supplements
        if n['verdict']=='pass':
            # An author logging error may invalidate the complete observation
            # contract while leaving independently recorded wall-flux evidence
            # useful for diagnosis. Do not fabricate missing pressure residuals.
            if task_id=='s-202':
                try:
                    row['wall_heat']=wall_heat_observations(artifacts)
                except (ValueError,KeyError,TypeError) as exc:
                    row['wall_heat_error']=str(exc)
            try:
                parsed=snapshot(artifacts,task_id)
                row['measurements']=parsed['measurements'];row['fluxes']=parsed['fluxes']
                row['observation_status']='complete'
                spatial[root.name]=parsed['spatial_volumes']
                if any('grad(T)' in name for name in artifacts):
                    try:
                        row['energy_balance']=(conjugate_energy_balance(artifacts,parsed)
                            if task_id=='s-202' else thermal_transport_balance(artifacts,parsed))
                    except (ValueError,KeyError,TypeError) as exc:
                        row['energy_balance']={'passed':False,'evidence_error':str(exc)}
            except Exception as exc:
                row['observation_status']='invalid_or_missing_native_evidence'
                row['observation_error']={'type':type(exc).__name__,'detail':str(exc)}
        else:
            row['native_error_excerpt']=n['log'][-1800:]
        rows.append(row)
    reference=next((name for name in ('mesh_finest','mesh_extra','mesh_fine','mesh_medium','base')
                    if name in spatial),None)
    comparisons={name:compare_spatial(value,spatial[reference]) for name,value in spatial.items()} if reference else {}
    report={'schema':'thermal-author-review-v1','task_id':task_id,'rows':rows,
        'spatial_reference_for_diagnostics_only':reference,'private_spatial_comparisons':comparisons,
        'paid_ready':False,'model_requests':0,
        'qualification_status':'Review convergence and energy evidence; native pass is not physical acceptance.'}
    if journal.read('summary') is not None:
        if journal.read('summary')!=report:
            raise ValueError('Analysis evidence changed; write a new summary output version')
    else:
        journal.write('summary',report)
    print(json.dumps({'kind':'author_review_written','output':str(output),'rows':len(rows),
                      'paid_ready':False,'model_requests':0}),flush=True)
    return report


class ThermalAuthorTask:
    """Exact byte-bound author control. This route cannot accept agent files."""
    def __init__(self, task_id, files, root, *, heat_flux=False, energy=False):
        old = load_task(task_id)
        self.root = Path(root)
        self.files = files
        self.identity = {'id': task_id, 'version': 'author-free-mesh-thermal-v1',
                         'runtime': '1b8daf015bedab9fc337a623e8516c81f805d69a53a6e58436c46fb3053b5bd1'}
        self.config = copy.deepcopy(old.config)
        self.config['metadata']['version'] = self.identity['version']
        self.config['metadata']['runtime'] = self.identity['runtime']
        regions = EDGE_REGIONS if task_id == 's-202' else ()
        # Full CHT energy always includes the native wall-flux artifacts.
        heat_flux=heat_flux or (energy and bool(regions))
        fields = list(old.execution.fields)
        for region in regions or ('',):
            for field in ('C','V'):
                fields.append((region+'/' if region else '')+field)
            if heat_flux and region:
                fields.append(region+'/wallHeatFlux')
            if region in ('', 'bottomWater', 'topAir'):
                fields.append((region+'/' if region else '')+'phi')
            if energy and region in ('bottomWater','topAir'):
                fields.append(region+'/grad(T)')
        if energy and task_id=='s-203':
            for name in ('U','T'):
                fields.append('grad('+name+')')
        # New author operations use exactly the published command ordering and
        # stage names. Historical fixtures remain bound to their saved specs;
        # --resume-recorded reconstructs those bytes without relabelling them.
        recipe=('free-mesh-multiregion-energy-v1' if energy else
                'free-mesh-multiregion-heat-v1' if heat_flux else
                'free-mesh-multiregion-v1') if regions else (
                'free-mesh-thermal-energy-v1' if energy else
                'free-mesh-thermal-transport-v1')
        commands=list(EDGE_RECIPES[recipe])
        self.config['metadata']['edge_recipe']=recipe
        self.execution = ExecutionSpec(tuple(commands), 'transient',
            100 if regions else 1.5, 1e-7, False, tuple(fields), 300, tuple(regions), True)
        self.config['metadata']['native_commands'] = [[k,*v] for k,v in commands]
        self.config['metadata']['artifact_fields'] = fields
        self.config['metadata']['native_mesh_geometry'] = True

    @property
    def binding(self):
        return {**self.identity, 'digest': fingerprint(self.files),
                'config_hash': fingerprint(self.config)}

    def acceptance(self):
        def safety(files):
            from agentcfd_bench.foam.inputs import validate_files
            validate_files(files)
            if fingerprint(files) != fingerprint(self.files):
                raise ValueError('Author control bytes changed')
        return SimpleNamespace(safety_inputs=safety,
            physics_contract=lambda files: {'passed': True,
                'reason': 'author_execution_only_not_model_acceptance'})


def resume_recorded(root):
    """Finish exactly one recorded operation; never advance the old batch."""
    root=Path(root)
    journal=NativeJournal(root)
    outer=journal.read('spec')
    config=journal.read('author_config')
    files=journal.read('author_inputs')
    native_spec=read_receipt(root/'native/runs/r-000001/spec.json')
    if any(item is None for item in (outer,config,files,native_spec)):
        raise ValueError('Recorded author control is incomplete; cannot reconstruct or guess')
    identity=outer['task']
    if (not identity['version'].startswith('author-free-mesh-thermal-')
            or native_spec['task']!=identity or fingerprint(files)!=native_spec['input_hash']
            or fingerprint(config)!=identity['config_hash']):
        raise ValueError('Recorded author provenance differs')
    meta=config['metadata']; timing=meta['native_completion']
    commands=tuple((label,tuple(argv)) for label,argv in native_spec['commands'])
    regions=EDGE_REGIONS if identity['id']=='s-202' else ()
    execution=ExecutionSpec(commands,timing['kind'],timing['end'],timing['tolerance'],
        timing['early_convergence'],tuple(meta['artifact_fields']),300,regions,
        meta.get('native_mesh_geometry',False))
    def safety(submitted):
        if submitted!=files:
            raise ValueError('Recorded author control bytes changed')
    task=SimpleNamespace(root=root,identity={k:identity[k] for k in ('id','version','runtime')},
        binding=identity,config=config,execution=execution,
        acceptance=lambda:SimpleNamespace(safety_inputs=safety,
            physics_contract=lambda submitted:{'passed':True,'reason':'author_execution_only_not_model_acceptance'}))
    print(json.dumps({'kind':'recover_one_recorded_operation','root':str(root),
        'model_requests':0,'will_advance_old_batch':False}),flush=True)
    result=observe(cluster_service(root/'native',task=task,author_seconds=outer['seconds']),
                   'r-000001',files,outer['seconds'])
    if journal.read('result') is None:
        journal.write('result',result)
    print(json.dumps({'kind':'recorded_operation_reclaimed','verdict':result['verdict'],
                      'stage':result['stage'],'native_seconds':result['native_seconds']}),flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=('s-202','s-203'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--resume-recorded',type=Path,
                        help='Observe/finish one frozen author operation, do not continue its batch')
    parser.add_argument('--summarize-recorded',type=Path,
                        help='Read-only author review of a completed task study; --output is new report directory')
    parser.add_argument('--controls', nargs='+', default=['base','mesh_medium','mesh_fine',
        'time_refined','wrong_physics','no_heating','missing_field'])
    parser.add_argument('--seconds', type=int, default=1800)
    parser.add_argument('--heat-flux', action='store_true')
    parser.add_argument('--energy', action='store_true')
    parser.add_argument('--execute-native', action='store_true')
    args = parser.parse_args()
    if args.summarize_recorded:
        if not args.output:
            parser.error('--output is required for a new read-only report')
        summarize_recorded(args.summarize_recorded,args.output)
        return 0
    if not args.execute_native:
        parser.error('Explicit --execute-native required; no models are called')
    if args.resume_recorded:
        return int(resume_recorded(args.resume_recorded)['verdict']=='error')
    if not args.task or not args.output:
        parser.error('--task and --output are required for a new study')
    fixtures = controls(args.task, extended=True)
    if any(name not in fixtures for name in args.controls):
        parser.error('Unknown control')
    summary = []
    for name in args.controls:
        root = args.output/args.task/name
        task = ThermalAuthorTask(args.task, fixtures[name], root, heat_flux=args.heat_flux, energy=args.energy)
        journal = NativeJournal(root)
        spec = {'task': task.binding, 'seconds': args.seconds, 'model_requests': 0}
        if journal.read('spec') is None:
            journal.write('spec', spec)
        if journal.read('spec') != spec:
            raise ValueError('Frozen author operation changed; use a new output path')
        if journal.read('author_inputs') is None:
            journal.write('author_inputs', fixtures[name])
            journal.write('author_config', task.config)
            journal.write('proposed_criteria', CRITERIA)
        print(json.dumps({'kind':'author_control_started','task':args.task,'control':name,
                          'model_requests':0}), flush=True)
        try:
            service = cluster_service(root/'native', task=task, author_seconds=args.seconds)
            result = observe(service, 'r-000001', fixtures[name], args.seconds)
            if journal.read('result') is None:
                journal.write('result', result)
            row = {'task':args.task, 'control':name, 'verdict':result['verdict'],
                   'stage':result['stage'], 'reason':result['reason'],
                   'native_seconds':result['native_seconds'],
                   'artifact_hash':result['artifact_hash']}
        except Exception as exc:
            row = {'task':args.task, 'control':name, 'verdict':'error',
                   'type':type(exc).__name__, 'detail':str(exc)}
            # Do not fabricate a result for an unresolved operation. The next
            # explicit invocation will observe the same durable service journal.
        summary.append(row)
        print(json.dumps({'kind':'author_control_finished', **row}, ensure_ascii=False), flush=True)
    print(json.dumps({'kind':'author_study_finished','rows':summary,'paid_ready':False,
                      'model_requests':0}, ensure_ascii=False), flush=True)
    return int(any(row['verdict']=='error' for row in summary))


if __name__ == '__main__':
    raise SystemExit(main())
