import os
import subprocess
import glif.utils as utils
import threading

GLIF_BUILD_EXTENSION      = 'info.kwarc.mmt.glf.GlfBuildServer'
GLIF_CONSTRUCT_EXTENSION  = 'info.kwarc.mmt.glf.GlfConstructServer'
ELPI_GENERATION_EXTENSION = 'info.kwarc.mmt.glf.ElpiGenerationServer'

class MMTServer(object):
    def __init__(self, mmt_jar):
        self.port = utils.find_free_port()
        extensions = [GLIF_BUILD_EXTENSION, GLIF_CONSTRUCT_EXTENSION, ELPI_GENERATION_EXTENSION]
        cmds = ['extension ' + e for e in extensions] + ['server on ' + str(self.port)]
        args = ['java', '-jar', mmt_jar, '--keepalive', '--shell', ' ; '.join(cmds)]
        pipe = os.pipe()
        self.mmt = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=pipe[1], stderr=pipe[1], text=True)
        self.infile = os.fdopen(pipe[0])
        self.outfd = pipe[1]
        self.mmtlogstart = []
        self.mmtlogtail = []

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
    def __init__(self, mmtjar, mathhubdir):
        pass

