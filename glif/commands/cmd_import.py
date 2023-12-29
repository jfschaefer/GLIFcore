from typing import Callable

from glif.glif_abc import GlifABC as Glif
from glif.commands.items import Items, Repr
from glif.commands.glif_command import GlifCommandType
from glif.utils import Result


def import_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str]) -> Items:
    logs = []
    errs = []
    for ma in mainargs:
        if '.' not in ma:
            errs.append(f'No file extension in file {ma} - skipping')
            continue
        extension = ma.split('.')[-1]
        import_lookup: dict[str, Callable[[str], Result]] = {
            'gf': glif.import_gf_file,
            'mmt': glif.import_mmt_file,
            'elpi': glif.import_elpi_file,
            'lex': glif.import_lex_file,
        }
        if extension not in import_lookup:
            errs.append(f'Unknown file extension in file {ma} - skipping')
            continue
        r = import_lookup[extension](ma)
        if r.success:
            logs.append(f'Successfully imported {ma}')
            if r.logs:
                logs.append(r.logs)
        else:
            errs.append(r.logs)

    return Items.from_vals(Repr.DEFAULT, logs).with_errors(errs)


IMPORT_COMMAND_TYPE = GlifCommandType(
    names=['import', 'i'],
    arguments=[],
    description='Imports a file',
    execute_fn=import_helper,
)
