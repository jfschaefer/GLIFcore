from typing import Optional

from ..glif_abc import GlifABC as Glif
from glif.commands.items import Items, Repr, Item
from .glif_command import GlifCommandType, GlifArg
from ..elpi import runelpi, items_to_stdin


def apply_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str], items: Items) -> Items:
    typecheck = 'no-typechecking' not in keys
    with_ast = 'with-AST' in keys
    file: Optional[str] = keyval['file']
    if file == '$DEFAULT':
        file = glif.get_defaultelpi()
    if not file:
        return Items([]).with_errors(
            ['No ELPI file was specified for the "{cmd.name}" command and no default file is available.'])
    if not file.endswith('.elpi'):
        file += '.elpi'
    predicate = keyval['predicate']
    new_items = Items([])
    if 'together' in keys:
        stdin = items_to_stdin(items, with_ast)
        r = runelpi(glif.get_cwd(), file, f'glif.apply_to_items {predicate}', typecheck, stdin)
        if not r.success:
            return Items([]).with_errors(items.errors + [r.logs])
        assert r.value
        new_item = Item(0).with_repr(Repr.DEFAULT, r.value[0])
        new_items.items.append(new_item)
    else:
        new_items.errors = items.errors
        for item in items.items:
            stdin = items_to_stdin(Items([item]), with_ast)
            r = runelpi(glif.get_cwd(), file, f'glif.apply_to_item {predicate}', typecheck, stdin)
            if not r.success:
                return items.with_errors(items.errors + [r.logs])
            # if not r.success:
            #     new_items.errors.append(r.logs)
            #     continue
            assert r.value
            new_item = item.get_clone().with_repr(Repr.DEFAULT, r.value[0])
            new_items.items.append(new_item)

    return new_items


APPLY_COMMAND_TYPE = GlifCommandType(
    names=['apply'],
    arguments=[
        GlifArg(names=['no-typechecking', 'notc', 'no-tc'], description='Disable type checking'),
        GlifArg(names=['file', 'f'], description='Elpi file', default_value='$DEFAULT'),
        GlifArg(names=['predicate', 'p'], description='Predicate to be applied', default_value='apply'),
        GlifArg(names=['with-AST', 'wA'], description='Include ASTs if available'),
        GlifArg(names=['together', 't'], description='Pass all items at once to the predicate (as as a list)'),
    ],
    description='Applies an ELPI predicate to logical expressions and returns the output',
    apply_fn=apply_helper,
    inrepr=Repr.LOGIC_ELPI,
    main_args_as_items=True,
)
