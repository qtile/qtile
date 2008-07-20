"""
    A command shell for Qtile.
"""
import cmd, readline, sys, pprint
import command


class Cmd(cmd.Cmd):
    prompt = "qsh> "
    def __init__(self, client):
        self.client = client
        for i in client.commands.keys():
            def _closure():
                htext = i.__doc__
                commandName = i
                moo = client
                def help(self):
                    return i.__doc__
                def do(self, arg):
                    if not arg:
                        arg = "()"
                    try:
                        val = eval(
                                    "client.%s%s"%(commandName, arg),
                                    {},
                                    dict(client=client, commandName=commandName)
                              )
                    except Exception, val:
                        print "Invalid command:"
                        print val
                    except command.CommandError:
                        print "Error: %s"%val
                    except command.CommandException:
                        print "Exception:"
                        pprint.pprint(val)
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

    def help_quit(self):
        return "Exit the program."
        

