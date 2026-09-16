"""Output-time evidence only. No executable or input configuration policy."""
from dataclasses import dataclass
import math
import re

EDGE_REGIONS = ('bottomWater', 'topAir', 'heater', 'leftSolid', 'rightSolid')


@dataclass(frozen=True)
class Completion:
    commands: tuple
    kind: str
    end: float
    tolerance: float
    early_convergence: bool
    fields: tuple
    qualification_seconds: int

    def completed(self, log):
        try:
            times = [float(x) for x in re.findall(r'^Time = ([^\s]+)\s*$', log, re.M)]
        except ValueError:
            return False
        if (not times or not all(math.isfinite(x) and x > 0 for x in times)
                or any(a>=b for a,b in zip(times,times[1:])) or not re.search(r'^End\s*$',log,re.M)):
            return False
        return abs(times[-1]-self.end)<=self.tolerance
