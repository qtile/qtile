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
import readline, sys, pprint, re
import fcntl, termios, struct
import command


def terminalWidth():
    width = None
    try:
        cr = struct.unpack('hh', fcntl.ioctl(0, termios.TIOCGWINSZ, '1234'))
        width = int(cr[1])
    except (IOError, ImportError):
        pass
    return width or 80


class QSh:
    def __init__(self, client, completekey = "tab"):
        self.clientroot, self.current = client, client
        self.completekey = completekey
        self.termwidth = terminalWidth()
        readline.set_completer(self.complete)
        readline.parse_and_bind(self.completekey+": complete")

    def complete(self, a, state):
        if state < 10:
            return a + "foo" + str(state)

    @property
    def prompt(self):
        return "%s> "%self.current.path

    def columnize(self, lst):
        ret = []
        if lst:
            lst = [str(i) for i in lst]
            mx = max([len(i) for i in lst])
            cols = self.termwidth / (mx+2)
            if not cols:
                cols = 1
            for i in range(len(lst)/cols):
                sl = lst[i*cols:(i+1)*cols]
                sl = [x + " "*(mx-len(x)) for x in sl]
                ret.append("  ".join(sl))
            if len(lst)%cols:
                sl = lst[-(len(lst)%cols):]
                sl = [x + " "*(mx-len(x)) for x in sl]
                ret.append("  ".join(sl))
        return "\n".join(ret)

    def smartLs(self, obj):
        """
            Returns an (attrs, keys) tuple.
        """
        if obj.parent and obj.myselector is None:
            t, itms = obj.parent.items(obj.name)
            attrs = obj._contains if t else None
            return attrs, itms
        else:
            return obj._contains, None
        sub = obj.parent

    def _findNode(self, src, *path):
        """
            Returns a node, or None if no such node exists.
        """
        attrs, itms = self.smartLs(src)
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
        next = self._findNode(self.current, *[i for i in arg.split("/") if i])
        if next:
            self.current = next
        else:
            return "No such path."

    def do_ls(self, arg):
        attrs, itms = self.smartLs(self.current)
        all = []
        if attrs:
            all.extend(attrs)
        if itms:
            all.extend(itms)
        all = ["%s/"%i for i in all]
        return self.columnize(all)

    def do_help(self, arg):
        return self.columnize(self.current.commands())

    def do_exit(self, args):
        sys.exit(0)
    do_quit = do_exit
    do_q = do_exit

    def _call(self, cmd, args):
        try:
            cmds = self.current.commands()
        except command.CommandError:
            cmds = []
        if cmd not in cmds:
            return "No such command: %s"%cmd

        cmd = getattr(self.current, cmd)
        if args:
            args = "".join(args)
        else:
            args = "()"
        try:
            val = eval(
                    "cmd%s"%"".join(args),
                    {},
                    dict(cmd=cmd)
                )
            return val
        except SyntaxError, v:
            return "Syntax error in expression: %s"%v.text
        except command.CommandException, val:
            return "Command exception: %s\n"%val

    def loop(self):
        while True:
            try:
                line = raw_input(self.prompt)
            except (EOFError, KeyboardInterrupt):
                return
            if not line:
                continue

            match = re.search(r"\W", line)
            if match:
                cmd, args = line[:match.start()].strip(), line[match.start():].strip()
            else:
                cmd, args = line, ""

            builtin = getattr(self, "do_"+cmd, None)
            if builtin:
                val = builtin(args)
            else:
                val = self._call(cmd, args)
            if isinstance(val, basestring):
                print val
            elif val:
                pprint.pprint(val)

