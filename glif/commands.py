import html
import os
import subprocess
from distutils.spawn import find_executable
from enum import Enum
from typing import Callable

from glif.parsing import *
from glif.utils import runelpi


class Repr(Enum):
    """ Different representations of item content """
    HTML = 'html'  # HTML representation (available for certain GLIF commands), has to coincide with DEFAULT
    DEFAULT = 'default'
    SENTENCE_ORIG = 'original sentence'
    SENTENCE = 'current sentence'
    AST = 'abstract syntax tree'
    LOGIC_PLAIN = 'logical expression (plain)'  # MMT without notations
    LOGIC_STANDARD = 'logical expression'  # MMT with notations
    LOGIC_ELPI = 'logical expression (elpi)'  # ELPI
    GRAPH_DOT = 'graph-dot'  # graph in dot format
    GRAPH_SVG = 'graph-svg'  # graph in svg format


class Item(object):
    """ Something that can be passed between commands (AST, sentence, logical expression, ...).
        Note that an item may have multiple representations simultaneously (e.g. a string and an AST).
    """

    def __init__(self, original_id):
        self.errors: list[str] = []
        self.original_id: int = original_id
        self.content: dict[Repr, str] = {}
        self.currentRepr: Optional[Repr] = None

    def try_get_repr(self, r: Repr) -> Result[str]:
        if r in self.content:
            return Result(True, self.content[r], '\n'.join(self.errors))
        else:
            message = f'Expected representation [{r}], falling back to [{Repr.DEFAULT}]'
            message += '\nAvailable representations: ' + ' '.join([f'[{rr}]' for rr in self.content])
            return Result(False, self.content[Repr.DEFAULT], '\n'.join(self.errors + [message]))

    def with_repr(self, r: Repr, val: str, update_default: bool = True, html_version: Optional[str] = None) -> 'Item':
        """ doesn't clone! """
        assert r != Repr.HTML
        if update_default:
            self.content[Repr.DEFAULT] = val
        self.content[r] = val
        self.currentRepr = r
        if html_version:
            self.content[Repr.HTML] = html_version
        elif Repr.HTML in self.content:
            del self.content[Repr.HTML]
        return self

    def get_clone(self) -> 'Item':  # TODO: use deepcopy instead
        i = Item(self.original_id)
        i.errors = self.errors[:]
        i.content = self.content.copy()
        return i

    def html(self) -> str:
        s = ''
        if Repr.HTML in self.content:
            s += self.content[Repr.HTML]
        elif Repr.DEFAULT in self.content:
            s += '<span class="glif-stdout">' + html.escape(self.content[Repr.DEFAULT]).replace('\n',
                                                                                                '<br/>') + '</span>'
        if self.errors:
            s += '\n<br/><span class="glif-stderr"><b>Errors</b><br/>' + '<br/>'.join(self.errors) + '</span>'
        return s

    def __str__(self):
        if Repr.DEFAULT not in self.content:
            return '[Item has no default representation]'
        s = self.content[Repr.DEFAULT]
        if self.errors:
            return 'Errors:\n    ' + '\n    '.join(self.errors) + '\n' + s
        return s


class Items(object):
    """ A collection of `Item` objects """

    def __init__(self, items: list[Item]):
        self.items: list[Item] = items
        self.errors: list[str] = []

    @classmethod
    def from_vals(cls, repr_: Repr, vals: list[str]) -> 'Items':
        items = Items([])
        for i, v in enumerate(vals):
            item = Item(i).with_repr(repr_, v)
            if repr_ == Repr.SENTENCE:
                item.content[Repr.SENTENCE_ORIG] = v
            items.items.append(item)
        return items

    def merge(self, items: 'Items'):
        self.items = self.items + items.items
        self.errors = self.errors + items.errors

    def with_errors(self, errors: list[str]) -> 'Items':
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
        """ If no input is/can provided """
        assert self.is_executable
        return Items([])

    def apply(self, glif: 'Glif.Glif', items: Items) -> Items:
        """ If input is provided (`items`) """
        assert self.is_applicable
        new_items = Items([])
        new_items.errors = items.errors
        for item in items.items:
            new_items.merge(self._apply_item(glif, item))
        return new_items

    def _apply_item(self, glif: 'Glif.Glif', item: Item) -> Items:
        raise NotImplementedError()


