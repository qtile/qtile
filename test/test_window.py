import pytest

from test import conftest
from test.conftest import BareConfig

bare_config = pytest.mark.parametrize("manager", [BareConfig], indirect=True)


@bare_config
def test_margin(manager):
    manager.test_window('one')

    # No margin
    manager.c.window.place(10, 20, 50, 60, 0, '000000')
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == 20
    assert manager.c.window.info()['width'] == 50
    assert manager.c.window.info()['height'] == 60

    # Margin as int
    manager.c.window.place(10, 20, 50, 60, 0, '000000', margin=8)
    assert manager.c.window.info()['x'] == 18
    assert manager.c.window.info()['y'] == 28
    assert manager.c.window.info()['width'] == 34
    assert manager.c.window.info()['height'] == 44

    # Margin as list
    manager.c.window.place(10, 20, 50, 60, 0, '000000', margin=[2, 4, 8, 10])
    assert manager.c.window.info()['x'] == 20
    assert manager.c.window.info()['y'] == 22
    assert manager.c.window.info()['width'] == 36
    assert manager.c.window.info()['height'] == 50


@bare_config
def test_transform(manager):
    manager.test_window('one')

    # No margin
    manager.c.window.place(10, 20, 50, 60, 0, '000000')
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == 20
    assert manager.c.window.info()['width'] == 50
    assert manager.c.window.info()['height'] == 60

    manager.c.window.transform(x=10, y=10, w=100, h=100)
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == 10
    assert manager.c.window.info()['width'] == 100
    assert manager.c.window.info()['height'] == 100

    manager.c.window.transform(x=0.0, y=0.0, w=1.0, h=1.0)
    assert manager.c.window.info()['x'] == 0
    assert manager.c.window.info()['y'] == 0
    assert manager.c.window.info()['width'] == conftest.WIDTH
    assert manager.c.window.info()['height'] == conftest.HEIGHT

    # upper quadrant of the screen, with a margin of 10 px.
    manager.c.window.transform(x=0.5, y=0.0, w=0.5, h=0.5, dw=-20, dh=-20, dx=10, dy=10)
    assert manager.c.window.info()['x'] == (conftest.WIDTH / 2) + 10
    assert manager.c.window.info()['y'] == 10
    assert manager.c.window.info()['width'] == (conftest.WIDTH / 2) - 20
    assert manager.c.window.info()['height'] == (conftest.HEIGHT / 2) - 20

    manager.c.window.place(0, 0, 300, 300, 0, '000000')

    # don't change size, move to the bottom left, with a margin of 20 px
    manager.c.window.transform(x=0.0, y=1.0, dx=10, dy=-10, px=0.0, py=1.0)
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == conftest.HEIGHT - 300 - 10
    assert manager.c.window.info()['width'] == 300
    assert manager.c.window.info()['height'] == 300

    manager.c.window.place(100, 100, 300, 300, 0, '000000')

    # Resize the window, by pivoting to the bottom right.
    manager.c.window.transform(dw=10, dh=10, px=1.0, py=1.0)
    assert manager.c.window.info()['x'] == 90
    assert manager.c.window.info()['y'] == 90
    assert manager.c.window.info()['width'] == 310
    assert manager.c.window.info()['height'] == 310
