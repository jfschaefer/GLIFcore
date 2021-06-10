from typing import Optional
from distutils.spawn import find_executable
import glif.gf as gf
import glif.commands as cmd
import glif.parsing as parsing
import glif.mmt as mmt
import glif.utils as utils
from glif.utils import Result
import os
import shutil


DEFAULT_ARCHIVE = 'tmpGLIF/default'


class Glif(object):
    def __init__(self):
        # GF
        self._gfshell: Optional[gf.GFShellRaw] = None
        self._gfshellFailedLogs: Optional[str] = None

        # MMT and MathHub
        self.mmtjar: Optional[str] = None
        self.mh: Optional[mmt.MathHub] = None
        self._mmt: Optional[mmt.MMTInterface] = None
        self._findMMTlogs: list[str] = []
        self._initMMTLocation()

        self.defaultview : Optional[str] = None

        # ELPI
        self.defaultelpi : Optional[str] = None
        self._typecheckelpi : bool = False

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

    def setArchive(self, archive: str, subdir: Optional[str], create: bool = False) -> Result[str]:
        if not self.mh:
            return Result(False, None, 'Error: MathHub folder not found\nLogs:' + parsing.indent('\n'.join(self._findMMTlogs)))
        logs = []
        if archive not in self.mh.archives:
            if create:
                r = self.mh.makeArchive(archive)
                if not r.success:
                    return Result(False, None, f'Error: Failed to create archive {archive}:' + parsing.indent(r.logs))
                logs.append(f'Successfully created archive {archive}')
            else:
                return Result(False, None, f'Error: Archive {archive} doesn\'t exist')
        if subdir and not self.mh.existsSubdir(archive, subdir):
            if create:
                assert self.mh.makeSubdir(archive, subdir).success
                logs.append(f'Successfully created directory {subdir} in archive {archive}')
            else:
                return Result(False, None, f'Error: Archive {archive} doesn\'t have a directory {subdir}')

        self._archive = archive
        self._subdir = subdir
        if self._subdir:
            self.cwd = os.path.join(self.mh.archives[self._archive], 'source', self._subdir)
        else:
            self.cwd = os.path.join(self.mh.archives[self._archive], 'source')
        if self._gfshell:
            self._gfshell.do_shutdown()
            self._gfshell = None
            logs.append('GF shell will be reloaded')
        return Result(True, '\n'.join(logs))

    def getArchiveSubdir(self) -> Result[tuple[str,Optional[str]]]:
        if self._archive:
            return Result(True, (self._archive, self._subdir))
        return Result(False, None, 'No MMT archive selected. This is probably due to problems during the initialization of MMT. Here are the logs:\n' + parsing.indent("\n".join(self._findMMTlogs)))


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

    def getMMT(self) -> Result[mmt.MMTInterface]:
        if self._mmt:
            return Result(True, self._mmt)
        if not (self.mmtjar and self.mh):
            return Result(False, logs = '\n'.join(self._findMMTlogs))
        assert self.mmtjar
        assert self.mh
        self._mmt = mmt.MMTInterface(self.mmtjar, self.mh)
        return Result(True, self._mmt)

    def _loadInitialCommands(self):
        # load GF commands
        for ct in cmd.GF_COMMAND_TYPES + cmd.GLIF_COMMAND_TYPES:
            for name in ct.names:
                self._commands[name] = ct

    def executeCell(self, code: str) -> list[Result[cmd.Items]]:
        fileR = parsing.identifyFile(code)
        if fileR.success:
            assert fileR.value
            type_ = fileR.value[0]
            name = fileR.value[1]
            ending = type_.split('-')[0]  # should be one in 'mmt', 'gf', 'elpi'
            archiveresult = self.getArchiveSubdir()
            if ending == 'mmt' and not archiveresult.success:
                return [Result(False, None, archiveresult.logs)]
            with open(os.path.join(self.cwd, f'{name}.{ending}'), 'w') as fp:
                if type_ in ['mmt-view', 'mmt-theory']:
                    assert archiveresult.value
                    archive, subdir = archiveresult.value
                    fp.write(f'namespace http://mathhub.info/{archive}{"/" + subdir if subdir else ""} ❚')
                elif type_ in ['elpi', 'elpi-notc']:
                    fp.write('accumulate glif. ')
                fp.write(fileR.value[2])
                if type_ in ['elpi', 'elpi-notc']:
                    fp.write('\n\nnamespace glifutil { type success (list string) -> prop. success _. }\n')

            try:
                if type_ == 'elpi':
                    self._typecheckelpi = True
                result = self.executeCommand(f'import "{name}.{ending}"')
            finally:
                self._typecheckelpi = False
            if result.success and type_ == 'mmt-view' and self.defaultview != name:
                if result.logs:
                    result.logs += '\n'
                result.logs += f'"{name}" is the new default view'
                self.defaultview = name

            return [result]

        # TODO: comments and multiple commands
        return self.executeCommands(code)

    def executeCommands(self, code: str) -> list[Result[cmd.Items]]:
        results = []
        currentcommand = ''
        for line in code.splitlines():
            line = line.strip()
            if line.startswith('"') or currentcommand.endswith('|'):
                currentcommand += '\n' + line
                continue
            if line.startswith('--') or line.startswith('//') or line.startswith('#'):
                continue
            if line == '':
                continue
            if currentcommand.strip():
                results.append(self.executeCommand(currentcommand))
            currentcommand = line
        if currentcommand.strip():
            results.append(self.executeCommand(currentcommand))
        if not results:
            return [Result(False, logs=f'No command given')]
        return results

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

    def importGFfile(self, filename: str) -> Result[None]:
        success = True
        logs = []
        gfresult = self.getGfShell()
        if gfresult.success:
            gf = gfresult.value
            assert gf
            r = gf.handle_command(f'import {filename}').strip()
            if r: # Failure
                success = False
                logs.append(f'GF import failed:\n{parsing.indent(r)}')
        else:
            success = False
            logs.append(f'GF import failed:\n{parsing.indent(gfresult.logs)}')

        mmtresult = self.getMMT()
        if mmtresult.success:
            mmt = mmtresult.value
            assert mmt
            assert self._archive
            rr = mmt.buildFile(self._archive, self._subdir, filename)
            if not rr.success and rr.logs:    # We get failures (without logs) for concrete syntaxes
                                              # TODO: Find a better solution!
                logs.append(f'MMT import failed:\n{parsing.indent(rr.logs)}')
                success = False
            if rr.success:
                rrr = mmt.elpigen('types', self._archive, self._subdir, filename + '/' + os.path.splitext(os.path.basename(filename))[0])
                if not rrr.success:
                    logs.append(f'ELPI export failed:\n{parsing.indent(rrr.logs)}')
                    success = False
                else:
                    assert rrr.value
                    with open(os.path.join(self.cwd, os.path.splitext(filename)[0]+'.elpi'), 'w') as fp:
                        fp.write(rrr.value)
        else:
            success = False
            logs.append(f'MMT import failed:\n{parsing.indent(mmtresult.logs)}')

        return Result(success, logs='\n'.join(logs))

    def importMMTfile(self, filename: str) -> Result[None]:
        mmtresult = self.getMMT()
        if mmtresult.success:
            mmt = mmtresult.value
            assert mmt
            assert self._archive
            rr = mmt.buildFile(self._archive, self._subdir, filename)
            if not rr.success:
                return Result(False, logs=rr.logs)
        else:
            return Result(False, logs=f'MMT import failed:\n{parsing.indent(mmtresult.logs)}')
        return Result(True)

    def importELPIfile(self, filename: str) -> Result[None]:
        fullpath = os.path.join(self.cwd, filename)

        # using f'elpi -I {__file__}' instead
        # shutil.copyfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'glif.elpi'),
        #         os.path.join(os.path.dirname(fullpath), 'glif.elpi'))

        if self._typecheckelpi:
            er = utils.runelpi(self.cwd, fullpath, 'glifutil.success')
            if not er.success:
                return Result(False, logs=er.logs)
            assert er.value
            warning = er.value[0].strip()   # stdout should be empty
            if warning:
                return Result(False, logs=warning)

        self.defaultelpi = fullpath
        r: Result[None] = Result(True)
        r.logs = f'{filename} is the new default file for ELPI commands'
        return r

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

        if self._mmt:
            self._mmt.do_shutdown()

