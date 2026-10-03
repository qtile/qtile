"""
Regression test for running the Wayland backend on a system without Xwayland.

Xwayland is an optional dependency for running Qtile on Wayland with X11 support.
This test ensures that Qtile can run correctly without Xwayland.

The test is skipped when Xwayland is installed. In CI it runs in the matrix entry
with QTILE_CI_XWAYLAND=false (set in .github/workflows/ci.yml), for which
scripts/ci-entrypoint removes Xwayland from the container.
"""

import shutil

import pytest

from test.backend.wayland.conftest import new_xdg_client

pytestmark = pytest.mark.skipif(
    shutil.which("Xwayland") is not None,
    reason="Xwayland is installed.",
)


def test_start_without_xwayland(wmanager):
    # Make sure Qtile starts with the correct log message when Xwayland is not available.
    # This also ensures that Qtile took the "no Xwayland" path.
    logs = wmanager.get_log_buffer()
    assert "continuing without X11 support" in logs

    # Qtile is up and responding to commands...
    assert wmanager.c.status() == "OK"

    # ...and native Wayland clients still work.
    proc = new_xdg_client(wmanager, name="no-xwayland")
    assert wmanager.c.window.info()["name"] == "no-xwayland"
    wmanager.kill_window(proc)
    assert wmanager.c.windows() == []
