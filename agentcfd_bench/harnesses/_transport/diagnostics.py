"""Bounded host-only exception evidence; never put this in model feedback."""
import re
import traceback


def exception_record(exc, *, secrets=()):
    def clean(text):
        for secret in secrets:
            if isinstance(secret, str) and secret:
                text = text.replace(secret, '[REDACTED]')
        text = re.sub(r'(?i)(Bearer\s+)\S+', r'\1[REDACTED]', text)
        text = re.sub(r'(?i)((?:api[_-]?key|access_token|refresh_token|authorization)'
                      r'[\s\"\x27:=]+)[^\s,}\"\x27]+', r'\1[REDACTED]', text)
        return text[:8000]

    result = {'type': type(exc).__name__, 'message': clean(str(exc)),
              # No locals or source lines: those can contain credentials/inputs.
              'traceback': [{'file': f.filename, 'line': f.lineno, 'function': f.name}
                            for f in traceback.extract_tb(exc.__traceback__)[-30:]]}
    if exc.__cause__ is not None:
        result['cause'] = {'type': type(exc.__cause__).__name__,
                           'message': clean(str(exc.__cause__))}
    return result
