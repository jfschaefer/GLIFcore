import os
from typing import Optional, TypeVar, Generic

T = TypeVar('T')

class Result(Generic[T]):
    def __init__(self, success: bool = False, value: Optional[T] = None, logs: str = ''):
        self.success = success
        self.value = value
        self.logs = logs

    def __str__(self):  # only for debugging
        return f'Success: {self.success}\nValue: {self.value}\nLogs: {self.logs}'

def find_free_port() -> int:
    ''' from https://stackoverflow.com/a/45690594 '''
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
    return Result(False, None, 'Failed to find mmt.jar')

def find_mathhub_dir(mmtjar : str) -> Result[str]:
    path = os.getenv('MATHHUB')
    if path and os.path.isdir(path):
        return Result(True, path, 'Inferred from environment variable MATHHUB')
    
    mmtrc =  os.path.join(os.path.dirname(mmtjar), 'mmtrc')
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
    return Result(False, None, 'Failed to determine MathHub path')


