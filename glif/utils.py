import os
from typing import Optional, TypeVar, Generic, Union
from distutils.spawn import find_executable
import subprocess

T = TypeVar('T')


class Result(Generic[T]):
    def __init__(self, success: bool = False, value: Union[None, T] = None, logs: str = ''):
        self.success = success
        self.value = value
        self.logs = logs

    def __str__(self):  # only for debugging
        return f'Success: {self.success}\nValue: {self.value}\nLogs: {self.logs}'


def indent(s: str, n: int = 4) -> str:
    return '    ' + s.replace('\n', '\n' + ' ' * n).strip()


def find_free_port() -> int:
    """ from https://stackoverflow.com/a/45690594 """
    import socket
    from contextlib import closing
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def find_mmt_jar() -> Result[str]:
    jar = os.getenv('MMT_JAR')
    if jar and os.path.isfile(jar):
        return Result(True, jar, 'Inferred from environment variable MMT_JAR')
    path = os.getenv('MMT_PATH')
    if path:
        jar = os.path.join(path, 'deploy', 'mmt.jar')
        if os.path.isfile(jar):
            return Result(True, jar, 'Inferred from environment variable MMT_PATH')
    for jar in [os.path.join(os.path.expanduser('~'), 'MMT', 'deploy', 'mmt.jar'),
                os.path.join(os.path.expanduser('~'), 'MMT', 'systems', 'MMT', 'deploy', 'mmt.jar')]:
        if os.path.isfile(jar):
            return Result(True, jar, 'Lucky guess')
    return Result(False, None, 'Failed to find mmt.jar (tip: set the MMT_JAR environment variable)')


def find_mathhub_dir(mmtjar: str) -> Result[str]:
    path = os.getenv('MATHHUB')
    if path and os.path.isdir(path):
        return Result(True, path, 'Inferred from environment variable MATHHUB')

    mmtrc = os.path.join(os.path.dirname(mmtjar), 'mmtrc')
    if os.path.isfile(mmtrc):
        with open(mmtrc, 'r') as f:
            for line in f:
                if not line.startswith('mathpath '):
                    continue
                path = line.strip().split(' ')[1]
                if os.path.isdir(path):
                    return Result(True, path, 'Inferred from mmtrc mathpath')

    path = os.path.join(os.path.dirname(mmtjar), '..', '..', '..', 'MMT-content')
    if os.path.isdir(path):
        return Result(True, os.path.realpath(path), 'Guessed from location of mmt.jar')
    return Result(False, None, 'Failed to determine MathHub path (tip: set the MATHHUB environment variable)')


def dot2svg(dot: bytes) -> Result[bytes]:
    dotpath = find_executable('dot')
    if not dotpath:
        return Result(False, None, 'Failed to locate executable "dot"')

    proc = subprocess.Popen([dotpath, '-Tsvg'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    assert proc.stdin
    assert proc.stdout
    proc.stdin.write(dot)
    proc.stdin.close()
    svg = proc.stdout.read()
    proc.stdout.close()
    proc.wait()
    return Result(True, svg)


def runelpi(cwd: str, filename: str, command: str, type_check: bool = True, stdin: str = '',
            args: Optional[list[str]] = None, isjusttypecheck: bool = False) -> Result[tuple[str, str]]:
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
    return Result(True, (out, err))
