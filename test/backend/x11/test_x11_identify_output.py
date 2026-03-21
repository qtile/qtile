import os
import re
import subprocess
import sys


def run_identify_output(env):
    cmd = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "libqtile", "scripts", "main.py"
    )
    argv = [sys.executable, cmd, "x11-identify-output"]

    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    stdout, stderr = proc.communicate()
    assert proc.returncode == 0, f"Command failed with stderr: {stderr.decode()}"
    stdout = stdout.decode()
    stderr = stderr.decode()
    return (stdout, stderr)


def check_identify_output(stdout, resolution):
    assert re.search(r"Output 0:", stdout)
    assert re.search(r"Make:\s+Unknown", stdout)
    assert re.search(r"Model:\s+Unknown", stdout)
    assert re.search(r"Serial Number:\s+Unknown", stdout)
    assert re.search(r"Position:\s+\(0,\s*0\)", stdout)
    assert re.search(rf"Resolution:\s+{resolution}", stdout)


def test_identify_output(xmanager_nospawn):
    backend = xmanager_nospawn.backend
    env = os.environ.copy()
    env.update(backend.env)
    stdout, _ = run_identify_output(env)
    resolution = "800x600"
    check_identify_output(stdout, resolution)
