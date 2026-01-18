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
