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

from libqtile import command, sh


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.3',
    )
    parser.add_argument(
        "-s", "--socket",
        action="store", type=str,
        default=None,
        help='Use specified socket to connect to qtile.'
    )
    parser.add_argument(
        "-r", "--run",
        action="store", type=str,
        default=None,
        dest="pyfile",
        help='The full path to python file with the \"main\" function to call.'
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

    args = parser.parse_args()

    client = command.Client(args.socket, is_json=args.is_json)
    if args.pyfile is None:
        qsh = sh.QSh(client)
        if args.command is not None:
            qsh.process_command(args.command)
        else:
            qsh.loop()
    else:
        print(client.run_external(args.pyfile))
