from typing import Optional
from glif.utils import Result
from distutils.spawn import find_executable
from glif import gf




class Glif(object):
    # This is all temporary
    def __init__(self, cwd):
        self.cwd = cwd
        self._gfshell: Optional[gf.GFShellRaw] = None
        self._gfshellFailedLogs: Optional[str] = None


    def getGfShell(self) -> Result[gf.GFShellRaw]:
        # TODO: may fail, if GF shell cannot be loaded
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





