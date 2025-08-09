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

import os
import subprocess
import sys


def run_qtile(args):
    cmd = os.path.join(os.path.dirname(__file__), "..", "libqtile", "scripts", "main.py")
    argv = [sys.executable, cmd]
    argv.extend(args)
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    assert proc.returncode == 0
    stdout = stdout.decode()
    stderr = stderr.decode()
    return (stdout, stderr)


def test_cmd_help_subcommand():
    args = ["help"]
    stdout, stderr = run_qtile(args)
    assert "usage: qtile" in stdout
    assert stderr == ""


def test_cmd_help_param():
    args = ["--help"]
    stdout, stderr = run_qtile(args)
    assert "usage: qtile" in stdout
    assert stderr == ""
