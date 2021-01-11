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

import fcntl
import inspect
import pprint
import re
import readline
import struct
import sys
import termios
from typing import List, Optional, Tuple

from libqtile.command import graph
from libqtile.command.interface import (
    CommandError,
    CommandException,
    CommandInterface,
    format_selectors,
)


def terminal_width():
    width = None
    try:
        cr = struct.unpack('hh', fcntl.ioctl(0, termios.TIOCGWINSZ, '1234'))
        width = int(cr[1])
    except (IOError, ImportError):
        pass
    return width or 80


class QSh:
    """Qtile shell instance"""
    def __init__(self, client: CommandInterface, completekey="tab") -> None:
        self._client = client
        self._current_node = graph.CommandGraphRoot()  # type: graph.CommandGraphNode
        self._completekey = completekey
        self._builtins = [i[3:] for i in dir(self) if i.startswith("do_")]
        self._termwidth = terminal_width()

    def complete(self, arg, state) -> Optional[str]:
        buf = readline.get_line_buffer()
        completers = self._complete(buf, arg)
        if completers and state < len(completers):
            return completers[state]
        return None

    def _complete(self, buf, arg) -> List[str]:
        if not re.search(r" |\(", buf) or buf.startswith("help "):
            options = self._builtins + self._commands
            lst = [i for i in options if i.startswith(arg)]
            return lst
        elif buf.startswith("cd ") or buf.startswith("ls "):
            last_slash = arg.rfind("/") + 1
            path, last = arg[:last_slash], arg[last_slash:]
            node = self._find_path(path)
            if node is None:
                return []
            options = [str(i) for i in self._ls(node)]
            lst = []
            if path and not path.endswith("/"):
                path += "/"
            for i in options:
                if i.startswith(last):
                    lst.append(path + i)

            if len(lst) == 1:
                # add a slash to continue completing the next part of the path
                return [lst[0] + "/"]

            return lst
        return []

    @property
    def prompt(self) -> str:
        return "{} > ".format(format_selectors(self._current_node.selectors))

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
                sl = lst[i * cols: (i + 1) * cols]
                sl = [x + " " * (mx - len(x)) for x in sl]
                ret.append("  ".join(sl))
        return "\n".join(ret)

    @property
    def _commands(self) -> List[str]:
        try:
            commands_cmd = self._current_node.call("commands")
            return self._client.execute(commands_cmd, (), {})
        except CommandError:
            return []

    def _inspect(self, obj: graph.CommandGraphNode) -> Tuple[Optional[List[str]], Optional[List[str]]]:
        """Returns an (attrs, keys) tuple"""
        if isinstance(obj, graph.CommandGraphObject) and obj.selector is None:
            items_call = obj.parent.call("items")
            allow_root, items = self._client.execute(items_call, (obj.object_type,), {})
            attrs = obj.children if allow_root else None
            return attrs, items
        else:
            return obj.children, None

    def _ls(self, obj: graph.CommandGraphNode) -> List[str]:
        attrs, itms = self._inspect(obj)
        all_items = []  # type: List[str]
        if attrs:
            all_items.extend(attrs)
        if itms:
            all_items.extend(itms)
        return all_items

    def _find_path(self, path: str) -> Optional[graph.CommandGraphNode]:
        """Find an object relative to the current node

        Finds and returns the command graph node that is defined relative to
        the current node.
        """
        root = graph.CommandGraphRoot() if path.startswith("/") else self._current_node
        parts = [i for i in path.split("/") if i]
        return self._find_node(root, *parts)

    def _find_node(self,
                   src: graph.CommandGraphNode,
                   *paths: str) -> Optional[graph.CommandGraphNode]:
        """Find an object in the command graph

        Return the object in the command graph at the specified path relative
        to the given node.
        """
        if len(paths) == 0:
            return src

        path, *next_path = paths

        next_node = None
        if path == "..":
            next_node = src.parent or src
        else:
            attrs, items = self._inspect(src)
            for transformation in [str, int]:
                try:
                    transformed_path = transformation(path)
                except ValueError:
                    continue

                if attrs is not None and transformed_path in attrs:
                    nav_node = src.navigate(transformed_path, None)
                    next_node = nav_node
                    break
                elif items is not None and transformed_path in items:
                    assert isinstance(src, graph.CommandGraphObject)
                    nav_node = src.parent.navigate(src.object_type, transformed_path)
                    next_node = nav_node
                    break

        if next_node:
            return self._find_node(next_node, *next_path)
        else:
            return None

    def do_cd(self, arg) -> str:
        """Change to another path.

        Examples
        ========

            cd layout/0

            cd ../layout
        """
        next_node = self._find_path(arg)
        if next_node is not None:
            self._current_node = next_node
            return format_selectors(self._current_node.selectors) or '/'
        else:
            return "No such path."

    def do_ls(self, arg: str) -> str:
        """List contained items on a node.

        Examples
        ========

                > ls
                > ls ../layout
        """
        if arg:
            node = self._find_path(arg)
            if not node:
                return "No such path."
        else:
            node = self._current_node

        ls = self._ls(node)
        formatted_ls = ["{}/".format(i) for i in ls]
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
        return format_selectors(self._current_node.selectors) or '/'

    def do_help(self, arg) -> str:
        """Give help on commands and builtins

        When invoked without arguments, provides an overview of all commands.
        When passed as an argument, also provides a detailed help on a specific command or builtin.

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
            cmds = self._commands
            if cmds:
                lst.extend([
                    "",
                    "Commands for this object",
                    "========================",
                    self.columnize(cmds),
                ])
            return "\n".join(lst)
        elif arg in self._commands:
            call = self._current_node.call("doc")
            return self._client.execute(call, (arg,), {})
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

    def process_line(self, line: str) -> str:
        builtin_match = re.fullmatch(r"(?P<cmd>\w+)(?:\s+(?P<arg>\S+))?", line)
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

            if not self._client.has_command(self._current_node, cmd):
                return "Command does not exist: {}".format(cmd)

            cmd_call = self._current_node.call(cmd)

            try:
                return self._client.execute(cmd_call, cmd_args, {})
            except CommandException as e:
                return "Command exception: {}\n".format(e)

        return "Invalid command: {}".format(line)

    def loop(self) -> None:
        readline.set_completer(self.complete)
        readline.parse_and_bind(self._completekey + ": complete")
        readline.set_completer_delims(" ()|")

        while True:
            try:
                line = input(self.prompt)
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue

            val = self.process_line(line)
            if isinstance(val, str):
                print(val)
            elif val:
                pprint.pprint(val)
