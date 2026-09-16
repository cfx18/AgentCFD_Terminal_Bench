"""Pure numeric extraction/comparison migrated from foam.normalize; no runtime policy."""
from decimal import Decimal, InvalidOperation
import re

NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z", re.ASCII)

class UnsupportedInput(ValueError):
    pass

class ParserResourceLimit(RuntimeError):
    """The grader reached an implementation limit, not a physical rejection.

    Deliberately not a ValueError: native_output_reader must not translate this
    into invalid model output. The scoring boundary records it as an error.
    """

def atom(value):
    if not NUMBER.fullmatch(value):
        return ("word", value)
    if len(value) > 4096:
        raise UnsupportedInput("numeric token exceeds budget")
    try:
        sign, digits, exponent = Decimal(value).as_tuple()
    except (InvalidOperation, ValueError):
        raise UnsupportedInput("invalid decimal") from None
    if not any(digits):
        return ("number", 0, (0,), 0)
    digits = list(digits)
    while digits[-1] == 0:
        digits.pop()
        exponent += 1
    return ("number", sign, tuple(digits), exponent)

def normalize(text):
    if not isinstance(text, str) or "\x00" in text:
        raise UnsupportedInput("text input required")
    tokens, stack = [], []
    i = 0
    pairs = {"}": "{", ")": "(", "]": "["}
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i + 2)
            i = len(text) if end < 0 else end + 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise UnsupportedInput("unclosed comment")
            i = end + 2
        elif c in "\"'":
            start, quote = i, c
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                elif text[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise UnsupportedInput("unclosed quoted string")
            tokens.append(("quoted", text[start:i]))
        elif c in "{}()[];":
            if c in "{([":
                stack.append(c)
            elif c in pairs:
                if not stack or stack.pop() != pairs[c]:
                    raise UnsupportedInput("unbalanced delimiter")
            tokens.append(("punctuation", c))
            i += 1
        else:
            start = i
            while i < len(text) and not text[i].isspace() and text[i] not in "{}()[];\"'":
                if text.startswith(("//", "/*"), i):
                    break
                i += 1
            tokens.append(atom(text[start:i]))
    if stack:
        raise UnsupportedInput("unclosed delimiter")
    return tuple(tokens)
