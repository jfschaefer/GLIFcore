from typing import Optional
from glif.utils import Result
from distutils.spawn import find_executable
from glif import gf
from glif import commands as cmd




class Glif(object):
    def __init__(self, cwd):
        self.cwd = cwd
        self._gfshell: Optional[gf.GFShellRaw] = None
        self._gfshellFailedLogs: Optional[str] = None
        self._commands: dict[str, cmd.CommandType] = {}   # command name -> command type
        self._loadInitialCommands()


    def _loadInitialCommands(self):
        # load GF commands
        for ct in cmd.GF_COMMAND_TYPES:
            for name in ct.names:
                self._commands[name] = ct

    # def executeCommand(self, command: str) -> cmd.Items:




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




