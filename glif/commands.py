from typing import Optional, Callable
from glif.utils import Result, runelpi
from glif.parsing import *
from enum import Enum
import os
import html
from distutils.spawn import find_executable
import subprocess


class Repr(Enum):
    ''' Different representations of item content '''
    HTML           = 'html'                         # HTML representation (available for certain GLIF commands), has to coincide with DEFAULT
    DEFAULT        = 'default'
    SENTENCE_ORIG  = 'original sentence'
    SENTENCE       = 'current sentence'
    AST            = 'abstract syntax tree'
    LOGIC_PLAIN    = 'logical expression (plain)'   # MMT without notations
    LOGIC_STANDARD = 'logical expression'           # MMT with notations
    LOGIC_ELPI     = 'logical expression (elpi)'    # ELPI
    GRAPH_DOT      = 'graph-dot'                    # graph in dot format
    GRAPH_SVG      = 'graph-svg'                    # graph in svg format

class Item(object):
    ''' Something that can be passed between commands (AST, sentence, logical expression, ...).
        Note that an item may have multiple representations simultaneously (e.g. a string and an AST).
    '''
    def __init__(self, original_id):
        self.errors: list[str] = []
        self.original_id: int = original_id
        self.content: dict[Repr, str] = {}
        self.currentRepr: Repr = None

    def tryGetRepr(self, r: Repr) -> Result[str]:
        if r in self.content:
            return Result(True, self.content[r], '\n'.join(self.errors))
        else:
            message = f'Expected representation [{r}], falling back to [{Repr.DEFAULT}]'
            message += '\nAvailable representations: ' + ' '.join([f'[{rr}]' for rr in self.content])
            return Result(False, self.content[Repr.DEFAULT], '\n'.join(self.errors + [message]))

    def withRepr(self, r: Repr, val: str, updateDefault: bool = True, htmlVersion: Optional[str] = None) -> 'Item':
        ''' doesn't clone! '''
        assert r != Repr.HTML
        if updateDefault:
            self.content[Repr.DEFAULT] = val
        self.content[r] = val
        self.currentRepr = r
        if htmlVersion:
            self.content[Repr.HTML] = htmlVersion
        elif Repr.HTML in self.content:
            del self.content[Repr.HTML]
        return self

    def getClone(self) -> 'Item':
        i = Item(self.original_id)
        i.errors = self.errors[:]
        i.content = self.content.copy()
        return i

    def html(self) -> str:
        s = ''
        if Repr.HTML in self.content:
            s += self.content[Repr.HTML]
        elif Repr.DEFAULT in self.content:
            s += '<span class="glif-stdout">' + html.escape(self.content[Repr.DEFAULT]).replace('\n', '<br/>') + '</span>'
        if self.errors:
            s += '\n<br/><span class="glif-stderr"><b>Errors</b><br/>' + '<br/>'.join(self.errors) + '</span>'
        return s

    def __str__(self):
        if not Repr.DEFAULT in self.content:
            return '[Item has no default representation]'
        s = self.content[Repr.DEFAULT]
        if self.errors:
            return 'Errors:\n    ' + '\n    '.join(self.errors) + '\n' + s
        return s



class Items(object):
    ''' A collection of `Item` objects '''
    def __init__(self, items: list[Item]):
        self.items : list[Item] = items
        self.errors : list[str] = []

    @classmethod
    def fromVals(self, repr_: Repr, vals: list[str]) -> 'Items':
        items = Items([])
        for i, v in enumerate(vals):
            item = Item(i).withRepr(repr_, v)
            if repr_ == Repr.SENTENCE:
                item.content[Repr.SENTENCE_ORIG] = v
            items.items.append(item)
        return items

    def merge(self, items: 'Items'):
        self.items = self.items + items.items
        self.errors = self.errors + items.errors

    def withErrors(self, errors: list[str]) -> 'Items':
        self.errors = self.errors + errors
        return self

    def html(self) -> str:
        s = '<br/>'.join([i.html() for i in self.items])
        if self.errors:
            s += '\n<br/><span class="glif-stderr"><b>Errors</b><br/>' + '<br/>'.join(self.errors) + '</span>'
        return s

    def __str__(self):
        items = '\n'.join([str(item) for item in self.items])
        if self.errors:
            return '\n'.join(self.errors) + '\n\n' + items
        return items


