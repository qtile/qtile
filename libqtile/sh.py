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
import readline, sys, pprint, shlex
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
    fd = sys.stdout
    def __init__(self, client):
        self.clientroot, self.current = client, client
        self.termwidth = terminalWidth()

    @property
    def prompt(self):
        print self.current.myname
        return "%s> "%command.formatSelector(self.current.selectors)

    def printColumns(self, lst):
        mx = max([len(i) for i in lst])
        cols = self.termwidth / (mx+2)
        if not cols:
            cols = 1
        for i in range(len(lst)/cols):
            sl = lst[i*cols:(i+1)*cols]
            sl = [x + " "*(mx-len(x)) for x in sl]
            print >> self.fd, "  ".join(sl)
        if len(lst)%cols:
            sl = lst[-(len(lst)%cols):]
            sl = [x + " "*(mx-len(x)) for x in sl]
            print >> self.fd, "  ".join(sl)

    def do_cd(self, arg):
        pass

    def do_ls(self):
        self.printColumns(self.current._contains)

    def do_help(self, arg):
        pass

    def loop(self):
        while True:
            line = raw_input(self.prompt)
            if not line:
                continue
            parts = shlex.split(line)

            builtin = getattr(self, "do_"+parts[0], None)
            if builtin:
                builtin(parts[1:])
            else:
                pass



