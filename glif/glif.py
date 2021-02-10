from typing import Optional


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
        self.errors : list[str] = None

    def merge(self, items: Items):
        self.items.append(items.items)
        self.errors.append(items.errors)



class Command(object):
    is_executable: bool = False
    is_applicable: bool = False

    def execute(self, glif: Glif) -> Items:
        ''' If no input is/can provided '''
        assert self.is_executable
        return Items([])

    def apply(self, glif: Glif, items: Items) -> Items:
        ''' If input is provided (`items`) '''
        assert self.is_applicable
        newItems = Items([])
        newItems.errors = items.errors
        for item in items:
            newItems.merge(self._applyItem(glif, item))

    def _applyItem(self, glif: Glif, item: Item) -> Items:
        raise NotImplemented()



class CommandType(object):
    def __init__(self, names: list[str], short_descr: str = '', long_descr: str = ''):
        self.names: list[str] = names         # Command names, e.g. ['view_tree', 'vt']
        self.short_descr: str = short_descr   # Short description
        self.long_descr: str  = long_descr    # Long description

    def fromString(self, string: str) -> Result[(Command, str)]:
        ''' returns (concrete command, remaining string (in case of pipes)). '''
        raise NotImplemented()



class Glif(object):
    def __init__(self):
        pass
