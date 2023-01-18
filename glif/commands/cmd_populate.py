from typing import Optional

from glif.commands.glif_command import GlifCommandType, GlifArg
from glif.commands.items import Items, Repr, Item
from glif.glif_abc import GlifABC as Glif


def populate_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str], items: Items) -> Items:
    mmt_result = glif.get_mmt()
    if not mmt_result.success:
        return Items([]).with_errors([mmt_result.logs])
    mmt = mmt_result.value
    assert mmt

    archsub = glif.get_archive_subdir()
    if not archsub.success:
        return Items([]).with_errors(['"populate" failed.', archsub.logs])
    assert archsub.value

    def helperunwrap(s: Optional[str]) -> str:
        assert s
        return s

    terms = list(helperunwrap(item.try_get_repr(Repr.LOGIC_STANDARD).value) for item in items.items)
    metatheory = keyval['meta']
    # print('TERMS:', terms)
    # print(list(helperunwrap(item.try_get_repr(Repr.LOGIC_STANDARD).value) for item in items.items))
    r = mmt.populate(terms, archsub.value[0], archsub.value[1], metatheory, name=keyval['name'], mode=keyval['mode'])
    if not r.success:
        return Items([]).with_errors(['"populate" failed.', r.logs])
    assert r.value

    return Items([
        Item(0).with_repr(Repr.DEFAULT,
                          r.value['theorypresentation'].replace('\n\t\t: ', ' : ').replace('\n\t❙', ' ❙')),
    ]).with_errors(items.errors)


POPULATE_COMMAND_TYPE = GlifCommandType(
    names=['populate'],
    arguments=[
        GlifArg(['meta', 'm'], 'The meta theory', has_value=True),
        GlifArg(['name', 'n'], 'Name of the generated theory', default_value='generated'),
        GlifArg(['mode'], 'Mode of population', default_value='default', value_set={'default', 'events'})
    ],
    description='Populates an MMT theory with the results of the semantics construction',
    main_args_as_items=True,
    apply_fn=populate_helper,
    inrepr=Repr.LOGIC_STANDARD,
)
