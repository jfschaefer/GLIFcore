from typing import Optional
from glif.utils import Result
from distutils.spawn import find_executable
from glif import gf
from glif import commands as cmd
from glif import mmt
from glif import utils
import os


DEFAULT_ARCHIVE = 'tmpGLIF/default'


class Glif(object):
    def __init__(self):
        # GF
        self._gfshell: Optional[gf.GFShellRaw] = None
        self._gfshellFailedLogs: Optional[str] = None

        # MMT and MathHub
        self.mmtjar: Optional[str] = None
        self.mh: Optional[mmt.MathHub] = None
        self._findMMTlogs: list[str] = []
        self._initMMTLocation()


        self._archive: Optional[str] = None
        self._subdir: Optional[str] = None
        if self.mh:
            if DEFAULT_ARCHIVE not in self.mh.archives:
                assert self.mh.makeArchive(DEFAULT_ARCHIVE).success
            self.cwd = os.path.join(self.mh.archives[DEFAULT_ARCHIVE], 'source')
            self._archive = DEFAULT_ARCHIVE
        else:
            self.cwd = os.getcwd()
        self._commands: dict[str, cmd.CommandType] = {}   # command name -> command type
        self._loadInitialCommands()

    def _initMMTLocation(self):
        # JAR
        mmtjar = utils.find_mmt_jar()
        self._findMMTlogs.append('Finding mmt.jar: "' + mmtjar.logs + '"')
        if not mmtjar.success:
            return
        assert mmtjar.value
        self._findMMTlogs.append('Location: ' + mmtjar.value)
        self.mmtjar = mmtjar.value

        # MH
        self._findMMTlogs.append('Finding MathHub: "' + mmtjar.logs + '"')
        mhdir = utils.find_mathhub_dir(self.mmtjar)
        if not mhdir.success:
            return
        assert mhdir.value
        self._findMMTlogs.append('Location: ' + mhdir.value)
        self.mh = mmt.MathHub(mhdir.value)


    def _loadInitialCommands(self):
        # load GF commands
        for ct in cmd.GF_COMMAND_TYPES:
            for name in ct.names:
                self._commands[name] = ct

    def executeCommand(self, command: str) -> Result[cmd.Items]:
        items = None
        rest = command.strip()
        while rest:
            if ' ' in rest:
                name = rest[:rest.find(' ')]
            else:
                name = rest
            if not name in self._commands:
                return Result(False, logs=f'Unkown command "{name}"')

            r = self._commands[name].fromString(rest)
            if not r.success:
                return Result(False, logs=r.logs)
            assert r.value
            cmd, rest = r.value
            if items:
                items = cmd.apply(self, items)
            else:
                items = cmd.execute(self)
            rest = rest.strip()

        if not items:
            return Result(False, logs=f'No command given')

        return Result(True, value=items)

    def getGfShell(self) -> Result[gf.GFShellRaw]:
        if not self._gfshell and self._gfshellFailedLogs is None:
            place = find_executable('gf')
            if place:
                self._gfshell = gf.GFShellRaw(place, cwd = self.cwd)
            else:
                self._gfshellFailedLogs = 'Failed to locate executable "gf"'
        if self._gfshell:
            return Result(True, self._gfshell)
        else:
            assert self._gfshellFailedLogs
            return Result(False, logs=self._gfshellFailedLogs)

    def do_shutdown(self):
        if self._gfshell:
            self._gfshell.do_shutdown()



