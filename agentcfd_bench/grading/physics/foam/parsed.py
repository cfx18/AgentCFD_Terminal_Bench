"""Pure numeric extraction/comparison migrated from foam.parsed; no runtime policy."""
from dataclasses import dataclass
from decimal import Decimal
import re
from .normalize import normalize, UnsupportedInput, ParserResourceLimit

@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int

@dataclass(frozen=True)
class Dictionary:
    items: tuple

@dataclass(frozen=True)
class Directive:
    name: str
    arguments: tuple

def tokens(text):
    normalize(text)  # Validate quotes, balanced delimiters and numeric spelling.
    result, i = [], 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text.startswith('//', i):
            end = text.find('\n', i+2)
            i = end if end >= 0 else len(text)
            continue
        if text.startswith('/*', i):
            i = text.index('*/', i+2)+2
            continue
        start = i
        if text.startswith('${', i):
            end = text.find('}',i+2)
            if end < 0: raise UnsupportedInput('Unterminated scoped reference')
            i = end+1
        elif text[i] in ('"', "'"):
            quote = text[i]
            i += 1
            while text[i] != quote:
                i += 2 if text[i] == '\\' else 1
            i += 1
        elif text[i] in '{}()[];':
            i += 1
        else:
            while i < len(text) and not text[i].isspace() and text[i] not in '{}()[];"\'':
                if text.startswith(('//', '/*'), i):
                    break
                i += 1
        result.append(Token(text[start:i], start, i))
    return tuple(result)

def literal(key):
    if key.startswith('"') and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key[1:-1]):
        return key[1:-1]
    return key

def parse(text):
    data = tokens(text)
    def scope(i, nested=False, depth=0):
        if depth > 64:
            raise ParserResourceLimit('Dictionary nesting exceeds safety limit')
        items = []
        while i < len(data):
            key = data[i].text
            if key == '}':
                if not nested:
                    raise UnsupportedInput('Unexpected dictionary closure')
                return Dictionary(tuple(items)), i+1
            if key == ';':
                i += 1
                continue
            if key in '{([])':
                raise UnsupportedInput('Invalid dictionary key')
            last = data[i].end
            i += 1
            # Function-like keys (div(phi,U), grad(U), nested laplacian keys)
            # are contiguous in source. "vertices (...)" remains a list value.
            if i < len(data) and data[i].text == '(' and data[i].start == last:
                level = 0
                while i < len(data):
                    value = data[i].text
                    key += value
                    level += (value == '(') - (value == ')')
                    i += 1
                    if level == 0:
                        break
            key = literal(key)
            if key.startswith('#'):
                arguments = []
                while i < len(data) and data[i].text not in (';', '}'):
                    if '\n' in text[last:data[i].start]:
                        break
                    arguments.append(data[i].text)
                    last = data[i].end
                    i += 1
                if i < len(data) and data[i].text == ';':
                    i += 1
                items.append((key, Directive(key, tuple(arguments))))
                continue
            if i < len(data) and data[i].text == '{':
                value, i = scope(i+1, True, depth+1)
            else:
                value, stack = [], []
                while i < len(data):
                    word = data[i].text
                    if not stack and word == ';':
                        i += 1
                        break
                    if not stack and word == '}':
                        raise UnsupportedInput('Dictionary entry missing semicolon')
                    if word in '({[':
                        stack.append(word)
                    elif word in ')}]':
                        stack.pop()
                    value.append(word)
                    i += 1
                else:
                    raise UnsupportedInput('Unterminated dictionary entry')
                value = tuple(value)
            items.append((key, value))
        if nested:
            raise UnsupportedInput('Unterminated dictionary')
        return Dictionary(tuple(items)), i
    return scope(0)[0]

def pattern_matches(key, wanted):
    """Only the finite alternatives used by solver dictionaries; no arbitrary regex."""
    if not key.startswith('"') or not key.endswith('"'):
        return False
    pattern = key[1:-1]
    match = re.fullmatch(r'\(([A-Za-z0-9_|]+)\)(Final)?', pattern)
    if match:
        return wanted in [word+(match[2] or '') for word in match[1].split('|')]
    return False

