from .cmd_import import IMPORT_COMMAND_TYPE
from .cmd_archive import ARCHIVE_COMMAND_TYPE
from .cmd_populate import POPULATE_COMMAND_TYPE
from .cmd_status import STATUS_COMMAND_TYPE
from .cmd_construct import CONSTRUCT_COMMAND_TYPE
from .cmd_elpigen import ELPIGEN_COMMAND_TYPE
from .cmd_filter import FILTER_COMMAND_TYPE
from .cmd_help import HELP_COMMAND_TYPE
from .cmd_query import QUERY_COMMAND_TYPE
from .cmd_apply import APPLY_COMMAND_TYPE

GLIF_COMMAND_TYPES = [
    IMPORT_COMMAND_TYPE,
    ARCHIVE_COMMAND_TYPE,
    STATUS_COMMAND_TYPE,
    CONSTRUCT_COMMAND_TYPE,
    POPULATE_COMMAND_TYPE,
    ELPIGEN_COMMAND_TYPE,
    FILTER_COMMAND_TYPE,
    HELP_COMMAND_TYPE,
    QUERY_COMMAND_TYPE,
    APPLY_COMMAND_TYPE,
]
