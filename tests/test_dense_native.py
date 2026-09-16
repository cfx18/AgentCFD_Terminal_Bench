"""Actual v2306 sampling on changed/skewed meshes, without advancing a solver."""
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np
import pytest

from agentcfd_bench.execution.runner import Runner
from agentcfd_bench.execution.sandbox import Sandbox
from agentcfd_bench.grading.dense import COLUMNS
from agentcfd_bench.grading.dense_native import sample_case, select_time, InvalidNativeFields
from agentcfd_bench.grading.physics.foam.science_metrics import field_values
from agentcfd_bench.records.store import read, write_once

ROOT = Path(__file__).resolve().parents[1]
FOAM = ROOT / 'environments/native-v2306/foam'
DIMS = {'T': '[0 0 0 1 0 0 0]', 'p': '[0 2 -2 0 0 0 0]', 'U': '[0 1 -1 0 0 0 0]'}


def header(name, kind='dictionary', location='system', fmt='ascii'):
    return f'FoamFile {{version 2.0; format {fmt}; class {kind}; object {name}; location "{location}";}}\n'


def operate(runner, work, argv):
    operation = runner.start(work, argv, kind='exec')
    until = time.monotonic() + 30
    while runner.status(operation['run_id'])['lifecycle'] == 'running':
        assert time.monotonic() < until
        time.sleep(.03)
    directory, state = runner.verify(operation['run_id'])
    assert state['success'], runner.logs(operation['run_id'], stream='stderr')
    shutil.copytree(directory / 'artifacts', work, dirs_exist_ok=True)


def fixture_case(root, nx, skewed, binary):
    work = root / 'case'
    for name in ('system', 'constant', '1.5'): (work / name).mkdir(parents=True)
    patch = 'renamedExterior' if skewed else 'outer'
    a, b = (.35, .65) if skewed else (.5, .5)
    vertices = [(0,0,0),(a,0,0),(a,1,0),(0,1,0),(1,0,0),(1,1,0),
                (0,0,1),(b,0,1),(b,1,1),(0,1,1),(1,0,1),(1,1,1)]
    coordinates = ' '.join('(' + ' '.join(map(str, p)) + ')' for p in vertices)
    (work / 'system/blockMeshDict').write_text(header('blockMeshDict') + f'''
scale 1; vertices ({coordinates});
blocks (hex (0 1 2 3 6 7 8 9) ({nx} 4 3) simpleGrading (1 1 1)
        hex (1 4 5 2 7 10 11 8) ({nx} 4 3) simpleGrading (1 1 1));
edges (); boundary (); mergePatchPairs ();
defaultPatch {{name {patch}; type wall;}}
''')
    (work / 'system/controlDict').write_text(header('controlDict') + '''
application pimpleFoam; startFrom startTime; startTime 0; stopAt endTime;
endTime 1.5; deltaT 0.01; writeControl timeStep; writeInterval 1;
writeFormat ascii; writePrecision 17; writeCompression off;
timeFormat general; timePrecision 12; runTimeModifiable false;
''')
    (work / 'system/fvSchemes').write_text(header('fvSchemes') + '''
ddtSchemes {default Euler;} gradSchemes {default Gauss linear;}
divSchemes {default none;} laplacianSchemes {default Gauss linear corrected;}
interpolationSchemes {default linear;} snGradSchemes {default corrected;}
''')
    (work / 'system/fvSolution').write_text(header('fvSolution') + 'solvers {}\n')
    for name, value in [('T', '300'), ('p', '4'), ('U', '(1 2 3)')]:
        kind = 'volVectorField' if name == 'U' else 'volScalarField'
        (work / '1.5' / name).write_text(header(name, kind, '1.5') + f'''
dimensions {DIMS[name]}; internalField uniform {value};
boundaryField {{{patch} {{type zeroGradient;}}}}
''')
    sandbox = Sandbox(foam_root=str(FOAM), mpi='intelmpi')
    runner = Runner(root / 'preparation', sandbox, seconds=30)
    operate(runner, work, ['blockMesh'])
    operate(runner, work, ['postProcess', '-func', 'writeCellCentres', '-time', '1.5'])
    c = np.asarray(field_values((work / '1.5/C').read_text(), 'C', 24 * nx, '[0 1 0 0 0 0 0]', 1.5))
    values = '\n'.join(format(v, '.17g') for v in (300 + 2 * c[:, 0]))
    (work / '1.5/T').write_text(header('T', 'volScalarField', '1.5') +
        f'dimensions {DIMS["T"]}; internalField nonuniform List<scalar> {len(c)} (\n{values}\n);\n'
        + f'boundaryField {{{patch} {{type zeroGradient;}}}}\n')
    if binary:
        operate(runner, work, ['foamDictionary', 'system/controlDict', '-entry', 'writeFormat', '-set', 'binary'])
        operate(runner, work, ['foamFormatConvert', '-time', '1.5'])
        assert b'format      binary;' in (work / '1.5/T').read_bytes() or b'binary;' in (work / '1.5/T').read_bytes()[:700]
    return work, sandbox


