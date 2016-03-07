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
from __future__ import division, print_function

import fcntl
import inspect
import pprint
import re
import readline
import struct
import sys
import termios

import six
from six.moves import input

from . import command, ipc


def terminalWidth():
    width = None
    try:
        cr = struct.unpack('hh', fcntl.ioctl(0, termios.TIOCGWINSZ, '1234'))
        width = int(cr[1])
    except (IOError, ImportError):
        pass
    return width or 80


class QSh(object):
    """Qtile shell instance"""
    def __init__(self, client, completekey="tab"):
        self.clientroot = client
        self.current = client
        self.completekey = completekey
        self.builtins = [i[3:] for i in dir(self) if i.startswith("do_")]
        self.termwidth = terminalWidth()

    def _complete(self, buf, arg):
        if not re.search(r" |\(", buf) or buf.startswith("help "):
            options = self.builtins + self._commands
            lst = [i for i in options if i.startswith(arg)]
            return lst
        elif buf.startswith("cd ") or buf.startswith("ls "):
            last_slash = arg.rfind("/") + 1
            path, last = arg[:last_slash], arg[last_slash:]
            node = self._findPath(path)
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

    def complete(self, arg, state):
        buf = readline.get_line_buffer()
        completers = self._complete(buf, arg)
        if completers and state < len(completers):
            return completers[state]

    @property
    def prompt(self):
        return "%s> " % self.current.path

    def columnize(self, lst, update_termwidth=True):
        if update_termwidth:
            self.termwidth = terminalWidth()

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

    def _inspect(self, obj):
        """Returns an (attrs, keys) tuple"""
        if obj.parent and obj.myselector is None:
            t, itms = obj.parent.items(obj.name)
            attrs = obj._contains if t else None
            return (attrs, itms)
        else:
            return (obj._contains, [])

    def _ls(self, obj):
        attrs, itms = self._inspect(obj)
        all = []
        if attrs:
            all.extend(attrs)
        if itms:
            all.extend(itms)
        return all

    @property
    def _commands(self):
        try:
            # calling `.commands()` here triggers `CommandRoot.cmd_commands()`
            return self.current.commands()
        except command.CommandError:
            return []

    def _findNode(self, src, *path):
        """Returns a node, or None if no such node exists"""
        if not path:
            return src

        attrs, itms = self._inspect(src)
        next = None
        if path[0] == "..":
            next = src.parent or src
        else:
            for trans in [str, int]:
                try:
                    tpath = trans(path[0])
                except ValueError:
                    continue
                if attrs and tpath in attrs:
                    next = getattr(src, tpath)
                elif itms and tpath in itms:
                    next = src[tpath]
        if next:
            if path[1:]:
                return self._findNode(next, *path[1:])
            else:
                return next
        else:
            return None

    def _findPath(self, path):
        root = self.clientroot if path.startswith("/") else self.current
        parts = [i for i in path.split("/") if i]
        return self._findNode(root, *parts)

    def do_cd(self, arg):
        """Change to another path.

        Examples
        ========

            cd layout/0

            cd ../layout
        """
        next = self._findPath(arg)
        if next:
            self.current = next
            return self.current.path or '/'
        else:
            return "No such path."

    def do_ls(self, arg):
        """List contained items on a node.

        Examples
        ========

                > ls
                > ls ../layout
        """
        path = self.current
        if arg:
            path = self._findPath(arg)
            if not path:
                return "No such path."

        l = self._ls(path)
        l = ["%s/" % i for i in l]
        return self.columnize(l)

    def do_pwd(self, arg):
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
        return self.current.path or '/'

    def do_help(self, arg):
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
                self.columnize(self.builtins),
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
            return self._call("doc", "(\"%s\")" % arg)
        elif arg in self.builtins:
            c = getattr(self, "do_" + arg)
            return inspect.getdoc(c)
        else:
            return "No such command: %s" % arg

    def do_exit(self, args):
        """Exit qshell"""
        sys.exit(0)

    do_quit = do_exit
    do_q = do_exit

    def _call(self, cmd_name, args):
        cmds = self._commands
        if cmd_name not in cmds:
            return "No such command: %s" % cmd_name

        cmd = getattr(self.current, cmd_name)
        if args:
            args = "".join(args)
        else:
            args = "()"
        try:
            val = eval(
                "cmd%s" % args,
                {},
                dict(cmd=cmd)
            )
            return val
        except SyntaxError as v:
            return "Syntax error in expression: %s" % v.text
        except command.CommandException as val:
            return "Command exception: %s\n" % val
        except ipc.IPCError:
            # on restart, try to reconnect
            if cmd_name == 'restart':
                client = command.Client(self.clientroot.client.fname)
                self.clientroot = client
                self.current = client
            else:
                raise

    def process_command(self, line):
        match = re.search(r"\W", line)
        if match:
            cmd = line[:match.start()].strip()
            args = line[match.start():].strip()
        else:
            cmd = line
            args = ''

        builtin = getattr(self, "do_" + cmd, None)
        if builtin:
            val = builtin(args)
        else:
            val = self._call(cmd, args)

        return val

    def loop(self):
        readline.set_completer(self.complete)
        readline.parse_and_bind(self.completekey + ": complete")
        readline.set_completer_delims(" ()|")

        while True:
            try:
                line = input(self.prompt)
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue

            val = self.process_command(line)
            if isinstance(val, six.string_types):
                print(val)
            elif val:
                pprint.pprint(val)
