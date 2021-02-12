from typing import Optional, Callable
from glif.utils import Result
from glif.parsing import *
from distutils.spawn import find_executable
from glif import gf


class Item(object):
    ''' Something that can be passed between commands (AST, sentence, logical expression, ...).
        Note that an item may have multiple representations simultaneously (e.g. a string and an AST).
    '''
    def __init__(self):
        self.errors            : list[str] = None
        self.plain             : Optional[str] = None
        self.sentence_original : Optional[str] = None
        self.original_id       : Optional[int] = None
        self.sentence_cur      : Optional[int] = None
        self.ast               : Optional[str] = None
        self.logic_plain       : Optional[str] = None  # MMT without notations
        self.logic_standard    : Optional[str] = None  # MMT with notations
        self.logic_elpi        : Optional[str] = None  # ELPI


class Items(object):
    ''' A collection of `Item` objects '''
    def __init__(self, items: list[Item]):
        self.items : list[Item] = items
        self.errors : list[str] = []

    def merge(self, items: 'Items'):
        self.items = self.items + items.items
        self.errors = self.errors + items.errors

    def withErrors(self, errors: list[str]) -> 'Items':
        self.errors = self.errors + errors
        return self



class Command(object):
    is_executable: bool = False
    is_applicable: bool = False

    def execute(self, glif: 'Glif') -> Items:
        ''' If no input is/can provided '''
        assert self.is_executable
        return Items([])

    def apply(self, glif: 'Glif', items: Items) -> Items:
        ''' If input is provided (`items`) '''
        assert self.is_applicable
        newItems = Items([])
        newItems.errors = items.errors
        for item in items.items:
            newItems.merge(self._applyItem(glif, item))
        return newItems

    def _applyItem(self, glif: 'Glif', item: Item) -> Items:
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


class GfCommand(object):
    ''' for standard GF commands '''
    def __init__(self, 
            shellCommand: str,
            getInput: Optional[Callable[[Item], Result[str]]],
            getOutput: Callable[[Optional[Item], str], Items]):
        self.shellCommand = shellCommand
        self.getInput = getInput
        self.getOutput = getOutput
        if not self.getInput:
            self.is_applicable = False

    def execute(self, glif):
        assert self.is_executable
        return self.getOutput(None, glif.gfshell.handle_command(self.shellCommand))
    
    def _applyItem(self, glif, item):
        assert self.getInput
        inp = self.getInput(item)
        assert inp.value
        s = glif.gfshell.handle_command(self.shellCommand + ' ' + inp.value)
        if inp.success:
            return self.getOutput(item, s)
        else:
            return self.getOutput(item, s).withErrors(inp.logs)

            
class GfCommandType(object):
    ''' for standard GF commands '''
    def __init__(self, names: list[str],
            getInput: Optional[Callable[[Item], Result[str]]],
            getOutput: Callable[[Optional[Item], str], Items]):
        self.names = names
        self.getInput = getInput      # obtains command input from item (None if no input is accepted)
        self.getOutput = getOutput    # obtains new items based on shell output

    def fromString(self, string: str) -> Result[tuple[GfCommand, str]]:
        string = string.strip()
        command, rest = parseCommandName(string.strip())
        assert command in self.names

        # skip over args
        while True:
            rest = rest.strip()
            if not rest:
                break
            if rest[0] == '-':
                r = parseCommandArg(rest)
                if not r.success:
                    return Result(False, logs=r.logs)
                assert r.value
                arg, rest = r.value
            else:
                break

        rest = rest.strip()

        if not rest:
            return Result(True, (GfCommand(string, self.getInput, self.getOutput), ''))

        if rest[0] == '|':
            return Result(True, (GfCommand(string[:-len(rest)], self.getInput, self.getOutput), rest[1:]))
        
        # Find next pipe
        i = 0
        while i < len(rest):
            if rest[i] == '|':
                # Done :)
                return Result(True, (GfCommand(string[:-len(rest[i-1:])], None, self.getOutput), rest[i+1:]))
            elif rest[i] == '"':
                rr = parseString(rest[i:])
                if not rr.success:
                    return Result(False, None, logs=rr.logs)
                assert rr.value
                rest = rr.value[1]
                i = 0
            else:
                i += 1

        return Result(True, (GfCommand(string, None, self.getOutput), ''))








class Glif(object):
    # This is all temporary
    def __init__(self, cwd):
        self.gfshell = gf.GFShellRaw(find_executable('gf'), cwd = cwd)



