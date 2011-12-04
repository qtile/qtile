import libqtile.utils as utils

# TODO: more tests are required here. Several of the utilities are untested.


class Foo:
    ran = False

    @utils.LRUCache(2)
    def one(self, x):
        self.ran = True
        return x


def test_translate_masks_one():
    assert utils.translateMasks(["shift", "control"])
    assert utils.translateMasks([]) == 0


def test_lrucache_decorator():
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


def test_lrucache_discard_lru():
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


def test_lrucache_size():
    f = Foo()
    f.one(1)
    f.one(2)
    f.one(3)
    assert len(f._cached_one) == 2
    assert len(f._cachelist_one) == 2


def test_rgb_hex():
    assert utils.rgb("ff00ff") == (1, 0, 1, 1)


def test_rgb_hex_string():
    assert utils.rgb("#00ff00") == (0, 1, 0, 1)


def test_rgb_hex_alpha():
    assert utils.rgb("ff0000.3") == (1, 0, 0, 0.3)


def test_rgb_hex_string_alpha():
    assert utils.rgb("#ff0000.5") == (1, 0, 0, 0.5)


def test_rgb_tuple():
    assert utils.rgb([255, 255, 0]) == (1, 1, 0, 1)


def test_rgb_tuple_alpha():
    assert utils.rgb([255, 255, 0, 0.5]) == (1, 1, 0, 0.5)

# TODO: test scrub to utf8
# TODO: test Data
# TODO: test issequencelike
# TODO: test isstringlike
# TODO: test shuffleUp, shuffleDown
# Probably do not require a whole lot of tests, but at least one for each
# function so that we can refactor with confidence.