class CommandType(object):
    def __init__(self, names: list[str]):
        self.names: list[str] = names  # Command names, e.g. ['view_tree', 'vt']

    def from_string(self, string: str) -> Result[tuple[Command, str]]:
        """ returns (concrete command, remaining string (in case of pipes)). """
        raise NotImplementedError()

    def _get_short_descr(self) -> str:
        return ''

    def _get_long_descr(self) -> str:
        return ''


# GF COMMANDS

class GfCommand(Command):
    """ for standard GF commands """

    def __init__(self, bc: BasicCommand, inrepr: Repr, outrepr: Repr):
        self.bc = bc

        self.is_executable = True
        self.is_applicable = True

        self.inrepr = inrepr
        self.outrepr = outrepr

    def handle_shell_output(self, out: str) -> tuple[list[str], list[str]]:  # (outputs, errors)
        # TODO: Implement this properly (error filtering, ...)
        if self.outrepr == Repr.GRAPH_DOT:
            return [out], []
        return [s.strip() for s in out.splitlines()], []

    def execute(self, glif):
        assert self.is_executable
        if self.bc.mainargs:
            items = Items.from_vals(self.inrepr, self.bc.mainargs)
            return self.apply(glif, items)

        gfshell = glif.getGfShell()
        if gfshell.success:
            assert gfshell.value
            output = gfshell.value.handle_command(self.bc.gfFormat(None))
            # TODO: better output handling
            vals, errs = self.handle_shell_output(output)
            return Items.from_vals(self.outrepr, vals).with_errors(errs)
        else:
            return Items([]).with_errors([gfshell.logs])

    def _apply_item(self, glif, item):
        inp = item.try_get_repr(self.inrepr)
        assert inp.value
        gfshell = glif.getGfShell()
        if not gfshell.success:
            return Items([]).with_errors(item.errors + [gfshell.logs])
        assert gfshell.value
        output = gfshell.value.handle_command(self.bc.gfFormat(inp.value, self.inrepr != Repr.AST))

        vals, errs = self.handle_shell_output(output)
        items = Items([]).with_errors(errs)
        for val in vals:
            items.items.append(item.get_clone().with_repr(self.outrepr, val))
        return items


class GfCommandType(CommandType):
    """ for standard GF commands """

    def __init__(self, names: list[str], inrepr: Repr, outrepr: Repr):
        CommandType.__init__(self, names)
        self.inrepr = inrepr
        self.outrepr = outrepr

    def from_string(self, string: str) -> Result[tuple[Command, str]]:
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
    GfCommandType(['put_tree', 'pt'], Repr.AST, Repr.AST),
    # TODO: some arguments probably won't work (e.g. `-smallest`)
    GfCommandType(['linearize', 'l'], Repr.AST, Repr.SENTENCE),
    GfCommandType(['visualize_tree', 'vt'], Repr.AST, Repr.GRAPH_DOT),
    GfCommandType(['visualize_parse', 'vp'], Repr.AST, Repr.GRAPH_DOT),
    # TODO: the following commands cannot be applied (only executed)
    GfCommandType(['generate_random', 'gr'], Repr.DEFAULT, Repr.AST),
    GfCommandType(['generate_trees', 'gt'], Repr.DEFAULT, Repr.AST),
]


# GLIF COMMANDS

class NonApplicableCommand(Command):
    def __init__(self, f: Callable[['Glif.Glif'], Result[list[str]]], outrepr: Repr = Repr.DEFAULT):
        self.f = f
        self.outrepr = outrepr

    def execute(self, glif):
        r = self.f(glif)
        assert r.value is not None
        items = Items.from_vals(self.outrepr, r.value)
        if not r.success and r.logs:
            return items.with_errors([r.logs])
        else:
            return items


class NonApplicableCommandType(CommandType):
    def __init__(self, names: list[str],
                 fgen: Callable[[BasicCommand], Callable[['Glif.Glif'], Result[list[str]]]],
                 outrepr: Repr = Repr.DEFAULT):
        CommandType.__init__(self, names)
        self.fgen = fgen
        self.outrepr = outrepr

    def from_string(self, string: str) -> Result[tuple[Command, str]]:
        string = string.strip()
        cmdresult = parseBasicCommand(string, splitMainArgAtSpace=True)
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
            return Items([]).with_errors(['No input was provided'])
        return self.f(glif, self.mainArgs)

    def apply(self, glif, items):
        items = self.f(glif, items)
        if self.mainArgs:
            items.with_errors(['Ignoring the provided arguments: ' + ', '.join([str(a) for a in self.mainArgs.items])])
        return items


