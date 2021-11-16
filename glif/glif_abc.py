"""
    Provides abstract base classes (abc) to avoid circular dependencies,
    which are mostly caused by imports for type hints.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any

from .utils import Result
from . import mmt, gf
from .commands import items


class GlifABC(ABC):

    @abstractmethod
    def set_archive(self, archive: str, subdir: Optional[str], create: bool = False) -> Result[str]:
        raise NotImplementedError()

    @abstractmethod
    def get_archive_subdir(self) -> Result[tuple[str, Optional[str]]]:
        raise NotImplementedError()

    def get_defaultview(self) -> Optional[str]:
        return None

    def get_defaultelpi(self) -> Optional[str]:
        return None

    @abstractmethod
    def get_commands(self) -> dict[str, Any]:
        raise NotImplementedError()

    @abstractmethod
    def stub_gen(self, target: str) -> Result[str]:
        raise NotImplementedError()

    @abstractmethod
    def get_cwd(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_mmt(self) -> Result[mmt.MMTInterface]:
        raise NotImplementedError()

    @abstractmethod
    def execute_cell(self, code: str) -> list[Result[items.Items]]:
        raise NotImplementedError()

    @abstractmethod
    def execute_commands(self, code: str) -> list[Result[items.Items]]:
        raise NotImplementedError()

    @abstractmethod
    def execute_command(self, command: str) -> Result[items.Items]:
        raise NotImplementedError()

    @abstractmethod
    def import_gf_file(self, filename: str) -> Result[None]:
        raise NotImplementedError()

    @abstractmethod
    def import_mmt_file(self, filename: str) -> Result[None]:
        raise NotImplementedError()

    @abstractmethod
    def import_elpi_file(self, filename: str) -> Result[None]:
        raise NotImplementedError()

    @abstractmethod
    def get_gf_shell(self) -> Result[gf.GFShellRaw]:
        raise NotImplementedError()

    @abstractmethod
    def do_shutdown(self):
        raise NotImplementedError()
