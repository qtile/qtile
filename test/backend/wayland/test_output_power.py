import pytest

from test.conftest import dualmonitor
from test.helpers import Retry


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_outputs(client, num=1):
    client.assert_ok(f"outputs {num}")


pytestmark = pytest.mark.parametrize("test_client", ["output-power-management"], indirect=True)


def test_opm(wmanager, test_client):
    """Test that client is notified about client state."""
    wait_for_outputs(test_client)
    test_client.assert_ok("count_on 1")
    test_client.assert_ok("power_off")
    test_client.assert_ok("count_on 0")
    test_client.assert_ok("power_on")
    test_client.assert_ok("count_on 1")


def test_opm_window_persistence(wmanager, test_client):
    """Check that client window is unaffected by power state."""
    wait_for_outputs(test_client)
    wmanager.test_window("opm")
    wmanager.c.window.set_size_floating(300, 200)
    wmanager.c.window.set_position_floating(100, 100)
    test_client.assert_ok("power_off")
    test_client.assert_ok("count_on 0")
    test_client.assert_ok("power_on")
    info = wmanager.c.window.info()
    assert info
    assert info["name"] == "opm"
    assert info["x"] == 100
    assert info["y"] == 100
    assert info["width"] == 300
    assert info["height"] == 200


@dualmonitor
def test_opm_dual_monitor(wmanager, test_client):
    """Check each output can be powered individually."""

    def get_output_state():
        return test_client.send_read_until("identify", "OK")

    # Check client is notified about two outputs
    wait_for_outputs(test_client, 2)

    outputs = get_output_state()
    assert "Output: HEADLESS-1 (Power: ON)" in outputs
    assert "Output: HEADLESS-2 (Power: ON)" in outputs

    test_client.assert_ok("power_off")
    outputs = get_output_state()
    assert "Output: HEADLESS-1 (Power: OFF)" in outputs
    assert "Output: HEADLESS-2 (Power: OFF)" in outputs

    test_client.assert_ok("power_on HEADLESS-1")
    outputs = get_output_state()
    assert "Output: HEADLESS-1 (Power: ON)" in outputs
    assert "Output: HEADLESS-2 (Power: OFF)" in outputs

    test_client.assert_ok("power_on HEADLESS-2")
    outputs = get_output_state()
    assert "Output: HEADLESS-1 (Power: ON)" in outputs
    assert "Output: HEADLESS-2 (Power: ON)" in outputs
