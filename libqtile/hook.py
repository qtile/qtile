# Copyright (c) 2009-2010 Aldo Cortesi
# Copyright (c) 2010 Lee McCuller
# Copyright (c) 2010 matt
# Copyright (c) 2010, 2014 dequis
# Copyright (c) 2010, 2012, 2014 roger
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2011 Paul Colomiets
# Copyright (c) 2011 Tzbob
# Copyright (c) 2012-2015 Tycho Andersen
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
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

from .log_utils import logger
from . import utils

subscriptions = {}
SKIPLOG = set()
qtile = None


def init(q):
    global qtile
    qtile = q


def clear():
    subscriptions.clear()


class Subscribe(object):
    def __init__(self):
        hooks = set([])
        for i in dir(self):
            if not i.startswith("_"):
                hooks.add(i)
        self.hooks = hooks

    def _subscribe(self, event, func):
        lst = subscriptions.setdefault(event, [])
        if func not in lst:
            lst.append(func)

    def startup_once(self, func):
        """
            Called when Qtile has initialized, exactly once (i.e. not on each
            lazy.restart()).
        """
        return self._subscribe("startup_once", func)

    def startup(self, func):
        """
            Called each time qtile is started (including the first time qtile starts)
        """
        return self._subscribe("startup", func)

    def setgroup(self, func):
        """
            Called when group is changed.
        """
        return self._subscribe("setgroup", func)

    def addgroup(self, func):
        """
            Called when group is added.
        """
        return self._subscribe("addgroup", func)

    def delgroup(self, func):
        """
            Called when group is deleted.
        """
        return self._subscribe("delgroup", func)

    def changegroup(self, func):
        """
            Called whenever a group change occurs.
        """
        return self._subscribe("changegroup", func)

    def focus_change(self, func):
        """
            Called when focus is changed.
        """
        return self._subscribe("focus_change", func)

    def float_change(self, func):
        """
            Called when a change in float state is made
        """
        return self._subscribe("float_change", func)

    def group_window_add(self, func):
        """
            Called when a new window is added to a group.
        """
        return self._subscribe("group_window_add", func)

    def window_name_change(self, func):
        """
            Called whenever a windows name changes.
        """
        return self._subscribe("window_name_change", func)

    def client_new(self, func):
        """
            Called before Qtile starts managing a new client. Use this hook to
            declare windows static, or add them to a group on startup. This
            hook is not called for internal windows.

            - arguments: window.Window object

            Example::

                def func(c):
                    if c.name == "xterm":
                        c.togroup("a")
                    elif c.name == "dzen":
                        c.static(0)

                libqtile.hook.subscribe.client_new(func)
        """
        return self._subscribe("client_new", func)

    def client_managed(self, func):
        """
            Called after Qtile starts managing a new client. That is, after a
            window is assigned to a group, or when a window is made static.
            This hook is not called for internal windows.

            - arguments: window.Window object
        """
        return self._subscribe("client_managed", func)

    def client_killed(self, func):
        """
            Called after a client has been unmanaged.

            - arguments: window.Window object of the killed window.
        """
        return self._subscribe("client_killed", func)

    def client_state_changed(self, func):
        """
            Called whenever client state changes.
        """
        return self._subscribe("client_state_changed", func)

    def client_type_changed(self, func):
        """
            Called whenever window type changes.
        """
        return self._subscribe("client_type_changed", func)

    def client_focus(self, func):
        """
            Called whenver focus changes.

            - arguments: window.Window object of the new focus.
        """
        return self._subscribe("client_focus", func)

    def client_mouse_enter(self, func):
        """
            Called when the mouse enters a client.
        """
        return self._subscribe("client_mouse_enter", func)

    def client_name_updated(self, func):
        """
            Called when the client name changes.
        """
        return self._subscribe("client_name_updated", func)

    def client_urgent_hint_changed(self, func):
        """
            Called when the client urgent hint changes.
        """
        return self._subscribe("client_urgent_hint_changed", func)

    def layout_change(self, func):
        """
            Called on layout change.
        """
        return self._subscribe("layout_change", func)

    def net_wm_icon_change(self, func):
        """
            Called on _NET_WM_ICON chance.
        """
        return self._subscribe("net_wm_icon_change", func)

    def selection_notify(self, func):
        """
            Called on selection notify.
        """
        return self._subscribe("selection_notify", func)

    def selection_change(self, func):
        """
            Called on selection chance.
        """
        return self._subscribe("selection_change", func)

    def screen_change(self, func):
        """
            Called when a screen is added or screen configuration is changed
            (via xrandr). The hook should take two arguments: the root qtile
            object and the ``xproto.randr.ScreenChangeNotify`` event. Common
            usage is simply to call ``qtile.cmd_restart()`` on each event (to
            restart qtile when there is a new monitor):

            Example::

                def restart_on_randr(qtile, ev):
                    qtile.cmd_restart()
        """
        return self._subscribe("screen_change", func)

    def current_screen_change(self, func):
        """
            Called when the current screen (i.e. the screen with focus)
            changes; no arguments.
        """
        return self._subscribe("current_screen_change", func)

subscribe = Subscribe()


class Unsubscribe(Subscribe):
    """
        This class mirrors subscribe, except the _subscribe member has been
        overridden to removed calls from hooks.
    """
    def _subscribe(self, event, func):
        lst = subscriptions.setdefault(event, [])
        try:
            lst.remove(func)
        except ValueError:
            raise utils.QtileError(
                "Tried to unsubscribe a hook that was not"
                " currently subscribed"
            )

unsubscribe = Unsubscribe()


def fire(event, *args, **kwargs):
    if event not in subscribe.hooks:
        raise utils.QtileError("Unknown event: %s" % event)
    if event not in SKIPLOG:
        logger.info("Internal event: %s(%s, %s)", event, args, kwargs)
    for i in subscriptions.get(event, []):
        try:
            i(*args, **kwargs)
        except:
            logger.exception("Error in hook %s", event)
