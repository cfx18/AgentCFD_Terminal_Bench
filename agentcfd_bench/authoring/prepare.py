"""Freeze original tutorial sources and author jobs without dispatching a model."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import tarfile

from ..records.store import read, write_once

ARCHIVE_SHA = 'd7fba773658c0f06ad17f90199565f32e9bf502b7bb03077503642064e1f5344'
PROJECT = Path(__file__).resolve().parents[2]

AUTHOR_PROTOCOL = '''You are a reference-data AUTHOR, not a benchmark contestant.
Use GPT-5.6 Luna through Codex; do not launch subagents. Work only inside /work.
Read the exact archived tutorial in /input/source. Native OpenFOAM v2306 is
available ONLY via python3 /opt/foamctl.py: exec -- COMMAND, run -- SOLVER ARGS,
status RUN_ID, logs RUN_ID, cancel RUN_ID. Native execution is serial, no MPI.
Commands snapshot /work. Completed artifacts are at /artifacts/RUN_ID; copy the
needed outputs back to /work before subsequent operations. Never resubmit an
unknown operation; poll it. A single Python shell script can poll without using
one model call per poll. Do NOT call submit: you are preparing reference data.
No cumulative native-time cap; no output-token cap. There are at most 120 model
calls for this author job. Preserve concise PUBLIC decisions/actions/evidence,
not private chain-of-thought. Record source file locations for physical facts.
Do not contact any external API from shell; do not access host credentials.
The installed runtime has executables but not bin/tools/RunFunctions. The exact
original helper is available in /input/source/OpenFOAM-v2306/bin/tools. For simple
cases run the original commands directly. Do not invent omitted initialization,
change a mesh/material/BC/endTime, or disable a physical model to force success.
Unsupported dynamic compilation, MPI or missing dependency => needs_support.
Disk storage is shared: keep work scoped to this one case; do not copy the full
tutorial tree. Do not delete evidence from /artifacts. Public source names are
private author evidence, not public benchmark instructions.
'''


def native_prompt(row):
    return AUTHOR_PROTOCOL + f'''
Prepare source {row['source_path']} as candidate {row['candidate_id']}.
1. Read the original files AND applicable local/ancestor Allrun scripts. Copy the
exact source case to /work/case. Identify dependencies before executing.
2. Execute its original preparation and native solver to the original endpoint;
use run for the actual solver. Perform checkMesh and appropriate quantitative
physics sanity checks: dimensions, finite fields, physical ranges, endpoint,
mass/energy consistency where measurable, and residual/stationarity evidence.
Do not equate exit zero with convergence. Finite tutorial outputs are acceptable
as numerical reconstruction targets if shortcomings are explicitly reported;
physical contradictions must be review, not pass. No mesh-convergence study needed.
3. Export outer geometry (no volume-mesh prescription) and dense native fields
with physical coordinates, volumes, field dimensions/units and endpoint metadata.
Use genuine native cell centres/volumes, never inferred analytic stand-ins.
Keep only actual fields; do not synthesize temperature for an isothermal case.
Native export or binary conversion may use a COPY after the solver: preserve its
original run ID and identify the separate export ID. No source physics edits.
4. Write /work/package/public/instruction.md in ENGLISH, styled after
/input/examples/s-203/instruction.md and s-204/instruction.md. State geometry,
known physical family/materials, initial condition, known vs inferred forcing,
observation time, ambiguities, and deliverable in physical language. The model
must build its own mesh/case; no solver dictionary recipe or original source name.
Allow general OpenFOAM docs/web research. Prevent target-field initialization or
pointwise forcing. Original configuration is ONE realization, not uniquely
identifiable GT. Do not copy thresholds from U/p/T examples to other physics.
5. Write /work/author-result.json with schema='tutorial-author-result-v1',
candidate_id, source_path, status ('candidate'|'needs_support'|'review'|'failed'),
solver_run_id, export_run_id, case_subdirectory='case', observed_endpoint,
source_changes (must be [] for an unmodified candidate), fields, physics_checks
(list of name, observed, criterion, passed, evidence), limitations, blockers,
proposed_grading (field-specific units/normalizers/metrics; uncertainty explicit).
Evidence paths should identify run IDs, logs and field files. Include which
checks remain unavailable; never assert 'no physical problems' without evidence.
Write /work/REVIEW.zh.md: Chinese expert-facing summary of decisions, commands,
observed numbers, scientific doubts and pipeline errors, with no fabricated runs.
Do not label the candidate released: the host independently verifies evidence.
If blocked, produce the same result/review with precise errors and stop cleanly.
'''


def prepare(config_path, destination):
    config = read(config_path)
    destination = Path(destination).resolve()
    archive = Path(config['archive'])
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA:
        raise ValueError('Original OpenFOAM release archive identity mismatch')
    if destination.exists():
        raise FileExistsError('Use a new timestamped author campaign directory')
    destination.mkdir(parents=True)
    public = destination / 'inputs'
    source = public / 'source'
    source.mkdir(parents=True)
    # No execution of archive scripts. The data filter rejects escaping links.
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if any(m.name.startswith(prefix) for prefix in (
            'OpenFOAM-v2306/tutorials/', 'OpenFOAM-v2306/modules/',
            'OpenFOAM-v2306/bin/tools/'))]
        tar.extractall(source, members=members, filter='data')
    inventory = read(config['inventory'])
    if inventory['archive_sha256'] != ARCHIVE_SHA:
        raise ValueError('Inventory and archived sources differ')
    rows = []
    for index, item in enumerate(inventory['inventory'], 1):
        source_path = item['source_path']
        if not source_path.startswith('OpenFOAM-v2306/'):
            source_path = 'OpenFOAM-v2306/tutorials/' + source_path
        rows.append({'candidate_id': f'q-{index:04d}', 'source_id': item['id'],
                     'source_path': source_path, 'inventory_source_path': item['source_path'],
                     'status': 'registered',
                     'original_inventory_status': item['status'],
                     'original_inventory_reasons': item.get('reasons', [])})
    write_once(destination / 'registry.json', {
        'schema': 'tutorial-author-registry-v1', 'created': datetime.now(timezone.utc).isoformat(),
        'archive_sha256': ARCHIVE_SHA, 'target_qualified_tasks': config['target_qualified_tasks'],
        'registered': len(rows), 'candidates': rows,
        'note': 'Old repair-task counts are not independent physics tasks; no candidate silently removed.'})
    for task in ('s-203', 's-204'):
        out = public / 'examples' / task
        out.mkdir(parents=True)
        for name in ('instruction.md', 'observations.md'):
            shutil.copyfile(PROJECT / 'tasks/releases/dense-reconstruction-v2' / task / 'public' / name, out / name)
    # Source context for the bounded library-development worker, not contestant data.
    shutil.copytree(PROJECT / 'agentcfd_bench', public / 'project/agentcfd_bench',
                    ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(PROJECT / 'tests', public / 'project/tests',
                    ignore=shutil.ignore_patterns('__pycache__'))
    write_once(public / 'registry.json', read(destination / 'registry.json'))
    jobs = {}
    prompts = destination / 'prompts'
    prompts.mkdir()
    for selected in config['pilot_sources']:
        matches = [row for row in rows if row['source_path'] == selected]
        if len(matches) != 1:
            raise ValueError('Pilot must be an exact registered original source: ' + selected)
        row = matches[0]
        job_id = row['candidate_id']
        path = prompts / (job_id + '.md')
        path.write_text(native_prompt(row))
        jobs[job_id] = {'prompt': str(path), 'candidate': row,
                        'expected_outputs': ['author-result.json', 'REVIEW.zh.md']}
    helper = prompts / 'library.md'
    helper.write_text(AUTHOR_PROTOCOL + '''
Bounded independent task: implement a reusable AUTHORING evidence validator and
generic dense observation exporter in /work/deliverables, with offline unit tests.
Inspect actual code under /input/project/agentcfd_bench and tests. Do not rewrite
the harness, existing dense grader, or alter current s-203/s-204 policies. No model
or native calls needed for this coding job. The main agent integrates your files.
Implement author_evidence.py, test_author_evidence.py, DESIGN.zh.md.
Validator accepts a real author-result.json and native operation directory. Check
recorded success, kind=run, immutable input/artifact hashes, no source physics
changes, executed solver not postProcess/meshing, actual final fields present,
physical-check evidence finite numbers and explicit criteria. Missing evidence
must remain review/error, not pass. Do not trust LLM passed=true blindly. Treat
the selected original reference as finite numerical GT, not mesh convergence.
Support explicit scalar/vector field schema (not fixed U/p/T), ASCII/gzip input,
provided native C/V fields and their dimensions; reject unsupported tensor/binary
data clearly, or require a native conversion receipt. No regex-only field parser.
Use existing parsed.py primitives where reliable; inspect their actual API.
All numeric observations must come from native fields. Public packages contain
geometry, observations, English physical prompt and schema; original files/logs
stay private. Propose exact validation/replay requirements for future publishing,
do not approve a release just because files exist. Unit tests must reject missing
exit, wrong hashes, altered source, negative volumes, absent fields, NaN, and
physical-check claims without evidence. Run tests locally using available python;
report dependency gaps truthfully. Keep scope small and APIs clear.
''')
    jobs['library'] = {'prompt': str(helper), 'expected_outputs': [
        'deliverables/author_evidence.py', 'deliverables/test_author_evidence.py', 'deliverables/DESIGN.zh.md']}
    runtime = {**config, 'root': str(destination), 'public': str(public), 'jobs': jobs}
    write_once(destination / 'campaign.json', runtime)
    return {'root': str(destination), 'registered': len(rows), 'jobs': list(jobs), 'started': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(__import__('json').dumps(prepare(args.config, args.output), ensure_ascii=False))