class OnlyApplicableCommandType(CommandType):
    def __init__(self, names: list[str], fgen: Callable[[BasicCommand], Callable[['Glif.Glif', Items], Items]],
                 arg_repr: Repr):
        CommandType.__init__(self, names)
        self.fgen = fgen
        self.argRepr = arg_repr

    def from_string(self, string: str) -> Result[tuple[Command, str]]:
        string = string.strip()
        cmdresult = parseBasicCommand(string, splitMainArgAtSpace=True)
        if not cmdresult.success:
            return Result(False, logs=cmdresult.logs)
        assert cmdresult.value
        cmd, rest = cmdresult.value
        assert cmd.name in self.names
        oacmd = OnlyApplicableCommand(self.fgen(cmd),
                                      Items.from_vals(self.argRepr, cmd.mainargs) if cmd.mainargs else None)
        return Result(True, value=(oacmd, rest))


def wrong_command_pattern_response(cmd: BasicCommand,
                                   allowed_key_args: Optional[list[set[str]]] = None,
                                   # each set contains synonyms of same arg
                                   allowed_key_val_args: Optional[list[set[str]]] = None,
                                   allow_repeated_args: bool = False,
                                   min_main_args: int = 0,
                                   max_main_args: Optional[int] = None) -> Optional[Result[list[str]]]:
    """ returns a failed result in case cmd doesn't satisfy basic requirements """
    assert (allowed_key_args is None and allowed_key_val_args is None) or (
            allowed_key_args is not None and allowed_key_val_args is not None)
    if allowed_key_args is not None and allowed_key_val_args is not None:
        allowed_key_args_flat = {ee for e in allowed_key_args for ee in e}
        allowed_key_val_args_flat = {ee for e in allowed_key_val_args for ee in e}
        for arg in cmd.args:
            if arg.value and arg.key not in allowed_key_val_args_flat:
                if arg.key in allowed_key_args_flat:
                    return Result(False, [], f'Argument "{arg.key}" for command "{cmd.name}" cannot have a value')
                else:
                    return Result(False, [], f'Illegal argument "{arg.key}" for command "{cmd.name}"')
            elif not arg.value and arg.key not in allowed_key_args_flat:
                if arg.key in allowed_key_val_args_flat:
                    return Result(False, [], f'Argument "{arg.key}" for command "{cmd.name}" requires a value')
                else:
                    return Result(False, [], f'Illegal argument "{arg.key}" for command "{cmd.name}"')
    if not allow_repeated_args:
        argkeys = []
        for arg in cmd.args:
            if arg.key in argkeys:
                return Result(False, [], f'Argument "{arg.key}" supplied multiple times to command "{cmd.name}"')
            argkeys.append(arg.key)
        if allowed_key_args is not None and allowed_key_val_args is not None:
            for kset in allowed_key_args + allowed_key_val_args:
                used = [k for k in kset if k in argkeys]
                if len(used) > 1:
                    return Result(False, [],
                                  f'You cannot use the synonymous arguments "{used[0]}" and "{used[1]}" at the same '
                                  f'time for the command "{cmd.name}".')

    if len(cmd.mainargs) < min_main_args:
        return Result(False, [],
                      f'Command "{cmd.name}" requires at least {min_main_args} arguments (found {len(cmd.mainargs)})')

    if max_main_args is not None and len(cmd.mainargs) > max_main_args:
        return Result(False, [],
                      f'Command "{cmd.name}" can have at most {max_main_args} arguments (found {len(cmd.mainargs)})')

    return None


def import_helper(cmd: BasicCommand):
    def _import_helper(glif: Glif.Glif) -> Result[list[str]]:
        pr = wrong_command_pattern_response(cmd, allowed_key_args=[], allowed_key_val_args=[], min_main_args=1)
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

    return _import_helper


def archive_helper(cmd: BasicCommand):
    def _archive_helper(glif: Glif.Glif) -> Result[list[str]]:
        pr = wrong_command_pattern_response(cmd, allowed_key_args=[], allowed_key_val_args=[], min_main_args=1,
                                            max_main_args=2)
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

    return _archive_helper


