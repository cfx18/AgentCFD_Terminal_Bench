"""Independent local transport worker. Submit once, observe, recover evidence.

Only trusted host code uses SSH. Agent argv is interpreted inside Apptainer.
"""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import tarfile
import time
import uuid

from ..execution.files import inventory
from ..records.store import read, write_once
from .slurm_runner import validate_remote

UPLOAD = r'''
import hashlib,json,os,pathlib,sys,tarfile
root=pathlib.Path(sys.argv[1])
allowed='/public3/home/sca2070/WORK/Caifeixue/AgentCFD_Terminal_Bench/'
if not str(root).startswith(allowed) or not os.path.realpath(str(root)).startswith(allowed): raise ValueError('scope')
root.mkdir(parents=True,exist_ok=False)
archive=root/'upload.tar.gz'
with archive.open('xb') as f:
 while True:
  data=sys.stdin.buffer.read(1048576)
  if not data: break
  f.write(data)
 f.flush(); os.fsync(f.fileno())
with tarfile.open(str(archive),'r:gz') as tar:
 members=tar.getmembers()
 if sum(x.size for x in members)>2147483648+10485760: raise ValueError('transfer too large')
 for m in members:
  p=pathlib.PurePosixPath(m.name)
  if p.is_absolute() or '..' in p.parts or not m.isfile(): raise ValueError('unsafe archive')
 tar.extractall(str(root),members=members)
(root/'case').mkdir(exist_ok=True)
with (root/'uploaded.json').open('x') as f:
 json.dump({'uploaded':True,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},f)
print('uploaded')
'''

SUBMIT = r'''
import fcntl,json,os,pathlib,re,shlex,subprocess,sys
root=pathlib.Path(sys.argv[1]); cfg=json.load(open(str(root/'spec.json')))['remote']
name='acfd-a-'+root.name[2:]
def save(path,value):
 tmp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
 with tmp.open('x') as f: json.dump(value,f); f.flush(); os.fsync(f.fileno())
 os.link(str(tmp),str(path)); tmp.unlink()
with (root/'submit.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 record=root/'slurm-job.json'
 if record.exists(): print(record.read_text()); sys.exit(0)
 if (root/'submit-intent.json').exists():
  candidates=set()
  for argv in (['squeue','--me','-h','-n',name,'-o','%i|%j'],['sacct','-n','-X','--name',name,'-o','JobIDRaw,JobName%64','-P']):
   p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
   for line in p.stdout.splitlines():
    parts=[x.strip() for x in line.split('|')]
    if len(parts)>=2 and parts[0].isdigit() and parts[1]==name: candidates.add(parts[0])
  if len(candidates)!=1: raise RuntimeError('Submission outcome unknown: never resubmit')
  value={'job_id':next(iter(candidates)),'job_name':name,'recovered':True}
 else:
  save(root/'submit-intent.json',{'job_name':name})
  command='exec '+ ' '.join(shlex.quote(x) for x in ['/usr/bin/python3',str(root/'job.py'),str(root)])
  argv=['sbatch','--parsable','--no-requeue','--partition='+cfg['partition'],'--ntasks=1','--cpus-per-task=1',
        '--mem=4096M','--time=0','--job-name='+name,'--chdir='+str(root),
        '--output='+str(root/'slurm-%j.out'),'--error='+str(root/'slurm-%j.err'),'--wrap='+command]
  p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
  job=p.stdout.strip().split(';')[0]
  if p.returncode or not job.isdigit():
   save(root/'submit-rejected.json',{'code':p.returncode,'stderr':p.stderr,'stdout':p.stdout})
   raise RuntimeError('sbatch did not return a valid acceptance receipt: '+p.stderr)
  value={'job_id':job,'job_name':name,'recovered':False}
 save(record,value); print(json.dumps(value))
'''

OBSERVE = r'''
import base64,json,pathlib,subprocess,sys
root=pathlib.Path(sys.argv[1]); offsets=json.loads(sys.argv[2]); result={}
for name in ('exit','result','slurm-job','execution-error'):
 p=root/(name+'.json')
 if p.exists(): result[name]=json.load(p.open())
result['logs']={}
for name,offset in offsets.items():
 p=root/(name+'.log')
 if p.exists():
  with p.open('rb') as f: f.seek(offset); result['logs'][name]=base64.b64encode(f.read(262144)).decode()
if 'result' not in result and 'slurm-job' in result:
 job=result['slurm-job']['job_id']
 p=subprocess.run(['squeue','-h','-j',job,'-o','%T'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
 states=p.stdout.strip().splitlines()
 if not states:
  p=subprocess.run(['sacct','-n','-X','-j',job,'-o','State','-P'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
  states=[x.strip('| ') for x in p.stdout.splitlines() if x.strip('| ')]
 result['scheduler_states']=states
print(json.dumps(result))
'''


def ssh(remote, argv, *, input_file=None, output_file=None, timeout=45):
    command = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
               '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3', remote['host'], shlex.join(argv)]
    result = subprocess.run(command, stdin=input_file, stdout=output_file or subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=timeout)
    if result.returncode:
        raise RuntimeError('SSH control failed (' + str(result.returncode) + '): ' + result.stderr.decode(errors='replace')[-4000:])
    return result.stdout or b''


def progress(root, **value):
    temporary = root / ('progress-' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value))
    temporary.replace(root / 'remote-progress.json')


