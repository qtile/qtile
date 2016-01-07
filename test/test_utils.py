# vim: tabstop=4 shiftwidth=4 expandtab
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

import six

import libqtile.utils as utils


class Foo:
    ran = False

    @utils.LRUCache(2)
    def one(self, x):
        self.ran = True
        return x


def test_translate_masks():
    assert utils.translateMasks(["shift", "control"])
    assert utils.translateMasks([]) == 0


def test_lrucache_works_as_decorator():
    f = Foo()
    assert f.one(1) == 1
    assert f.one('test') == 'test'


def test_lrucache_caches():
    f = Foo()
    f.one(1)
    f.one(2)
    f.ran = False
    f.one(1)
    assert not f.ran
    f.one(2)
    assert not f.ran


def test_lrucache_discards_lru_item():
    f = Foo()
    f.one(1)
    assert f.ran
    f.ran = False
    f.one(1)
    assert not f.ran
    f.one(2)
    f.one(3)
    f.one(1)
    assert f.ran


def test_lrucache_maintains_size():
    f = Foo()
    f.one(1)
    f.one(2)
    f.one(3)
    assert len(f._cached_one) == 2
    assert len(f._cachelist_one) == 2


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
    assert utils.scrub_to_utf8(six.b("foo")) == six.u("foo")

def test_shuffle():
    l = list(range(3))
    utils.shuffleUp(l)
    assert l != list(range(3))
    utils.shuffleDown(l)
    assert l == list(range(3))
