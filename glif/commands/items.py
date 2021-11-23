import html
from enum import Enum
from typing import Optional, Callable

from glif.utils import Result


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

    def get_clone(self) -> 'Item':  # TODO: use __deepcopy__ instead
        i = Item(self.original_id)
        i.errors = self.errors[:]
        i.content = self.content.copy()
        return i

    def html(self) -> str:
        s = ''
        if Repr.HTML in self.content:
            s += self.content[Repr.HTML]
        elif Repr.DEFAULT in self.content:
            s += '<span class="glif-stdout">' + \
                    html.escape(self.content[Repr.DEFAULT]).replace('\n', '<br/>').replace('  ', '&nbsp;&nbsp;') +\
                 '</span>'
        if self.errors:
            s += '\n<br/><span class="glif-stderr"><b>Errors</b><br/>' +\
                 '<br/>'.join([e.replace('\n', '<br/>') for e in self.errors]) + '</span>'
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
            s += '\n<br/><span class="glif-stderr"><b>Errors</b><br/>' +\
                 '<br/>'.join([e.replace('\n', '<br/>') for e in self.errors]) + '</span>'
        return s

    def __str__(self):
        items = '\n'.join([str(item) for item in self.items])
        if self.errors:
            return '\n'.join(self.errors) + '\n\n' + items
        return items

    def flatmap(self, fn: Callable[[Item], 'Items']):
        new_items = Items([])
        new_items.errors = self.errors
        for item in self.items:
            new_items.merge(fn(item))
        return new_items
