"""Create an ADDITIVE immutable runtime on the cluster from installed v2306.

Never overwrite an old runtime or an existing library with a different hash.
Execute explicitly on the cluster; this script does not call any model.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing',required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    base,source,output=Path(args.existing),Path(args.source),Path(args.output)
    if output.exists(): raise FileExistsError('Do not overwrite a runtime')
    original=json.loads((base/'manifest.json').read_text())
    for name,digest in original['files'].items():
        if sha(base/'content'/name)!=digest: raise ValueError('Existing runtime file changed: '+name)
    options=original['wm_options']; mpi=original['foam_mpi']
    source_lib=source/'platforms'/options/'lib'
    source_bin=source/'platforms'/options/'bin'
    shutil.copytree(base/'content',output/'content')
    content=output/'content'
    search=[content/'lib'/mpi,content/'lib',content/'deps',source_lib/mpi,source_lib]
    env={**os.environ,'LD_LIBRARY_PATH':':'.join(map(str,search))}
    names=('buoyantSimpleFoam','chtMultiRegionFoam','splitMeshRegions','changeDictionary')
    pending=[]
    origin={}
    def add(src,dst):
        src=Path(src).resolve()
        if not src.is_file(): raise ValueError('Missing runtime dependency')
        dst=content/dst
        if dst.exists():
            if sha(src)!=sha(dst): raise ValueError('Library collision: '+dst.name)
            return
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        origin[str(dst.relative_to(content))]={'source':str(src),'sha256':sha(dst)}
        pending.append(dst)
    for name in names: add(source_bin/name,Path('bin')/name)
    examined=set()
    while pending:
        item=pending.pop()
        if str(item) in examined: continue
        examined.add(str(item))
        result=subprocess.run(['/usr/bin/ldd',str(item)],env=env,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,universal_newlines=True,check=True)
        if 'not found' in result.stdout: raise ValueError('Unresolved dependency: '+result.stdout)
        for line in result.stdout.splitlines():
            match=re.search(r'=>\s+(/\S+)\s+\(',line)
            if not match: continue
            path=Path(match[1])
            if str(path).startswith(str(content)+'/') or str(path).startswith(('/lib','/usr/lib')):
                continue
            is_foam=str(path.resolve()).startswith(str(source.resolve())+'/')
            add(path,Path('lib' if is_foam else 'deps')/path.name)
    files={p.relative_to(content).as_posix():sha(p) for p in sorted(content.rglob('*')) if p.is_file()}
    for name,digest in original['files'].items():
        if files.get(name)!=digest: raise ValueError('Additive extension changed an old file')
    manifest={**original,'tools':sorted(set(original['tools'])|set(names)),
              'files':files,'ready':True,'unresolved':[],
              'extension':{'version':'edge-runtime-additive-v1','base_manifest_sha256':sha(base/'manifest.json'),
                           'added_files':origin,'old_files_preserved':True}}
    with (output/'manifest.json').open('x') as handle:
        json.dump(manifest,handle,sort_keys=True,indent=2)
        handle.write('\n')
    print(json.dumps({'manifest_sha256':sha(output/'manifest.json'),
                      'added_files':list(origin),'old_files_preserved':True}),flush=True)


if __name__=='__main__': main()
