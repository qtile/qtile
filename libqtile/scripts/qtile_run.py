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

from libqtile import command


def parse_args():
    parser = argparse.ArgumentParser(description="Run a command applying rules"
                                     " to the new windows")
    parser.add_argument('-s', '--socket', type=str, dest="socket",
                        help='Use specified communication socket.')
    parser.add_argument('-i', '--intrusive',
                        dest="intrusive", action='store_true',
                        help='If the new window should be intrusive.')
    parser.add_argument('-f', '--float', dest="floating", action='store_true',
                        help='If the new window should be float.')
    parser.add_argument('-b', '--dont-break', dest="dont_break",
                        action='store_true',
                        help='Don\'t break on match(keep applying rules).')
    parser.add_argument('-g', '--group', dest="group", type=str,
                        help='Set the window group.')
    parser.add_argument('cmd', nargs=argparse.REMAINDER,
                        help='Command to execute')

    opts = parser.parse_args()
    if not opts.cmd:
        parser.print_help()
        exit()
    return opts


def main():
    opts = parse_args()
    client = command.Client(opts.socket)

    proc = subprocess.Popen(opts.cmd)
    match_args = {"net_wm_pid": [proc.pid]}
    rule_args = {"float": opts.floating, "intrusive": opts.intrusive,
                 "group": opts.group, "break_on_match": not opts.dont_break}
    rule_id = client.add_rule(match_args, rule_args)

    atexit.register(lambda: client.remove_rule(rule_id))

    proc.wait()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