def status_helper(cmd: BasicCommand):
    def _status_helper(glif: Glif.Glif) -> Result[list[str]]:
        pr = wrong_command_pattern_response(cmd,
                                            allowed_key_args=[{'load-gf'}, {'load-mmt'}, {'gf-logs'}, {'mmt-logs'}],
                                            allowed_key_val_args=[], min_main_args=0, max_main_args=0)
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

    return _status_helper


def construct_helper(cmd: BasicCommand):
    def _construct_helper(glif: Glif.Glif, items: Items) -> Items:
        pr = wrong_command_pattern_response(cmd, allowed_key_args=[{'de', 'delta-expand'}, {'no-simplify'}],
                                            allowed_key_val_args=[{'v', 'view'}])
        if pr:
            return Items([]).with_errors([pr.logs])
        view = cmd.getValOrDefault({'v', 'view'}, glif.defaultview if glif.defaultview else '')
        delta = any(arg.key in {'de', 'delta-expand'} for arg in cmd.args)
        simplify = not any(arg.key in {'no-simplify'} for arg in cmd.args)
        if not view:
            return Items([]).with_errors(['No semantics construction view has been specified for the "construct" '
                                          'command and no default view is available.'])

        mmt_result = glif.getMMT()
        if not mmt_result.success:
            return Items([]).with_errors([mmt_result.logs])
        mmt = mmt_result.value
        assert mmt

        archsub = glif.getArchiveSubdir()
        if not archsub.success:
            return Items([]).with_errors(['"construct" failed.', archsub.logs])
        assert archsub.value

        def helperunwrap(s: Optional[str]) -> str:
            assert s
            return s

        asts = list({helperunwrap(item.try_get_repr(Repr.AST).value) for item in items.items})
        r = mmt.construct(asts, archsub.value[0], archsub.value[1], view, deltaExpand=delta, simplify=simplify)

        if not r.success:
            return Items([]).with_errors(['"construct" failed.', r.logs])
        assert r.value

        d = {asts[i]: i for i in range(len(asts))}
        new_items = Items([])
        new_items.errors = items.errors
        for item in items.items:
            astrepr = item.try_get_repr(Repr.AST)
            assert astrepr.value
            i = item.get_clone().with_repr(Repr.LOGIC_STANDARD, r.value['mmt'][d[astrepr.value]])
            if 'elpi' in r.value:
                i = i.with_repr(Repr.LOGIC_ELPI, r.value['elpi'][d[astrepr.value]], False)
            if not astrepr.success:
                i.errors.append(astrepr.logs)
            new_items.items.append(i)
        return new_items

    return _construct_helper


def filter_helper(cmd: BasicCommand):
    def _filter_helper(glif: Glif.Glif, items: Items) -> Items:
        pr = wrong_command_pattern_response(cmd, allowed_key_args=[{'notc', 'no-typechecking'}],
                                            allowed_key_val_args=[{'f', 'file'}, {'p', 'predicate'}])
        if pr:
            return Items([]).with_errors([pr.logs])
        typecheck = not any(arg.key in {'notc', 'no-typechecking'} for arg in cmd.args)
        file = cmd.getValOrDefault({'f', 'file'}, glif.defaultelpi if glif.defaultelpi else '')
        if not file:
            return Items([]).with_errors(
                ['No ELPI file was specified for the "{cmd.name}" command and now default file is available.'])
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
            return items.with_errors(items.errors + [r.logs])
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
        items.with_errors(output)
        return items

    return _filter_helper


def elpigen_helper(cmd: BasicCommand):
    def _elpigen_helper(glif: Glif.Glif) -> Result[list[str]]:
        pr = wrong_command_pattern_response(cmd, allowed_key_args=[{'with-meta', 'wm'}, {'no-includes', 'ni'}],
                                            allowed_key_val_args=[{'f', 'file'}, {'m', 'mode'}], min_main_args=1,
                                            max_main_args=1)
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

    return _elpigen_helper


GLIF_COMMAND_TYPES: list[CommandType] = [
    NonApplicableCommandType(['import', 'i'], import_helper),
    NonApplicableCommandType(['archive', 'a'], archive_helper),
    NonApplicableCommandType(['elpigen', 'eg'], elpigen_helper),
    NonApplicableCommandType(['status'], status_helper),
    OnlyApplicableCommandType(['construct', 'c'], construct_helper, Repr.AST),
    OnlyApplicableCommandType(['filter'], filter_helper, Repr.LOGIC_ELPI),
]
