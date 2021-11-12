from ..glif_abc import GlifABC as Glif
from .items import Items, Repr
from .glif_command import GlifCommandType


def archive_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str]) -> Items:
    archive = mainargs[0]
    subdir = None
    if len(mainargs) > 1:
        subdir = mainargs[1]
    r = glif.set_archive(archive, subdir, create=True)
    output = []
    if r.value:
        output.append(r.value)
    if r.success:
        output.append('Successfully changed archive')
    errors = []
    if r.logs:
        errors.append(r.logs)
    return Items.from_vals(Repr.DEFAULT, output).with_errors(errors)


ARCHIVE_COMMAND_TYPE = GlifCommandType(
    names=['archive', 'a'],
    arguments=[],
    execute_fn=archive_helper,
    min_main_args=1,
    max_main_args=2,
)