import glif.Glif as Glif

class Command(object):
    is_executable: bool = False
    is_applicable: bool = False

    def execute(self, glif: 'Glif.Glif') -> Items:
        ''' If no input is/can provided '''
        assert self.is_executable
        return Items([])

    def apply(self, glif: 'Glif.Glif', items: Items) -> Items:
        ''' If input is provided (`items`) '''
        assert self.is_applicable
        newItems = Items([])
        newItems.errors = items.errors
        for item in items.items:
            newItems.merge(self._applyItem(glif, item))
        return newItems

    def _applyItem(self, glif: 'Glif.Glif', item: Item) -> Items:
        raise NotImplementedError()



class CommandType(object):
    def __init__(self, names: list[str]):
        self.names: list[str] = names         # Command names, e.g. ['view_tree', 'vt']

    def fromString(self, string: str) -> Result[tuple[Command, str]]:
        ''' returns (concrete command, remaining string (in case of pipes)). '''
        raise NotImplementedError()

    def _getShortDescr(self) -> str:
        return ''

    def _getLongDescr(self) -> str:
        return ''


# GF COMMANDS

class GfCommand(Command):
    ''' for standard GF commands '''
    def __init__(self, bc : BasicCommand, inrepr: Repr, outrepr: Repr):
        self.bc = bc

        self.is_executable = True
        self.is_applicable = True

        self.inrepr = inrepr
        self.outrepr = outrepr

    def handleShellOutput(self, out: str) -> tuple[list[str], list[str]]:    # (outputs, errors)
        # TODO: Implement this properly (error filtering, ...)
        if self.outrepr == Repr.GRAPH_DOT:
            return ([out], [])
        return ([s.strip() for s in out.splitlines()], [])

    def execute(self, glif):
        assert self.is_executable
        if self.bc.mainargs:
            items = Items.fromVals(self.inrepr, self.bc.mainargs)
            return self.apply(glif, items)

        gfshell = glif.getGfShell()
        if gfshell.success:
            assert gfshell.value
            output = gfshell.handle_command(bc.gfFormat(None))
            # TODO: better output handling
            vals, errs = self.handleShellOutput(output)
            return Items.fromVals(self.outrepr, vals).withErrors(errs)
        else:
            return Items([]).withErrors([gfshell.logs])

    def _applyItem(self, glif, item):
        inp = item.tryGetRepr(self.inrepr)
        assert inp.value
        gfshell = glif.getGfShell()
        if not gfshell.success:
            return Items([]).withErrors(item.errors + [gfshell.logs])
        assert gfshell.value
        output = gfshell.value.handle_command(self.bc.gfFormat(inp.value, self.inrepr != Repr.AST))

        vals, errs = self.handleShellOutput(output)
        items = Items([]).withErrors(errs)
        for val in vals:
            items.items.append(item.getClone().withRepr(self.outrepr, val))
        return items


class GfCommandType(CommandType):
    ''' for standard GF commands '''
    def __init__(self, names: list[str], inrepr : Repr, outrepr : Repr):
        CommandType.__init__(self, names)
        self.inrepr = inrepr
        self.outrepr = outrepr

    def fromString(self, string: str) -> Result[tuple[Command, str]]:
        string = string.strip()
        cmdresult = parseBasicCommand(string)
        if not cmdresult.success:
            return Result(False, logs=cmdresult.logs)
        assert cmdresult.value
        cmd, rest = cmdresult.value
        assert cmd.name in self.names
        return Result(True, value=(GfCommand(cmd, self.inrepr, self.outrepr), rest))



GF_COMMAND_TYPES: list[GfCommandType] = [
        GfCommandType(['parse', 'p'], Repr.SENTENCE, Repr.AST),
        GfCommandType(['put_string', 'ps'], Repr.SENTENCE, Repr.SENTENCE),
        GfCommandType(['linearize', 'l'], Repr.AST, Repr.SENTENCE),
        GfCommandType(['visualize_tree', 'vt'], Repr.AST, Repr.GRAPH_DOT),
]


