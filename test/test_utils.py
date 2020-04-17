# Copyright (c) 2008, 2010 Aldo Cortesi
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Anshuman Bhaduri
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

from libqtile import utils


def test_rgb_from_hex_number():
    assert utils.rgb("ff00ff") == (1, 0, 1, 1)


def test_rgb_from_hex_string():
    assert utils.rgb("#00ff00") == (0, 1, 0, 1)


def test_rgb_from_hex_number_with_alpha():
    assert utils.rgb("ff0000.3") == (1, 0, 0, 0.3)


def test_rgb_from_hex_string_with_alpha():
    assert utils.rgb("#ff0000.5") == (1, 0, 0, 0.5)


def test_rgb_from_base10_tuple():
    assert utils.rgb([255, 255, 0]) == (1, 1, 0, 1)


def test_rgb_from_base10_tuple_with_alpha():
    assert utils.rgb([255, 255, 0, 0.5]) == (1, 1, 0, 0.5)


def test_scrub_to_utf8():
    assert utils.scrub_to_utf8(b"foo") == "foo"


def test_shuffle():
    test_l = list(range(3))
    utils.shuffle_up(test_l)
    assert test_l != list(range(3))
    utils.shuffle_down(test_l)
    assert test_l == list(range(3))
