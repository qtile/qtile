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
import readline
import sys
import pprint
import re
import textwrap
import fcntl
import termios
import struct
import command
import ipc


def terminalWidth():
    width = None
    try:
        cr = struct.unpack('hh', fcntl.ioctl(0, termios.TIOCGWINSZ, '1234'))
        width = int(cr[1])
    except (IOError, ImportError):
        pass
    return width or 80


class QSh:

    def __init__(self, client, completekey="tab"):
        self.clientroot = client
        self.current = client
        self.completekey = completekey
        self.termwidth = terminalWidth()
        readline.set_completer(self.complete)
        readline.parse_and_bind(self.completekey + ": complete")
        readline.set_completer_delims(" ()|")
        self.builtins = [i[3:] for i in dir(self) if i.startswith("do_")]

    def _complete(self, buf, arg, state):
        if not re.search(r" |\(", buf) or buf.startswith("help "):
            options = self.builtins + self._commands()
            lst = [i for i in options if i.startswith(arg)]
            if lst and state < len(lst):
                return lst[state]
        elif buf.startswith("cd ") or buf.startswith("ls "):
            path = [i for i in arg.split("/") if i]
            if arg.endswith("/"):
                last = ""
            else:
                last = path[-1]
                path = path[:-1]
            node = self._findNode(self.current, *path)
            options = [str(i) for i in self._ls(node)]
            lst = []
            path = "/".join(path)
            if path:
                path += "/"
            for i in options:
                if i.startswith(last):
                    lst.append(path + i)
            if lst and state < len(lst):
                return lst[state]

    def complete(self, arg, state):
        buf = readline.get_line_buffer()
        return self._complete(buf, arg, state)

    @property
    def prompt(self):
        return "%s> " % self.current.path

    def columnize(self, lst):
        ret = []
        if lst:
            lst = [str(i) for i in lst]
            mx = max([len(i) for i in lst])
            cols = self.termwidth / (mx + 2) or 1
            for i in range(len(lst) / cols):
                sl = lst[i * cols: (i + 1) * cols]
                sl = [x + " " * (mx - len(x)) for x in sl]
                ret.append("  ".join(sl))
            if len(lst) % cols:
                sl = lst[-(len(lst) % cols):]
                sl = [x + " " * (mx - len(x)) for x in sl]
                ret.append("  ".join(sl))
        return "\n".join(ret)

    def _inspect(self, obj):
        """
            Returns an (attrs, keys) tuple.
        """
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

    def _commands(self):
        try:
            return self.current.commands()
        except command.CommandError:
            return []

    def _findNode(self, src, *path):
        """
            Returns a node, or None if no such node exists.
        """
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

    def do_cd(self, arg):
        """
            Change to another path.

            Examples:

                cd layout/0

                cd ../layout
        """
        next = self._findNode(self.current, *[i for i in arg.split("/") if i])
        if next:
            self.current = next
        else:
            return "No such path."

    def do_ls(self, arg):
        """
            List contained items on a node.

            Examples:

                ls

                ls ../layout
        """
        l = self._ls(self.current)
        l = ["%s/" % i for i in l]
        return self.columnize(l)

    def do_help(self, arg):
        """
            Provide an overview of all commands or detailed
            help on a specific command or builtin.

            Examples:

                help

                help command
        """
        cmds = self._commands()
        if not arg:
            lst = [
                "help command   -- Help for a specific command.",
                "",
                "Builtins:",
                "=========",
                self.columnize(self.builtins),
            ]
            if cmds:
                lst += [
                    "",
                    "Commands for this object:",
                    "=========================",
                    self.columnize(cmds),
                ]
            return "\n".join(lst)
        elif arg in cmds:
            return self._call("doc", "(\"%s\")" % arg)
        elif arg in self.builtins:
            c = getattr(self, "do_" + arg)
            return textwrap.dedent(c.__doc__).lstrip()
        else:
            return "No such command: %s" % arg

    def do_exit(self, args):
        """
            Exit qsh.
        """
        sys.exit(0)
    do_quit = do_exit
    do_q = do_exit

    def _call(self, cmd_name, args):
        cmds = self._commands()
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
        except SyntaxError, v:
            return "Syntax error in expression: %s" % v.text
        except command.CommandException, val:
            return "Command exception: %s\n" % val
        except ipc.IPCError:
            # on restart, try to reconnect
            if cmd_name == 'restart':
                client = command.Client(self.clientroot.client.fname)
                self.clientroot = client
                self.current = client
            else:
                raise

    def loop(self):
        while True:
            try:
                line = raw_input(self.prompt)
            except (EOFError, KeyboardInterrupt):
                print
                return
            if not line:
                continue

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
            if isinstance(val, basestring):
                print val
            elif val:
                pprint.pprint(val)