def public_fixture(path):
    (path / 'observations').mkdir(parents=True)
    points = np.array([[x,y,z] for z in (.17,.44,.83) for y in (.13,.51,.89) for x in (.12,.38,.72,.88)])
    data = np.column_stack((points, np.ones(len(points)) / len(points),
                            np.tile([1,2,3], (len(points),1)), np.full(len(points),4), 300 + 2 * points[:,0]))
    csv = path / 'observations/fields.csv'
    np.savetxt(csv, data, delimiter=',', header=','.join(COLUMNS), comments='', fmt='%.17g')
    schema = {'schema':'dense-observation-v1', 'point_count':len(points),
              'csv_sha256':hashlib.sha256(csv.read_bytes()).hexdigest(),
              'normalizers':{'U':{'value':1,'unit':'m/s'},'T':{'value':2,'unit':'K'},'p':{'value':1,'unit':'m2/s2'}}}
    write_once(path / 'observations/schema.json', schema)
    return {'dimensions':DIMS, 'endpoint_kind':'physical_time', 'required_time':1.5}


@pytest.mark.parametrize('nx,skewed,binary', [(3,False,False),(6,True,False),(4,True,True)])
def test_real_sampling_changed_mesh_boundary_names_and_binary(tmp_path, nx, skewed, binary):
    work, sandbox = fixture_case(tmp_path, nx, skewed, binary)
    public = tmp_path / 'public'; reference = public_fixture(public)
    result = sample_case(work, public, reference, sandbox, tmp_path / 'sampling')
    assert result['coverage'] == 1 and result['metric_status'] == 'completed'
    assert result['metrics']['U']['maximum_absolute_error'] < 1e-12
    assert result['metrics']['p']['maximum_absolute_error'] < 1e-12
    # Cell sampling retains discretization error instead of smoothing it away.
    assert 0 < result['metrics']['T']['maximum_absolute_error'] < 2 / nx
    operations = list((tmp_path / 'sampling/native').glob('r-*'))
    assert len(operations) == 1
    assert sample_case(work, public, reference, sandbox, tmp_path / 'sampling') == result
    assert list((tmp_path / 'sampling/native').glob('r-*')) == operations


def test_unknown_sampler_dispatch_is_not_reissued(tmp_path):
    work, sandbox = fixture_case(tmp_path, 2, False, False)
    reference = public_fixture(tmp_path / 'public')
    output = tmp_path / 'sampling'; output.mkdir()
    write_once(output / 'dispatch-intent.json', {'unknown':True})
    with pytest.raises(RuntimeError, match='do not replay'):
        sample_case(work, tmp_path / 'public', reference, sandbox, output)
    assert not list((output / 'native').glob('r-*'))


def test_wrong_pressure_dimensions_rejected_before_sampling(tmp_path):
    work, _ = fixture_case(tmp_path, 2, False, False)
    p = work / '1.5/p'
    p.write_text(p.read_text().replace(DIMS['p'], '[1 -1 -2 0 0 0 0]'))
    reference = public_fixture(tmp_path / 'public')
    with pytest.raises(InvalidNativeFields, match='dimensions'):
        select_time(work, reference)


def test_nonphysical_temperature_is_candidate_failure_not_infrastructure(tmp_path):
    work, sandbox = fixture_case(tmp_path, 2, False, False)
    field = work / '1.5/T'
    field.write_text(header('T', 'volScalarField', '1.5') +
                     f'dimensions {DIMS["T"]}; internalField uniform -1;\n'
                     + 'boundaryField {outer {type zeroGradient;}}\n')
    reference = public_fixture(tmp_path / 'public')
    with pytest.raises(InvalidNativeFields, match='Nonpositive'):
        sample_case(work, tmp_path / 'public', reference, sandbox, tmp_path / 'sampling')


def test_frozen_solver_input_survives_native_writes(tmp_path):
    work, sandbox = fixture_case(tmp_path, 2, False, False)
    original = (work / 'system/controlDict').read_text()
    runner = Runner(tmp_path / 'input-audit', sandbox, seconds=30)
    operation = runner.start(work, ['foamDictionary','system/controlDict','-entry','endTime','-set','2'], kind='run')
    until = time.monotonic() + 30
    while runner.status(operation['run_id'])['lifecycle'] == 'running':
        assert time.monotonic() < until
        time.sleep(.03)
    native, result = runner.verify(operation['run_id'])
    assert result['success']
    assert (native / 'inputs/system/controlDict').read_text() == original
    assert (native / 'artifacts/system/controlDict').read_text() != original
    (native / 'inputs/system/controlDict').write_text('tampered')
    with pytest.raises(RuntimeError, match='input evidence changed'):
        runner.verify(operation['run_id'])
