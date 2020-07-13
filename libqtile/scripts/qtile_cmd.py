#!/usr/bin/env python3
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

import argparse
import pprint
import sys
import textwrap
from typing import List

from libqtile.command_client import InteractiveCommandClient
from libqtile.command_interface import (
    CommandError,
    CommandException,
    IPCCommandInterface,
)
from libqtile.ipc import Client, find_sockfile


def get_formated_info(obj: InteractiveCommandClient, cmd: str, args=True, short=True) -> str:
    """Get documentation for command/function and format it.

    Returns:
      * args=True, short=True - '*' if arguments are present and a summary line.
      * args=True, short=False - (function args) and a summary line.
      * args=False - a summary line.

    If 'doc' function is not present in object or there is no doc string for
    given cmd it returns empty string.  The arguments are extracted from doc[0]
    line, the summary is constructed from doc[1] line.
    """

    if hasattr(obj, "doc"):
        doc = obj.doc(cmd).splitlines()
    else:
        doc = None

    if doc is not None:
        tdoc = doc[0]
        doc_args = tdoc[tdoc.find("(") + 1:tdoc.find(")")].strip()

        short_description = doc[1] if len(doc) > 1 else ""

        if doc_args:  # return formatted args
            doc_args = "({})".format(doc_args)
    else:
        doc_args = ""
        short_description = ""

    if args is False:
        doc_args = ""
    elif args and short:
        doc_args = "*" if len(doc_args) > 1 else " "

    return (doc_args + " " + short_description).rstrip()


def print_commands(prefix: str, obj: InteractiveCommandClient) -> None:
    """Print available commands for given object."""
    prefix += " -f "
    output = []
    max_cmd = 0  # max len of cmd for formatting

    try:
        cmds = obj.commands()
    except AttributeError:
        print("error: Sorry no commands in ", prefix)
        sys.exit(1)
    except CommandError:
        print("error: Sorry no such object ", prefix)
        sys.exit(1)

    for cmd in cmds:
        doc_args = get_formated_info(obj, cmd)

        pcmd = prefix + cmd
        max_cmd = max(len(pcmd), max_cmd)
        output.append([pcmd, doc_args])

    # Print formatted output
    formating = "{:<%d}\t{}" % (max_cmd + 1)
    for line in output:
        print(formating.format(line[0], line[1]))


def get_object(client: InteractiveCommandClient, argv: List[str]) -> InteractiveCommandClient:
    """
    Constructs a path to object and returns given object (if it exists).
    """
    if argv[0] == "cmd":
        argv = argv[1:]

    # Generate full obj specification
    for arg in argv:
        try:
            # check if it is an item
            client = client[client.normalize_item(arg)]
            continue
        except KeyError:
            pass

        try:
            # check if it is an attr
            client = getattr(client, arg)
            continue
        except AttributeError:
            pass

        print("Specified object does not exist " + " ".join(argv))
        sys.exit(1)

    return client


def run_function(client: InteractiveCommandClient, funcname: str, args: List[str]) -> str:
    "Run command with specified args on given object."
    try:
        func = getattr(client, funcname)
    except AttributeError:
        print("error: Sorry no function ", funcname)
        sys.exit(1)

    try:
        ret = func(*args)
    except CommandError:
        print("error: Sorry command '{}' cannot be found".format(funcname))
        sys.exit(1)
    except CommandException:
        print("error: Sorry cannot run function '{}' with arguments {}"
              .format(funcname, args))
        sys.exit(1)

    return ret


def print_base_objects() -> None:
    """Prints access objects of Client, use cmd for commands."""
    actions = ["-o cmd", "-o window", "-o layout", "-o group", "-o bar",
               "-o screen"]
    print("Specify an object on which to execute command")
    print("\n".join(actions))


def main() -> None:
    "Runs tool according to specified arguments."
    description = 'Simple tool to expose qtile.command functionality to shell.'
    epilog = textwrap.dedent('''\
    Examples:
     qtile-cmd
     qtile-cmd -o cmd
     qtile-cmd -o cmd -f prev_layout -i
     qtile-cmd -o cmd -f prev_layout -a 3 # prev_layout on group 3
     qtile-cmd -o group 3 -f focus_back''')
    fmt = argparse.RawDescriptionHelpFormatter

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=fmt)
    parser.add_argument('--object', '-o', dest='obj_spec', nargs='+',
                        help='Specify path to object (space separated).  '
                             'If no --function flag display available commands.  '
                             'Use `cmd` to specify root command.')
    parser.add_argument('--function', '-f', default="help",
                        help='Select function to execute.')
    parser.add_argument('--args', '-a', nargs='+', default=[],
                        help='Set arguments supplied to function.')
    parser.add_argument('--info', '-i', action='store_true',
                        help='With both --object and --function args prints documentation for function.')
    parser.add_argument(
        "--socket", "-s",
        help='Path of the Qtile IPC socket.'
    )
    args = parser.parse_args()

    if args.obj_spec:
        sock_file = args.socket or find_sockfile()
        ipc_client = Client(sock_file)
        cmd_object = IPCCommandInterface(ipc_client)
        cmd_client = InteractiveCommandClient(cmd_object)
        obj = get_object(cmd_client, args.obj_spec)

        if args.function == "help":
            print_commands("-o " + " ".join(args.obj_spec), obj)
        elif args.info:
            print(get_formated_info(obj, args.function, args=True, short=False))
        else:
            ret = run_function(obj, args.function, args.args)
            if ret is not None:
                pprint.pprint(ret)
    else:
        print_base_objects()
        sys.exit(1)


if __name__ == "__main__":
    main()
