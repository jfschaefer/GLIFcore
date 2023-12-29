from glif.glif_abc import GlifABC as Glif
from glif.utils import indent
from glif.commands.items import Items, Repr
from glif.commands.glif_command import GlifCommandType


def help_helper(glif: Glif, keyval: dict[str, str], keys: set[str], mainargs: list[str]) -> Items:
    result = []
    errors = []
    commands = glif.get_commands()
    if not mainargs:
        for command in set(commands.values()):
            result.append(indent(', '.join(command.names), 4))
        result.sort()
        result = ['Currently available commands:'] + result
        result.append('\n\nRun "help [COMMAND]" to learn more about a particular command')
    else:
        for arg in mainargs:
            if arg not in commands:
                errors.append(f'Unknown command "{arg}"')
                continue
            result.append(commands[arg].get_long_descr(glif))

    return Items.from_vals(Repr.DEFAULT, result).with_errors(errors)


HELP_COMMAND_TYPE = GlifCommandType(
    names=['help', 'h'],
    arguments=[],
    description='Prints information about available GLIF commands',
    execute_fn=help_helper,
    example_calls=['help', 'help construct'],
)
