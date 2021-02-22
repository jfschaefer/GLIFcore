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
    def __init__(self, key: str, value: str = ''):
        self.key = key
        self.value = value

    def __eq__(self, r):
        return self.key == r.key and self.value == r.value
    
    def __str__(self):
        if self.value:
            return f'-{self.key}={argformat(self.value)}'
        return f'-{self.key}'

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
            return Result(success = True, value=(CommandArgument(argname, argval), s))
        else:
            return Result(success = False, logs=res.logs)
        # r = parseString(s)
    elif s[0].isidentifier() or s[0].isalnum():
        argval, s = parseIdentifier(s, canbenum=True)
        return Result(success = True, value=(CommandArgument(argname, argval), s))
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
    assert s[0].isidentifier() or (canbenum and s[0].isalnum) or s[0] == '?'   # ? for user-defined macros
    identifier = s[0]
    i = 1
    while i < len(s):
        if s[i].isalnum() or s[i].isidentifier():  # not '7'.isidentifier()
            identifier += s[i]
            i += 1
        else:
            return (identifier, s[i:])
    return (identifier, '')

class BasicCommand(object):
    def __init__(self, name: str, args: list[CommandArgument], mainargs: list[str]):
        self.name = name
        self.args = args
        self.mainargs = mainargs

    def gfFormat(self, mainarg: Optional[str], mainargIsStr: bool = False):
        head = f'{self.name} {" ".join([str(a) for a in self.args])}'
        if mainarg:
            return f'{head} {strformat(mainarg) if mainargIsStr else mainarg}'
        else:
            return head

def argformat(s : str) -> str:
    if s.isidentifier() or s.isalnum():
        return s
    return strformat(s)

def strformat(s : str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

def parseBasicCommand(string: str) -> Result[tuple[BasicCommand, str]]:
    string = string.strip()
    commandname, rest = parseCommandName(string.strip())
    command = BasicCommand(commandname, [], [])

    # Args
    while True:
        rest = rest.strip()
        if not rest:
            break
        if rest[0] == '-':
            r = parseCommandArg(rest)
            if not r.success:
                return Result(False, logs=r.logs)
            assert r.value
            arg, rest = r.value
            command.args.append(arg)
        else:
            break

    rest = rest.strip()

    if not rest:
        return Result(True, (command, ''))

    if rest[0] == '|':
        return Result(True, (command, rest[1:]))
    
    # Find next pipe
    mainarg = ''    # Record main argument
    i = 0
    while i < len(rest):
        if rest[i] == '|':
            # Done :)
            mainarg = mainarg.strip()
            if mainarg:
                command.mainargs.append(mainarg)
            return Result(True, (command, rest[i+1:]))
        elif rest[i] == '"':
            rr = parseString(rest[i:])
            if not rr.success:
                return Result(False, None, logs=rr.logs)
            assert rr.value
            rest = rr.value[1]
            command.mainargs.append(rr.value[0])
            i = 0
        else:
            i += 1
            mainarg += rest[i-1]
    mainarg = mainarg.strip()
    if mainarg:
        command.mainargs.append(mainarg)
    return Result(True, (command, ''))

def indent(s: str, level: int = 4) -> str:
    return '\n'.join([' '*level + l for l in s.splitlines()])
