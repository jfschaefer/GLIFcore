from ..glif_abc import GlifABC as Glif
from glif.commands.items import Items, Repr
from .glif_command import GlifCommandType


def import_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str]) -> Items:
    logs = []
    errs = []
    for ma in mainargs:
        if ma.endswith('.gf'):
            r = glif.import_gf_file(ma)
            if r.success:
                logs.append(f'Successfully imported {ma}')
            else:
                errs.append(r.logs)
        elif ma.endswith('.mmt'):
            r = glif.import_mmt_file(ma)
            if r.success:
                logs.append(f'Successfully imported {ma}')
            else:
                errs.append(r.logs)
        elif ma.endswith('.elpi'):
            r = glif.import_elpi_file(ma)
            if r.success:
                logs.append(f'Successfully imported {ma}')
                if r.logs:
                    logs.append(r.logs)
            else:
                errs.append(r.logs)
        elif ma.endswith(".lex"):
            r = glif.import_lex_file(ma)
            if r.success:
                logs.append(f'Successfully imported {ma}')
                if r.logs:
                    logs.append(r.logs)
            else:
                errs.append(r.logs)
        else:
            errs.append(f'Unknown file extension in file {ma}')
    return Items.from_vals(Repr.DEFAULT, logs).with_errors(errs)


IMPORT_COMMAND_TYPE = GlifCommandType(
    names=['import', 'i'],
    arguments=[],
    description='Imports a file',
    execute_fn=import_helper,
)