# GLIF COMMANDS

class NonApplicableCommand(Command):
    def __init__(self, f: Callable[['Glif.Glif'], Result[list[str]]], outrepr: Repr = Repr.DEFAULT):
        self.f = f
        self.outrepr = outrepr

    def execute(self, glif):
        r = self.f(glif)
        assert r.value is not None
        items = Items.fromVals(self.outrepr, r.value)
        if not r.success and r.logs:
            return items.withErrors([r.logs])
        else:
            return items


class NonApplicableCommandType(CommandType):
    def __init__(self, names: list[str],
            fgen: Callable[[BasicCommand], Callable[['Glif.Glif'], Result[list[str]]]],
            outrepr : Repr = Repr.DEFAULT):
        CommandType.__init__(self, names)
        self.fgen = fgen
        self.outrepr = outrepr

    def fromString(self, string: str) -> Result[tuple[Command, str]]:
        string = string.strip()
        cmdresult = parseBasicCommand(string, splitMainArgAtSpace = True)
        if not cmdresult.success:
            return Result(False, logs=cmdresult.logs)
        assert cmdresult.value
        cmd, rest = cmdresult.value
        assert cmd.name in self.names
        return Result(True, value=(NonApplicableCommand(self.fgen(cmd), self.outrepr), rest))


class OnlyApplicableCommand(Command):
    def __init__(self, f: Callable[['Glif.Glif', Items], Items], mainArgs: Optional[Items]):
        self.f = f
        self.mainArgs = mainArgs
        if self.mainArgs:
            self.is_executable = False
            self.is_applicable = True
        else:
            self.is_executable = True
            self.is_applicable = False

    def execute(self, glif):
        if not self.is_executable:
            return Items([]).withErrors(['No input was provided'])
        return self.f(glif, self.mainArgs)

    def apply(self, glif, items):
        items = self.f(glif, items)
        if self.mainArgs:
            items.withErrors(['Ignoring the provided arguments: ' + ', '.join([str(a) for a in self.mainArgs.items])])
        return items


class OnlyApplicableCommandType(CommandType):
    def __init__(self, names: list[str], fgen: Callable[[BasicCommand], Callable[['Glif.Glif', Items], Items]], argRepr: Repr):
        CommandType.__init__(self, names)
        self.fgen = fgen
        self.argRepr = argRepr

    def fromString(self, string: str) -> Result[tuple[Command, str]]:
        string = string.strip()
        cmdresult = parseBasicCommand(string, splitMainArgAtSpace = True)
        if not cmdresult.success:
            return Result(False, logs=cmdresult.logs)
        assert cmdresult.value
        cmd, rest = cmdresult.value
        assert cmd.name in self.names
        oacmd = OnlyApplicableCommand(self.fgen(cmd), Items.fromVals(self.argRepr, cmd.mainargs) if cmd.mainargs else None)
        return Result(True, value=(oacmd, rest))