def resolve(root, *, allow_scope_paths=False):
    count = 0
    def lookup(name, scopes):
        if allow_scope_paths and name.startswith('../'):
            while name.startswith('../'):
                if len(scopes)<=1: raise UnsupportedInput('Reference escapes dictionary scope')
                scopes=scopes[:-1]
                name=name[3:]
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            raise UnsupportedInput('Only bare local dictionary references are supported')
        for index in range(len(scopes)-1, -1, -1):
            scope = scopes[index]
            direct = [(key, value) for key, value in scope.items if key == name]
            if len(direct) > 1:
                raise UnsupportedInput('Ambiguous duplicate macro target')
            if direct:
                return direct[0][1], scopes[:index+1]
            matches = [(key, value) for key, value in scope.items if pattern_matches(key, name)]
            if len(matches) > 1:
                raise UnsupportedInput('Ambiguous pattern macro target')
            if matches:
                return matches[0][1], scopes[:index+1]
        raise UnsupportedInput('Unresolved local dictionary reference')

    def expand(value, scopes, seen=()):
        nonlocal count
        count += 1
        if count > 500000 or len(seen) > 64:
            raise ParserResourceLimit('Dictionary expansion exceeds safety limit')
        if isinstance(value, Directive):
            return value
        if isinstance(value, Dictionary):
            result, explicit = {}, set()
            current = (*scopes, value)
            for key, item in value.items:
                if key.startswith('$'):
                    if item:
                        raise UnsupportedInput('Dictionary splice must have no value')
                    copied = reference(key[1:], current, seen)
                    if not isinstance(copied, dict):
                        raise UnsupportedInput('Dictionary inheritance needs a dictionary')
                    for name, content in copied.items():
                        result.setdefault(name, content)
                    continue
                if key in explicit:
                    raise UnsupportedInput('Duplicate explicit dictionary entry')
                explicit.add(key)
                result[key] = expand(item, current, seen)
            return result
        # Native scalar/vector fields are literal data, not macro expansions.
        # A legal 100,800-cell vector field already contains 504,005 tokens.
        # Reuse its parsed tuple without copying it through the macro budget.
        # File quotas and field_values' count/shape/finite checks still apply.
        if not any('$' in word or '#' in word for word in value):
            return value
        result = []
        for word in value:
            if word.startswith('$'):
                copied = reference(word[1:], scopes, seen)
                if not isinstance(copied, tuple):
                    raise UnsupportedInput('Value reference needs a literal value')
                result.extend(copied)
            elif '$' in word or '#' in word:
                raise UnsupportedInput('Embedded substitution or directive is not supported')
            else:
                result.append(word)
            if len(result) > 500000:
                raise ParserResourceLimit('Expanded value exceeds safety limit')
        return tuple(result)

    def reference(name, scopes, seen):
        if name.startswith('{') and name.endswith('}') and allow_scope_paths:
            name=name[1:-1]
        value, containing = lookup(name, scopes)
        marker = (id(containing[-1]), name)
        if marker in seen:
            raise UnsupportedInput('Cyclic dictionary reference')
        return expand(value, containing, (*seen, marker))
    return expand(root, ())

def read(text):
    return resolve(parse(text))

def canonical(value):
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if isinstance(value, Directive):
        return {'directive': value.name, 'arguments': list(value.arguments)}
    return normalize(' '.join(value))

def scalar(value):
    data = normalize(' '.join(value))
    if len(data) != 1 or data[0][0] != 'number':
        raise UnsupportedInput('Expected literal scalar')
    return Decimal(data[0][1:])

def list_dictionary(value):
    if not value or value[0] != '(' or value[-1] != ')':
        raise UnsupportedInput('Expected dictionary list')
    return read(' '.join(value[1:-1]))
