#!/usr/bin/env python
#
# Copyright (c) 2017, Piotr Przymus
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
    Command-line tool to expose qtile.command functionality to shell.
    This can be used standalone or in other shell scripts.
"""

import pprint
import argparse
from libqtile.command import Client
from libqtile.command import CommandError, CommandException


def get_formated_info(obj, cmd, args=True, short=True):
    """
    Get documentation for command/function and format it.

    Returns:
      * args=True, short=False - (function args) and a summary line.
      * args=True, short=True - '*' if arguments are present and a summary line.
      * args=False - a summary line.

    If 'doc' function is not present in object or there is no doc string for given cmd it returns empty string.
    The arguments are extracted from doc[0] line, the summary is constructed from doc[1] line.
    """

    doc_func = obj.doc if hasattr(obj, "doc") else lambda x: ""
    doc = doc_func(cmd).splitlines()
    doc_args = ""

    if doc:
        short_description = doc[1] if len(doc) > 1 else ""

        tdoc = doc[0]
        doc_args = tdoc[tdoc.find("(") + 1:tdoc.find(")")].strip()

        if doc_args:  # return formatted args
            doc_args = "({})".format(doc_args)

    if args is False:
        doc_args = ""
    elif args and short:
        doc_args = "*" if len(doc_args) > 1 else " "

    return (doc_args + " " + short_description).rstrip()


def print_commands(prefix, obj):
    "Print available commands for given object."
    prefix += " -f "
    output = []
    max_cmd = 0  # max len of cmd for formatting

    try:
        cmds = obj.commands()
    except AttributeError:
        print("error: Sorry no commands in ", prefix)
        exit()
    except CommandError:
        print("error: Sorry no such object ", prefix)
        exit()

    for cmd in cmds:
        doc_args = get_formated_info(obj, cmd)

        pcmd = prefix + cmd
        max_cmd = max(len(pcmd), max_cmd)
        output.append([pcmd, doc_args])

    # Print formatted output
    formating = "{:<%d}\t{}" % (max_cmd + 1)
    for line in output:
        print(formating.format(line[0], line[1]))


def get_object(argv):
    """
    Constructs a path to object and returns given object (if it exists).
    """

    client = Client()
    obj = client

    if argv[0] == "cmd":
        argv = argv[1:]

    # Generate full obj specification
    for arg in argv:
        try:
            obj = obj[arg]  # check if it is an item
        except KeyError:
            try:
                obj = getattr(obj, arg)  # check it it is an attr
            except AttributeError:
                print("Specified object does not exist " + " ".join(argv))
                exit()

    return obj


def run_function(obj, funcname, args):
    "Run command with specified args on given object."
    try:
        func = getattr(obj, funcname)
    except AttributeError:
        print("error: Sorry no function ", funcname)
        exit()

    try:
        ret = func(*args)
    except CommandError:
        print("error: Sorry command '{}' cannot be found".format(funcname))
        exit()
    except CommandException:
        print("error: Sorry cannot run function '{}' with arguments {}"
              .format(funcname, args))
        exit()

    return ret


def print_base_objects():
    "Prints access objects of Client, use cmd for commands."
    actions = ["-o cmd", "-o window", "-o layout", "-o group", "-o bar"]
    print("\n".join(actions))


def main():
    "Runs tool according to specified arguments."
    description = 'Simple tool to expose qtile.command functionality to shell.'
    epilog = '''\
Examples:\n\
 qtile-cmd\n\
 qtile-cmd -o cmd\n\
 qtile-cmd -o cmd -f prev_layout -i\n\
 qtile-cmd -o cmd -f prev_layout -a 3 # prev_layout on group 3\n\
 qtile-cmd -o group 3 -f focus_back\n
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
            print(get_formated_info(obj, args.function[0],
                                    args=True, short=False))
        else:
            ret = run_function(obj, args.function[0], args.args)
            if ret is not None:
                pprint.pprint(ret)
            else:
                print_commands("-o " + " ".join(args.obj_spec), obj)

    else:
        print_base_objects()


if __name__ == "__main__":
    main()