def wrongCommandPatternResponse(cmd: BasicCommand,
        allowedKeyArgs: Optional[list[set[str]]] = None,      # each set contains synonyms of same arg
        allowedKeyValArgs: Optional[list[set[str]]] = None,
        allowRepeatedArgs: bool = False,
        minMainargs: int = 0,
        maxMainargs: Optional[int] = None) -> Optional[Result[list[str]]]:
    ''' returns a failed result in case cmd doesn't satisfy basic requirements '''
    assert (allowedKeyArgs is None and allowedKeyValArgs is None) or (allowedKeyArgs is not None and allowedKeyValArgs is not None)
    if allowedKeyArgs is not None and allowedKeyValArgs is not None:
        allowedKeyArgsFlat = {ee for e in allowedKeyArgs for ee in e}
        allowedKeyValArgsFlat = {ee for e in allowedKeyValArgs for ee in e}
        for arg in cmd.args:
            if arg.value and arg.key not in allowedKeyValArgsFlat:
                if arg.key in allowedKeyArgsFlat:
                    return Result(False, [], f'Argument "{arg.key}" for command "{cmd.name}" cannot have a value')
                else:
                    return Result(False, [], f'Illegal argument "{arg.key}" for command "{cmd.name}"')
            elif not arg.value and arg.key not in allowedKeyArgsFlat:
                if arg.key in allowedKeyValArgsFlat:
                    return Result(False, [], f'Argument "{arg.key}" for command "{cmd.name}" requires a value')
                else:
                    return Result(False, [], f'Illegal argument "{arg.key}" for command "{cmd.name}"')
    if not allowRepeatedArgs:
        argkeys = []
        for arg in cmd.args:
            if arg.key in argkeys:
                return Result(False, [], f'Argument "{arg.key}" supplied multiple times to command "{cmd.name}"')
            argkeys.append(arg.key)
        if allowedKeyArgs is not None and allowedKeyValArgs is not None:
            for kset in allowedKeyArgs + allowedKeyValArgs:
                used = [k for k in kset if k in argkeys]
                if len(used) > 1:
                    return Result(False, [], f'You cannot use the synonymous arguments "{used[0]}" and "{used[1]}" at the same time for the command "{cmd.name}".')

    if len(cmd.mainargs) < minMainargs:
        return Result(False, [], f'Command "{cmd.name}" requires at least {minMainargs} arguments (found {len(cmd.mainargs)})')

    if maxMainargs is not None and len(cmd.mainargs) > maxMainargs:
        return Result(False, [], f'Command "{cmd.name}" can have at most {maxMainargs} arguments (found {len(cmd.mainargs)})')

    return None


def importHelper(cmd: BasicCommand):
    def _importHelper(glif: Glif.Glif) -> Result[list[str]]:
        pr = wrongCommandPatternResponse(cmd, allowedKeyArgs = [], allowedKeyValArgs = [], minMainargs = 1)
        if pr:
            return pr
        logs = []
        errs = []
        for ma in cmd.mainargs:
            if ma.endswith('.gf'):
                r = glif.importGFfile(ma)
                if r.success:
                    logs.append(f'Successfully imported {ma}')
                else:
                    errs.append(r.logs)
            elif ma.endswith('.mmt'):
                r = glif.importMMTfile(ma)
                if r.success:
                    logs.append(f'Successfully imported {ma}')
                else:
                    errs.append(r.logs)
            elif ma.endswith('.elpi'):
                r = glif.importELPIfile(ma)
                if r.success:
                    logs.append(f'Successfully imported {ma}')
                    if r.logs:
                        logs.append(r.logs)
                else:
                    errs.append(r.logs)
            else:
                errs.append(f'Unknown file extension')
        if errs:
            return Result(False, logs, '\n'.join(errs))
        else:
            return Result(True, logs)

    return _importHelper


def archiveHelper(cmd: BasicCommand):
    def _archiveHelper(glif: Glif.Glif) -> Result[list[str]]:
        pr = wrongCommandPatternResponse(cmd, allowedKeyArgs = [], allowedKeyValArgs = [], minMainargs = 1, maxMainargs = 2)
        if pr:
            return pr
        archive = cmd.mainargs[0]
        subdir = None
        if len(cmd.mainargs) > 1:
            subdir = cmd.mainargs[1]

        r = glif.setArchive(archive, subdir, create=True)
        output = []
        if r.value:
            output.append(r.value)
        if r.success:
            output.append('Successfully changed archive')
        return Result(r.success, output, r.logs)

    return _archiveHelper

