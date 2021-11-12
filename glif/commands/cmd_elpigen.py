import os

from ..glif_abc import GlifABC as Glif
from .items import Items, Repr
from .glif_command import GlifCommandType, GlifArg

def elpigen_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str]) -> Items:
    meta = 'with-meta' in keys
    includes = 'no-includes' not in keys
    mode = keyval['mode']
    theory = mainargs[0]
    file = keyval['file']
    if file == '$DEFAULT':
        file = theory

    if not file.endswith('.elpi'):
        file += '.elpi'

    mmtr = glif.get_mmt()
    if not mmtr.success:
        return Items([]).with_errors(['Failed load MMT:\n' + mmtr.logs])
    assert mmtr.value
    mmt = mmtr.value
    asr = glif.get_archive_subdir()
    if not asr.success:
        return Items([]).with_errors([asr.logs])
    assert asr.value
    archive, subdir = asr.value

    r = mmt.elpigen(mode, archive, subdir, theory, meta, includes)
    if not r.success:
        return Items([]).with_errors(['Failed to generate ELPI code:\n' + r.logs])
    assert r.value
    with open(os.path.join(glif.get_cwd(), file), 'w') as f:
        f.write(r.value)
    return Items.from_vals(Repr.DEFAULT, [f'Successfully created {file}'])


ELPIGEN_COMMAND_TYPE = GlifCommandType(
    names=['elpigen', 'eg'],
    arguments=[
        GlifArg(['with-meta', 'wm'], 'Also generate ELPI code for meta theories'),
        GlifArg(['no-includes', 'ni'], 'Don\'t generate ELPI code for included theories'),
        GlifArg(['file', 'f'], 'The file to generate ELPI code from', default_value='$DEFAULT'),
        GlifArg(['mode', 'm'], 'The mode of ELPI generation', default_value='types',
                value_set={'types', 'simpleprover'}),
    ],
    min_main_args=1,
    max_main_args=1,
    execute_fn=elpigen_helper,
)
