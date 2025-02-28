# Copyright (c) 2024 Thomas Krug
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

import multiprocessing
import os
import subprocess
import tempfile
import time

import test

repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
socket_path = tempfile.NamedTemporaryFile().name


def run_qtile(backend):
    cmd = os.path.join(repo_path, "bin/qtile")
    args = [cmd, "start", "-s", socket_path]
    args.extend(["-b", backend.name])

    env = os.environ.copy()
    if backend.name == "wayland":
        env.update(backend.env)

    proc = subprocess.Popen(args, env=env, stdout=subprocess.PIPE)
    out, err = proc.communicate(timeout=10)
    exitcode = proc.returncode
    return exitcode


def stop_qtile(code):
    cmd = os.path.join(repo_path, "bin/qtile")
    args = [cmd, "cmd-obj", "-o", "cmd", "-s", socket_path, "-f", "shutdown"]
    if code:
        args.extend(["-a", str(code)])
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    proc.communicate(timeout=10)
    exitcode = proc.returncode
    return exitcode


def deferred_stop(code=0):
    # wait for qtile process to start
    wait = 10
    while not test.helpers.can_connect_qtile(socket_path):
        time.sleep(1)
        if not wait:
            raise Exception("timeout waiting for qtile process")
        wait -= 1

    stop_qtile(code)


# in these testcases there are two qtile instances
# one started by the helpers.TestManager,
# which is used to evaluate code coverage
# and a second instance started by run_qtile,
# which is used to test the actual exit code behavior
def test_exitcode_default(backend):
    proc = multiprocessing.Process(target=deferred_stop)
    proc.start()

    exitcode = run_qtile(backend)
    proc.join()
    assert exitcode == 0


def test_exitcode_explicit(backend):
    code = 23

    proc = multiprocessing.Process(target=deferred_stop, args=(code,))
    proc.start()

    exitcode = run_qtile(backend)
    proc.join()
    assert exitcode == code
