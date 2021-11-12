import subprocess
from distutils.spawn import find_executable
from typing import Any

from .items import Items, Repr
from .glif_command import GlifCommandType, GlifArg


def status_helper(glif: Any, keyval: dict[str, str], keys: set[str], mainargs: list[str]) -> Items:
    # Note using `glif: Any` as it has to work with the internals of Glif, which are not offered by GlifABC

    result = ['Current working directory: ' + glif._cwd]

    # GF
    if 'load-gf' in keys:
        glif.get_gf_shell()
    result.append('')
    result.append('GF STATUS')
    if glif._gfshell:
        result.append('GF is running')
        if 'gf-logs' in keys:
            result.append('GF LOGS')
            result.append(glif._gfshell.initialOutput)
    else:
        result.append('GF is not running')
        if glif._gfshellFailedLogs:
            result.append(glif._gfshellFailedLogs)

    # MMT
    if 'load-mmt' in keys:
        glif.get_mmt()
    result.append('')
    result.append('MMT STATUS')
    if glif._mmt:
        result.append(f'MMT is running on port {glif._mmt.server.port}')
    else:
        result.append(f'MMT is not running')
    result.append('Logs from initialization')
    result += glif._findMMTlogs
    if glif._mmtFailedStartupMessage:
        result.append(glif._mmtFailedStartupMessage)
    if 'mmt-logs' in keys:
        result.append('MMT STARTUP LOGS')
        if glif._mmt:
            result += glif._mmt.server.mmtlogstart
            result.append('MMT MOST RECENT LOGS')
            result += glif._mmt.server.mmtlogtail
        else:
            result += glif._mmtFailedStartupLogs

    # ELPI
    result.append('')
    result.append('ELPI STATUS')
    elpipath = find_executable('elpi')
    if not elpipath:
        result.append('Failed to locate executable "elpi"')
    else:
        result.append('ELPI location: ' + elpipath)
        try:
            result.append('ELPI version: ' + subprocess.check_output([elpipath, '-version'], text=True).strip())
        except:
            result.append('"elpi -version" failed')

    return Items.from_vals(Repr.DEFAULT, result)


STATUS_COMMAND_TYPE = GlifCommandType(
    names=['status', 's'],
    arguments=[
        GlifArg(['load-gf', 'lg'], 'Load the GF shell if it hadn\'t been loaded before'),
        GlifArg(['load-mmt', 'lm'], 'Load the MMT interface if it hadn\'t been loaded before'),
        GlifArg(['gf-logs', 'gl'], 'Show the output of the GF start-up'),
        GlifArg(['mmt-logs', 'ml'], 'Show MMT logs'),
    ],
    max_main_args=0,
    execute_fn=status_helper,
)
