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
    def __init__(self, client):
        self.clientroot, self.current = client, client
        self.termwidth = terminalWidth()

    @property
    def prompt(self):
        s = self.current.selectors[:]
        if self.current.name:
            s += [(self.current.name, self.current.myselector)]
        return "%s> "%command.formatSelector(s)

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
                ret.append("  ".join(sl) + "\n")
            if len(lst)%cols:
                sl = lst[-(len(lst)%cols):]
                sl = [x + " "*(mx-len(x)) for x in sl]
                ret.append("  ".join(sl) + "\n")
        return "".join(ret)

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

    def _cd(self, *arg):
        attrs, itms = self.smartLs(self.current)
        next = None
        if arg[0] == "..":
            next = self.current.parent or self.current
        else:
            for trans in [str, int]:
                try:
                    targ = trans(arg[0])
                except ValueError:
                    continue
                if attrs and targ in attrs:
                    next = getattr(self.current, targ)
                elif itms and targ in itms:
                    next = self.current[targ]
        if next:
            self.current = next
            if arg[1:]:
                return self._cd(*arg[1:])
            else:
                return
        else:
            return "No such item: %s"%arg

    def do_cd(self, arg):
        check = self.current
        v = self._cd(*[i for i in arg.split("/") if i])
        if v:
            self.current = check
            return v

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
                if val:
                    print val
            else:
                val = self._call(cmd, args)
                if val:
                    pprint.pprint(val)



