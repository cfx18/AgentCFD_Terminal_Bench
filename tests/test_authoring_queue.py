from pathlib import Path

from agentcfd_bench.authoring.queue import inspect_source, select


def row(i, family='incompressible', **kwargs):
    return {'candidate_id': str(i), 'source_path': f'OpenFOAM-v2306/tutorials/{family}/solver/case{i}',
            'family': family, 'application': 'solver', 'screening': 'candidate', **kwargs}


def test_round_robin_keeps_registry_and_explicit_pending():
    rows = [row(1), row(2), row(3, 'heatTransfer'), row(4, 'compressible'),
            row(5, screening='needs_support')]
    assert [x['candidate_id'] for x in select(rows, 3)] == ['1', '3', '4']
    assert len(rows) == 5
    assert len(select(rows, 100, excluded=['1'])) == 3


def test_static_screening_is_not_physics_approval(tmp_path):
    source = row(1)
    case = tmp_path / source['source_path'] / 'system'
    case.mkdir(parents=True)
    (case / 'controlDict').write_text('application solver;')
    foam = tmp_path / 'foam'
    (foam / 'bin').mkdir(parents=True)
    (foam / 'bin/solver').write_text('not executed')
    result = inspect_source(source, tmp_path, foam)
    assert result['screening'] == 'candidate'
    assert 'no assertion' in result['note']
    (foam / 'bin/solver').unlink()
    assert inspect_source(source, tmp_path, foam)['reason'] == 'application_not_installed'
