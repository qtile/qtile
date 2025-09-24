import asyncio
import os
from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest

from libqtile import utils


def test_rgb_from_hex_number():
    assert utils.rgb("ff00ff") == (1, 0, 1, 1)


def test_rgb_from_hex_string():
    assert utils.rgb("#00ff00") == (0, 1, 0, 1)


def test_rgb_from_hex_number_with_alpha():
    assert utils.rgb("ff0000.3") == (1, 0, 0, 0.3)


def test_rgb_from_hex_string_with_alpha():
    assert utils.rgb("#ff0000.5") == (1, 0, 0, 0.5)


def test_rgb_from_hex_number_with_hex_alpha():
    assert utils.rgb("ff000000") == (1, 0, 0, 0.0)


def test_rgb_from_hex_string_with_hex_alpha():
    assert utils.rgb("#ff000000") == (1, 0, 0, 0.0)


def test_rgb_from_base10_tuple():
    assert utils.rgb([255, 255, 0]) == (1, 1, 0, 1)


def test_rgb_from_base10_tuple_with_alpha():
    assert utils.rgb([255, 255, 0, 0.5]) == (1, 1, 0, 0.5)


def test_rgb_from_3_digit_hex_number():
    assert utils.rgb("f0f") == (1, 0, 1, 1)


def test_rgb_from_3_digit_hex_string():
    assert utils.rgb("#f0f") == (1, 0, 1, 1)


def test_rgb_from_3_digit_hex_number_with_alpha():
    assert utils.rgb("f0f.5") == (1, 0, 1, 0.5)


def test_rgb_from_3_digit_hex_string_with_alpha():
    assert utils.rgb("#f0f.5") == (1, 0, 1, 0.5)


def test_has_transparency():
    colours = [
        ("#00000000", True),
        ("#000000ff", False),
        ("#ff00ff.5", True),
        ((255, 255, 255, 0.5), True),
        ((255, 255, 255), False),
        (["#000000", "#ffffff"], False),
        (["#000000", "#ffffffaa"], True),
    ]

    for colour, expected in colours:
        assert utils.has_transparency(colour) == expected


def test_remove_transparency():
    colours = [
        ("#00000000", (0.0, 0.0, 0.0)),
        ("#ffffffff", (255.0, 255.0, 255.0)),
        ((255, 255, 255, 0.5), (255.0, 255.0, 255.0)),
        ((255, 255, 255), (255.0, 255.0, 255.0)),
        (["#000000", "#ffffff"], [(0.0, 0.0, 0.0), (255.0, 255.0, 255.0)]),
        (["#000000", "#ffffffaa"], [(0.0, 0.0, 0.0), (255.0, 255.0, 255.0)]),
    ]

    for colour, expected in colours:
        assert utils.remove_transparency(colour) == expected


def test_scrub_to_utf8():
    assert utils.scrub_to_utf8(b"foo") == "foo"


def test_guess_terminal_accepts_a_preference(path):
    term = "shitty"
    Path(path, term).touch(mode=0o777)
    assert utils.guess_terminal(term) == term


def test_guess_terminal_accepts_a_list_of_preferences(path):
    term = "shitty"
    Path(path, term).touch(mode=0o777)
    assert utils.guess_terminal(["nutty", term]) == term


def test_guess_terminal_falls_back_to_defaults(path):
    Path(path, "kitty").touch(mode=0o777)
    assert utils.guess_terminal(["nutty", "witty", "petty"]) == "kitty"


@pytest.fixture
def path(monkeypatch):
    "Create a TemporaryDirectory as the PATH"
    with TemporaryDirectory() as d:
        monkeypatch.setenv("PATH", d)
        yield d


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TEST_DIR, "data")


class TestScanFiles:
    def test_audio_volume_muted(self):
        name = "audio-volume-muted.*"
        dfiles = utils.scan_files(DATA_DIR, name)
        result = dfiles[name]
        assert len(result) == 2
        png = os.path.join(DATA_DIR, "png", "audio-volume-muted.png")
        assert png in result
        svg = os.path.join(DATA_DIR, "svg", "audio-volume-muted.svg")
        assert svg in result

    def test_only_svg(self):
        name = "audio-volume-muted.svg"
        dfiles = utils.scan_files(DATA_DIR, name)
        result = dfiles[name]
        assert len(result) == 1
        svg = os.path.join(DATA_DIR, "svg", "audio-volume-muted.svg")
        assert svg in result

    def test_multiple(self):
        names = OrderedDict()
        names["audio-volume-muted.*"] = 2
        names["battery-caution-charging.*"] = 1
        dfiles = utils.scan_files(DATA_DIR, *names)
        for name, length in names.items():
            assert len(dfiles[name]) == length


@pytest.mark.asyncio
async def test_acall_process_pid_tracking():
    """Test that acall_process tracks PIDs in ASYNC_PIDS and reap_zombies breaks when it finds tracked processes."""
    waitid_calls = []

    def mock_waitid(idtype, id_or_pid, options):
        waitid_calls.append((idtype, id_or_pid, options))

        # For the first call (P_ALL check), return a mock result with a PID that's being tracked
        if idtype == os.P_ALL:
            if len(waitid_calls) == 1:
                # Return a tracked PID on the first call
                mock_result = Mock()
                mock_result.si_pid = 12345  # Mock PID that we'll add to ASYNC_PIDS
                return mock_result
            else:
                # No more processes to reap
                return None

        # For P_PID calls (specific PID), just return None (handled)
        return None

    with patch("os.waitid", side_effect=mock_waitid):
        utils.ASYNC_PIDS.add(12345)

        utils.reap_zombies()

        # Should only make one call (P_ALL) because it breaks when finding tracked PID
        assert len(waitid_calls) == 1

        # First call should be P_ALL to check for any zombies
        first_call = waitid_calls[0]
        assert first_call[0] == os.P_ALL
        assert first_call[2] & os.WEXITED
        assert first_call[2] & os.WNOHANG
        assert first_call[2] & os.WNOWAIT
        utils.ASYNC_PIDS.clear()


@pytest.mark.asyncio
async def test_acall_process_adds_removes_pid():
    """Test that acall_process properly adds and removes PIDs from ASYNC_PIDS."""
    task = asyncio.create_task(utils.acall_process(["echo", "test"]))
    result = await task

    assert result.strip() == "test"
    assert len(utils.ASYNC_PIDS) == 0


@pytest.mark.asyncio
async def test_concurrent_acall_processes():
    """Test that multiple concurrent acall_process calls track PIDs correctly."""
    tasks = [asyncio.create_task(utils.acall_process(["echo", f"test{i}"])) for i in range(3)]

    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        assert result.strip() == f"test{i}"

    assert len(utils.ASYNC_PIDS) == 0
