# Copyright (c) 2023, elParaguayo. All rights reserved.
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
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from libqtile.scripts.migrations._base import NoChange
from test.test_check import run_qtile_check


class SourceCode:
    def __init__(self, test):
        self.source = textwrap.dedent(test.input)
        self.expected = textwrap.dedent(test.output)
        self.dir = tempfile.TemporaryDirectory()
        self.source_path = Path(self.dir.name) / "config.py"
        self.needs_lint = not isinstance(test, NoChange)

    def __enter__(self):
        self.source_path.write_text(self.source)
        return self

    def __exit__(self, type, value, traceback):
        self.dir.cleanup()
        del self.dir


class MigrationTester:
    def __init__(self, test_id, test):
        self.test_id = test_id
        self.test = test
        self.cmd = Path(__file__).parent / ".." / ".." / "libqtile" / "scripts" / "main.py"

    def assert_migrate(self):
        if not self.test.source:
            assert False, f"{self.test_id} has no tests."
        argv = [
            sys.executable,
            self.cmd,
            "migrate",
            "--yes",
            "-r",
            self.test_id,
            "-c",
            self.test.source_path,
        ]
        try:
            subprocess.check_call(argv)
        except subprocess.CalledProcessError:
            assert False

        updated = Path(f"{self.test.source_path}").read_text()
        assert updated == self.test.expected

    def assert_lint(self):
        argv = [
            sys.executable,
            self.cmd,
            "migrate",
            "--lint",
            "-r",
            self.test_id,
            "-c",
            self.test.source_path,
        ]
        try:
            output = subprocess.run(argv, capture_output=True, check=True)
        except subprocess.CalledProcessError:
            assert False

        assert any(self.test_id in line for line in output.stdout.decode().splitlines())

    def assert_check(self):
        if not self.test.source:
            assert False, f"{self.test_id} has no Check test."

        self.assert_migrate()

        assert run_qtile_check(self.test.source_path)


@pytest.fixture
def migration_tester(request):
    test_id, test = getattr(request, "param", (None, None))
    if test is None:
        test = NoChange("")
    with SourceCode(test) as sc:
        yield MigrationTester(test_id, sc)
