from typing import Optional
from distutils.spawn import find_executable

import glif.commands.items
from . import gf, mmt, parsing, utils, glif_abc, stub_gen
from . import commands as cmd
import os

from .utils import Result

DEFAULT_ARCHIVE = 'tmpGLIF/default'


class Glif(glif_abc.GlifABC):
    def __init__(self):
        # GF
        self._gfshell: Optional[gf.GFShellRaw] = None
        self._gfshellFailedLogs: Optional[str] = None

        # MMT and MathHub
        self.mmtjar: Optional[str] = None
        self.mh: Optional[mmt.MathHub] = None
        self._mmt: Optional[mmt.MMTInterface] = None
        self._findMMTlogs: list[str] = []
        self._mmtFailedStartupLogs: list[str] = []
        self._mmtFailedStartupMessage: Optional[str] = None
        self._init_mmt_location()

        self._defaultview: Optional[str] = None

        # ELPI
        self._defaultelpi: Optional[str] = None
        self._typecheckelpi: bool = False

        self._archive: Optional[str] = None
        self._subdir: Optional[str] = None
        self._cwd: str
        if self.mh:
            if DEFAULT_ARCHIVE not in self.mh.archives:
                assert self.mh.make_archive(DEFAULT_ARCHIVE).success
            self._cwd = os.path.join(self.mh.archives[DEFAULT_ARCHIVE], 'source')
            self._archive = DEFAULT_ARCHIVE
        else:
            self._cwd = os.getcwd()
        self._commands: dict[str, cmd.command.CommandType] = {}  # command name -> command type
        self._load_initial_commands()

    def set_archive(self, archive: str, subdir: Optional[str], create: bool = False) -> Result[str]:
        if not self.mh:
            return Result(False, None,
                          'Error: MathHub folder not found\nLogs:' + parsing.indent('\n'.join(self._findMMTlogs)))
        logs = []
        new_archive_created = False
        if archive not in self.mh.archives:
            if create:
                r = self.mh.make_archive(archive)
                if not r.success:
                    return Result(False, None, f'Error: Failed to create archive {archive}:' + parsing.indent(r.logs))
                logs.append(f'Successfully created archive {archive}')
                new_archive_created = True
            else:
                return Result(False, None, f'Error: Archive {archive} doesn\'t exist')
        if subdir and not self.mh.exists_subdir(archive, subdir):
            if create:
                assert self.mh.make_subdir(archive, subdir).success
                logs.append(f'Successfully created directory {subdir} in archive {archive}')
            else:
                return Result(False, None, f'Error: Archive {archive} doesn\'t have a directory {subdir}')

        self._archive = archive
        self._subdir = subdir
        if self._subdir:
            self._cwd = os.path.join(self.mh.archives[self._archive], 'source', self._subdir)
        else:
            self._cwd = os.path.join(self.mh.archives[self._archive], 'source')
        if new_archive_created and self._mmt:
            self._mmt.do_shutdown()
            self._mmt = None
            self._mmtFailedStartupLogs = []
            self._mmtFailedStartupMessage = None
            logs.append('MMT will be reloaded')
        if self._gfshell:
            self._gfshell.do_shutdown()
            self._gfshell = None
            logs.append('GF shell will be reloaded')
        return Result(True, '\n'.join(logs))

    def get_archive_subdir(self) -> Result[tuple[str, Optional[str]]]:
        if self._archive:
            return Result(True, (self._archive, self._subdir))
        return Result(False, None,
                      'No MMT archive selected. This is probably due to problems during the initialization of MMT. '
                      'Here are the logs:\n' + parsing.indent("\n".join(self._findMMTlogs)))

    def get_defaultview(self) -> Optional[str]:
        return self._defaultview

    def get_defaultelpi(self) -> Optional[str]:
        return self._defaultelpi

    def get_commands(self) -> dict[str, cmd.command.CommandType]:
        return self._commands

    def get_cwd(self) -> str:
        return self._cwd

    def _init_mmt_location(self):
        # JAR
        mmtjar = utils.find_mmt_jar()
        self._findMMTlogs.append('Finding mmt.jar: "' + mmtjar.logs + '"')
        if not mmtjar.success:
            return
        assert mmtjar.value
        self._findMMTlogs.append('Location: ' + mmtjar.value)
        self.mmtjar = mmtjar.value

        # MH
        mhdir = utils.find_mathhub_dir(self.mmtjar)
        self._findMMTlogs.append('Finding MathHub: "' + mhdir.logs + '"')
        if not mhdir.success:
            return
        assert mhdir.value
        self._findMMTlogs.append('Location: ' + mhdir.value)
        self.mh = mmt.MathHub(mhdir.value)

    def get_mmt(self) -> Result[mmt.MMTInterface]:
        if self._mmt:
            return Result(True, self._mmt)
        if not (self.mmtjar and self.mh):
            return Result(False, logs='\n'.join(self._findMMTlogs))
        assert self.mmtjar
        assert self.mh
        try:
            self._mmt = mmt.MMTInterface(self.mmtjar, self.mh)
        except mmt.MMTStartupException as ex:
            self._mmtFailedStartupLogs = ex.logs
            self._mmtFailedStartupMessage = ex.message
            return Result(False, logs=ex.message)
        return Result(True, self._mmt)

    def _load_initial_commands(self):
        for ct in cmd.GLIF_COMMAND_TYPES + cmd.GF_COMMAND_TYPES:
            for name in ct.names:
                self._commands[name] = ct

    def execute_cell(self, code: str) -> list[Result[glif.commands.items.Items]]:
        file_r = parsing.identify_file(code)
        if file_r.success:
            assert file_r.value
            type_ = file_r.value[0]
            name = file_r.value[1]
            ending = type_.split('-')[0]  # should be one in 'mmt', 'gf', 'elpi'
            archiveresult = self.get_archive_subdir()
            if ending == 'mmt' and not archiveresult.success:
                return [Result(False, None, archiveresult.logs)]
            with open(os.path.join(self._cwd, f'{name}.{ending}'), 'w', encoding='utf8') as fp:
                if type_ in ['mmt-view', 'mmt-theory']:
                    assert archiveresult.value
                    archive, subdir = archiveresult.value
                    fp.write(f'namespace http://mathhub.info/{archive}{"/" + subdir if subdir else ""} ❚')
                elif type_ in ['elpi', 'elpi-notc']:
                    fp.write('accumulate glif. ')
                fp.write(file_r.value[2])
                if type_ in ['elpi', 'elpi-notc']:
                    fp.write('\n\nnamespace glifutil { type success (list string) -> prop. success _. }\n')

            try:
                if type_ == 'elpi':
                    self._typecheckelpi = True
                result = self.execute_command(f'import "{name}.{ending}"')
            finally:
                self._typecheckelpi = False
            if result.success and type_ == 'mmt-view' and self._defaultview != name:
                if result.logs:
                    result.logs += '\n'
                result.logs += f'"{name}" is the new default view'
                self._defaultview = name

            return [result]

        # TODO: comments and multiple commands
        return self.execute_commands(code)

    def execute_commands(self, code: str) -> list[Result[glif.commands.items.Items]]:
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
                results.append(self.execute_command(currentcommand))
            currentcommand = line
        if currentcommand.strip():
            results.append(self.execute_command(currentcommand))
        if not results:
            return [Result(False, logs=f'No command given')]
        return results

    def execute_command(self, command: str) -> Result[glif.commands.items.Items]:
        items = None
        rest = command.strip()
        while rest:
            if ' ' in rest:
                name = rest[:rest.find(' ')]
            else:
                name = rest
            if name not in self._commands:
                return Result(False, logs=f'Unkown command "{name}"')

            r = self._commands[name].from_string(rest)
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

    def import_gf_file(self, filename: str) -> Result[None]:
        success = True
        logs = []
        gfresult = self.get_gf_shell()
        if gfresult.success:
            gf = gfresult.value
            assert gf
            r = gf.handle_command(f'import {filename}').strip()
            if r and not r.startswith('Abstract changed'):  # Failure
                success = False
                logs.append(f'GF import failed:\n{parsing.indent(r)}')
        else:
            success = False
            logs.append(f'GF import failed:\n{parsing.indent(gfresult.logs)}')

        mmtresult = self.get_mmt()
        if mmtresult.success:
            mmt = mmtresult.value
            assert mmt
            assert self._archive
            rr = mmt.build_file(self._archive, self._subdir, filename)
            if not rr.success and rr.logs:  # We get failures (without logs) for concrete syntaxes
                # TODO: Find a better solution!
                logs.append(f'MMT import failed:\n{parsing.indent(rr.logs)}')
                success = False
            if rr.success:
                rrr = mmt.elpigen('types', self._archive, self._subdir,
                                  filename + '/' + os.path.splitext(os.path.basename(filename))[0])
                if not rrr.success:
                    logs.append(f'ELPI export failed:\n{parsing.indent(rrr.logs)}')
                    success = False
                else:
                    assert rrr.value is not None
                    with open(os.path.join(self._cwd, os.path.splitext(filename)[0] + '.elpi'), 'w',
                              encoding='utf8') as fp:
                        fp.write(rrr.value)
        else:
            success = False
            logs.append(f'MMT import failed:\n{parsing.indent(mmtresult.logs)}')

        return Result(success, logs='\n'.join(logs))

    def import_mmt_file(self, filename: str) -> Result[None]:
        mmtresult = self.get_mmt()
        if mmtresult.success:
            mmt = mmtresult.value
            assert mmt
            assert self._archive
            rr = mmt.build_file(self._archive, self._subdir, filename)
            if not rr.success:
                return Result(False, logs=rr.logs)
        else:
            return Result(False, logs=f'MMT import failed:\n{parsing.indent(mmtresult.logs)}')
        return Result(True)

    def import_elpi_file(self, filename: str) -> Result[None]:
        fullpath = os.path.join(self._cwd, filename)

        # using f'elpi -I {__file__}' instead
        # shutil.copyfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'glif.elpi'),
        #         os.path.join(os.path.dirname(fullpath), 'glif.elpi'))

        if self._typecheckelpi:
            er = utils.runelpi(self._cwd, fullpath, 'glifutil.success')
            if not er.success:
                return Result(False, logs=er.logs)
            assert er.value
            warning = er.value[0].strip()  # stdout should be empty
            if warning:
                return Result(False, logs=warning)

        self._defaultelpi = fullpath
        r: Result[None] = Result(True)
        r.logs = f'{filename} is the new default file for ELPI commands'
        return r

    def get_gf_shell(self) -> Result[gf.GFShellRaw]:
        if not self._gfshell and self._gfshellFailedLogs is None:
            place = find_executable('gf')
            if place:
                self._gfshell = gf.GFShellRaw(place, cwd=self._cwd)
            else:
                self._gfshellFailedLogs = 'Failed to locate executable "gf"'
        if self._gfshell:
            return Result(True, self._gfshell)
        else:
            assert self._gfshellFailedLogs
            return Result(False, logs=self._gfshellFailedLogs)

    def stub_gen(self, target: str) -> Result[str]:
        archiveresult = self.get_archive_subdir()
        if archiveresult.success:
            assert archiveresult.value
            archive, subdir = archiveresult.value
            base = f'http://mathhub.info/{archive}{"/" + subdir if subdir else ""}'
            return stub_gen.generate(target, self.get_cwd(), base)
        elif target.startswith('concrete'):
            return stub_gen.generate(target, self.get_cwd(), None)
        else:
            return Result(False, None, archiveresult.logs)

    def do_shutdown(self):
        if self._gfshell:
            self._gfshell.do_shutdown()

        if self._mmt:
            self._mmt.do_shutdown()
