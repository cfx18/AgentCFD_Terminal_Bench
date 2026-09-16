"""User-approved reconstruction rubric; not a convergence or mechanism certificate."""
import math

VERSION = 'dense-reconstruction-reward-v1'


def approved_rubric(task_id):
    if task_id not in ('s-203', 's-204'):
        raise ValueError('No approved dense rubric for this task')
    return {
        'version': VERSION,
        'approval': 'user_confirmed_2026-09-16',
        'full_credit': {'normalized_rmse': .05, 'normalized_maximum_error': .20},
        'zero_credit': {'normalized_rmse': .30, 'normalized_maximum_error': 1.0},
        'interpolation': 'linear_between_anchors',
        'aggregation': 'minimum_over_metrics_and_fields',
        'pressure_alignment': 'volume_weighted_constant_offset' if task_id == 's-203' else 'none',
        'scope': 'reconstruct_public_finite_numerical_reference',
    }


def metric_score(measurement, rubric):
    """Score trusted numerical measurements independently of eligibility."""
    if rubric.get('version') != VERSION:
        raise ValueError('Unsupported reconstruction rubric')
    if measurement.get('metric_status') != 'completed' or measurement.get('coverage') != 1:
        raise ValueError('Complete native measurements required for scoring')
    scores = {}
    for field in ('U', 'T', 'p'):
        row = measurement['metrics'][field]
        if field == 'p' and rubric['pressure_alignment'] == 'volume_weighted_constant_offset':
            errors = {'normalized_rmse': row['gauge_aligned_rmse'] / row['normalizer'],
                      'normalized_maximum_error': row['gauge_aligned_maximum_error'] / row['normalizer']}
        else:
            errors = {key: row[key] for key in ('normalized_rmse', 'normalized_maximum_error')}
        components = {}
        for key, error in errors.items():
            good, bad = rubric['full_credit'][key], rubric['zero_credit'][key]
            if not all(math.isfinite(v) for v in (error, good, bad)) or not 0 <= good < bad or error < 0:
                raise ValueError('Invalid metric or reward anchors')
            components[key] = max(0.0, min(1.0, (bad - error) / (bad - good)))
        scores[field] = {'errors_used': errors, 'components': components, 'reward': min(components.values())}
    return {**measurement, 'metric_reward': min(row['reward'] for row in scores.values()),
            'reward_version': VERSION, 'field_scores': scores,
            'convergence_certified': False, 'mechanism_identification_scored': False}


def score(measurement, rubric, integrity):
    """Keep diagnostic accuracy visible without granting unresolved reward."""
    numerical = metric_score(measurement, rubric)
    verdict = integrity['verdict']
    if verdict not in ('pass', 'fail', 'review', 'error'):
        raise ValueError('Unsupported integrity verdict')
    common = {**numerical, 'integrity': integrity,
              'integrity_review_required': verdict == 'review',
              'eligibility': {'pass': 'eligible', 'fail': 'invalid',
                              'review': 'review', 'error': 'error'}[verdict],
              'grading_schema_version': 'dense-result-v2'}
    if verdict != 'pass':
        return {**common,
                'verdict': {'fail': 'fail', 'review': 'not_evaluated', 'error': 'error'}[verdict],
                'reason': {'fail': 'reconstruction_integrity_failed',
                           'review': 'integrity_review_required',
                           'error': 'integrity_infrastructure_error'}[verdict],
                'reward': 0.0 if verdict == 'fail' else None}
    reward = numerical['metric_reward']
    return {**common, 'verdict': 'pass' if reward == 1 else 'fail',
            'reason': 'dense_reconstruction_full_credit' if reward == 1 else 'dense_reconstruction_below_full_credit',
            'reward': reward}
