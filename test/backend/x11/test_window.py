import pytest
import xcffib.xproto
import xcffib.xtest

import libqtile.config
from libqtile.backend.x11 import window, xcbq
from test.conftest import no_xinerama
from test.helpers import (
    SECOND_HEIGHT,
    SECOND_WIDTH,
    WIDTH,
    BareConfig,
    assert_window_died,
)
from test.test_manager import ManagerConfig

bare_config = pytest.mark.parametrize("xmanager", [BareConfig], indirect=True)
manager_config = pytest.mark.parametrize("xmanager", [ManagerConfig], indirect=True)


@manager_config
@no_xinerama
def test_kill_via_message(xmanager):
    xmanager.test_window("one")
    window_info = xmanager.c.window.info()
    conn = xcbq.Connection(xmanager.display)
    data = xcffib.xproto.ClientMessageData.synthetic([0, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms['_NET_CLOSE_WINDOW'], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    conn.finalize()
    assert_window_died(xmanager.c, window_info)


@manager_config
@no_xinerama
def test_change_state_via_message(xmanager):
    xmanager.test_window("one")
    window_info = xmanager.c.window.info()
    conn = xcbq.Connection(xmanager.display)

    data = xcffib.xproto.ClientMessageData.synthetic([window.IconicState, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms['WM_CHANGE_STATE'], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    assert xmanager.c.window.info()["minimized"]

    data = xcffib.xproto.ClientMessageData.synthetic([window.NormalState, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms['WM_CHANGE_STATE'], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    assert not xmanager.c.window.info()["minimized"]

    conn.finalize()


@manager_config
@no_xinerama
def test_default_float_hints(xmanager):
    xmanager.c.next_layout()
    w = None
    conn = xcbq.Connection(xmanager.display)

    def size_hints():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)

        # set the size hints
        hints = [0] * 18
        hints[0] = xcbq.NormalHintsFlags["PMinSize"] | xcbq.NormalHintsFlags["PMaxSize"]
        hints[5] = hints[6] = hints[7] = hints[8] = 10
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()

    try:
        xmanager.create_window(size_hints)
        assert xmanager.c.window.info()['floating'] is True
    finally:
        w.kill_client()
        conn.finalize()

    w = None
    conn = xcbq.Connection(xmanager.display)

    def size_hints():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)

        # set the aspect hints
        hints = [0] * 18
        hints[0] = xcbq.NormalHintsFlags["PAspect"]
        hints[11] = hints[12] = hints[13] = hints[14] = 1
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()

    try:
        xmanager.create_window(size_hints)
        assert xmanager.c.window.info()['floating'] is True
        info = xmanager.c.window.info()
        assert info['width'] == 10
        assert info['height'] == 10
        xmanager.c.window.toggle_floating()
        assert xmanager.c.window.info()['floating'] is False
        info = xmanager.c.window.info()
        assert info['width'] == 398
        assert info['height'] == 578
        xmanager.c.window.toggle_fullscreen()
        info = xmanager.c.window.info()
        assert info['width'] == 800
        assert info['height'] == 600
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_user_position(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

    def user_position_window():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        # xmanager config automatically floats "float"
        w.set_property("WM_CLASS", "float", type="STRING", format=8)
        # set the user specified position flag
        hints = [0] * 18
        hints[0] = xcbq.NormalHintsFlags["USPosition"]
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()
    try:
        xmanager.create_window(user_position_window)
        assert xmanager.c.window.info()['floating'] is True
        assert xmanager.c.window.info()['x'] == 5
        assert xmanager.c.window.info()['y'] == 5
        assert xmanager.c.window.info()['width'] == 10
        assert xmanager.c.window.info()['height'] == 10
    finally:
        w.kill_client()
        conn.finalize()


def wait_for_focus_events(conn):
    got_take_focus = False
    got_focus_in = False
    while True:
        event = conn.conn.poll_for_event()
        if not event:
            break

        if (isinstance(event, xcffib.xproto.ClientMessageEvent) and
                event.type != conn.atoms["WM_TAKE_FOCUS"]):
            got_take_focus = True

        if isinstance(event, xcffib.xproto.FocusInEvent):
            got_focus_in = True
    return got_take_focus, got_focus_in


@manager_config
def test_only_one_focus(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

    def both_wm_take_focus_and_input_hint():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.set_attribute(eventmask=xcffib.xproto.EventMask.FocusChange)
        # xmanager config automatically floats "float"
        w.set_property("WM_CLASS", "float", type="STRING", format=8)

        # set both the input hit
        hints = [0] * 14
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 1  # set hints to 1, i.e. we want them
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)

        # and add the WM_PROTOCOLS protocol WM_TAKE_FOCUS
        conn.conn.core.ChangePropertyChecked(
            xcffib.xproto.PropMode.Append,
            w.wid,
            conn.atoms["WM_PROTOCOLS"],
            conn.atoms["ATOM"],
            32,
            1,
            [conn.atoms["WM_TAKE_FOCUS"]],
        ).check()

        w.map()
        conn.conn.flush()
    try:
        xmanager.create_window(both_wm_take_focus_and_input_hint)
        assert xmanager.c.window.info()['floating'] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert not got_take_focus
        assert got_focus_in
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_only_wm_protocols_focus(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

    def only_wm_protocols_focus():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.set_attribute(eventmask=xcffib.xproto.EventMask.FocusChange)
        # xmanager config automatically floats "float"
        w.set_property("WM_CLASS", "float", type="STRING", format=8)

        hints = [0] * 14
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 0  # set hints to 0, i.e. we don't want them
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)

        # add the WM_PROTOCOLS protocol WM_TAKE_FOCUS
        conn.conn.core.ChangePropertyChecked(
            xcffib.xproto.PropMode.Append,
            w.wid,
            conn.atoms["WM_PROTOCOLS"],
            conn.atoms["ATOM"],
            32,
            1,
            [conn.atoms["WM_TAKE_FOCUS"]],
        ).check()

        w.map()
        conn.conn.flush()
    try:
        xmanager.create_window(only_wm_protocols_focus)
        assert xmanager.c.window.info()['floating'] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert got_take_focus
        assert not got_focus_in
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_only_input_hint_focus(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

    def only_input_hint():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.set_attribute(eventmask=xcffib.xproto.EventMask.FocusChange)
        # xmanager config automatically floats "float"
        w.set_property("WM_CLASS", "float", type="STRING", format=8)

        # set the input hint
        hints = [0] * 14
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 1  # set hints to 1, i.e. we want them
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)

        w.map()
        conn.conn.flush()
    try:
        xmanager.create_window(only_input_hint)
        assert xmanager.c.window.info()['floating'] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert not got_take_focus
        assert got_focus_in
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_no_focus(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

    def no_focus():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.set_attribute(eventmask=xcffib.xproto.EventMask.FocusChange)
        # xmanager config automatically floats "float"
        w.set_property("WM_CLASS", "float", type="STRING", format=8)

        hints = [0] * 14
        hints[0] = xcbq.HintsFlags["InputHint"]
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        w.map()
        conn.conn.flush()
    try:
        xmanager.create_window(no_focus)
        assert xmanager.c.window.info()['floating'] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert not got_take_focus
        assert not got_focus_in
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_hints_setting_unsetting(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

    def no_input_hint():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.map()
        conn.conn.flush()

    try:
        xmanager.create_window(no_input_hint)
        # We default the input hint to true since some non-trivial number of
        # windows don't set it, and most of them want focus. The spec allows
        # WMs to assume "convenient" values.
        assert xmanager.c.window.hints()['input']

        # now try to "update" it, but don't really set an update (i.e. the
        # InputHint bit is 0, so the WM should not derive a new hint from the
        # content of the message at the input hint's offset)
        hints = [0] * 14
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        conn.flush()

        # should still have the hint
        assert xmanager.c.window.hints()['input']

        # now do an update: turn it off
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 0
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        conn.flush()
        assert not xmanager.c.window.hints()['input']

        # turn it back on
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 1
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        conn.flush()
        assert xmanager.c.window.hints()['input']

    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_strut_handling(xmanager):
    w = []
    conn = xcbq.Connection(xmanager.display)

    def has_struts():
        nonlocal w
        w.append(conn.create_window(0, 0, 10, 10))
        w[-1].set_property("_NET_WM_STRUT_PARTIAL", [0, 0, 0, 10, 0, 0, 0, 0, 0, 0, 0, 800])
        w[-1].map()
        conn.conn.flush()

    def with_gaps_left():
        nonlocal w
        w.append(conn.create_window(800, 0, 10, 10))
        w[-1].set_property("_NET_WM_STRUT_PARTIAL", [820, 0, 0, 0, 0, 480, 0, 0, 0, 0, 0, 0])
        w[-1].map()
        conn.conn.flush()

    def with_gaps_bottom():
        nonlocal w
        w.append(conn.create_window(800, 0, 10, 10))
        w[-1].set_property("_NET_WM_STRUT_PARTIAL", [0, 0, 0, 130, 0, 0, 0, 0, 0, 0, 800, 1440])
        w[-1].map()
        conn.conn.flush()

    def test_initial_state():
        while xmanager.c.screen.info()["index"] != 0:
            xmanager.c.next_screen()
        assert xmanager.c.window.info()['width'] == 798
        assert xmanager.c.window.info()['height'] == 578
        assert xmanager.c.window.info()['x'] == 0
        assert xmanager.c.window.info()['y'] == 0
        bar_id = xmanager.c.bar["bottom"].info()["window"]
        bar = xmanager.c.window[bar_id].info()
        assert bar["height"] == 20
        assert bar["y"] == 580
        xmanager.c.next_screen()
        assert xmanager.c.window.info()['width'] == 638
        assert xmanager.c.window.info()['height'] == 478
        assert xmanager.c.window.info()['x'] == 800
        assert xmanager.c.window.info()['y'] == 0

    xmanager.test_window('one')
    xmanager.c.next_screen()
    xmanager.test_window('two')
    test_initial_state()

    try:
        while xmanager.c.screen.info()["index"] != 0:
            xmanager.c.next_screen()
        xmanager.create_window(has_struts)
        xmanager.c.window.static(None, None, None, None, None)
        assert xmanager.c.window.info()['width'] == 798
        assert xmanager.c.window.info()['height'] == 568
        assert xmanager.c.window.info()['x'] == 0
        assert xmanager.c.window.info()['y'] == 0
        bar_id = xmanager.c.bar["bottom"].info()["window"]
        bar = xmanager.c.window[bar_id].info()
        assert bar["height"] == 20
        assert bar["y"] == 570

        xmanager.c.next_screen()
        xmanager.create_window(with_gaps_bottom)
        xmanager.c.window.static(None, None, None, None, None)
        xmanager.create_window(with_gaps_left)
        xmanager.c.window.static(None, None, None, None, None)
        assert xmanager.c.window.info()['width'] == 618
        assert xmanager.c.window.info()['height'] == 468
        assert xmanager.c.window.info()['x'] == 820
        assert xmanager.c.window.info()['y'] == 0
    finally:
        for win in w:
            win.kill_client()
        conn.finalize()

    test_initial_state()


class BringFrontClickConfig(ManagerConfig):
    bring_front_click = True


class BringFrontClickFloatingOnlyConfig(ManagerConfig):
    bring_front_click = "floating_only"


@pytest.fixture
def bring_front_click(request):
    return request.param


@pytest.mark.parametrize(
    "xmanager, bring_front_click",
    [
        (ManagerConfig, False),
        (BringFrontClickConfig, True),
        (BringFrontClickFloatingOnlyConfig, "floating_only"),
    ],
    indirect=True,
)
def test_bring_front_click(xmanager, bring_front_click):
    def get_all_windows(conn):
        root = conn.default_screen.root.wid
        q = conn.conn.core.QueryTree(root).reply()
        return list(q.children)

    def fake_click(conn, xtest, x, y):
        root = conn.default_screen.root.wid
        xtest.FakeInput(6, 0, xcffib.xproto.Time.CurrentTime, root, x, y, 0)
        xtest.FakeInput(4, 1, xcffib.xproto.Time.CurrentTime, root, 0, 0, 0)
        xtest.FakeInput(5, 1, xcffib.xproto.Time.CurrentTime, root, 0, 0, 0)
        conn.conn.flush()

    conn = xcbq.Connection(xmanager.display)
    xtest = conn.conn(xcffib.xtest.key)

    # this is a tiled window.
    xmanager.test_window("one")
    xmanager.c.sync()

    xmanager.test_window("two")
    xmanager.c.window.set_position_floating(50, 50)
    xmanager.c.window.set_size_floating(50, 50)
    xmanager.c.sync()

    xmanager.test_window("three")
    xmanager.c.window.set_position_floating(150, 50)
    xmanager.c.window.set_size_floating(50, 50)
    xmanager.c.sync()

    wids = [x["id"] for x in xmanager.c.windows()]
    names = [x["name"] for x in xmanager.c.windows()]

    assert names == ["one", "two", "three"]
    wins = get_all_windows(conn)
    assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window two
    fake_click(conn, xtest, 55, 55)
    xmanager.c.sync()
    wins = get_all_windows(conn)
    if bring_front_click:
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window one
    fake_click(conn, xtest, 10, 10)
    xmanager.c.sync()
    wins = get_all_windows(conn)
    if bring_front_click == "floating_only":
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    elif bring_front_click:
        assert wins.index(wids[2]) < wins.index(wids[1]) < wins.index(wids[0])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])


class CursorWarpConfig(ManagerConfig):
    cursor_warp = "floating_only"
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.GroupBox(),
                ],
                20,
            ),
        ),
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.GroupBox(),
                ],
                20,
            ),
        ),
    ]


