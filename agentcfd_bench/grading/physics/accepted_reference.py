"""Pure numeric extraction/comparison migrated from accepted_reference; no runtime policy."""
import math
from . import free_mesh_buoyant as buoyant, free_mesh_shock as shock, free_mesh_thermal as thermal
from .evaluation import native_output_reader

VERSION = 'expert-reference-v1'

POLICY = {'version': VERSION, 'meaning': 'agreement_with_expert_accepted_finite_numerical_target',
    'thermal_relative_rms': .05, 'thermal_temperature_absolute_K': .01,
    'buoyant_T_scaled_l1': .05, 'buoyant_U_relative_l1': .10, 'buoyant_heat_relative': .05,
    'shock_normalized_l1': .04, 'convergence_diagnostics_are_gates': False,
    'reward_mapping': None}

def schema(task_id):
    if task_id in ('s-202', 's-203'):
        return thermal.measurement_schema(task_id)
    return {'s-204': buoyant.SCHEMA, 's-205': shock.SCHEMA}[task_id]

@native_output_reader
def snapshot(artifacts, task_id):
    if task_id in ('s-202', 's-203'):
        return thermal.snapshot(artifacts, task_id)
    return {'s-204': buoyant.snapshot, 's-205': shock.snapshot}[task_id](artifacts)

def compare(task_id, observed, target):
    """Reuse the existing dimensional norms/limits, with an explicit new target."""
    if task_id in ('s-202', 's-203'):
        errors = thermal.compare_spatial(observed['spatial_volumes'], target['spatial_volumes'])
        for name, row in errors.items():
            row['limit'] = max(POLICY['thermal_relative_rms'] * row['reference_rms'],
                POLICY['thermal_temperature_absolute_K'] if name.split('/')[-1] == 'T' else 1e-12)
            row['passed'] = row['rms_difference'] <= row['limit']
        return all(row['passed'] for row in errors.values()), errors
    obs, ref = observed['measurements'], target['measurements']
    errors = {}
    if task_id == 's-204':
        for field, limit in [('T', POLICY['buoyant_T_scaled_l1']), ('Uy', POLICY['buoyant_U_relative_l1'])]:
            a = [v for axis in ('x', 'y') for v in obs[field+'_'+axis+'_bin_mean']['value']]
            b = [v for axis in ('x', 'y') for v in ref[field+'_'+axis+'_bin_mean']['value']]
            scale = buoyant.DT if field == 'T' else max(math.fsum(abs(v) for v in b)/len(b), 1e-12)
            errors[field] = {'error': math.fsum(abs(x-y) for x,y in zip(a,b))/len(a)/scale, 'limit': limit}
        errors['wall_heat'] = {'error': max(abs(obs[n+'_wall_heat_rate']['value']/ref[n+'_wall_heat_rate']['value']-1)
            for n in ('hot', 'cold')), 'limit': POLICY['buoyant_heat_relative']}
    else:
        exact = shock.solution()
        scales = {'rho': exact.left.rho, 'p': exact.left.p, 'T': 348.432,
                  'Ux': math.sqrt(shock.GAMMA*exact.left.p/exact.left.rho)}
        for field, scale in scales.items():
            a, b = obs[field+'_axial_bin_mean']['value'], ref[field+'_axial_bin_mean']['value']
            errors[field] = {'error': math.fsum(abs(x-y) for x,y in zip(a,b))/len(a)/scale,
                             'limit': POLICY['shock_normalized_l1']}
    for row in errors.values():
        row['passed'] = row['error'] <= row['limit']
    return all(row['passed'] for row in errors.values()), errors

def diagnostics(task_id, observed, artifacts):
    """Visible to expert review, never a hidden extra convergence requirement."""
    if task_id in ('s-202', 's-203'):
        # Some completed historical sources have no temporal/gradient exports.
        # Missing diagnostic evidence remains missing; it never becomes zero.
        try:
            balance = (thermal.conjugate_energy_balance(artifacts, observed) if task_id == 's-202'
                       else thermal.thermal_transport_balance(artifacts, observed))
        except (ValueError, KeyError) as exc:
            balance = {'status': 'not_evaluated', 'error_type': type(exc).__name__}
        return {'energy_balance': balance}
    if task_id == 's-205':
        return {'independent_analytic_normalized_l1': observed['normalized_l1'],
                'equation_of_state_relative_max': observed['equation_of_state_relative_max']}
    heat = observed['heat']
    return {'solver_claimed_convergence': observed['convergence_claim'],
        'outer_residuals': observed['outer_residuals'],
        'optional_velocity_residuals': observed['optional_velocity_residuals'],
        'previous_write': observed['previous_write'],
        'heat_balance_relative': abs(math.fsum(heat.values()))/max(abs(heat['hot']), abs(heat['cold']), 1e-12),
        **{name: observed['measurements'][name]['value'] for name in
           ('T_last_write_relative_change', 'U_last_write_relative_change')}}