def unpack_verified(archive, output, result):
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        names = set()
        if sum(m.size for m in members) > 3 * 1024**3:
            raise ValueError('Remote output exceeds transfer safety limit')
        for member in members:
            path = PurePosixPath(member.name)
            if (not member.isfile() or path.is_absolute() or '..' in path.parts or member.name in names
                    or not (member.name.startswith('artifacts/') or member.name in ('stdout.log', 'stderr.log'))):
                raise ValueError('Unsafe or duplicate remote artifact path')
            names.add(member.name)
        expected = {'artifacts/' + key for key in result['artifacts'] if not key.startswith('@')}
        expected |= {'stdout.log', 'stderr.log'}
        if names != expected:
            raise ValueError('Transferred artifact set differs from recorded native result')
        tar.extractall(output, filter='data')
    actual = inventory(output / 'artifacts')
    for name in ('stdout.log', 'stderr.log'):
        actual['@' + name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    if actual != result['artifacts']:
        raise ValueError('Remote native artifact evidence changed')


def run(root):
    root = Path(root).resolve()
    remote = validate_remote(read(root / 'remote-config.json'))
    spec = read(root / 'spec.json')
    destination = remote['root'] + '/' + root.name
    if (root / 'result.json').exists():
        return read(root / 'result.json')
    progress(root, phase='staging_remote_inputs')
    if not (root / 'upload-intent.json').exists():
        payload = root / 'remote-spec.json'
        write_once(payload, {**spec, 'remote': remote})
        bundle = root / 'upload.tar.gz'
        with tarfile.open(bundle, 'w:gz') as tar:
            for name in inventory(root / 'case'):
                tar.add(root / 'case' / name, arcname='case/' + name, recursive=False)
            tar.add(payload, arcname='spec.json', recursive=False)
            tar.add(Path(__file__).with_name('slurm_job.py'), arcname='job.py', recursive=False)
        write_once(root / 'upload-intent.json', {'destination': destination})
        with bundle.open('rb') as source:
            ssh(remote, ['python3', '-c', UPLOAD, destination], input_file=source, timeout=600)
        write_once(root / 'upload-completed.json', {'destination': destination})
    elif not (root / 'upload-completed.json').exists():
        # Observation is idempotent. Never repeat an uncertain transfer to a new job.
        value = json.loads(ssh(remote, ['cat', destination + '/uploaded.json']))
        if not value.get('uploaded'):
            raise RuntimeError('Remote staging outcome unknown; not uploading again')
        write_once(root / 'upload-completed.json', value)
    if not (root / 'slurm-job.json').exists():
        # Remote submit lock/intent discovers accepted jobs, including fast-completed
        # jobs via sacct, and refuses to issue a second sbatch after unknown delivery.
        if remote.get('pool'):
            pool = remote['pool']['root']
            job = json.loads(ssh(remote, ['python3', pool + '/pool.py', 'enqueue', pool, destination]))
        else:
            job = json.loads(ssh(remote, ['python3', '-c', SUBMIT, destination]))
        write_once(root / 'slurm-job.json', job)
    job = read(root / 'slurm-job.json')
    errors, cancelled = 0, False
    while True:
        if (root / 'cancel.json').exists() and not cancelled:
            code = "import pathlib,sys; p=pathlib.Path(sys.argv[1])/'cancel.json'; p.touch(exist_ok=True)"
            ssh(remote, ['python3', '-c', code, destination])
            cancelled = True
        offsets = {name: (root / (name + '.log')).stat().st_size if (root / (name + '.log')).exists() else 0
                   for name in ('stdout', 'stderr')}
        try:
            observation = json.loads(ssh(remote, ['python3', '-c', OBSERVE, destination, json.dumps(offsets)]))
            errors = 0
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            errors += 1
            write_once(root / ('read-error-' + uuid.uuid4().hex + '.json'), {'type': type(exc).__name__, 'message': str(exc)})
            progress(root, phase='transport_read_error', slurm_job_id=job['job_id'], consecutive_errors=errors)
            if errors >= 5:
                raise
            time.sleep(10)
            continue
        for name, content in observation['logs'].items():
            with (root / (name + '.log')).open('ab') as stream:
                stream.write(base64.b64decode(content))
                stream.flush()
        if 'execution-error' in observation:
            raise RuntimeError('Remote execution/collection infrastructure error: ' + json.dumps(observation['execution-error']))
        if 'exit' in observation and not (root / 'exit.json').exists():
            write_once(root / 'exit.json', observation['exit'])
        if 'result' in observation:
            result = observation['result']
            if result['run_id'] != root.name or result['kind'] != spec['kind']:
                raise ValueError('Remote result identity differs from requested operation')
            progress(root, phase='collecting_remote_artifacts', slurm_job_id=job['job_id'])
            archive = root / ('download-' + uuid.uuid4().hex + '.tar.gz')
            with archive.open('xb') as target:
                ssh(remote, ['cat', destination + '/output.tar.gz'], output_file=target, timeout=600)
                target.flush()
                os.fsync(target.fileno())
            staging = root / ('collection-' + uuid.uuid4().hex)
            staging.mkdir()
            unpack_verified(archive, staging, result)
            (staging / 'artifacts').rename(root / 'artifacts')
            for name in ('stdout.log', 'stderr.log'):
                (staging / name).replace(root / name)
            write_once(root / 'result.json', result)
            return result
        states = observation.get('scheduler_states', [])
        if states and all(x.split()[0] in ('COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT', 'NODE_FAIL', 'OUT_OF_MEMORY', 'PREEMPTED') for x in states):
            raise RuntimeError('Slurm terminated without complete native evidence: ' + ','.join(states))
        progress(root, phase='collecting_remote_artifacts' if 'exit' in observation else 'queued_or_running',
                 slurm_job_id=job['job_id'], scheduler_states=states)
        time.sleep(5)


if __name__ == '__main__':
    root = Path(sys.argv[1])
    try:
        run(root)
    except BaseException as exc:
        write_once(root / 'transport-error.json', {'error_type': type(exc).__name__, 'message': str(exc),
                                                 'native_replayed': False})
        raise
