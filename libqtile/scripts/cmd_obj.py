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
import itertools
import pprint
import sys
import textwrap
from pathlib import Path
from typing import List, Optional

import typer
from typer import Option

from libqtile.command.base import CommandError, CommandException, SelectError
from libqtile.command.client import CommandClient
from libqtile.command.graph import CommandGraphRoot
from libqtile.command.interface import IPCCommandInterface
from libqtile.ipc import Client, find_sockfile


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
    doc_args = tdoc[tdoc.find("("):tdoc.find(")") + 1].strip()

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
    formatting = "{:<%d}\t{}" % (max_cmd + 1)
    for line in output:
        print(formatting.format(line[0], line[1]))


def get_object(client: CommandClient, argv: List[str]) -> CommandClient:
    """
    Constructs a path to object and returns given object (if it exists).
    """
    if argv[0] == "cmd":
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


def run_function(client: CommandClient, funcname: str, args: List[str]) -> str:
    "Run command with specified args on given object."
    try:
        ret = client.call(funcname, *args)
    except SelectError:
        print("error: Sorry no function ", funcname)
        sys.exit(1)
    except CommandError as e:
        print("error: Command '{}' returned error: {}".format(funcname, str(e)))
        sys.exit(1)
    except CommandException as e:
        print("error: Sorry cannot run function '{}' with arguments {}: {}"
              .format(funcname, args, str(e)))
        sys.exit(1)

    return ret


def print_base_objects() -> None:
    """Prints access objects of Client, use cmd for commands."""
    root = CommandGraphRoot()
    actions = ["-o cmd"] + [f"-o {key}" for key in root.children]
    print("Specify an object on which to execute command")
    print("\n".join(actions))


def cmd_obj(
    obj_spec: List[str] = Option(
        None, "-o", "--object", help="Specify path to object (space separated). "
                                     "If no --function flag display available "
                                     "commands. Use `cmd` to specify root command."
    ),
    function: Optional[str] = Option(
        None, "-f", "--function", help="Select function to execute."
    ),
    args: List[str] = Option(
        None, "-a", "--args", help="Set arguments supplied to function."
    ),
    info: bool = Option(
        False, "-i", "--info", help="With both --object and --function args prints documentation."
    ),
    socket: Optional[Path] = Option(None, "-s", "--socket", help="Path of the Qtile IPC socket."),
) -> None:
    """
    qtile.command functionality exposed to the shell.
    """

    if obj_spec:
        sock_file = socket or find_sockfile()
        ipc_client = Client(sock_file)
        cmd_object = IPCCommandInterface(ipc_client)
        cmd_client = CommandClient(cmd_object)
        obj = get_object(cmd_client, obj_spec)

        if function == "help":
            try:
                print_commands("-o " + " ".join(obj_spec), obj)
            except CommandError:
                if len(args.obj_spec) == 1:
                    print(f"{args.obj_spec} object needs a specified identifier e.g. '-o bar top'.")
                    typer.Exit(code=1)
                else:
                    raise
        elif info:
            print(function + get_formated_info(obj, function, args=True, short=False))
        else:
            ret = run_function(obj, function, args)
            if ret is not None:
                pprint.pprint(ret)
    else:
        print_base_objects()
        typer.Exit(code=1)
