# Copyright (c) 2008, 2010 Aldo Cortesi
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Anshuman Bhaduri
# Copyright (c) 2020 Matt Colligan
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
from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory

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


def test_shuffle():
    test_l = list(range(3))
    utils.shuffle_up(test_l)
    assert test_l != list(range(3))
    utils.shuffle_down(test_l)
    assert test_l == list(range(3))


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
