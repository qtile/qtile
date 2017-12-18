#!/usr/bin/env python
# pylint: disable=C0325
import pprint
import argparse
from libqtile.command import Client


class DocHelper(object):
    """Simplifies doc string processing"""
    def __init__(self, obj, cmd):
        super(DocHelper, self).__init__()
        self.obj = obj
        self.doc_func = obj.doc if hasattr(obj, "doc") else lambda x: ""
        self.doc = self.doc_func(cmd).splitlines()

    def get_args(self):
        if len(self.doc) < 2:
            return ""

        _doc_args = self.doc[0].split("(")[1]
        _doc_args = _doc_args.split(")")[0]
        _doc_args = _doc_args.strip()

        if _doc_args:  # return formatted args
            return "({})".format(_doc_args)
        return ""  # if no args return empty string

    def get_short_description(self):
        # append function description line if any
        if len(self.doc) > 1:
            return self.doc[1]
        return ""

    def get_formated_info(self, args=True, short=True):
        if args is False:
            doc_args = ""
        elif args and short:
            doc_args = "*" if len(self.get_args()) > 1 else " "
        else:
            doc_args = self.get_args()

        return (doc_args + " " + self.get_short_description()).rstrip()


def print_commands(prefix, obj):
    prefix += " -f "
    output = []
    max_cmd = 0  # max len of cmd for formatting

    try:
        cmds = obj.commands()
    except Exception as e:
        print("Sorry no commands in ", prefix)
        exit()

    for cmd in cmds:
        dhelper = DocHelper(obj, cmd)
        doc_args = dhelper.get_formated_info()

        pcmd = prefix + cmd
        max_cmd = max(len(pcmd), max_cmd)
        output.append([pcmd, doc_args])

    # Print formatted output
    formating = "{:<%d}\t{}" % (max_cmd + 1)
    for line in output:
        print(formating.format(line[0], line[1]))


def get_object(argv):

    c = Client()

    if argv[0] == "cmd":
        obj = c
    else:
        obj = getattr(c, argv[0])

    # Generate full obj specification
    for arg in argv[1:]:
        try:
            obj = obj[arg]  # check if it is an item
        except Exception as e:
            try:
                obj = getattr(obj, arg)  # check it it is an attr
            except Exception as e:
                print("Specified object does not exist" + " ".join(argv))
                exit()

    return obj


def run_function(obj, func, args):
    try:
        func = getattr(obj, func)
    except Exception as e:
        print("Sorry func", func, "does not exist")
        exit()

    try:
        ret = func(*args)
    except Exception as e:
        print("Sorry cannot run function", func, "with arguments", args)
        exit()

    return ret


def help_function(obj, func):
    dhelper = DocHelper(obj, func)
    print(dhelper.get_formated_info(args=True, short=False))


def print_base_objects():
    actions = ["-o cmd", "-o window", "-o layout", "-o group"]
    print("\n".join(actions))


def main():
    description = 'Simple tool to expose qtile.command functionality to shell.'
    epilog = '''\
Examples:\n\
 qcmd\n\
 qcmd -q cmd\n\
 qcmd -o cmd -f prev_layout -i\n\
 qcmd -o cmd -f prev_layout -a 3 # prev_layout on group 3\n\
 qcmd -o group 3 -f focus_back\n
'''
    fmt = argparse.RawDescriptionHelpFormatter

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=fmt)
    parser.add_argument('--object', '-o', dest='obj_spec', nargs='+',
                        help='''Specify path to object (space separated).\
                        If no --function flag display available commands.''')
    parser.add_argument('--function', '-f', dest='function', nargs=1,
                        default="help", help='Select function to execute.')
    parser.add_argument('--args', '-a', dest='args', nargs='+',
                        default=[], help='Set arguments supplied to function.')
    parser.add_argument('--info', '-i', dest='info', action='store_true',
                        help='''With both --object and --function args prints\
                        documentation for function.''')
    args = parser.parse_args()

    if args.obj_spec:

        obj = get_object(args.obj_spec)

        if args.function == "help":
            print_commands("-o " + " ".join(args.obj_spec), obj)
        elif args.info:
            help_function(obj, args.function[0])
        else:
            ret = run_function(obj, args.function[0], args.args)
            if ret is not None:
                pprint.pprint(ret)
            else:
                print_commands("-o " + " ".join(args.obj_spec), obj)

    else:  # TODO: print error if -f are used without -o ?
        print_base_objects()


if __name__ == "__main__":
    main()
