from typing import Callable, Optional
from abc import ABC, abstractmethod

from glif.glif_abc import GlifABC as Glif
from glif.commands.items import Items
from glif.parsing import parse_basic_command, BasicCommand
from glif.utils import Result


class CommandTypeABC(ABC):
    @abstractmethod
    def get_main_name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_long_descr(self, glif: Glif) -> str:
        raise NotImplementedError()


class Command(object):
    """
        A command that may be executed or applied to items.
    """

    def __init__(self,
                 command_type: CommandTypeABC,
                 execute_fn: Optional[Callable[[Glif], Items]] = None,
                 apply_fn: Optional[Callable[[Glif, Items], Items]] = None,
                 itemsFromArgs: Optional[Items] = None):
        self.command_type = command_type
        self.execute_fn = execute_fn
        self.apply_fn = apply_fn
        self.itemsFromArgs = itemsFromArgs

    def execute(self, glif: Glif) -> Items:
        if self.itemsFromArgs:
            return self._internal_apply(glif, self.itemsFromArgs)
        elif self.execute_fn:
            return self.execute_fn(glif)
        else:
            return Items([]).with_errors([f'No input was provided for command {self.command_type.get_main_name()}'])

    def apply(self, glif: Glif, items: Items) -> Items:
        """ If input is provided (`items`) """
        if self.itemsFromArgs and self.itemsFromArgs.items:
            return self.itemsFromArgs.with_errors(
                [f'No input was expected for command {self.command_type.get_main_name()}'])
        return self._internal_apply(glif, items)

    def _internal_apply(self, glif: Glif, items: Items) -> Items:
        if not self.apply_fn:
            return items.with_errors([f'No input was expected for the command {self.command_type.get_main_name()}'])
        return self.apply_fn(glif, items)


class CommandType(CommandTypeABC):
    """
        A type of command (e.g. parse) that can parse command strings of that type
        to create concrete commands.
    """
    _split_mainarg_at_space: bool = True
    _long_descr: Optional[str] = None

    def __init__(self, names: list[str]):
        assert names
        self.names: list[str] = names  # Command names, e.g. ['view_tree', 'vt']

    def from_string(self, string: str) -> Result[tuple[Command, str]]:
        """ returns (concrete command, remaining string (in case of pipes)). """
        string = string.strip()
        cmdresult = parse_basic_command(string, split_mainarg_at_space=self._split_mainarg_at_space)
        if not cmdresult.success:
            return Result(False, logs=cmdresult.logs)
        assert cmdresult.value
        cmd, rest = cmdresult.value
        assert cmd.name in self.names
        command = self._basiccommand_to_command(cmd)
        if command.success:
            assert command.value
            return Result(True, value=(command.value, rest))
        else:
            return Result(False, None, command.logs)

    def _basiccommand_to_command(self, cmd: BasicCommand) -> Result[Command]:
        raise NotImplementedError()

    #     def get_short_descr(self, glif: Glif) -> str:
    #         return 'No description available'

    def get_long_descr(self, glif: Glif) -> str:
        if not self._long_descr:
            return 'No description available'
        return self._long_descr

    def get_main_name(self) -> str:
        return self.names[0]
