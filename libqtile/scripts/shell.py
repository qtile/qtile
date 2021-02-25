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

from libqtile import ipc, sh
from libqtile.command import interface


def qshell(args) -> None:
    if args.socket is None:
        socket = ipc.find_sockfile()
    else:
        socket = args.socket
    client = ipc.Client(socket, is_json=args.is_json)
    cmd_object = interface.IPCCommandInterface(client)
    qsh = sh.QSh(cmd_object)
    if args.command is not None:
        qsh.process_line(args.command)
    else:
        qsh.loop()


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser(
        "shell",
        parents=parents,
        help="shell-like interface to qtile"
    )
    parser.add_argument(
        "-s", "--socket",
        action="store", type=str,
        default=None,
        help='Use specified socket to connect to qtile.'
    )
    parser.add_argument(
        "-c", "--command",
        action="store", type=str,
        default=None,
        help='Run the specified qshell command and exit.'
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        default=False,
        dest="is_json",
        help='Use json in order to communicate with qtile server.'
    )
    parser.set_defaults(func=qshell)
