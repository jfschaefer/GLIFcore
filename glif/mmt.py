import os
import subprocess
import glif.utils as utils
from glif.utils import Result
import threading

from typing import Optional

GLIF_BUILD_EXTENSION      = 'info.kwarc.mmt.glf.GlfBuildServer'
GLIF_CONSTRUCT_EXTENSION  = 'info.kwarc.mmt.glf.GlfConstructServer'
ELPI_GENERATION_EXTENSION = 'info.kwarc.mmt.glf.ElpiGenerationServer'



class MathHub(object):
    def __init__(self, mathhubdir: str):
        self.mhdir: str = mathhubdir
        self.archives: dict[str, str] = self.__findArchives(self.mhdir)

    def __findArchives(self, root: str):
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
            archives.update(self.__findArchives(path))  # recurse
        return archives

    def makeArchive(self, archive: str) -> Result[str]:
        if archive in self.archives:
            return Result(False, self.archives[archive], 'archive existed already')
        path = self.mhdir
        for a in archive.split('/'):
            path = os.path.join(path, a)
            if not os.path.isdir(path):
                os.mkdir(path)

        mi = os.path.join(path, 'META-INF')
        if os.path.isdir(mi):
            return Result(False, None, f'{path} already exists')
        os.mkdir(mi)
        self.archives[archive] = path
        with open(os.path.join(mi, 'MANIFEST.MF'), 'w') as f:
            f.write(f'id: {archive}\nnarration-base: http://mathhub.info/{archive}')
        return Result(True, path, '')

    def makeSubdir(self, archive: str, subdir: str) -> Result[str]:
        if not archive in self.archives:
            return Result(False, None, 'archive doesn\'t exist')
        path = self.archives[archive]
        for a in subdir.split('/'):
            path = os.path.join(path, a)
            if not os.path.isdir(path):
                os.mkdir(path)

        return Result(True, path, '')

    def getFilePath(self, archive: str, subdir: Optional[str], filename: str) -> str:
        if subdir:
            return os.path.join(self.archives[archive], subdir.replace('/', os.path.sep), filename)
        return os.path.join(self.archives[archive], filename)


class MMTServer(object):
    def __init__(self, mmt_jar: str):
        self.port = utils.find_free_port()
        extensions = [GLIF_BUILD_EXTENSION, GLIF_CONSTRUCT_EXTENSION, ELPI_GENERATION_EXTENSION]
        cmds = ['extension ' + e for e in extensions] + ['server on ' + str(self.port)]
        args = ['java', '-jar', mmt_jar, '--keepalive', '--shell', ' ; '.join(cmds)]
        pipe = os.pipe()
        self.mmt = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=pipe[1], stderr=pipe[1], text=True)
        self.infile = os.fdopen(pipe[0])
        self.outfd = pipe[1]
        self.mmtlogstart: list[str] = []
        self.mmtlogtail: list[str] = []

        # wait until server started
        for line in self.infile:
            self.mmtlogstart.append(line)
            if 'Server started at' in line:
                break
        self.mmtlogthread = threading.Thread(target=self.__updateMMTlogs)
        self.mmtlogthread.start()
        
    
    def __updateMMTlogs(self):
        for line in self.infile:
            if len(self.mmtlogstart) < 500:
                self.mmtlogstart.append(line)
                continue
            if len(self.mmtlogtail) > 1000:
                self.mmtlogtail = self.mmtlogtail[500:]
            self.mmtlogtail.append(line)


    def do_shutdown(self):
        """ Shuts down the MMT server and the MMT shell """
        self.mmt.stdin.write('server off\nexit\n')
        self.mmt.stdin.close()
        self.mmt.kill()
        os.fdopen(self.outfd).close()    # TODO: Shouldn't it already be closed?
        self.mmtlogthread.join()



class MMTInterface(object):
    def __init__(self, mmtjar: str, mathhub: MathHub):
        self.server: MMTServer = MMTServer(mmtjar)
        self.mh: MathHub = mathhub




