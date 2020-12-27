import pytest

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
