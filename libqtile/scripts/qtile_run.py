# Copyright (c) 2014, Roger Duran
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the \"Software\"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
    Command-line wrapper to run commands and add rules to new windows
"""

import argparse
import atexit
import subprocess

from libqtile import command_graph, ipc


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a command applying rules to the new windows")
    parser.add_argument(
        '-s',
        '--socket',
        help='Use specified communication socket.')
    parser.add_argument(
        '-i',
        '--intrusive',
        action='store_true',
        help='If the new window should be intrusive.')
    parser.add_argument(
        '-f',
        '--float',
        action='store_true',
        help='If the new window should be float.')
    parser.add_argument(
        '-b',
        '--dont-break',
        action='store_true',
        help='Do not break on match (keep applying rules).')
    parser.add_argument(
        '-g',
        '--group',
        help='Set the window group.')
    parser.add_argument(
        'cmd',
        nargs=argparse.REMAINDER,
        help='Command to execute')

    opts = parser.parse_args()
    if not opts.cmd:
        parser.print_help()
        exit()
    return opts


def main() -> None:
    opts = parse_args()
    if opts.socket is None:
        socket = ipc.find_sockfile()
    else:
        socket = opts.socket
    client = ipc.Client(socket)
    root = command_graph.CommandGraphRoot()

    proc = subprocess.Popen(opts.cmd)
    match_args = {"net_wm_pid": [proc.pid]}
    rule_args = {"float": opts.float, "intrusive": opts.intrusive,
                 "group": opts.group, "break_on_match": not opts.dont_break}

    cmd = root.navigate("add_rule", None)
    assert isinstance(cmd, command_graph.CommandGraphCall)
    _, rule_id = client.send((root.selectors, cmd.name, (match_args, rule_args), {}))

    def remove_rule():
        cmd = root.navigate("remove_rule", None)
        assert isinstance(cmd, command_graph.CommandGraphCall)
        client.send((root.selectors, cmd.name, (rule_id,), {}))

    atexit.register(remove_rule)

    proc.wait()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
