from typing import Optional, Literal

from glif.glif_abc import GlifABC as Glif
from glif.commands.items import Items, Repr
from glif.commands.glif_command import GlifCommandType, GlifArg
from glif.elpi import runelpi


def query_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str], items: Items) -> Items:
    typecheck = 'no-typechecking' not in keys
    file: Optional[str] = keyval['file']
    if file == '$DEFAULT':
        file = glif.get_defaultelpi()
    if not file:
        return Items([]).with_errors(
            ['No ELPI file was specified for the "{cmd.name}" command and no default file is available.'])
    if not file.endswith('.elpi'):
        file += '.elpi'

    new_items = Items([])
    new_items.errors = items.errors
    for item in items.items:
        query = item.try_get_repr(Repr.DEFAULT)
        assert query.value
        infofilter: Literal['none', 'full', 'partial'] = keyval['infofilter']   # type: ignore
        assert infofilter in {'none', 'full', 'partial'}
        r = runelpi(glif.get_cwd(), file, f'glif.query {keyval["number"]} ({query.value})', typecheck,
                    filterstderr=infofilter)
        if not r.success:
            new_items.errors.append(r.logs)
            continue
        assert r.value
        new_item = item.get_clone().with_repr(Repr.DEFAULT, r.value[0] + r.value[1].strip())
        new_items.items.append(new_item)
    return new_items


QUERY_COMMAND_TYPE = GlifCommandType(
    names=['query'],
    arguments=[
        GlifArg(names=['no-typechecking', 'notc', 'no-tc'], description='Disable type checking'),
        GlifArg(names=['file', 'f'], description='Elpi file', default_value='$DEFAULT'),
        GlifArg(names=['number', 'n'], description='Number of results', default_value='1'),
        GlifArg(names=['infofilter', 'if'], description='Filter information about e.g. execution time',
                default_value='full', value_set={'none', 'partial', 'full'}),
    ],
    description='Runs an elpi query',
    apply_fn=query_helper,
    inrepr=Repr.DEFAULT,
    main_args_as_items=True,
)
