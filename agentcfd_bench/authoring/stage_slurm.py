"""Create a new full v2306 runtime from approved read-only cluster sources."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .slurm_transport import ssh
from ..records.store import write_once

STAGE = r'''
import hashlib,json,os,pathlib,shutil,sys
base=pathlib.Path(sys.argv[1]); source=pathlib.Path('/public3/home/sca2070/software-sca2070-bak/OpenFOAM/dev/OpenFOAM-v2306')
old=pathlib.Path('/public3/home/sca2070/WORK/Caifeixue/AgentCFD/execution_tracks_20260910/openfoam-runtime-v4')
prefix='/public3/home/sca2070/WORK/Caifeixue/AgentCFD_Terminal_Bench/'
if not str(base).startswith(prefix) or not os.path.realpath(str(base)).startswith(prefix): raise ValueError('scope')
base.mkdir(parents=True,exist_ok=False)
target=base/'runtime'
shutil.copytree(str(old/'content'),str(target/'content'))
def overlay(src,dst):
 for directory,dirs,files in os.walk(str(src)):
  out=dst/pathlib.Path(directory).relative_to(src); out.mkdir(parents=True,exist_ok=True)
  for name in files: shutil.copy2(str(pathlib.Path(directory)/name),str(out/name))
platform=source/'platforms/linux64IccDPInt32Opt'
overlay(platform/'bin',target/'content/bin')
overlay(platform/'lib',target/'content/lib')
overlay(source/'bin/tools',target/'content/bin/tools')
files={}
for path in sorted((target/'content').rglob('*')):
 if path.is_file():
  h=hashlib.sha256()
  with path.open('rb') as f:
   for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
  files[str(path.relative_to(target/'content'))]=h.hexdigest()
manifest={'schema':'author-full-v2306-runtime-v1','source':str(source),'dependency_base':str(old),
          'foam_mpi':'intelmpi','wm_options':'linux64IccDPInt32Opt','files':files,
          'native_binaries':sorted(p.name for p in (platform/'bin').iterdir() if p.is_file()),
          'qualification':'copied_and_hashed; execution probes still required'}
raw=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
with (target/'manifest.json').open('xb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
print(json.dumps({'runtime':str(target),'manifest_sha256':hashlib.sha256(raw).hexdigest(),
                 'binaries':len(manifest['native_binaries']),'files':len(files)}))
'''


def stage(output):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    root = '/public3/home/sca2070/WORK/Caifeixue/AgentCFD_Terminal_Bench/authoring/' + stamp
    prepared = json.loads(ssh({'host': 'sca2070'}, ['python3', '-c', STAGE, root], timeout=600))
    value = {'host': 'sca2070', 'root': root + '/operations', 'partition': 'amd_256',
             'runtime': prepared['runtime'], 'runtime_manifest_sha256': prepared['manifest_sha256'],
             'python': '/public3/home/sca2070/WORK/Caifeixue/AgentCFD/execution_tracks_20260910/portable-runtime/python',
             'apptainer': '/public3/soft/singularity/apptainer-1.1.9-1.el7/bin/apptainer',
             'image': '/public3/soft/singularity/sif/centos7-with-lsb.sif',
             'source_openfoam': '/public3/home/sca2070/software-sca2070-bak/OpenFOAM/dev/OpenFOAM-v2306',
             'runtime_preparation': prepared}
    write_once(output, value)
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.output), ensure_ascii=False, indent=2))
