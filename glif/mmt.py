import os
import requests
import subprocess
import simplejson.errors  # type: ignore
import xml.etree.ElementTree as ET  # need XML processing for uncaught MMT exceptions
import threading
from typing import Optional, Any

from . import utils
from .utils import Result

GLIF_BUILD_EXTENSION = 'info.kwarc.mmt.glf.GlfBuildServer'
GLIF_CONSTRUCT_EXTENSION = 'info.kwarc.mmt.glf.GlfConstructServer'
GLIF_ACCUMULATE_EXTENSION = 'info.kwarc.mmt.glf.GlfAccumulateServer'
ELPI_GENERATION_EXTENSION = 'info.kwarc.mmt.glf.ElpiGenerationServer'
MMT_STARTUP_TIMEOUT = 20


class MathHub(object):
    def __init__(self, mathhubdir: str):
        self.mhdir: str = mathhubdir
        self.archives: dict[str, str] = self.__find_archives(self.mhdir)

    def __find_archives(self, root: str):
        archives = {}
        for p in os.listdir(root):
            path = os.path.join(root, p)
            if not os.path.isdir(path):
                continue
            mf = os.path.join(path, 'META-INF', 'MANIFEST.MF')
            if os.path.isfile(mf):
                with open(mf, 'r') as fp:
                    k = None
                    for line in fp:
                        if line.startswith('id: '):
                            k = line.strip().split(' ')[1]
                            break
                    if k:
                        archives[k] = path
                continue
            archives.update(self.__find_archives(path))  # recurse
        return archives

    def make_archive(self, archive: str) -> Result[str]:
        if archive in self.archives:
            return Result(False, self.archives[archive], 'archive existed already')
        path = self.mhdir
        for a in archive.split('/'):
            path = os.path.join(path, a)
            if not os.path.isdir(path):
                os.mkdir(path)

        sourcedir = os.path.join(path, 'source')
        if not os.path.isdir(sourcedir):
            os.mkdir(sourcedir)

        mfdir = os.path.join(path, 'META-INF')
        if os.path.isdir(mfdir):
            return Result(False, None, f'{path} already exists')
        os.mkdir(mfdir)
        self.archives[archive] = path
        with open(os.path.join(mfdir, 'MANIFEST.MF'), 'w') as f:
            f.write(f'id: {archive}\nnarration-base: http://mathhub.info/{archive}')
        return Result(True, path, '')

    def exists_subdir(self, archive: str, subdir: str) -> bool:
        return os.path.isdir(os.path.join(self.archives[archive], 'source', subdir))

    def make_subdir(self, archive: str, subdir: str) -> Result[str]:
        if archive not in self.archives:
            return Result(False, None, 'archive doesn\'t exist')
        path = os.path.join(self.archives[archive], 'source')
        for a in subdir.split('/'):
            path = os.path.join(path, a)
            if not os.path.isdir(path):
                os.mkdir(path)

        return Result(True, path, '')

    def get_file_path(self, archive: str, subdir: Optional[str], filename: str) -> str:
        if subdir:
            return os.path.join(self.archives[archive], 'source', subdir.replace('/', os.path.sep), filename)
        return os.path.join(self.archives[archive], 'source', filename)


class MMTStartupException(Exception):
    def __init__(self, message, logs):
        Exception.__init__(self, message)
        self.message = message
        self.logs = logs


