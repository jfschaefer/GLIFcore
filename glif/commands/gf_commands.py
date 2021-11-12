from typing import Optional

from .command import Command, CommandType
from ..glif_abc import GlifABC as Glif
from glif.commands.items import Repr, Items, Item
from ..parsing import BasicCommand
from ..utils import Result



class GfCommandType(CommandType):
    """ for standard GF commands """

    def __init__(self, names: list[str], inrepr: Optional[Repr], outrepr: Repr):
        super().__init__(names)
        self.inrepr = inrepr
        self.outrepr = outrepr
        if inrepr == Repr.AST:
            self._split_mainarg_at_space = False  # e.g. "linearize abc (def ghi)"

    def _basiccommand_to_command(self, cmd: BasicCommand) -> Result[Command]:
        def run(glif: Glif, onItem: Optional[Item]) -> Items:
            gfshell = glif.get_gf_shell()
            if not gfshell.success:
                return Items([]).with_errors((onItem.errors if onItem else []) + [gfshell.logs])
            assert gfshell.value
            if onItem:
                assert self.inrepr
                inp = onItem.try_get_repr(self.inrepr)
                assert inp.value
                output = gfshell.value.handle_command(cmd.gf_format(inp.value, self.inrepr != Repr.AST))
            else:
                output = gfshell.value.handle_command(cmd.gf_format(None))
            # TODO: Error handling
            errs: list[str] = []
            if self.outrepr == Repr.GRAPH_DOT:
                vals = [output]
            else:
                vals = [s.strip() for s in output.splitlines()]

            if onItem:
                items = Items([]).with_errors(errs)
                for val in vals:
                    items.items.append(onItem.get_clone().with_repr(self.outrepr, val))
                return items
            else:
                return Items.from_vals(self.outrepr, vals).with_errors(errs)
        if self.inrepr:
            return Result(True, Command(self, lambda glif : run(glif, None),
                                        lambda glif, items: items.flatmap(lambda item: run(glif, item)),
                                        Items.from_vals(self.inrepr, cmd.mainargs) if cmd.mainargs else None))
        else:
            return Result(True, Command(self, lambda glif : run(glif, None), None, None))

    def get_long_descr(self, glif: Glif) -> str:
        if not self._long_descr:
            gfresult = glif.get_gf_shell()
            if gfresult.success:
                gfshell = gfresult.value
                assert gfshell
                self._long_descr = gfshell.handle_command(f'help {self.names[0]}')
                return self._long_descr
            else:
                return f'Failed to get GF shell\nError: {gfresult.logs}'
        else:
            return self._long_descr


GF_COMMAND_TYPES: list[GfCommandType] = [
    GfCommandType(['parse', 'p'], Repr.SENTENCE, Repr.AST),
    GfCommandType(['put_string', 'ps'], Repr.SENTENCE, Repr.SENTENCE),
    GfCommandType(['put_tree', 'pt'], Repr.AST, Repr.AST),
    # TODO: some sorting arguments probably won't work (e.g. `pt -smallest`)
    GfCommandType(['linearize', 'l'], Repr.AST, Repr.SENTENCE),
    GfCommandType(['visualize_tree', 'vt'], Repr.AST, Repr.GRAPH_DOT),
    GfCommandType(['visualize_parse', 'vp'], Repr.AST, Repr.GRAPH_DOT),
    GfCommandType(['generate_random', 'gr'], None, Repr.AST),
    GfCommandType(['generate_trees', 'gt'], None, Repr.AST),
]