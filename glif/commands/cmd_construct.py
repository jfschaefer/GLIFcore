from typing import Optional

from ..glif_abc import GlifABC as Glif
from glif.commands.items import Items, Repr
from .glif_command import GlifCommandType, GlifArg


def construct_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str], items: Items) -> Items:
    view: Optional[str] = keyval['view']
    if view == '$DEFAULT':
        view = glif.get_defaultview()
    delta_expand = 'delta-expand' in keys
    simplify = not 'no-simplify' in keys
    if not view:
        return Items([]).with_errors(['No semantics construction view has been specified for the "construct" '
                                      'command and no default view is available.'])

    mmt_result = glif.get_mmt()
    if not mmt_result.success:
        return Items([]).with_errors([mmt_result.logs])
    mmt = mmt_result.value
    assert mmt

    archsub = glif.get_archive_subdir()
    if not archsub.success:
        return Items([]).with_errors(['"construct" failed.', archsub.logs])
    assert archsub.value

    def helperunwrap(s: Optional[str]) -> str:
        assert s
        return s

    asts = list({helperunwrap(item.try_get_repr(Repr.AST).value) for item in items.items})
    r = mmt.construct(asts, archsub.value[0], archsub.value[1], view, delta_expand=delta_expand, simplify=simplify)

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


CONSTRUCT_COMMAND_TYPE = GlifCommandType(
    names=['construct', 'c'],
    arguments=[
        GlifArg(['delta-expand', 'de'], 'Expand defined constants'),
        GlifArg(['no-simplify'], 'Don\'t simpilfy the resulting expression'),
        GlifArg(['view', 'v'], 'Specify the semantics construction view', default_value='$DEFAULT'),
    ],
    description='Applies the semantics construction',
    main_args_as_items=True,
    apply_fn=construct_helper,
    inrepr=Repr.AST,
)
