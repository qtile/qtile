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

from __future__ import annotations

import argparse
import itertools
import json
import sys
import textwrap

from libqtile.command.base import CommandError, CommandException, SelectError
from libqtile.command.client import CommandClient
from libqtile.command.graph import CommandGraphRoot
from libqtile.command.interface import IPCCommandInterface
from libqtile.ipc import Client, find_sockfile


def set_to_list(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def get_formated_info(obj: CommandClient, cmd: str, args=True, short=True) -> str:
    """Get documentation for command/function and format it.

    Returns:
      * args=True, short=True - '*' if arguments are present and a summary line.
      * args=True, short=False - (function args) and a summary line.
      * args=False - a summary line.

    If 'doc' function is not present in object or there is no doc string for
    given cmd it returns empty string.  The arguments are extracted from doc[0]
    line, the summary is constructed from doc[1] line.
    """

    doc = obj.call("doc", cmd).splitlines()

    tdoc = doc[0]
    doc_args = tdoc[tdoc.find("(") : tdoc.find(")") + 1].strip()

    short_description = doc[1] if len(doc) > 1 else ""

    if not args:
        doc_args = ""
    elif short:
        doc_args = " " if doc_args == "()" else "*"

    return (doc_args + " " + short_description).rstrip()


def print_commands(prefix: str, obj: CommandClient) -> None:
    """Print available commands for given object."""
    prefix += " -f "

    cmds = obj.call("commands")

    output = []
    for cmd in cmds:
        doc_args = get_formated_info(obj, cmd)

        pcmd = prefix + cmd
        output.append([pcmd, doc_args])

    max_cmd = max(len(pcmd) for pcmd, _ in output)

    # Print formatted output
    formatting = f"{{:<{(max_cmd + 1):d}}}\t{{}}"
    for line in output:
        print(formatting.format(line[0], line[1]))


def get_object(client: CommandClient, argv: list[str]) -> CommandClient:
    """
    Constructs a path to object and returns given object (if it exists).
    """
    if argv[0] in ("cmd", "root"):
        argv = argv[1:]

    # flag noting if we have consumed arg1 as the selector, eg screen[0]
    parsed_next = False

    for arg0, arg1 in itertools.zip_longest(argv, argv[1:]):
        # previous argument was an item, skip here
        if parsed_next:
            parsed_next = False
            continue

        # check if it is an item
        try:
            client = client.navigate(arg0, arg1)
            parsed_next = True
            continue
        except SelectError:
            pass

        # check if it is an attr
        try:
            client = client.navigate(arg0, None)
            continue
        except SelectError:
            pass

        print("Specified object does not exist: " + " ".join(argv))
        sys.exit(1)

    return client


def run_function(client: CommandClient, funcname: str, args: list[str]) -> str:
    "Run command with specified args on given object."
    try:
        ret = client.call(funcname, *args, lifted=True)
    except SelectError:
        print("error: Sorry no function ", funcname)
        sys.exit(1)
    except CommandError as e:
        print(f"error: Command '{funcname}' returned error: {str(e)}")
        sys.exit(1)
    except CommandException as e:
        print(f"error: Sorry cannot run function '{funcname}' with arguments {args}: {str(e)}")
        sys.exit(1)

    return ret


def print_base_objects() -> None:
    """Prints access objects of Client, use cmd for commands."""
    root = CommandGraphRoot()
    actions = ["-o cmd"] + [f"-o {key}" for key in root.children]
    print("Specify an object on which to execute command")
    print("\n".join(actions))


def cmd_obj(args) -> None:
    "Runs tool according to specified arguments."

    if args.obj_spec:
        sock_file = args.socket or find_sockfile()
        ipc_client = Client(sock_file)
        cmd_object = IPCCommandInterface(ipc_client)
        cmd_client = CommandClient(cmd_object)
        obj = get_object(cmd_client, args.obj_spec)

        if args.function == "help":
            try:
                print_commands("-o " + " ".join(args.obj_spec), obj)
            except CommandError:
                if len(args.obj_spec) == 1:
                    print(
                        f"{args.obj_spec} object needs a specified identifier e.g. '-o bar top'."
                    )
                    sys.exit(1)
                else:
                    raise
        elif args.info:
            print(args.function + get_formated_info(obj, args.function, args=True, short=False))
        else:
            ret = run_function(obj, args.function, args.args)
            if ret is not None:
                print(json.dumps(ret, indent=2, default=set_to_list))
    else:
        print_base_objects()
        sys.exit(1)


def add_subcommand(subparsers, parents):
    epilog = textwrap.dedent(
        """\
    Examples:
     qtile cmd-obj
     qtile cmd-obj -o root # same as above
     qtile cmd-obj -o root -f prev_layout -a 3 # prev_layout on group 3
     qtile cmd-obj -o group 3 -f focus_back
     qtile cmd-obj -o root -f restart # restart qtile
    The graph traversal recurses:
     qtile cmd-obj -o screen 0 bar bottom screen group window -f info
     """
    )
    description = "Access the command interface from a shell."
    parser = subparsers.add_parser(
        "cmd-obj",
        help=description,
        parents=parents,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--object",
        "-o",
        dest="obj_spec",
        nargs="+",
        default=["root"],
        help="Specify path to object (space separated).  "
        "If no --function flag display available commands.  "
        "The root node is selected by default or you can pass `root` explicitly.",
    )
    parser.add_argument("--function", "-f", default="help", help="Select function to execute.")
    parser.add_argument(
        "--args", "-a", nargs="+", default=[], help="Set arguments supplied to function."
    )
    parser.add_argument(
        "--info",
        "-i",
        action="store_true",
        help="With both --object and --function args prints documentation for function.",
    )
    parser.add_argument("--socket", "-s", help="Use specified socket for IPC.")
    parser.set_defaults(func=cmd_obj)
