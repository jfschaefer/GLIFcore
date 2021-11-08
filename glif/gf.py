import os
import subprocess

from typing import Optional

# Basically a unique string that will never show up in the output (hopefully)
COMMAND_SEPARATOR = "COMMAND_SEPARATOR===??!<>239'_"


class GFShellRaw(object):
    def __init__(self, gf_path: str, cwd: str = None, args: Optional[list[str]] = None):
        if args is None:
            args = []
        pipe = os.pipe()
        self.gf_shell = subprocess.Popen([gf_path, '--run'] + args,
                                         stdin=subprocess.PIPE,
                                         stderr=pipe[1],
                                         stdout=pipe[1],
                                         text=True,
                                         cwd=cwd)
        self.commandcounter = 0
        self.infile = os.fdopen(pipe[0])
        self.gfoutfd = pipe[1]
        assert self.gf_shell.stdin is not None
        self.outfile = self.gf_shell.stdin

        # catch any initial messages
        sep = self.__write_separator()
        self.outfile.flush()
        self.initialOutput = self.__get_output(sep)

    def __write_cmd(self, cmd):
        if not cmd.endswith('\n'):
            cmd += '\n'
        self.outfile.write(cmd)
        self.commandcounter += 1

    def __write_separator(self):
        sep = COMMAND_SEPARATOR + str(self.commandcounter)
        self.outfile.write(f"ps \"{sep}\"\n")
        return sep

    def __get_output(self, sep):
        """Reads lines until sep found"""
        output = ""
        for line in self.infile:
            if line.rstrip() == sep:
                return output
            if line != '\n':  # ignore empty lines
                output += line

    def handle_command(self, cmd: str) -> str:
        """Forwards a command to the GF Shell and returns the output"""
        self.__write_cmd(cmd)
        sep = self.__write_separator()
        self.outfile.flush()
        res = self.__get_output(sep).strip()
        return res

    def do_shutdown(self):
        """Terminates the GF shell"""
        self.gf_shell.communicate('q\n', timeout=1)
        self.outfile.close()
        self.infile.close()
        self.gf_shell.kill()
        os.fdopen(self.gfoutfd).close()  # TODO: Why do I need this?


if __name__ == "__main__":
    from distutils.spawn import find_executable

    path = find_executable('gf')
    assert path is not None
    gfShell = GFShellRaw(path)
    print(gfShell.initialOutput)
    print('\n------------\n')
    while True:
        line = input("> ")
        print(gfShell.handle_command(line))
