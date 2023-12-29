from typing import Optional

from glif.glif_abc import GlifABC as Glif
from glif.commands.items import Items, Repr
from glif.commands.glif_command import GlifCommandType, GlifArg
from glif.elpi import runelpi, items_to_stdin


def filter_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str], items: Items) -> Items:
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
    stdin = items_to_stdin(items, with_ast)
    r = runelpi(glif.get_cwd(), file, f'glif.filter {predicate}', typecheck, stdin)
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


FILTER_COMMAND_TYPE = GlifCommandType(
    names=['filter'],
    arguments=[
        GlifArg(names=['no-typechecking', 'notc', 'no-tc'], description='Disable type checking'),
        GlifArg(names=['file', 'f'], description='Elpi file', default_value='$DEFAULT'),
        GlifArg(names=['predicate', 'p'], description='Filter predicate', default_value='filter'),
        GlifArg(names=['with-AST', 'wA'], description='Include ASTs if available'),
    ],
    description='Filters logical expressions using ELPI',
    apply_fn=filter_helper,
    inrepr=Repr.LOGIC_ELPI,
    main_args_as_items=True,
)
