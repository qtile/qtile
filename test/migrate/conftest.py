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
