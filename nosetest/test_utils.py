import libqtile.utils as utils


def test_translate_masks():
    assert utils.translateMasks(["shift", "control"])
    assert utils.translateMasks([]) == 0


def test_LRUCache():
    class Foo:
        ran = False

        @utils.LRUCache(2)
        def one(self, x):
            self.ran = True
            return x

    f = Foo()
    assert f.one(1) == 1
    assert f.ran
    f.ran = False
    assert f.one(1) == 1
    assert not f.ran

    f.ran = False
    assert f.one(1) == 1
    assert not f.ran
    assert f.one(2) == 2
    assert f.one(3) == 3
    assert f.ran

    f.ran = False
    assert f.one(1) == 1
    assert f.ran

    assert len(f._cached_one) == 2
    assert len(f._cachelist_one) == 2


def test_rgb():
    assert utils.rgb([255, 255, 0, 0.5]) == (1, 1, 0, 0.5)
    assert utils.rgb([255, 255, 0]) == (1, 1, 0, 1)
    assert utils.rgb("ff0000") == (1, 0, 0, 1)
    assert utils.rgb("ff0000.5") == (1, 0, 0, 0.5)