def statusHelper(cmd: BasicCommand):
    def _statusHelper(glif: Glif.Glif) -> Result[list[str]]:
        pr = wrongCommandPatternResponse(cmd, allowedKeyArgs = [{'load-gf'}, {'load-mmt'}, {'gf-logs'}, {'mmt-logs'}],
                allowedKeyValArgs = [], minMainargs = 0, maxMainargs = 0)
        loadgf = any(arg.key in {'load-gf'} for arg in cmd.args)
        loadmmt = any(arg.key in {'load-mmt'} for arg in cmd.args)
        gflogs = any(arg.key in {'gf-logs'} for arg in cmd.args)
        mmtlogs = any(arg.key in {'mmt-logs'} for arg in cmd.args)

        result = ['Current working directory: ' + glif.cwd]

        # GF
        if loadgf:
            glif.getGfShell()
        result.append('')
        result.append('GF STATUS')
        if glif._gfshell:
            result.append('GF is running')
            if gflogs:
                result.append('GF LOGS')
                result.append(glif._gfshell.initialOutput)
        else:
            result.append('GF is not running')
            if glif._gfshellFailedLogs:
                result.append(glif._gfshellFailedLogs)
        
        # MMT
        if loadmmt:
            glif.getMMT()
        result.append('')
        result.append('MMT STATUS')
        if glif._mmt:
            result.append(f'MMT is running on port {glif._mmt.server.port}')
        else:
            result.append(f'MMT is not running')
        result.append('Logs from initialization')
        result += glif._findMMTlogs
        if glif._mmtFailedStartupMessage:
            result.append(glif._mmtFailedStartupMessage)
        if mmtlogs:
            result.append('MMT STARTUP LOGS')
            if glif._mmt:
                result += glif._mmt.server.mmtlogstart
                result.append('MMT MOST RECENT LOGS')
                result += glif._mmt.server.mmtlogtail
            else:
                result += glif._mmtFailedStartupLogs
        
        # ELPI
        result.append('')
        result.append('ELPI STATUS')
        elpipath = find_executable('elpi')
        if not elpipath:
            result.append('Failed to locate executable "elpi"')
        else:
            result.append('ELPI location: ' + elpipath)
            try:
                result.append('ELPI version: ' + subprocess.check_output([elpipath, '-version'], text=True).strip())
            except:
                result.append('"elpi -version" failed')

        return Result(True, result)

    return _statusHelper


def constructHelper(cmd: BasicCommand):
    def _constructHelper(glif: Glif.Glif, items: Items) -> Items:
        pr = wrongCommandPatternResponse(cmd, allowedKeyArgs = [{'de', 'delta-expand'}, {'no-simplify'}], allowedKeyValArgs = [{'v', 'view'}])
        if pr:
            return Items([]).withErrors([pr.logs])
        view = cmd.getValOrDefault({'v', 'view'}, glif.defaultview if glif.defaultview else '')
        delta = any(arg.key in {'de', 'delta-expand'} for arg in cmd.args)
        simplify = not any(arg.key in {'no-simplify'} for arg in cmd.args)
        if not view:
            return Items([]).withErrors(['No semantics construction view has been specified for the "construct" command and no default view is available.'])

        mmt_result = glif.getMMT()
        if not mmt_result.success:
            return Items([]).withErrors([mmt_result.logs])
        mmt = mmt_result.value
        assert mmt

        archsub = glif.getArchiveSubdir()
        if not archsub.success:
            return Items([]).withErrors(['"construct" failed.', archsub.logs])
        assert archsub.value

        def helperunwrap(s : Optional[str]) -> str:
            assert s
            return s
        asts = list({ helperunwrap(item.tryGetRepr(Repr.AST).value) for item in items.items })
        r = mmt.construct(asts, archsub.value[0], archsub.value[1], view, deltaExpand = delta, simplify = simplify)

        if not r.success:
            return Items([]).withErrors(['"construct" failed.', r.logs])
        assert r.value

        d = {asts[i] : i for i in range(len(asts))}
        newItems = Items([])
        newItems.errors = items.errors
        for item in items.items:
            astrepr = item.tryGetRepr(Repr.AST)
            assert astrepr.value
            i = item.getClone().withRepr(Repr.LOGIC_STANDARD, r.value['mmt'][d[astrepr.value]])
            if 'elpi' in r.value:
                i = i.withRepr(Repr.LOGIC_ELPI, r.value['elpi'][d[astrepr.value]], False)
            if not astrepr.success:
                i.errors.append(astrepr.logs)
            newItems.items.append(i)
        return newItems

    return _constructHelper

