import os
import shutil
import subprocess
import tempfile
from multiprocessing import Value

import pytest
import xcffib.xproto
import xcffib.xtest

import libqtile.config
from libqtile import hook, layout, utils
from libqtile.backend.x11 import window, xcbq
from libqtile.backend.x11.xcbq import Connection
from test.conftest import dualmonitor
from test.helpers import (
    HEIGHT,
    SECOND_HEIGHT,
    SECOND_WIDTH,
    WIDTH,
    BareConfig,
    assert_window_died,
)
from test.test_images2 import should_skip
from test.test_manager import ManagerConfig

bare_config = pytest.mark.parametrize("xmanager", [BareConfig], indirect=True)
manager_config = pytest.mark.parametrize("xmanager", [ManagerConfig], indirect=True)


@manager_config
def test_kill_via_message(xmanager, conn):
    xmanager.test_window("one")
    window_info = xmanager.c.window.info()
    data = xcffib.xproto.ClientMessageData.synthetic([0, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms["_NET_CLOSE_WINDOW"], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    assert_window_died(xmanager.c, window_info)


@manager_config
def test_change_state_via_message(xmanager, conn):
    xmanager.test_window("one")
    window_info = xmanager.c.window.info()

    data = xcffib.xproto.ClientMessageData.synthetic([window.IconicState, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms["WM_CHANGE_STATE"], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    assert xmanager.c.window.info()["minimized"]

    data = xcffib.xproto.ClientMessageData.synthetic([window.NormalState, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms["WM_CHANGE_STATE"], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    assert not xmanager.c.window.info()["minimized"]


def set_urgent(w):
    w.urgent = True
    hook.fire("client_urgent_hint_changed", w)
    return False


class UrgentConfig(BareConfig):
    focus_on_window_activation = "urgent"


class SmartConfig(BareConfig):
    focus_on_window_activation = "smart"


class FuncConfig(BareConfig):
    # must be a static method here because otherwise it gets turned into a MethodType (we need a FunctionType)
    # this is only an issue in this test and not the real config file
    focus_on_window_activation = staticmethod(set_urgent)


@dualmonitor
def test_urgent_hook_fire(xmanager_nospawn):
    xmanager_nospawn.display = xmanager_nospawn.backend.env["DISPLAY"]
    conn = Connection(xmanager_nospawn.display)

    xmanager_nospawn.hook_fired = Value("i", 0)

    def _hook_test(val):
        xmanager_nospawn.hook_fired.value += 1

    hook.subscribe.client_urgent_hint_changed(_hook_test)

    xmanager_nospawn.start(UrgentConfig)

    xmanager_nospawn.test_window("one")
    window_info = xmanager_nospawn.c.window.info()

    # send activate window message
    data = xcffib.xproto.ClientMessageData.synthetic([0, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms["_NET_ACTIVE_WINDOW"], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()

    xmanager_nospawn.terminate()
    assert xmanager_nospawn.hook_fired.value == 1

    # test that focus_on_window_activation = "smart" also fires the hook
    xmanager_nospawn.start(SmartConfig, no_spawn=True)

    xmanager_nospawn.test_window("one")
    window_info = xmanager_nospawn.c.window.info()
    xmanager_nospawn.c.window.toscreen(1)

    # send activate window message
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms["_NET_ACTIVE_WINDOW"], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    xmanager_nospawn.terminate()

    assert xmanager_nospawn.hook_fired.value == 2

    # test that a custom function also fires the hook
    xmanager_nospawn.start(FuncConfig, no_spawn=True)

    xmanager_nospawn.test_window("one")
    window_info = xmanager_nospawn.c.window.info()
    xmanager_nospawn.c.window.toscreen(1)

    # send activate window message
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms["_NET_ACTIVE_WINDOW"], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()

    xmanager_nospawn.terminate()

    assert xmanager_nospawn.hook_fired.value == 3


@manager_config
def test_default_float_hints(xmanager, conn):
    xmanager.c.next_layout()
    w = None

    def size_hints():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)

        # set the size hints
        hints = [0] * 18
        hints[0] = xcbq.NormalHintsFlags["PMinSize"] | xcbq.NormalHintsFlags["PMaxSize"]
        hints[5] = hints[6] = hints[7] = hints[8] = 10
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.xsync()

    try:
        xmanager.create_window(size_hints)
        assert xmanager.c.window.info()["floating"] is True
    finally:
        w.kill_client()

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
        assert xmanager.c.window.info()["floating"] is True
        info = xmanager.c.window.info()
        assert info["width"] == 10
        assert info["height"] == 10
        xmanager.c.window.toggle_floating()
        assert xmanager.c.window.info()["floating"] is False
        info = xmanager.c.window.info()
        assert info["width"] == 398
        assert info["height"] == 578
        xmanager.c.window.toggle_fullscreen()
        info = xmanager.c.window.info()
        assert info["width"] == 800
        assert info["height"] == 600
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_user_position(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["floating"] is True
        assert xmanager.c.window.info()["x"] == 5
        assert xmanager.c.window.info()["y"] == 5
        assert xmanager.c.window.info()["width"] == 10
        assert xmanager.c.window.info()["height"] == 10
    finally:
        w.kill_client()


def wait_for_focus_events(conn):
    got_take_focus = False
    got_focus_in = False
    while True:
        event = conn.conn.poll_for_event()
        if not event:
            break

        if (
            isinstance(event, xcffib.xproto.ClientMessageEvent)
            and event.type != conn.atoms["WM_TAKE_FOCUS"]
        ):
            got_take_focus = True

        if isinstance(event, xcffib.xproto.FocusInEvent):
            got_focus_in = True
    return got_take_focus, got_focus_in


@manager_config
def test_only_one_focus(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["floating"] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert not got_take_focus
        assert got_focus_in
    finally:
        w.kill_client()


@manager_config
def test_only_wm_protocols_focus(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["floating"] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert got_take_focus
        assert not got_focus_in
    finally:
        w.kill_client()


@manager_config
def test_only_input_hint_focus(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["floating"] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert not got_take_focus
        assert got_focus_in
    finally:
        w.kill_client()


@manager_config
def test_no_focus(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["floating"] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert not got_take_focus
        assert not got_focus_in
    finally:
        w.kill_client()


@manager_config
def test_hints_setting_unsetting(xmanager, conn):
    w = None

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
        assert xmanager.c.window.get_hints()["input"]

        # now try to "update" it, but don't really set an update (i.e. the
        # InputHint bit is 0, so the WM should not derive a new hint from the
        # content of the message at the input hint's offset)
        hints = [0] * 14
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        conn.flush()

        # should still have the hint
        assert xmanager.c.window.get_hints()["input"]

        # now do an update: turn it off
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 0
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        conn.flush()
        assert not xmanager.c.window.get_hints()["input"]

        # turn it back on
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 1
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        conn.flush()
        assert xmanager.c.window.get_hints()["input"]

    finally:
        w.kill_client()


@dualmonitor
@manager_config
def test_strut_handling(xmanager, conn):
    w = []

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
        assert xmanager.c.window.info()["width"] == 798
        assert xmanager.c.window.info()["height"] == 578
        assert xmanager.c.window.info()["x"] == 0
        assert xmanager.c.window.info()["y"] == 0
        bar_id = xmanager.c.bar["bottom"].info()["window"]
        bar = xmanager.c.window[bar_id].info()
        assert bar["height"] == 20
        assert bar["y"] == 580
        xmanager.c.next_screen()
        assert xmanager.c.window.info()["width"] == 638
        assert xmanager.c.window.info()["height"] == 478
        assert xmanager.c.window.info()["x"] == 800
        assert xmanager.c.window.info()["y"] == 0

    xmanager.test_window("one")
    xmanager.c.next_screen()
    xmanager.test_window("two")
    test_initial_state()

    try:
        while xmanager.c.screen.info()["index"] != 0:
            xmanager.c.next_screen()
        xmanager.create_window(has_struts)
        xmanager.c.window.static(None, None, None, None, None)
        assert xmanager.c.window.info()["width"] == 798
        assert xmanager.c.window.info()["height"] == 568
        assert xmanager.c.window.info()["x"] == 0
        assert xmanager.c.window.info()["y"] == 0
        bar_id = xmanager.c.bar["bottom"].info()["window"]
        bar = xmanager.c.window[bar_id].info()
        assert bar["height"] == 20
        assert bar["y"] == 570

        xmanager.c.next_screen()
        xmanager.create_window(with_gaps_bottom)
        xmanager.c.window.static(None, None, None, None, None)
        xmanager.create_window(with_gaps_left)
        xmanager.c.window.static(None, None, None, None, None)
        assert xmanager.c.window.info()["width"] == 618
        assert xmanager.c.window.info()["height"] == 468
        assert xmanager.c.window.info()["x"] == 820
        assert xmanager.c.window.info()["y"] == 0
    finally:
        for win in w:
            win.kill_client()
        conn.conn.flush()

    test_initial_state()


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


@dualmonitor
@pytest.mark.parametrize(
    "xmanager",
    [CursorWarpConfig],
    indirect=True,
)
def test_cursor_warp(xmanager, conn):
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


@dualmonitor
def test_click_focus_screen(xmanager):
    screen1 = (WIDTH // 2, HEIGHT // 2)
    screen2 = (WIDTH + SECOND_WIDTH // 2, SECOND_HEIGHT // 2)
    xmanager.c.eval(f"self.core.warp_pointer{screen1}")
    assert xmanager.c.screen.info()["index"] == 0

    # Warping alone shouldn't change the current screen
    xmanager.c.eval(f"self.core.warp_pointer{screen2}")
    assert xmanager.c.screen.info()["index"] == 0
    # Clicking should
    xmanager.backend.fake_click(*screen2)
    assert xmanager.c.screen.info()["index"] == 1

    xmanager.c.eval(f"self.core.warp_pointer{screen1}")
    assert xmanager.c.screen.info()["index"] == 1
    xmanager.backend.fake_click(*screen1)
    assert xmanager.c.screen.info()["index"] == 0


@bare_config
def test_min_size_hint(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["width"] == 100
        assert xmanager.c.window.info()["height"] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()["width"] == 100
        assert xmanager.c.window.info()["height"] == 100

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()["width"] == 200
        assert xmanager.c.window.info()["height"] == 200
    finally:
        w.kill_client()


@bare_config
def test_min_size_hint_no_flag(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["width"] == 100
        assert xmanager.c.window.info()["height"] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()["width"] == 50
        assert xmanager.c.window.info()["height"] == 50

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()["width"] == 200
        assert xmanager.c.window.info()["height"] == 200
    finally:
        w.kill_client()


@bare_config
def test_max_size_hint(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["width"] == 100
        assert xmanager.c.window.info()["height"] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()["width"] == 50
        assert xmanager.c.window.info()["height"] == 50

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()["width"] == 100
        assert xmanager.c.window.info()["height"] == 100
    finally:
        w.kill_client()


@bare_config
def test_max_size_hint_no_flag(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["width"] == 100
        assert xmanager.c.window.info()["height"] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()["width"] == 50
        assert xmanager.c.window.info()["height"] == 50

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()["width"] == 200
        assert xmanager.c.window.info()["height"] == 200
    finally:
        w.kill_client()


@bare_config
def test_both_size_hints(xmanager, conn):
    w = None

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
        assert xmanager.c.window.info()["width"] == 100
        assert xmanager.c.window.info()["height"] == 100

        xmanager.c.window.set_size_floating(50, 50)
        assert xmanager.c.window.info()["width"] == 100
        assert xmanager.c.window.info()["height"] == 100

        xmanager.c.window.set_size_floating(200, 200)
        assert xmanager.c.window.info()["width"] == 100
        assert xmanager.c.window.info()["height"] == 100
    finally:
        w.kill_client()


@manager_config
def test_inspect_window(xmanager):
    xmanager.test_window("one")
    assert xmanager.c.window.inspect()["wm_class"]


class MultipleBordersConfig(BareConfig):
    layouts = [
        layout.Stack(
            border_focus=["#000000", "#111111", "#222222", "#333333", "#444444"],
            border_width=5,
        )
    ]


@pytest.mark.skipif(should_skip(), reason="recent version of imagemagick not found")
@pytest.mark.parametrize("xmanager", [MultipleBordersConfig], indirect=True)
def test_multiple_borders(xmanager):
    xmanager.test_window("one")
    wid = xmanager.c.window.info()["id"]

    name = os.path.join(tempfile.gettempdir(), "test_multiple_borders.txt")
    cmd = [
        shutil.which("import"),
        "-border",
        "-window",
        str(wid),
        "-crop",
        "5x1+0+4",
        "-depth",
        "8",
        name,
    ]
    subprocess.run(cmd, env={"DISPLAY": xmanager.display})

    with open(name) as f:
        data = f.readlines()
    os.unlink(name)

    # just test that each of the 5 borders is lighter than the last as the screenshot is
    # not pixel-perfect
    avg = -1
    for i in range(5):
        color = utils.rgb(data[i + 1].split()[2])
        next_avg = sum(color) / 3
        assert avg < next_avg
        avg = next_avg


class NetFrameExtentsConfig(BareConfig):
    layouts = [
        layout.Columns(border_width=2, border_on_single=True),
        layout.Columns(border_width=4, border_on_single=True),
    ]
    floating_layout = layout.Floating(border_width=6)


@pytest.mark.parametrize("xmanager", [NetFrameExtentsConfig], indirect=True)
def test_net_frame_extents(xmanager, conn):
    def assert_frame(wid, frame):
        r = conn.conn.core.GetProperty(
            False, wid, conn.atoms["_NET_FRAME_EXTENTS"], conn.atoms["CARDINAL"], 0, (2**32) - 1
        ).reply()
        assert r.value.to_atoms() == frame

    pid = xmanager.test_window("one")
    wid = xmanager.c.window.info()["id"]
    assert_frame(wid, (2, 2, 2, 2))
    xmanager.c.next_layout()
    assert_frame(wid, (4, 4, 4, 4))
    xmanager.c.window.enable_floating()
    assert_frame(wid, (6, 6, 6, 6))
    xmanager.kill_window(pid)


def test_net_wm_state_focused(xmanager, conn):
    atom = conn.atoms["_NET_WM_STATE_FOCUSED"]

    def assert_state_focused(wid, has_state):
        r = conn.conn.core.GetProperty(
            False, wid, conn.atoms["_NET_WM_STATE"], conn.atoms["ATOM"], 0, (2**32) - 1
        ).reply()
        assert (atom in r.value.to_atoms()) == has_state

    one = xmanager.test_window("one")
    wid1 = xmanager.c.window.info()["id"]
    assert_state_focused(wid1, True)

    two = xmanager.test_window("two")
    wid2 = xmanager.c.window.info()["id"]
    assert_state_focused(wid1, False)
    assert_state_focused(wid2, True)
    xmanager.kill_window(two)
    assert_state_focused(wid1, True)
    xmanager.kill_window(one)


@manager_config
def test_window_stacking_order(xmanager):
    """Test basic window stacking controls."""
    conn = xcbq.Connection(xmanager.display)

    def _wnd(name):
        return xmanager.c.window[{w["name"]: w["id"] for w in xmanager.c.windows()}[name]]

    def _clients():
        root = conn.default_screen.root.wid
        q = conn.conn.core.QueryTree(root).reply()
        stack = list(q.children)
        wins = [(w["name"], stack.index(w["id"])) for w in xmanager.c.windows()]
        wins.sort(key=lambda x: x[1])
        return [x[0] for x in wins]

    xmanager.test_window("one")
    xmanager.test_window("two")
    xmanager.test_window("three")
    xmanager.test_window("four")
    xmanager.test_window("five")

    # We're testing 3 "layers"
    # BELOW, 'everything else', ABOVE

    # New windows added on top of each other
    assert _clients() == ["one", "two", "three", "four", "five"]

    # Moving above/below moves above/below next client in the layer
    _wnd("one").move_up()
    assert _clients() == ["two", "one", "three", "four", "five"]
    _wnd("four").move_up()
    assert _clients() == ["two", "one", "three", "five", "four"]
    _wnd("one").move_down()
    assert _clients() == ["one", "two", "three", "five", "four"]

    # Keeping above/below moves client to ABOVE/BELOW layer
    # When moving to ABOVE, client will be placed at top of that layer
    # When moving to BELOW, client will be placed at bottom of layer

    # BELOW: None, ABOVE: two
    _wnd("two").keep_above()
    assert _clients() == ["one", "three", "five", "four", "two"]
    _wnd("five").move_up()
    assert _clients() == ["one", "three", "four", "five", "two"]

    # BELOW: three, ABOVE: two
    _wnd("three").keep_below()
    assert _clients() == ["three", "one", "four", "five", "two"]
    _wnd("four").move_down()
    assert _clients() == ["three", "four", "one", "five", "two"]

    # BELOW: four, three, ABOVE: two
    _wnd("four").keep_below()
    assert _clients() == ["four", "three", "one", "five", "two"]

    # BELOW: four, three, ABOVE: two, one
    _wnd("one").keep_above()
    assert _clients() == ["four", "three", "five", "two", "one"]
    _wnd("five").move_up()
    assert _clients() == ["four", "three", "five", "two", "one"]
    _wnd("five").move_down()
    assert _clients() == ["four", "three", "five", "two", "one"]

    # BELOW: two, four, three, ABOVE: one
    _wnd("two").keep_below()
    assert _clients() == ["two", "four", "three", "five", "one"]

    # BELOW: two, three, ABOVE: one, four
    _wnd("four").keep_above()
    assert _clients() == ["two", "three", "five", "one", "four"]

    # BELOW: two, three, ABOVE: one
    _wnd("four").keep_above()
    assert _clients() == ["two", "three", "five", "four", "one"]
    _wnd("five").move_up()
    assert _clients() == ["two", "three", "four", "five", "one"]

    # BELOW: two, three, ABOVE: None
    _wnd("one").keep_above()
    assert _clients() == ["two", "three", "four", "five", "one"]

    # BELOW: two, ABOVE: None
    _wnd("three").keep_below()
    assert _clients() == ["two", "three", "four", "five", "one"]
    _wnd("one").move_down()
    assert _clients() == ["two", "three", "four", "one", "five"]

    # BELOW: None ABOVE: None
    _wnd("two").keep_below()
    assert _clients() == ["two", "three", "four", "one", "five"]

    # BELOW: three, ABOVE: None
    _wnd("three").keep_below()
    assert _clients() == ["three", "two", "four", "one", "five"]
    _wnd("two").move_down()
    assert _clients() == ["three", "two", "four", "one", "five"]
    _wnd("one").move_down()
    assert _clients() == ["three", "two", "one", "four", "five"]

    _wnd("two").move_to_top()
    assert _clients() == ["three", "one", "four", "five", "two"]

    # three is kept_below so moving to bottom is still above that
    _wnd("five").move_to_bottom()
    assert _clients() == ["three", "five", "one", "four", "two"]

    # three is the only window kept_below so this will have no effect
    _wnd("three").move_to_top()
    assert _clients() == ["three", "five", "one", "four", "two"]

    # Keep three above everything else
    _wnd("three").keep_above()
    assert _clients() == ["five", "one", "four", "two", "three"]

    # This should have no effect as it's the only window kept_above
    _wnd("three").move_to_bottom()
    assert _clients() == ["five", "one", "four", "two", "three"]


@manager_config
def test_floats_kept_above(xmanager):
    """Test config option to pin floats to a higher level."""
    conn = xcbq.Connection(xmanager.display)

    def _wnd(name):
        return xmanager.c.window[{w["name"]: w["id"] for w in xmanager.c.windows()}[name]]

    def _clients():
        root = conn.default_screen.root.wid
        q = conn.conn.core.QueryTree(root).reply()
        stack = list(q.children)
        wins = [(w["name"], stack.index(w["id"])) for w in xmanager.c.windows()]
        wins.sort(key=lambda x: x[1])
        return [x[0] for x in wins]

    xmanager.test_window("one", floating=True)
    xmanager.test_window("two")

    # Confirm floating window is above window that was opened later
    assert _clients() == ["two", "one"]

    # Open a different floating window. This should be above the first floating one.
    xmanager.test_window("three", floating=True)
    assert _clients() == ["two", "one", "three"]


@manager_config
def test_fullscreen_on_top(xmanager):
    """Test fullscreen, focused windows are on top."""
    conn = xcbq.Connection(xmanager.display)

    def _wnd(name):
        return xmanager.c.window[{w["name"]: w["id"] for w in xmanager.c.windows()}[name]]

    def _clients():
        root = conn.default_screen.root.wid
        q = conn.conn.core.QueryTree(root).reply()
        stack = list(q.children)
        wins = [(w["name"], stack.index(w["id"])) for w in xmanager.c.windows()]
        wins.sort(key=lambda x: x[1])
        return [x[0] for x in wins]

    xmanager.test_window("one", floating=True)
    xmanager.test_window("two")

    # window "one" is kept_above, "two" is norm
    assert _clients() == ["two", "one"]

    # A fullscreen, focused window should display above windows that are "kept above"
    _wnd("two").enable_fullscreen()
    _wnd("two").focus()
    assert _clients() == ["one", "two"]

    # Focusing the other window should cause the fullscreen window to drop from the highest layer
    _wnd("one").focus()
    assert _clients() == ["two", "one"]

    # Disabling fullscreen will put the window below the "kept above" window, even if it has focus
    _wnd("two").focus()
    _wnd("two").toggle_fullscreen()
    assert _clients() == ["two", "one"]


class UnpinFloatsConfig(ManagerConfig):
    # New floating windows not set to "keep_above"
    floats_kept_above = False


# Floating windows should be moved above tiled windows when first floated, regardless
# of whether `floats_kept_above` is True
@pytest.mark.parametrize("xmanager", [ManagerConfig, UnpinFloatsConfig], indirect=True)
def test_move_float_above_tiled(xmanager):
    conn = xcbq.Connection(xmanager.display)

    def _wnd(name):
        return xmanager.c.window[{w["name"]: w["id"] for w in xmanager.c.windows()}[name]]

    def _clients():
        root = conn.default_screen.root.wid
        q = conn.conn.core.QueryTree(root).reply()
        stack = list(q.children)
        wins = [(w["name"], stack.index(w["id"])) for w in xmanager.c.windows()]
        wins.sort(key=lambda x: x[1])
        return [x[0] for x in wins]

    xmanager.test_window("one")
    xmanager.test_window("two")
    xmanager.test_window("three")
    assert _clients() == ["one", "two", "three"]

    _wnd("two").toggle_floating()
    assert _clients() == ["one", "three", "two"]


def test_multiple_wm_types(xmanager):
    conn = xcbq.Connection(xmanager.display)
    w = conn.create_window(50, 50, 50, 50)
    normal = conn.atoms["_NET_WM_WINDOW_TYPE_NORMAL"]
    kde_override = conn.atoms["_KDE_NET_WM_WINDOW_TYPE_OVERRIDE"]
    w.set_property("_NET_WM_WINDOW_TYPE", [kde_override, normal])
    assert w.get_wm_type() == "normal"
