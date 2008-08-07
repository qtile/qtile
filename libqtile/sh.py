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
import cmd, readline, sys, pprint, textwrap, traceback
import command


class Cmd(cmd.Cmd):
    prompt = "qsh> "
    def __init__(self, client):
        self.client = client
        self.builtins = []
        for i in client.commands.keys():
            self.builtins.append(i)
            def _closure():
                htext = client.commands.doc(i)
                commandName = i
                def help(self):
                    print htext
                def do(self, arg):
                    if not arg:
                        arg = "()"
                    try:
                        val = eval(
                                    "client.%s%s"%(commandName, arg),
                                    {},
                                    dict(client=client, commandName=commandName)
                              )
                    except command.CommandError, val:
                        print "Error: %s"%val
                    except command.CommandException, val:
                        print val
                    except Exception, val:
                        print val
                    else:
                        if val:
                            pprint.pprint(val)
                setattr(Cmd, "do_"+i, do)
                setattr(Cmd, "help_"+i, help)
            _closure()
        cmd.Cmd.__init__(self)

    def do_quit(self, arg):
        sys.exit(0)
    do_exit = do_quit
    do_q = do_quit
    do_EOF = do_quit

    def help_quit(self):
        return "Exit the program."

    def do_helpall(self, arg):
        for i in self.client.commands.keys():
            print self.client.commands.doc(i)
            print
