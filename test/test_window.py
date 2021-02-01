import pytest

from libqtile.backend.x11 import xcbq
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
def test_no_size_hint(manager):
    manager.test_window('one')
    manager.c.window.enable_floating()
    assert manager.c.window.info()['width'] == 100
    assert manager.c.window.info()['height'] == 100

    manager.c.window.set_size_floating(50, 50)
    assert manager.c.window.info()['width'] == 50
    assert manager.c.window.info()['height'] == 50

    manager.c.window.set_size_floating(200, 200)
    assert manager.c.window.info()['width'] == 200
    assert manager.c.window.info()['height'] == 200


@bare_config
def test_min_size_hint(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def size_hints():
        nonlocal w
        w = conn.create_window(0, 0, 100, 100)

        # set the size hints
        hints = [0] * 18
        hints[0] = xcbq.NormalHintsFlags["PMinSize"]
        hints[5] = hints[6] = 100
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()

    try:
        manager.create_window(size_hints)
        manager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert manager.c.window.info()['width'] == 100
        assert manager.c.window.info()['height'] == 100

        manager.c.window.set_size_floating(50, 50)
        assert manager.c.window.info()['width'] == 100
        assert manager.c.window.info()['height'] == 100

        manager.c.window.set_size_floating(200, 200)
        assert manager.c.window.info()['width'] == 200
        assert manager.c.window.info()['height'] == 200
    finally:
        w.kill_client()
        conn.finalize()


@bare_config
def test_min_size_hint_no_flag(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def size_hints():
        nonlocal w
        w = conn.create_window(0, 0, 100, 100)

        # set the size hints
        hints = [0] * 18
        hints[5] = hints[6] = 100
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()

    try:
        manager.create_window(size_hints)
        manager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert manager.c.window.info()['width'] == 100
        assert manager.c.window.info()['height'] == 100

        manager.c.window.set_size_floating(50, 50)
        assert manager.c.window.info()['width'] == 50
        assert manager.c.window.info()['height'] == 50

        manager.c.window.set_size_floating(200, 200)
        assert manager.c.window.info()['width'] == 200
        assert manager.c.window.info()['height'] == 200
    finally:
        w.kill_client()
        conn.finalize()


@bare_config
def test_max_size_hint(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def size_hints():
        nonlocal w
        w = conn.create_window(0, 0, 100, 100)

        # set the size hints
        hints = [0] * 18
        hints[0] = xcbq.NormalHintsFlags["PMaxSize"]
        hints[7] = hints[8] = 100
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()

    try:
        manager.create_window(size_hints)
        manager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert manager.c.window.info()['width'] == 100
        assert manager.c.window.info()['height'] == 100

        manager.c.window.set_size_floating(50, 50)
        assert manager.c.window.info()['width'] == 50
        assert manager.c.window.info()['height'] == 50

        manager.c.window.set_size_floating(200, 200)
        assert manager.c.window.info()['width'] == 100
        assert manager.c.window.info()['height'] == 100
    finally:
        w.kill_client()
        conn.finalize()


@bare_config
def test_max_size_hint_no_flag(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def size_hints():
        nonlocal w
        w = conn.create_window(0, 0, 100, 100)

        # set the size hints
        hints = [0] * 18
        hints[7] = hints[8] = 100
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()

    try:
        manager.create_window(size_hints)
        manager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert manager.c.window.info()['width'] == 100
        assert manager.c.window.info()['height'] == 100

        manager.c.window.set_size_floating(50, 50)
        assert manager.c.window.info()['width'] == 50
        assert manager.c.window.info()['height'] == 50

        manager.c.window.set_size_floating(200, 200)
        assert manager.c.window.info()['width'] == 200
        assert manager.c.window.info()['height'] == 200
    finally:
        w.kill_client()
        conn.finalize()


@bare_config
def test_both_size_hints(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def size_hints():
        nonlocal w
        w = conn.create_window(0, 0, 100, 100)

        # set the size hints
        hints = [0] * 18
        hints[0] = xcbq.NormalHintsFlags["PMinSize"] | xcbq.NormalHintsFlags["PMaxSize"]
        hints[5] = hints[6] = hints[7] = hints[8] = 100
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()

    try:
        manager.create_window(size_hints)
        manager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert manager.c.window.info()['width'] == 100
        assert manager.c.window.info()['height'] == 100

        manager.c.window.set_size_floating(50, 50)
        assert manager.c.window.info()['width'] == 100
        assert manager.c.window.info()['height'] == 100

        manager.c.window.set_size_floating(200, 200)
        assert manager.c.window.info()['width'] == 100
        assert manager.c.window.info()['height'] == 100
    finally:
        w.kill_client()
        conn.finalize()
