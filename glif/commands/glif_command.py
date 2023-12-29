from glif.commands.command import Command, CommandType
from glif.parsing import BasicCommand
from glif.commands.items import Items, Repr
from glif.glif_abc import GlifABC as Glif
from glif.utils import Result, indent

from typing import Callable, Optional


class GlifArg(object):
    has_value: bool
    value_set: Optional[set[str]] = None
    names: list[str]
    description: str
    default: Optional[str] = None  # no default => mandatory argument

    def __init__(self, names: list[str], description: str, has_value: Optional[bool] = None,
                 value_set: Optional[set[str]] = None, default_value: Optional[str] = None):
        assert names
        self.names = names
        self.description = description
        if has_value or value_set or default_value:
            assert has_value or has_value is None
            self.has_value = True
            if value_set:
                self.value_set = value_set
            if default_value:
                self.default = default_value
                if value_set:
                    assert default_value in value_set
        else:
            self.has_value = False

    def get_main_name(self) -> str:
        return self.names[0]

    def __str__(self) -> str:
        r = ' | '.join(f'-{n}' for n in self.names)
        if self.value_set:
            r += '\n    Possible values: ' + ', '.join(self.value_set)
        if self.default:
            r += '\n    Default value: ' + (self.default if self.default != '$DEFAULT' else 'chosen from context')
        r += '\n    ' + self.description
        return r


class GlifCommandType(CommandType):
    """ for standard GLIF commands """

    def __init__(self, names: list[str], arguments: list[GlifArg], min_main_args: int = 0,
                 description: str = 'No description provided',
                 max_main_args: Optional[int] = None, main_args_as_items: bool = False,
                 inrepr: Optional[Repr] = None,
                 execute_fn: Optional[Callable[[Glif, dict[str, str], set[str], list[str]], Items]] = None,
                 apply_fn: Optional[Callable[[Glif, dict[str, str], set[str], list[str], Items], Items]] = None,
                 example_calls: list[str] = []):
        super().__init__(names)
        self.arguments = arguments
        self.str_to_arg: dict[str, GlifArg] = {}
        for arg in arguments:
            for name in arg.names:
                self.str_to_arg[name] = arg
        self.min_main_args = min_main_args
        self.max_main_args = max_main_args
        self.main_args_as_items = main_args_as_items
        self.inrepr = inrepr
        self.execute_fn = execute_fn
        self.apply_fn = apply_fn
        if main_args_as_items:
            assert self.inrepr

        # generate description
        self._long_descr = f'{description}\n\nFlags:\n'
        if not arguments:
            self._long_descr += '    None'
        else:
            self._long_descr += '\n\n'.join((indent(str(arg), 4) for arg in arguments))
        self._long_descr += '\n\nExample calls:\n'
        if example_calls:
            self._long_descr += '\n'.join((indent(ec, 4) for ec in example_calls))
        else:
            self._long_descr += '    None'

    def _basiccommand_to_command(self, cmd: BasicCommand) -> Result[Command]:
        args = self.extract_arguments(cmd)
        if not args.success:
            return Result(False, None, args.logs)
        assert args.value
        execute_fn = None
        if self.execute_fn:
            execute_fn = lambda glif: self.execute_fn(glif, args.value[0], args.value[1], cmd.mainargs)
        apply_fn = None
        if self.apply_fn:
            apply_fn = lambda glif, item: self.apply_fn(glif, args.value[0], args.value[1], cmd.mainargs, item)
        main_arg_items = None
        if self.main_args_as_items:
            assert self.inrepr
            main_arg_items = Items.from_vals(self.inrepr, cmd.mainargs)
        command = Command(self, execute_fn, apply_fn, main_arg_items)
        return Result(True, command)

    def extract_arguments(self, cmd: BasicCommand) -> Result[tuple[dict[str, str], set[str]]]:
        """ returns keyval dict and flags """
        keyvals: dict[str, str] = {}
        flags: set[str] = set()
        for arg in cmd.args:
            if arg.key not in self.str_to_arg:
                return Result(False, None, f'Invalid argument "{arg.key}" for command "{cmd.name}"')
            argument = self.str_to_arg[arg.key]
            arg_main_name = argument.get_main_name()
            if arg_main_name in keyvals or arg_main_name in flags:
                return Result(False, None,
                              f'Argument "{arg.value}" provided twice for command "{cmd.name}"')
            if arg.value:
                if not argument.has_value:
                    return Result(False, None,
                                  f'Argument "{arg.key}" must not have a value for command "{cmd.name}"')
                if argument.value_set and arg.value not in argument.value_set:
                    return Result(False, None, f'Invalid value "{arg.value}" for argument "{arg.key}" '
                                               f'for command "{cmd.name}"')
                keyvals[arg_main_name] = arg.value
            else:
                if argument.has_value:
                    return Result(False, None,
                                  f'Argument "{arg.key}" must have a value for command "{cmd.name}"')
                flags.add(arg_main_name)

        if len(cmd.mainargs) < self.min_main_args:
            return Result(False, None, f'Command "{cmd.name}" requires at least {self.min_main_args} arguments '
                                       f'(found {len(cmd.mainargs)})')

        if self.max_main_args is not None and len(cmd.mainargs) > self.max_main_args:
            return Result(False, None, f'Command "{cmd.name}" can have at most {self.max_main_args} arguments '
                                       f'(found {len(cmd.mainargs)})')
        for argument in self.str_to_arg.values():
            arg_main_name = argument.get_main_name()
            if arg_main_name not in flags and arg_main_name not in keyvals:
                if argument.has_value:
                    if argument.default is None:
                        return Result(False, None,
                                      f'Command "{cmd.name}" requires argument "{argument.get_main_name()}"')
                    else:
                        keyvals[arg_main_name] = argument.default
        return Result(True, (keyvals, flags))