def filterHelper(cmd: BasicCommand):
    def _filterHelper(glif: Glif.Glif, items: Items) -> Items:
        pr = wrongCommandPatternResponse(cmd, allowedKeyArgs = [{'notc', 'no-typechecking'}], allowedKeyValArgs = [{'f', 'file'}, {'p', 'predicate'}])
        if pr:
            return Items([]).withErrors([pr.logs])
        typecheck = not any(arg.key in {'notc', 'no-typechecking'} for arg in cmd.args)
        file = cmd.getValOrDefault({'f', 'file'}, glif.defaultelpi if glif.defaultelpi else '')
        if not file:
            return Items([]).withErrors(['No ELPI file was specified for the "{cmd.name}" command and now default file is available.'])
        if not file.endswith('.elpi'):
            file += '.elpi'
        predicate = cmd.getValOrDefault({'p', 'predicate'}, 'filter')
        expressions = []
        for itemid, item in enumerate(items.items):
            expr = f'glif.mkItem {itemid} {item.original_id} '
            s = item.content.get(Repr.SENTENCE)
            if s is None:
                expr += f'glif.none '
            else:
                expr += f'(glif.some "{s}") '
            for e in [item.content.get(Repr.AST), item.content.get(Repr.LOGIC_ELPI)]:
                if e is None:
                    expr += f'glif.none '
                else:
                    expr += f'(glif.some {e}) '
            expressions.append(expr.strip() + '.')

        stdin = '\n'.join(expressions + ['glif.endofitems.'])
        r = runelpi(glif.cwd, file, f'glif.filter {predicate}', typecheck, stdin)
        if not r.success:
            return items.withErrors(items.errors + [r.logs])
        tokeep = []
        output = []
        assert r.value
        for line in r.value[0].splitlines():
            line = line.strip()
            if line.startswith('filter-output:'):
                tokeep.append(int(line[len('filter-output:'):].strip()))
            elif line:
                output.append(line)
        items.items = [items.items[i] for i in tokeep]
        items.withErrors(output)
        return items

    return _filterHelper


def elpigenHelper(cmd: BasicCommand):
    def _elpigenHelper(glif: Glif.Glif) -> Result[list[str]]:
        pr = wrongCommandPatternResponse(cmd, allowedKeyArgs = [{'with-meta', 'wm'}, {'no-includes', 'ni'}],
                allowedKeyValArgs = [{'f', 'file'}, {'m', 'mode'}], minMainargs = 1, maxMainargs = 1)
        if pr:
            return pr
        meta = any(arg.key in {'with-meta', 'wm'} for arg in cmd.args)
        includes = not any(arg.key in {'no-includes', 'ni'} for arg in cmd.args)
        mode = cmd.getValOrDefault({'m', 'mode'}, 'types')
        if mode not in {'types', 'simpleprover'}:
            return Result(False, [], f'Unsupported mode "{mode}"')
        theory = cmd.mainargs[0]
        file = cmd.getValOrDefault({'f', 'file'}, theory)
        if not file.endswith('.elpi'):
            file += '.elpi'

        mmtr = glif.getMMT()
        if not mmtr.success:
            return Result(False, [], 'Failed load MMT:\n' + mmtr.logs)
        assert mmtr.value
        mmt = mmtr.value
        asr = glif.getArchiveSubdir()
        if not asr.success:
            return Result(False, [], asr.logs)
        assert asr.value
        archive, subdir = asr.value

        r = mmt.elpigen(mode, archive, subdir, theory, meta, includes)
        if not r.success:
            return Result(False, [], 'Failed to generate ELPI code:\n' + r.logs)
        assert r.value
        with open(os.path.join(glif.cwd, file), 'w') as f:
            f.write(r.value)
        return Result(True, [f'Successfully created {file}'])

    return _elpigenHelper


GLIF_COMMAND_TYPES : list[CommandType] = [
            NonApplicableCommandType(['import', 'i'], importHelper),
            NonApplicableCommandType(['archive', 'a'], archiveHelper),
            NonApplicableCommandType(['elpigen', 'eg'], elpigenHelper),
            NonApplicableCommandType(['status'], statusHelper),
            OnlyApplicableCommandType(['construct', 'c'], constructHelper, Repr.AST),
            OnlyApplicableCommandType(['filter'], filterHelper, Repr.LOGIC_ELPI),
        ]

