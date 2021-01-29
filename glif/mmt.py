import os
import subprocess
import glif.utils as utils
import threading

GLIF_BUILD_EXTENSION      = 'info.kwarc.mmt.glf.GlfBuildServer'
GLIF_CONSTRUCT_EXTENSION  = 'info.kwarc.mmt.glf.GlfConstructServer'
ELPI_GENERATION_EXTENSION = 'info.kwarc.mmt.glf.ElpiGenerationServer'

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
    def __init__(self, mmtjar: str, mathhubdir: str):
        self.server: MMTServer = MMTServer(mmtjar)
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