@pytest.mark.parametrize(
    "xmanager",
    [CursorWarpConfig],
    indirect=True,
)
def test_cursor_warp(xmanager):
    conn = xcbq.Connection(xmanager.display)
    root = conn.default_screen.root.wid

    assert xmanager.c.screen.info()["index"] == 0

    xmanager.test_window("one")
    xmanager.c.window.set_position_floating(50, 50)
    xmanager.c.window.set_size_floating(50, 50)

    xmanager.c.to_screen(1)
    assert xmanager.c.screen.info()["index"] == 1

    p = conn.conn.core.QueryPointer(root).reply()
    # Here pointer should warp to the second screen as there are no windows
    # there.
    assert p.root_x == WIDTH + SECOND_WIDTH // 2
    # Reduce the bar height from the screen height.
    assert p.root_y == (SECOND_HEIGHT - 20) // 2

    xmanager.c.to_screen(0)
    assert xmanager.c.window.info()["name"] == "one"

    p = conn.conn.core.QueryPointer(xmanager.c.window.info()["id"]).reply()

    # Here pointer should warp to the window.
    assert p.win_x == 25
    assert p.win_y == 25
    assert p.same_screen


@bare_config
def test_min_size_hint(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

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
        xmanager.create_window(size_hints)
        xmanager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert xmanager.c.window.info()['width'] == 100
        assert xmanager.c.window.info()['height'] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()['width'] == 100
        assert xmanager.c.window.info()['height'] == 100

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()['width'] == 200
        assert xmanager.c.window.info()['height'] == 200
    finally:
        w.kill_client()
        conn.finalize()


@bare_config
def test_min_size_hint_no_flag(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

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
        xmanager.create_window(size_hints)
        xmanager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert xmanager.c.window.info()['width'] == 100
        assert xmanager.c.window.info()['height'] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()['width'] == 50
        assert xmanager.c.window.info()['height'] == 50

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()['width'] == 200
        assert xmanager.c.window.info()['height'] == 200
    finally:
        w.kill_client()
        conn.finalize()


@bare_config
def test_max_size_hint(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

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
        xmanager.create_window(size_hints)
        xmanager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert xmanager.c.window.info()['width'] == 100
        assert xmanager.c.window.info()['height'] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()['width'] == 50
        assert xmanager.c.window.info()['height'] == 50

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()['width'] == 100
        assert xmanager.c.window.info()['height'] == 100
    finally:
        w.kill_client()
        conn.finalize()


@bare_config
def test_max_size_hint_no_flag(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

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
        xmanager.create_window(size_hints)
        xmanager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert xmanager.c.window.info()['width'] == 100
        assert xmanager.c.window.info()['height'] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()['width'] == 50
        assert xmanager.c.window.info()['height'] == 50

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()['width'] == 200
        assert xmanager.c.window.info()['height'] == 200
    finally:
        w.kill_client()
        conn.finalize()


@bare_config
def test_both_size_hints(xmanager):
    w = None
    conn = xcbq.Connection(xmanager.display)

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
        xmanager.create_window(size_hints)
        xmanager.c.window.enable_floating()
        print(w.get_wm_normal_hints())
        assert xmanager.c.window.info()['width'] == 100
        assert xmanager.c.window.info()['height'] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()['width'] == 100
        assert xmanager.c.window.info()['height'] == 100

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()['width'] == 100
        assert xmanager.c.window.info()['height'] == 100
    finally:
        w.kill_client()
        conn.finalize()
