import os
import subprocess
from distutils.spawn import find_executable
from typing import Optional, Literal

from glif.commands.items import Repr, Items
from glif.utils import Result


def runelpi(cwd: str, filename: str, command: str, type_check: bool = True, stdin: str = '',
            args: Optional[list[str]] = None, isjusttypecheck: bool = False,
            filterstderr: Literal['none', 'partial', 'full'] = 'none') -> Result[tuple[str, str]]:
    elpipath = find_executable('elpi')
    if not elpipath:
        return Result(False, None, 'Failed to locate executable "elpi"')

    call = [elpipath, filename, '-exec', command, '-I', os.path.realpath(os.path.dirname(__file__))]
    if not type_check:
        call.append('-no-tc')
    if args:
        call.append('--')
        call += args

    proc = subprocess.Popen(call, text=True,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            cwd=cwd)
    assert proc.stdin
    assert proc.stdout
    assert proc.stderr
    proc.stdin.write(stdin)
    proc.stdin.close()
    out = proc.stdout.read()
    err = proc.stderr.read()
    proc.stderr.close()
    proc.stdout.close()
    proc.wait()
    # if proc.returncode not in [0,1]:   # Why should 1 be acceptable?
    if proc.returncode:
        if isjusttypecheck:
            # TODO: better extract type checking errors (they are sometimes in stderr and sometimes in stdout)
            err = err.strip()
            return Result(False, None,
                          'Typecheck failed:\n' + out + ('\n' + err if not err.endswith('Data.State.Halt') else ''))
        return Result(False, None,
                      'ELPI ERROR: ' + str(
                          proc.returncode) + '\nOUTPUT:\n' + out + '\nERROR:\n' + err + '\nCALL:\n' + str(call))

    if filterstderr != 'none':
        lines: list[str] = []
        for line in err.splitlines():
            if not line:
                continue
            if line.startswith('Parsing time:') or line.startswith('Compilation time:') or \
                    line.startswith('Success:') or line.startswith('Typechecking time:'):
                continue
            if filterstderr == 'full' and (line.startswith('Time:') or line.startswith('Constraints:') or
                                           line.startswith('State:')):
                continue
            lines.append(line)
        err = '\n'.join(lines)
    return Result(True, (out, err))


def items_to_stdin(items: Items, with_ast: bool) -> str:
    expressions = []
    for itemid, item in enumerate(items.items):
        expr = f'glif.mkItem {itemid} {item.original_id} '
        s = item.content.get(Repr.SENTENCE)
        if s is None:
            expr += f'glif.none '
        else:
            expr += f'(glif.some "{s}") '
        for e in [item.content.get(Repr.AST) if with_ast else None, item.content.get(Repr.LOGIC_ELPI)]:
            if e is None:
                expr += f'glif.none '
            else:
                expr += f'(glif.some {e}) '
        expressions.append(expr.strip() + '.')
    stdin = '\n'.join(expressions + ['glif.endofitems.'])
    return stdin
