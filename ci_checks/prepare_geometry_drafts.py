"""Print or save author-review surface candidates. No model/native execution."""
import argparse
import json
from pathlib import Path
import tomllib

from agentcfd_bench.geometry_assets import candidate
from agentcfd_bench.task_package import PROJECT, load_task


def build():
    registry = tomllib.loads((PROJECT/'tasks/dataset.toml').read_text())
    return {row['id']:candidate(load_task(row['id'])) for row in registry['tasks']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args = parser.parse_args(argv)
    values = build()  # Validate all ten before creating anything.
    root = Path(args.output)
    root.mkdir(parents=True,exist_ok=False)
    for task,value in values.items():
        for relative,text in value['public_files'].items():
            file = root/task/relative
            file.parent.mkdir(parents=True,exist_ok=True)
            with file.open('x') as handle: handle.write(text)
    manifest = {'version':'geometry-only-free-mesh-draft-v1','registered':len(values),
                'paid_ready':False,'tasks':{k:v['review'] for k,v in values.items()}}
    with (root/'author-review.json').open('x') as handle:
        json.dump(manifest,handle,indent=2,ensure_ascii=False)
    print(json.dumps({'output':str(root),'registered':len(values),'paid_ready':False}))


if __name__=='__main__':
    main()
