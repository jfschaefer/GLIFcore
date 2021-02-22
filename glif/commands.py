from typing import Optional, Callable
from glif.utils import Result
from glif.parsing import *
from glif import glif
from enum import Enum


class Repr(Enum):
    ''' Different representations of item content '''
    DEFAULT        = 'default'
    SENTENCE_ORIG  = 'original sentence'
    SENTENCE       = 'current sentence'
    AST            = 'abstract syntax tree'
    LOGIC_PLAIN    = 'logical expression (plain)'   # MMT without notations
    LOGIC_STANDARD = 'logical expression'          # MMT with notations
    LOGIC_ELPI     = 'logical expression (elpi)'    # MMT with notations


class Item(object):
    ''' Something that can be passed between commands (AST, sentence, logical expression, ...).
        Note that an item may have multiple representations simultaneously (e.g. a string and an AST).
    '''
    def __init__(self, original_id):
        self.errors: list[str] = []
        self.original_id: int = original_id
        self.content: dict[Repr, str] = {}

    def tryGetRepr(self, r: Repr) -> Result[str]:
        if r in self.content:
            return Result(True, self.content[r], '\n'.join(self.errors))
        else:
            message = f'Expected representation [{r}], falling back to [{Repr.DEFAULT}]'
            message += '\nAvailable representations: ' + ' '.join([f'[{rr}]' for rr in self.content])
            return Result(False, self.content[Repr.DEFAULT], '\n'.join(self.errors + [message]))

    def withRepr(self, r: Repr, val: str) -> 'Item':
        ''' doesn't clone! '''
        self.content[Repr.DEFAULT] = val
        self.content[r] = val
        return self

    def getClone(self) -> 'Item':
        i = Item(self.original_id)
        i.errors = self.errors
        i.content = self.content
        return i

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
            item = Item(i)
            item.content[repr_] = v
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

    def __str__(self):
        items = '\n'.join([str(item) for item in self.items])
        if self.errors:
            return '\n'.join(self.errors) + '\n\n' + items
        return items



class Command(object):
    is_executable: bool = False
    is_applicable: bool = False

    def execute(self, glif: 'glif.Glif') -> Items:
        ''' If no input is/can provided '''
        assert self.is_executable
        return Items([])

    def apply(self, glif: 'glif.Glif', items: Items) -> Items:
        ''' If input is provided (`items`) '''
        assert self.is_applicable
        newItems = Items([])
        newItems.errors = items.errors
        for item in items.items:
            newItems.merge(self._applyItem(glif, item))
        return newItems

    def _applyItem(self, glif: 'glif.Glif', item: Item) -> Items:
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
        output = gfshell.value.handle_command(self.bc.gfFormat(inp.value, self.inrepr))

        vals, errs = self.handleShellOutput(output)
        items = Items([]).withErrors(errs)
        for val in vals:
            items.items.append(item.getClone().withRepr(self.outrepr, val))
        return items



class GfCommandType(object):
    ''' for standard GF commands '''
    def __init__(self, names: list[str], inrepr : Repr, outrepr : Repr):
        self.names = names
        self.inrepr = inrepr
        self.outrepr = outrepr

    def fromString(self, string: str) -> Result[tuple[GfCommand, str]]:
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
]
