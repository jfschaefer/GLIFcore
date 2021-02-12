'''
    Various utilities for parsing commands.
    Function pattern:
        input string -> (result, remaining string)
    or:
        input string -> Result[(result, remaining string)]

    Example:
        parseCommand('parse -lang=Eng "hello world"')
        returns
        ('parse', '-lang=Eng "hello world"')

    Remark:
        These tools are not optimized for efficiency and
        tend to be rather hacky.
'''

from typing import Optional, Union
from glif.utils import Result


# Command parsing

def parseCommandName(s: str) -> tuple[str, str]:
    s = s.strip()
    assert s
    i = s.find(' ')
    if i > 0:  # space was found
        return (s[:i], s[i+1:].strip())
    else:      # command is only command name
        return (s, '')

class CommandArgument(object):
    def __init__(self, key: str, value: str = '', stringvalue: str = ''):
        self.key = key
        self.value = value
        self.stringvalue = stringvalue

    def __eq__(self, r):
        return self.key == r.key and self.value == r.value and self.stringvalue == r.stringvalue

def parseCommandArg(s0: str) -> Result[tuple[CommandArgument, str]]:
    s = s0.strip()
    # Deal with leading "-" or "--"
    if not s or not s[0] == '-' or len(s) == 1:
        return Result(success = False, logs = f'Expected argument starting with "-", found "{s}"')
    if s[1] == '-':
        s = s[2:]
    else:
        s = s[1:]

    argname, s = parseIdentifier(s)
    if not s:
        return Result(True, (CommandArgument(argname), ''))
    if s[0] == ' ':
        return Result(True, (CommandArgument(argname), s[1:]))
    if s[0] != '=':
        return Result(success = False, logs = f'Unexpected character "{s[0]}" when parsing "{s0}"')
    s = s[1:]
    if not s:
        return Result(success = False, logs = f'Missing argument value in "{s0}"')
    if s[0] == '"':
        res = parseString(s)
        if res.success:
            assert res.value
            argval, s = res.value
            return Result(success = True, value=(CommandArgument(argname, stringvalue=argval), s))
        else:
            return Result(success = False, logs=res.logs)
        # r = parseString(s)
    elif s[0].isidentifier() or s[0].isalnum():
        argval, s = parseIdentifier(s, canbenum=True)
        return Result(success = True, value=(CommandArgument(argname, value=argval), s))
    else:
        return Result(success = False, logs=f'Unexpected argument value in "{s0}"')


def parseString(s: str) -> Result[tuple[str, str]]:
    assert s[0] == '"'
    i = 1
    lastWasBackslash = False
    res = ''
    while i < len(s):
        if lastWasBackslash:
            if s[i] in ['"', '\\']:
                res += s[i]
            else:   # assume backslash wasn't use for escaping
                res += '\\' + s[i]
            lastWasBackslash = False
        elif s[i] == '\\':
            lastWasBackslash = True
        elif s[i] == '"':  # end of string
            return Result(True, (res, s[i+1:]))
        else:
            res += s[i]
        i += 1
    return Result(False, logs = f'String not closed: "{s}"')
            
def parseIdentifier(s: str, canbenum: bool = False) -> tuple[str, str]:
    assert s
    assert s[0].isidentifier() or (canbenum and s[0].isalnum)
    identifier = s[0]
    i = 1
    while i < len(s):
        if s[i].isalnum() or s[i].isidentifier():  # not '7'.isidentifier()
            identifier += s[i]
            i += 1
        else:
            return (identifier, s[i:])
    return (identifier, '')


