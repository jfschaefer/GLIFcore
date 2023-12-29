"""
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
"""

from typing import Optional

from glif.utils import Result


# COMMAND PARSING

def parse_command_name(s: str) -> tuple[str, str]:
    s = s.strip()
    assert s
    i = s.find(' ')
    if i > 0:  # space was found
        return s[:i], s[i + 1:].strip()
    else:  # command is only command name
        return s, ''


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


def parse_command_arg(s0: str) -> Result[tuple[CommandArgument, str]]:
    s = s0.strip()
    # Deal with leading "-" or "--"
    if not s or not s[0] == '-' or len(s) == 1:
        return Result(success=False, logs=f'Expected argument starting with "-", found "{s}"')
    if s[1] == '-':
        s = s[2:]
    else:
        s = s[1:]

    argname, s = parse_identifier(s, allow_minus=True)
    if not s:
        return Result(True, (CommandArgument(argname), ''))
    if s[0] == ' ':
        return Result(True, (CommandArgument(argname), s[1:]))
    if s[0] != '=':
        return Result(success=False, logs=f'Unexpected character "{s[0]}" when parsing "{s0}"')
    s = s[1:]
    if not s:
        return Result(success=False, logs=f'Missing argument value in "{s0}"')
    if s[0] == '"':
        res = parse_string(s)
        if res.success:
            assert res.value
            argval, s = res.value
            return Result(success=True, value=(CommandArgument(argname, argval), s))
        else:
            return Result(success=False, logs=res.logs)
        # r = parseString(s)
    elif s[0].isidentifier() or s[0].isalnum() or s[0] in {'.', '/'}:
        argval, s = parse_until_space(s)
        return Result(success=True, value=(CommandArgument(argname, argval), s))
    else:
        return Result(success=False, logs=f'Unexpected argument value in "{s0}"')


def parse_string(s: str) -> Result[tuple[str, str]]:
    assert s[0] == '"'
    i = 1
    last_was_backslash = False
    res = ''
    while i < len(s):
        if last_was_backslash:
            if s[i] in ['"', '\\']:
                res += s[i]
            else:  # assume backslash wasn't use for escaping
                res += '\\' + s[i]
            last_was_backslash = False
        elif s[i] == '\\':
            last_was_backslash = True
        elif s[i] == '"':  # end of string
            return Result(True, (res, s[i + 1:]))
        else:
            res += s[i]
        i += 1
    return Result(False, logs=f'String not closed: "{s}"')


def parse_until_space(s: str) -> tuple[str, str]:
    assert s
    result = s[0]
    i = 1
    while i < len(s):
        if s[i].isspace():
            return result, s[i:]
        else:
            result += s[i]
            i += 1
    return result, ''


def parse_identifier(s: str, canbenum: bool = False, allow_minus: bool = False) -> tuple[str, str]:
    assert s
    assert s[0].isidentifier() or (canbenum and s[0].isalnum()) or s[0] == '?'  # ? for user-defined macros
    identifier = s[0]
    i = 1
    while i < len(s):
        if s[i].isalnum() or s[i].isidentifier() or (allow_minus and s[i] == '-'):  # not '7'.isidentifier()
            identifier += s[i]
            i += 1
        else:
            return identifier, s[i:]
    return identifier, ''


class BasicCommand(object):
    def __init__(self, name: str, args: list[CommandArgument], mainargs: list[str]):
        self.name = name
        self.args = args
        self.mainargs = mainargs

    def gf_format(self, mainarg: Optional[str], mainarg_is_str: bool = False):
        head = f'{self.name} {" ".join([str(a) for a in self.args])}'
        if mainarg:
            return f'{head} {strformat(mainarg) if mainarg_is_str else mainarg}'
        else:
            return head

    def get_val_or_default(self, variants: set[str], default: str) -> str:
        for c in self.args:
            if c.key in variants:
                return c.value
        return default


def argformat(s: str) -> str:
    if s.isidentifier() or s.isalnum():
        return s
    return strformat(s)


