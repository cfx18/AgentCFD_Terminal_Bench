import math

METRICS = {'ux_profile': ('m/s', 20), 'uy_rms': ('m/s', 1),
           'final_time': ('s', 1), 'ux_final_initial_residual': ('1', 1)}


def analytic_profile():
    # Start from rest; top wall impulsively starts at U=1. H=1, nu=0.1, t=2.
    return [y + sum(2 * (-1)**n / (n * math.pi) * math.sin(n * math.pi * y)
                    * math.exp(-0.1 * (n * math.pi)**2 * 2)
                    for n in range(1, 101)) for y in ((j + 0.5) / 20 for j in range(20))]

