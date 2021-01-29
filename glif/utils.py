import os
from typing import Optional

def find_free_port() -> int:
    ''' from https://stackoverflow.com/a/45690594 '''
    import socket
    from contextlib import closing
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def find_mmt_jar() -> Optional[tuple[str, str]]:
    jar = os.getenv('MMT_JAR')
    if jar and os.path.isfile(jar):
        return (jar, 'Inferred from environment variable MMT_JAR')
    path = os.getenv('MMT_PATH')
    if path:
        jar = os.path.join(path, 'deploy', 'mmt.jar')
        if os.path.isfile(jar):
            return (jar, 'Inferred from environment variable MMT_PATH')
    for jar in [os.path.join(os.path.expanduser('~'), 'MMT', 'deploy', 'mmt.jar'),
                os.path.join(os.path.expanduser('~'), 'MMT', 'systems', 'MMT', 'deploy', 'mmt.jar')]:
        if os.path.isfile(jar):
            return (jar, 'Lucky guess')
    return None

def find_mathhub_dir(mmtjar : str) -> Optional[tuple[str, str]]:
    path = os.getenv('MATHHUB')
    if path and os.path.isdir(path):
        return (path, 'Inferred from environment variable MATHHUB')
    
    mmtrc =  os.path.join(os.path.dirname(mmtjar), 'mmtrc')
    if os.path.isfile(mmtrc):
        with open(mmtrc, 'r') as f:
            for line in f:
                if not line.startswith('mathpath '):
                    continue
                path = line.strip().split(' ')[1]
                if os.path.isdir(path):
                    return (path, 'Inferred from mmtrc mathpath')

    path = os.path.join(os.path.dirname(mmtjar), '..', '..', '..', 'MMT-content')
    if os.path.isdir(path):
        return (path, 'Guessed from location of mmt.jar')
    return None