class MMTServer(object):
    def __init__(self, mmt_jar: str):
        self.port = utils.find_free_port()
        extensions = [GLIF_BUILD_EXTENSION,
                GLIF_CONSTRUCT_EXTENSION,
                # GLIF_ACCUMULATE_EXTENSION, # TODO not working right now
                ELPI_GENERATION_EXTENSION,
        ]
        cmds = ['show version'] + ['extension ' + e for e in extensions] + ['server on ' + str(self.port)]
        args = ['java', '-jar', mmt_jar, '--keepalive', '--shell', ' ; '.join(cmds)]
        pipe = os.pipe()
        self.mmt = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=pipe[1], stderr=pipe[1], text=True, shell=False)
        self.infile = os.fdopen(pipe[0])
        self.outfd = pipe[1]
        self.mmtlogstart: list[str] = []
        self.mmtlogtail: list[str] = []

        self.serverStarted = False

        def start_server():
            for line in self.infile:
                self.mmtlogstart.append(line)
                if 'Server started at' in line:
                    self.serverStarted = True
                    break
                if 'error:' in line:
                    break

        start_thread = threading.Thread(target=start_server)
        start_thread.start()
        start_thread.join(timeout=MMT_STARTUP_TIMEOUT)

        if not self.serverStarted:
            assert self.mmt.stdin
            self.mmt.stdin.close()
            os.fdopen(self.outfd).close()
            self.mmt.terminate()  # TODO: This doesn't seem to kill the process...
            if start_thread.is_alive():
                start_thread.join()
                raise MMTStartupException(f'MMT startup timed out after {MMT_STARTUP_TIMEOUT} seconds',
                                          self.mmtlogstart)
            else:
                raise MMTStartupException('Failed to start MMT', self.mmtlogstart)

        self.mmtlogthread = threading.Thread(target=self.__update_mmt_logs)
        self.mmtlogthread.start()

    def __update_mmt_logs(self):
        for line in self.infile:
            if len(self.mmtlogstart) < 500:
                self.mmtlogstart.append(line)
                continue
            if len(self.mmtlogtail) > 1000:
                self.mmtlogtail = self.mmtlogtail[500:]
            self.mmtlogtail.append(line)

    def do_shutdown(self):
        """ Shuts down the MMT server and the MMT shell """
        assert self.mmt.stdin is not None
        self.mmt.stdin.write('server off\nexit\n')
        self.mmt.stdin.close()
        self.mmt.kill()
        os.fdopen(self.outfd).close()  # TODO: Shouldn't it already be closed?
        self.mmtlogthread.join()

    def post_request(self, extension: str, json: Any) -> Result[Any]:
        url = f'http://127.0.0.1:{self.port}/:{extension}'
        try:
            response = requests.post(url, json=json)
        except requests.exceptions.ConnectionError:
            return Result(False, None, 'Connection error when trying to reach ' + url)

        # TODO: Check headers for content-type to see if it's xml/json?
        try:
            # Ideally we would check for the status code.
            # Unfortunately, MMT also returns 200 for uncaught exceptions :/
            # https://github.com/UniFormal/MMT/issues/329
            return Result(True, response.json(), '')
        except simplejson.errors.JSONDecodeError:
            # probably an uncaught MMT exception, which is XML
            try:
                return Result(False, None, '\n'.join(ET.fromstring(response.text).itertext()))
            except ET.ParseError:
                return Result(False, None, response.text)


class MMTInterface(object):
    def __init__(self, mmtjar: str, mathhub: MathHub):
        self.server: MMTServer = MMTServer(mmtjar)
        self.mh: MathHub = mathhub

    def build_file(self, archive: str, subdir: Optional[str], filename: str) -> Result[None]:
        result = self.server.post_request('glf-build',
                                          json={
                                              'archive': archive,
                                              'file': '/'.join([subdir, filename]) if subdir else filename,
                                          })

        if result.success:  # request was successful
            response: Any = result.value
            if response['isSuccessful']:
                return Result(True)
            return Result(False, None, '\n'.join(response['errors']))
        return Result(False, None, result.logs)

    def construct(self, ASTs: list[str], archive: str, subdir: Optional[str], view: str,
                  delta_expand: bool = False, simplify: bool = True) -> Result[dict[str, list[str]]]:
        result = self.server.post_request(
            'glf-construct',
            json={
                'semanticsView': f'http://mathhub.info/{archive}{"/" + subdir if subdir else ""}/{view}',
                'ASTs': ASTs,
                'deltaExpansion': delta_expand,
                'simplify': simplify,
                'version': 2,
            }
        )

        if result.success:  # request was successful
            response: Any = result.value
            if response['isSuccessful']:
                return Result(True, response['result'], '\n'.join(response['errors']))
            return Result(False, None, '\n'.join(response['errors']))
        return Result(False, None, result.logs)

    def populate(self, terms: list[str], archive: str, subdir: Optional[str], meta_theory: str,
                 name: str = 'generated', mode: str = 'default') -> Result[dict[str, str]]:
        if '/' not in meta_theory:
            meta_theory = f'http://mathhub.info/{archive}{"/" + subdir if subdir else ""}/{meta_theory}'
        result = self.server.post_request(
            'glf-accumulate',
            json={
                'terms': terms,
                'mode': mode,
                'metatheory': meta_theory,
                'theorypath': f'http://mathhub.info/{archive}{"/" + subdir if subdir else ""}/{name}',
                'version': 1,
            }
        )
        if result.success:  # request was successful
            response: Any = result.value
            if response['isSuccessful']:
                return Result(True, response, '\n'.join(response['errors']))
            return Result(False, None, '\n'.join(response['errors']))
        return Result(False, None, result.logs)

    def elpigen(self, mode: str, archive: str, subdir: Optional[str], theory: str,
                meta: bool = False, includes: bool = True) -> Result[str]:
        result = self.server.post_request(
            'glif-elpigen',
            json={
                'theory': f'http://mathhub.info/{archive}{"/" + subdir if subdir else ""}/{theory}',
                'mode': mode,
                'follow-meta': meta,
                'follow-includes': includes,
                'version': 2,
            }
        )
        if result.success:  # request was successful
            response: Any = result.value
            if response['isSuccessful']:
                return Result(True, response['result'], '\n'.join(response['errors']))
            return Result(False, None, '\n'.join(response['errors']))
        return Result(False, None, result.logs)

    def do_shutdown(self):
        self.server.do_shutdown()
