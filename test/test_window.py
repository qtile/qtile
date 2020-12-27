import pytest

from test.conftest import BareConfig

bare_config = pytest.mark.parametrize("qtile", [BareConfig], indirect=True)


@bare_config
def test_margin(qtile):
    qtile.test_window('one')

    # No margin
    qtile.c.window.place(10, 20, 50, 60, 0, '000000')
    assert qtile.c.window.info()['x'] == 10
    assert qtile.c.window.info()['y'] == 20
    assert qtile.c.window.info()['width'] == 50
    assert qtile.c.window.info()['height'] == 60

    # Margin as int
    qtile.c.window.place(10, 20, 50, 60, 0, '000000', margin=8)
    assert qtile.c.window.info()['x'] == 18
    assert qtile.c.window.info()['y'] == 28
    assert qtile.c.window.info()['width'] == 34
    assert qtile.c.window.info()['height'] == 44

    # Margin as list
    qtile.c.window.place(10, 20, 50, 60, 0, '000000', margin=[2, 4, 8, 10])
    assert qtile.c.window.info()['x'] == 20
    assert qtile.c.window.info()['y'] == 22
    assert qtile.c.window.info()['width'] == 36
    assert qtile.c.window.info()['height'] == 50
