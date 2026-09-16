"""Run immutable author-native controls, never a model or a paid API request.

The output directory owns a private TaskPackage, each input, native journal, and
an independent acceptance receipt. Reusing a directory observes its operations;
it cannot alter or silently re-execute a previously submitted control.
"""
import argparse
import copy
import json
from pathlib import Path
import time

from agentcfd_bench.free_mesh_buoyant_shock_reference import controls
from agentcfd_bench.identity import fingerprint
from agentcfd_bench.journal import NativeJournal,read_receipt
from agentcfd_bench.runtime import cluster_service,Pending
from agentcfd_bench.task_package import load_task,TaskPackage


def write_once(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_text()!=text: raise ValueError('Cannot alter author snapshot: '+str(path))
    else:
        with path.open('x') as out: out.write(text)


def author_task(task_id,output):
    old=load_task(task_id)
    config=copy.deepcopy(old.config)
    from agentcfd_bench.execution_spec import EDGE_RECIPES
    recipe='free-mesh-shock-v1' if task_id=='s-205' else 'free-mesh-buoyant-heat-v1'
    meta=config['metadata']; meta['version']='author-free-mesh-buoyant-shock-v1'
    meta['edge_recipe']=recipe
    meta['native_commands']=[[label,*argv] for label,argv in EDGE_RECIPES[recipe]]
    meta['artifact_fields']=[*meta['artifact_fields'],'C','V']
    if task_id=='s-204':
        meta['artifact_fields'].append('wallHeatFlux')
        meta['native_completion']['end']=6000
    module='free_mesh_shock' if task_id=='s-205' else 'free_mesh_buoyant'
    imported=__import__('agentcfd_bench.'+module,fromlist=['GROUPS'])
    meta['acceptance_groups']=imported.GROUPS
    root=Path(output)/'task-packages'/task_id
    write_once(root/'solution/profile.json',(old.root/'solution/profile.json').read_text())
    write_once(root/'solution/proposed-policy.json',json.dumps(imported.POLICY,indent=2,sort_keys=True)+'\n')
    write_once(root/'solution/grader-source.py',Path(imported.__file__).read_text())
    write_once(root/'solution/control-builder-source.py',
               (Path(__file__).resolve().parents[1]/'agentcfd_bench/free_mesh_buoyant_shock_reference.py').read_text())
    write_once(root/'author-config.json',json.dumps(config,indent=2,sort_keys=True)+'\n')
    wrapper=('from pathlib import Path\nfrom agentcfd_bench.'+module+' import create\n'
             '_a=create(Path(__file__).resolve().parents[1])\n'
             'safety_inputs=_a.safety_inputs\nphysics_contract=_a.physics_contract\n'
             'extract=_a.extract\nparse_action=_a.parse_action\nevaluate=_a.evaluate\n'
             'validate_measurements=_a.validate_measurements\n')
    write_once(root/'tests/acceptance.py',wrapper)
    return TaskPackage(root,config)


def export_shock_candidate(evidence,destination):
    """Offline package proposal, guarded by real controls; never registers it."""
    import hashlib
    from agentcfd_bench import free_mesh_shock as checker
    from agentcfd_bench.free_mesh_buoyant_shock_reference import public_materials,fabricate_measurements
    evidence,destination=Path(evidence),Path(destination)
    old=load_task('s-205'); acceptance=checker.create(old.root)
    inputs=controls('s-205'); rows={}; evaluations={}; checks={}
    for name,files in inputs.items():
        matches=[read_receipt(p) for p in (evidence/'native/runs').glob('r-*/result.json')]
        matches=[row for row in matches if row and row['input_hash']==fingerprint(files)]
        if len(matches)!=1: raise ValueError('Exact completed native control required: '+name)
        native=matches[0]
        if read_receipt(evidence/'native/runs'/native['run_id']/'released.json')!={'released':True}:
            raise ValueError('Native control not released: '+name)
        if native['artifact_hash']!=fingerprint(native['artifacts']): raise ValueError('Changed native evidence')
        rows[name]={'run_id':native['run_id'],'source':str(evidence/'native/runs'/native['run_id']),
                    'input_hash':native['input_hash'],'result_hash':fingerprint(native),
                    'artifact_hash':native['artifact_hash'],'native_verdict':native['verdict']}
        if native['verdict']=='pass':
            measurements=acceptance.extract(native['artifacts'])
            evaluations[name]=acceptance.evaluate({'measurements':measurements},native)
            if name=='mesh_400':
                forged=acceptance.evaluate({'measurements':fabricate_measurements(measurements)},native)
                checks['fabricated_report_rejected']=forged['verdict']=='fail' and not forged['checks']['report_matches_artifacts']
            if name=='wrong_physics':
                # An explicit grader stress test, not a modified native receipt:
                # the numerical checks must reject even if the static gate lies.
                stress={**native,'contract':{'passed':True}}
                verdict=acceptance.evaluate({'measurements':measurements},stress)
                checks['wrong_output_rejected_without_static_gate']=verdict['verdict']=='fail'
        else:
            evaluations[name]={'verdict':'not_evaluated','reason':native['reason']}
    checks['three_distinct_meshes_pass']=all(evaluations[n]['verdict']=='pass' for n in ('valid','mesh_200','mesh_400'))
    checks['wrong_physics_runs_but_fails']=rows['wrong_physics']['native_verdict']=='pass' and evaluations['wrong_physics']['verdict']=='fail'
    checks['missing_velocity_native_rejected']=rows['invalid']['native_verdict']=='fail'
    checks['mesh_error_decreases']=all(evaluations['mesh_400']['private_errors']['normalized_l1'][n]
        <=evaluations['mesh_200']['private_errors']['normalized_l1'][n]
        <=evaluations['valid']['private_errors']['normalized_l1'][n] for n in checker.UNITS)
    if not all(checks.values()): raise ValueError('Author control checks incomplete: '+str(checks))
    meta=copy.deepcopy(old.config['metadata'])
    from agentcfd_bench.execution_spec import EDGE_RECIPES
    meta['version']='free-mesh-v2';meta['edge_recipe']='free-mesh-shock-v1'
    meta['native_commands']=[[label,*argv] for label,argv in EDGE_RECIPES[meta['edge_recipe']]]
    meta['artifact_fields']=[*meta['artifact_fields'],'C','V'];meta['acceptance_groups']=checker.GROUPS
    meta.pop('qualification',None)
    config={'schema_version':'1.4','metadata':meta,'verifier':{'environment_mode':'separate',
                                                               'environment':{'network_mode':'no-network'}}}
    files=public_materials('s-205')
    for name,value in [('solution/profile.json',acceptance.profile),('solution/reference-inputs.json',inputs['mesh_400']),
        ('solution/control-inputs.json',inputs),('environment/acceptance-policy.json',checker.POLICY),
        ('recommended-native-config.json',config),('author-qualification.json',{
            'version':checker.VERSION,'qualified':True,'paid_ready':False,'model_requests':0,
            'checks':checks,'native_controls':rows,'evaluations':evaluations})]:
        files[name]=json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n'
    geometry=Path(__file__).resolve().parents[1]/'tasks/releases/free-mesh-v1/s-205/geometry'
    for path in geometry.iterdir():
        if path.is_file(): files['geometry/'+path.name]=path.read_text()
    files['public-task.json']=json.dumps({'schema':'geometry-public-task-v1',
        'texts':['instruction.md','protocol.md','observations.md'],'assets':{
            n:hashlib.sha256(t.encode()).hexdigest() for n,t in files.items() if n.startswith('geometry/')}},indent=2)+'\n'
    files['tests/acceptance.py']=('from pathlib import Path\nfrom agentcfd_bench.free_mesh_shock import create\n'
        '_a=create(Path(__file__).resolve().parents[1])\n'+''.join(n+'=_a.'+n+'\n' for n in
        ('safety_inputs','physics_contract','extract','parse_action','evaluate','validate_measurements')))
    files['solution/reference.py']=('import json\nfrom pathlib import Path\n'
        'from agentcfd_bench.free_mesh_buoyant_shock_reference import fabricate_measurements\n'
        'def _read(): return json.loads((Path(__file__).resolve().parent/"control-inputs.json").read_text())\n'
        'def reference_files(): return _read()["mesh_400"]\n'
        'def alternative_mesh(): return _read()["mesh_200"]\n'
        'def qualification_controls():\n r=_read()\n return {"valid":r["mesh_400"],"invalid":r["invalid"],'
        '"wrong_physics":r["wrong_physics"],"invalid_stage":"startup"}\n')
    meta_simple={k:v for k,v in meta.items() if not isinstance(v,dict)}
    lines=['schema_version = "1.4"','[metadata]']+[k+' = '+json.dumps(v) for k,v in meta_simple.items()]
    for section in ('native_completion','acceptance_groups'):
        lines+=['[metadata.'+section+']']+[k+' = '+json.dumps(v) for k,v in meta[section].items()]
    lines+=['[verifier]','environment_mode = "separate"','[verifier.environment]','network_mode = "no-network"']
    files['task.toml']='\n'.join(lines)+'\n'
    files['README.md']='# 激波管自由网格候选\n\n作者真实三网格/错误物理/缺文件控制已验证；尚未注册或启动付费评测。\n'
    root=destination/'s-205'
    for name,text in files.items(): write_once(root/name,text)
    from agentcfd_bench.public_task import load
    load(root)
    import tomllib
    task=TaskPackage(root,tomllib.loads((root/'task.toml').read_text()))
    task.execution;task.acceptance();task.reference().qualification_controls()
    return {'path':str(root),'author_qualified':True,'paid_ready':False,'checks':checks,'files_hash':fingerprint(files)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task',choices=['s-204','s-205'],required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--controls',nargs='+',default=None)
    p.add_argument('--seconds',type=int,default=1800)
    p.add_argument('--native',action='store_true')
    p.add_argument('--collect-native-run',help='Recover only this existing run; never register another control')
    p.add_argument('--export-candidate',type=Path,help='Read existing s205 controls and export a complete private candidate; no native execution')
    args=p.parse_args()
    if args.export_candidate:
        if args.task!='s-205': p.error('Only independently qualified shock reference can be exported')
        print(json.dumps(export_shock_candidate(args.output,args.export_candidate),ensure_ascii=False),flush=True)
        return 0
    if not args.native: p.error('--native explicitly required; no model requests are made')
    args.output.mkdir(parents=True,exist_ok=True)
    if args.collect_native_run:
        import re
        if not re.fullmatch(r'r-[0-9]{6}',args.collect_native_run): p.error('Canonical existing run ID required')
        root=args.output/'task-packages'/args.task
        task=TaskPackage(root,json.loads((root/'author-config.json').read_text()))
        runroot=args.output/'native/runs'/args.collect_native_run
        files=read_receipt(runroot/'inputs.json')
        spec=read_receipt(runroot/'spec.json')
        if files is None or spec is None or read_receipt(runroot/'handle.json') is None:
            p.error('Existing input/spec/handle required; no new computation started')
        if spec['seconds']!=args.seconds or spec['task']!=task.binding or spec['input_hash']!=fingerprint(files):
            p.error('Existing run evidence does not match immutable author task/budget')
        collector=NativeJournal(args.output/'collection'/args.collect_native_run)
        collector.write('request',{'run_id':args.collect_native_run,'native_spec_hash':fingerprint(spec),
            'task':task.binding,'model_requests':0,'only_collect_existing':True})
        service=cluster_service(args.output/'native',task=task,author_seconds=args.seconds)
        while True:
            try:
                result=service.execute(args.collect_native_run,files,args.seconds)
                break
            except Pending as exc:
                print(json.dumps({'kind':'collect_existing_pending','reason':str(exc)}),flush=True)
                time.sleep(10)
        collector.write('native-result',result)
        print(json.dumps({'kind':'existing_native_collected','run_id':args.collect_native_run,
                          'native_verdict':result['verdict'],'native_reason':result['reason']}),flush=True)
        return 0
    task=author_task(args.task,args.output)
    service=cluster_service(args.output/'native',task=task,author_seconds=args.seconds)
    registered=controls(args.task)
    selected=args.controls or list(registered)
    if any(n not in registered for n in selected): p.error('Unknown author control')
    manifest={'task':task.binding,'controls':list(registered),'input_hashes':{
        name:fingerprint(files) for name,files in registered.items()},'author_seconds':args.seconds,
        'model_request_count':0,'model_per_run_budget_unchanged':300}
    NativeJournal(args.output/'audit').write('manifest',manifest)
    results={}
    acceptance=task.acceptance()
    for name in selected:
        run_id=f'r-{list(registered).index(name)+1:06d}'
        print(json.dumps({'kind':'native_control_started','task':args.task,'control':name,
                          'run_id':run_id,'model_requests':0}),flush=True)
        while True:
            try:
                native=service.execute(run_id,registered[name],args.seconds)
                break
            except Pending as exc:
                print(json.dumps({'kind':'observe_existing_operation','control':name,'reason':str(exc)}),flush=True)
                time.sleep(10)
        row={'run_id':run_id,'input_hash':native['input_hash'],'native_verdict':native['verdict'],
             'native_reason':native['reason'],'native_seconds':native['native_seconds'],
             'contract':native['contract'],'artifact_hash':native['artifact_hash']}
        if native['verdict']=='pass':
            try:
                measures=acceptance.extract(native['artifacts'])
                action={'action':'report','run_id':run_id,'measurements':measures}
                row['acceptance']=acceptance.evaluate(action,native)
            except (ValueError,RuntimeError) as exc:
                row['acceptance']={'verdict':'error','reason':str(exc),'type':type(exc).__name__}
        NativeJournal(args.output/'evaluation'/name).write('result',row)
        results[name]=row
        print(json.dumps({'kind':'native_control_finished','control':name,**row},ensure_ascii=False),flush=True)
        if args.task=='s-204' and name not in ('invalid','wrong_physics'):
            required=('solver_convergence','residuals','mass_conservation',
                      'wall_energy_balance','adiabatic_walls','stationarity')
            checks=row.get('acceptance',{}).get('checks',{})
            if native['verdict']!='pass' or any(checks.get(key) is not True for key in required):
                remaining=selected[selected.index(name)+1:]
                deferred={'reason':'positive_author_control_not_qualified',
                          'failed_control':name,'not_started':remaining,'model_requests':0}
                NativeJournal(args.output/'audit').write('deferred-controls',deferred)
                print(json.dumps({'kind':'dependent_controls_deferred',**deferred}),flush=True)
                break
    print(json.dumps({'kind':'author_batch_finished','model_requests':0,'controls':{
        k:{'native':v['native_verdict'],'acceptance':v.get('acceptance',{}).get('verdict','not_evaluated')}
        for k,v in results.items()}},ensure_ascii=False),flush=True)
    return 0


if __name__=='__main__': raise SystemExit(main())
