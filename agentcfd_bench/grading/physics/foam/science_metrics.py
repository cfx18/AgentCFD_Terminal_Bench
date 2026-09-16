"""Pure numeric extraction/comparison migrated from foam.science_metrics; no runtime policy."""
import math
from .parsed import canonical, read, scalar

def number(value):
    result = float(scalar((value,)))
    # Reject nonfinite or absurd magnitudes before squared reductions overflow.
    if not math.isfinite(result) or abs(result) > 1e100:
        raise ValueError('Native number outside finite supported range')
    return result

def field_values(text, name, count, dimensions, end, *, region=None, allow_missing_location=False):
    from ..tutorial_tasks import list_values
    if type(count) is not int or not 0 < count <= 1000000:
        raise ValueError('Unsupported cell count')
    tree = read(text)
    header = tree.get('FoamFile', {})
    vector = name in ('U', 'C')
    kind = 'volVectorField' if vector else 'volScalarField'
    if (header.get('class') != (kind,) or header.get('format') != ('ascii',)
            or header.get('object') != (name,)):
        raise ValueError('Native field header class/format/object mismatch: '+name)
    if canonical(tree.get('dimensions', ())) != canonical(read('_ '+dimensions+';')['_']):
        raise ValueError('Native field dimensions mismatch: '+name)
    location = header.get('location', ())
    parts = location[0].strip('"').split('/') if len(location) == 1 else []
    # Native output evidence remains strict. Input dictionaries may omit this
    # optional header entry; a present but incorrect location is never ignored.
    missing_allowed = allow_missing_location and 'location' not in header
    if not missing_allowed and (len(parts) != (2 if region else 1) or (region and parts[-1] != region)
                               or abs(number(parts[0])-end) > 1e-7):
        raise ValueError('Native field header location mismatch: '+name)
    value = tree.get('internalField', ())
    if value[:1] == ('uniform',):
        if vector:
            row = list_values(value[1:])
            if len(row) != 3 or any(not isinstance(x, str) for x in row):
                raise ValueError('Malformed uniform vector')
            return [[number(x) for x in row] for _ in range(count)]
        if len(value) != 2:
            raise ValueError('Malformed uniform scalar')
        return [number(value[1])] * count
    required = 'List<vector>' if vector else 'List<scalar>'
    if len(value) < 5 or value[:2] != ('nonuniform', required) or number(value[2]) != count:
        raise ValueError('Native field list type or declared size mismatch: '+name)
    data = list_values(value[3:])
    if len(data) != count:
        raise ValueError('Native field actual cell count mismatch: '+name)
    if vector:
        if any(not isinstance(row, list) or len(row) != 3
               or any(not isinstance(x, str) for x in row) for row in data):
            raise ValueError('Malformed nonuniform vector list')
        return [[number(x) for x in row] for row in data]
    if any(not isinstance(x, str) for x in data):
        raise ValueError('Malformed nonuniform scalar list')
    return [number(x) for x in data]