def strformat(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def parse_basic_command(string: str, split_mainarg_at_space=False) -> Result[tuple[BasicCommand, str]]:
    string = string.strip()
    commandname, rest = parse_command_name(string.strip())
    command = BasicCommand(commandname, [], [])

    # Args
    while True:
        rest = rest.strip()
        if not rest:
            break
        if rest[0] == '-':
            r = parse_command_arg(rest)
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
    mainarg = ''  # Record main argument
    i = 0
    while i < len(rest):
        if rest[i] == '|':
            # Done :)
            mainarg = mainarg.strip()
            if mainarg:
                command.mainargs.append(mainarg)
            return Result(True, (command, rest[i + 1:]))
        elif rest[i] == '"':
            rr = parse_string(rest[i:])
            if not rr.success:
                return Result(False, None, logs=rr.logs)
            assert rr.value
            rest = rr.value[1]
            command.mainargs.append(rr.value[0])
            i = 0
        elif split_mainarg_at_space and rest[i].isspace():
            mainarg = mainarg.strip()
            if mainarg:
                command.mainargs.append(mainarg)
            mainarg = ''
            i += 1
        else:
            i += 1
            mainarg += rest[i - 1]
    mainarg = mainarg.strip()
    if mainarg:
        command.mainargs.append(mainarg)
    return Result(True, (command, ''))


# OTHER USEFUL THINGS

def _nextup(s, i, s2):
    if len(s) - i < len(s2):
        return 0  # failure
    if s[i:i + len(s2)] == s2:
        return i + len(s2)  # > 0 (assuming s2 != '')
    return 0  # failure


def _skipto(s, i, s2):
    while i < len(s):
        n = _nextup(s, i, s2)
        if n:
            return n
        i += 1
    return -1


def identify_file(s: str) -> Result[tuple[str, str, str]]:  # (type, name, content)
    i = 0
    while True:
        if i == -1 or i >= len(s):
            return Result(False)
        elif s[i].isspace():
            i += 1
        elif _nextup(s, i, '//'):  # mmt comment
            i = _skipto(s, i, '❚')
        elif _nextup(s, i, '--'):  # gf comment
            i = _skipto(s, i, '\n')
        elif _nextup(s, i, '{-'):  # gf block comment
            i = _skipto(s, i, '-}')
        elif _nextup(s, i, '%'):  # elpi comment
            i = _skipto(s, i, '\n')
        elif _nextup(s, i, '/*'):  # elpi block comment
            i = _skipto(s, i, '*/')
        elif _nextup(s, i, 'namespace'):
            i = _skipto(s, i, '❚')
        elif _nextup(s, i, '#'):
            i = _skipto(s, i, '\n')
        else:
            for (k, t) in [('theory', 'mmt-theory'), ('view', 'mmt-view'),
                           ('abstract', 'gf-abstract'), ('concrete', 'gf-concrete'), ('resource', 'gf-resource'),
                           ('interface', 'gf-interface'), ('instance', 'gf-instance'),
                           ('incomplete concrete', 'gf-incomplete concrete'),
                           ('mmt:', 'mmt'), ('elpi:', 'elpi'), ('elpi-notc:', 'elpi-notc'), ('gf:', 'gf'),
                           ('MMT:', 'mmt'), ('ELPI:', 'elpi'), ('ELPI-NOTC:', 'elpi-notc'), ('GF:', 'gf'),
                           ('kind', 'elpi'), ('type', 'elpi'), ('Lexicon', 'lex')]:
                n = _nextup(s, i, k)
                if n:
                    s2 = s[n:].strip()
                    if not s2[0].isidentifier():
                        return Result(False, None, f'Expected identifier after "{k}"')
                    pi = parse_identifier(s2)
                    return Result(True, (t, pi[0], pi[1] if k.endswith(':') else s))
            return Result(False)


def indent(s: str, level: int = 4) -> str:
    return '\n'.join([' ' * level + line for line in s.splitlines()])
