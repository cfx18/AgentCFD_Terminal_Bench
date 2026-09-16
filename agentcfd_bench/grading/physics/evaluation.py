"""Pure numeric extraction/comparison migrated from evaluation; no runtime policy."""
from functools import wraps

class NativeOutputError(ValueError):
    """Frozen native output cannot satisfy the task's supported output schema."""

def native_output_reader(reader):
    """Give a legacy ValueError-based *parser* a typed boundary, not the scorer."""
    @wraps(reader)
    def read(*args, **kwargs):
        try:
            return reader(*args, **kwargs)
        except ValueError as exc:
            raise NativeOutputError(str(exc)) from exc
    return read
