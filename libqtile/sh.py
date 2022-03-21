# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
    A command shell for Qtile.
"""

from __future__ import annotations

import fcntl
import inspect
import pprint
import re
import struct
import sys
import termios
from importlib import import_module
from typing import TYPE_CHECKING

from libqtile.command.client import CommandClient
from libqtile.command.interface import (
    CommandError,
    CommandException,
    CommandInterface,
    format_selectors,
)

if TYPE_CHECKING:
    from typing import Any


def terminal_width():
    width = None
    try:
        cr = struct.unpack("hh", fcntl.ioctl(0, termios.TIOCGWINSZ, "1234"))
        width = int(cr[1])
    except (IOError, ImportError):
        pass
    return width or 80


class QSh:
    """Qtile shell instance"""

    def __init__(self, client: CommandInterface, completekey="tab") -> None:
        # Readline is imported here to prevent issues with terminal resizing
        # which would result from readline being imported when qtile is first
        # started
        self.readline = import_module("readline")
        self._command_client = CommandClient(client)
        self._completekey = completekey
        self._builtins = [i[3:] for i in dir(self) if i.startswith("do_")]

    def complete(self, arg, state) -> str | None:
        buf = self.readline.get_line_buffer()
        completers = self._complete(buf, arg)
        if completers and state < len(completers):
            return completers[state]
        return None

    def _complete(self, buf, arg) -> list[str]:
        if not re.search(r" |\(", buf) or buf.startswith("help "):
            options = self._builtins + self._command_client.commands
            lst = [i for i in options if i.startswith(arg)]
            return lst
        elif buf.startswith("cd ") or buf.startswith("ls "):
            path, sep, last = arg.rpartition("/")
            node, rest_path = self._find_path(path)

            if node is None:
                return []

            children, items = self._ls(node, rest_path)
            options = children + items
            completions = [path + sep + i for i in options if i.startswith(last)]

            if len(completions) == 1:
                # add a slash to continue completing the next part of the path
                return [completions[0] + "/"]

            return completions
        return []

    @property
    def prompt(self) -> str:
        return "{} > ".format(format_selectors(self._command_client.selectors))

    def columnize(self, lst, update_termwidth=True) -> str:
        if update_termwidth:
            self.termwidth = terminal_width()

        ret = []
        if lst:
            lst = list(map(str, lst))
            mx = max(map(len, lst))
            cols = self.termwidth // (mx + 2) or 1
            # We want `(n-1) * cols + 1 <= len(lst) <= n * cols` to return `n`
            # If we subtract 1, then do `// cols`, we get `n - 1`, so we can then add 1
            rows = (len(lst) - 1) // cols + 1
            for i in range(rows):
                # Because Python array slicing can go beyond the array bounds,
                # we don't need to be careful with the values here
                sl = lst[i * cols : (i + 1) * cols]
                sl = [x + " " * (mx - len(x)) for x in sl]
                ret.append("  ".join(sl))
        return "\n".join(ret)

    def _ls(self, client: CommandClient, object_type: str | None) -> tuple[list[str], list[str]]:
        if object_type is not None:
            allow_root, items = client.items(object_type)
            str_items = [str(i) for i in items]
            if allow_root:
                children = client.navigate(object_type, None).children
            else:
                children = []
            return children, str_items
        else:
            return client.children, []

    def _find_path(self, path: str) -> tuple[CommandClient | None, str | None]:
        """Find an object relative to the current node

        Finds and returns the command graph node that is defined relative to
        the current node.
        """
        root = self._command_client.root if path.startswith("/") else self._command_client
        parts = [i for i in path.split("/") if i]
        return self._find_node(root, *parts)

    def _find_node(
        self, src: CommandClient, *paths: str
    ) -> tuple[CommandClient | None, str | None]:
        """Find an object in the command graph

        Return the object in the command graph at the specified path relative
        to the given node.
        """
        if len(paths) == 0:
            return src, None

        path, *next_path = paths

        if path == "..":
            return self._find_node(src.parent or src, *next_path)

        if path not in src.children:
            return None, None

        if len(next_path) == 0:
            return src, path

        item, *maybe_next_path = next_path
        allow_root, items = src.items(path)

        for transformation in [str, int]:
            try:
                transformed_item = transformation(item)
            except ValueError:
                continue

            if transformed_item in items:
                next_node = src.navigate(path, transformed_item)
                return self._find_node(next_node, *maybe_next_path)

        if not allow_root:
            return None, None

        next_node = src.navigate(path, None)
        return self._find_node(next_node, *next_path)

    def do_cd(self, arg: str | None) -> str:
        """Change to another path.

        Examples
        ========

            cd layout/0

            cd ../layout
        """
        if arg is None:
            self._command_client = self._command_client.root
            return "/"

        next_node, rest_path = self._find_path(arg)
        if next_node is None:
            return "No such path."

        if rest_path is None:
            self._command_client = next_node
        else:
            allow_root, _ = next_node.items(rest_path)
            if not allow_root:
                return "Item required for {}".format(rest_path)
            self._command_client = next_node.navigate(rest_path, None)

        return format_selectors(self._command_client.selectors) or "/"

    def do_ls(self, arg: str | None) -> str:
        """List contained items on a node.

        Examples
        ========

                > ls
                > ls ../layout
        """
        if arg:
            node, rest_path = self._find_path(arg)
            if not node:
                return "No such path."
            base_path = arg.rstrip("/") + "/"
        else:
            node = self._command_client
            rest_path = None
            base_path = ""

        assert node is not None

        objects, items = self._ls(node, rest_path)

        formatted_ls = ["{}{}/".format(base_path, i) for i in objects] + [
            "{}[{}]/".format(base_path[:-1], i) for i in items
        ]
        return self.columnize(formatted_ls)

    def do_pwd(self, arg) -> str:
        """Returns the current working location

        This is the same information as presented in the qshell prompt, but is
        very useful when running iqshell.

        Examples
        ========

            > pwd
            /
            > cd bar/top
            bar['top']> pwd
            bar['top']
        """
        return format_selectors(self._command_client.selectors) or "/"

    def do_help(self, arg: str | None) -> str:
        """Give help on commands and builtins

        When invoked without arguments, provides an overview of all commands. When
        passed as an argument, also provides a detailed help on a specific command or
        builtin.

        Examples
        ========

            > help

            > help command
        """
        if not arg:
            lst = [
                "help command   -- Help for a specific command.",
                "",
                "Builtins",
                "========",
                self.columnize(self._builtins),
            ]
            cmds = self._command_client.commands
            if cmds:
                lst.extend(
                    [
                        "",
                        "Commands for this object",
                        "========================",
                        self.columnize(cmds),
                    ]
                )
            return "\n".join(lst)
        elif arg in self._command_client.commands:
            return self._command_client.call("doc", arg)
        elif arg in self._builtins:
            c = getattr(self, "do_" + arg)
            ret = inspect.getdoc(c)
            assert ret is not None
            return ret
        else:
            return "No such command: %s" % arg

    def do_exit(self, args) -> None:
        """Exit qshell"""
        sys.exit(0)

    do_quit = do_exit
    do_q = do_exit

    def process_line(self, line: str) -> Any:
        builtin_match = re.fullmatch(r"(?P<cmd>\w+)(?:\s+(?P<arg>\S*))?", line)
        if builtin_match:
            cmd = builtin_match.group("cmd")
            args = builtin_match.group("arg")
            if cmd in self._builtins:
                builtin = getattr(self, "do_" + cmd)
                val = builtin(args)
                return val
            else:
                return "Invalid builtin: {}".format(cmd)

        command_match = re.fullmatch(r"(?P<cmd>\w+)\((?P<args>[\w\s,]*)\)", line)
        if command_match:
            cmd = command_match.group("cmd")
            args = command_match.group("args")
            if args:
                cmd_args = tuple(map(str.strip, args.split(",")))
            else:
                cmd_args = ()

            if cmd not in self._command_client.commands:
                return "Command does not exist: {}".format(cmd)

            try:
                return self._command_client.call(cmd, *cmd_args)
            except CommandException as e:
                return (
                    "Caught command exception (is the command invoked incorrectly?): {}\n".format(
                        e
                    )
                )

        return "Invalid command: {}".format(line)

    def loop(self) -> None:
        self.readline.set_completer(self.complete)
        self.readline.parse_and_bind(self._completekey + ": complete")
        self.readline.set_completer_delims(" ()|")

        while True:
            try:
                line = input(self.prompt)
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue

            try:
                val = self.process_line(line)
            except CommandError as e:
                val = "Caught command error (is the current path still valid?): {}\n".format(e)
            if isinstance(val, str):
                print(val)
            elif val:
                pprint.pprint(val)
